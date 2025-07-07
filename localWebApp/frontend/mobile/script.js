// This script runs when the HTML page has finished loading
document.addEventListener('DOMContentLoaded', () => {

    // --- STATE MANAGEMENT (Client-side) ---
    const state = {
        gridDim: 0,
        starsPerRegion: 0,
        regionGrid: [],
        playerGrid: [],
        sourcePuzzleData: {},
        history: {
            mark: { stack: [], pointer: -1 },
            draw: { stack: [], pointer: -1 },
            border: { stack: [], pointer: -1 }
        },
        markIsX: true,
        isLoading: true,
        solution: null,
        isViewingSolution: false,
        activeMode: 'mark',
        // State for interaction
        isLeftDown: false,
        isDragging: false, 
        lastPos: null,
        currentDragChanges: [], // Batch changes for a single drag-undo
        isDrawing: false, // Flag for requestAnimationFrame
        // Drawing and border state
        currentBorderPath: new Set(),
        customBorders: [],
        colorToReplace: null,
        currentColorIndex: 0,
        brushSize: 5,
        isBwMode: true,
		highlightErrors: true,
        autoXAroundStars: false,
        autoXOnMaxLines: false,
        autoXOnMaxRegions: false,
        bufferCanvas: document.createElement('canvas'),
        bufferCtx: null,
        puzzleDefs: [
            { text: "5x5 (1-star, Easy)", dim: 5, stars: 1 },
            { text: "6x6 (1-star, Easy)", dim: 6, stars: 1 },
            { text: "6x6 (1-star, Medium)", dim: 6, stars: 1 },
            { text: "8x8 (1-star, Medium)", dim: 8, stars: 1 },
            { text: "8x8 (1-star, Hard)", dim: 8, stars: 1 },
            { text: "10x10 (2-star, Medium)", dim: 10, stars: 2 },
            { text: "10x10 (2-star, Hard)", dim: 10, stars: 2 },
            { text: "14x14 (3-star, Medium)", dim: 14, stars: 3 },
            { text: "14x14 (3-star, Hard)", dim: 14, stars: 3 },
            { text: "17x17 (4-star, Hard)", dim: 17, stars: 4 },
            { text: "21x21 (5-star, Hard)", dim: 21, stars: 5 },
            { text: "25x25 (6-star, Hard)", dim: 25, stars: 6 },
        ]
    };
    const API_BASE_URL = 'https://StarBattle.pythonanywhere.com/api';
    const LOCAL_STORAGE_KEY = 'starBattleSaves';

    // --- DOM ELEMENT REFERENCES ---
	const homeScreen = document.getElementById('home-screen');
    const gameScreen = document.getElementById('game-screen');
    const backToHomeBtn = document.getElementById('back-to-home-btn');
    const toolbarTabBtns = document.querySelectorAll('.toolbar-tab-btn');
    const toolbarTabContents = document.querySelectorAll('.toolbar-tab-content');
    const contextualControls = document.getElementById('contextual-controls');
	const highlightErrorsToggle = document.getElementById('highlight-errors-toggle');
    const gridContainer = document.getElementById('grid-container');
    const sizeSelect = document.getElementById('size-select');
    const solverStatus = document.getElementById('solver-status');
    const newPuzzleBtn = document.getElementById('new-puzzle-btn');
    const savePuzzleBtn = document.getElementById('save-puzzle-btn');
    const loadPuzzleBtn = document.getElementById('load-puzzle-btn');
    const checkSolutionBtn = document.getElementById('check-solution-btn');
    const findSolutionBtn = document.getElementById('find-solution-btn');
    const importBtn = document.getElementById('import-btn');
    const exportBtn = document.getElementById('export-btn');
    const clearBtn = document.getElementById('clear-btn');
    const toggleMarkBtn = document.getElementById('toggle-mark-btn');
    const undoBtn = document.getElementById('undo-btn');
    const redoBtn = document.getElementById('redo-btn');
    const loadingSpinner = document.getElementById('loading-spinner');
    const markModeBtn = document.getElementById('mark-mode-btn');
    const drawModeBtn = document.getElementById('draw-mode-btn');
    const borderModeBtn = document.getElementById('border-mode-btn');
    const drawCanvas = document.getElementById('draw-canvas');
    const drawCtx = drawCanvas.getContext('2d');
    const brushSizeSlider = document.getElementById('brush-size-slider');
    const brushSizeValue = document.getElementById('brush-size-value');
    const brushSizeWrapper = document.getElementById('brush-size-wrapper');
    const colorPickerWrapper = document.getElementById('color-picker-wrapper');
	const settingsBtn = document.getElementById('settings-btn');
	const settingsModal = document.getElementById('settings-modal');
	const settingsModalCloseBtn = document.getElementById('settings-modal-close-btn');
	const bwModeToggle = document.getElementById('bw-mode-toggle');
	const autoXAroundToggle = document.getElementById('auto-x-around-toggle');
	const autoXMaxLinesToggle = document.getElementById('auto-x-max-lines-toggle');
	const autoXMaxRegionsToggle = document.getElementById('auto-x-max-regions-toggle');
    const loadModal = document.getElementById('load-modal');
    const modalContent = document.getElementById('modal-content');
    const modalCloseBtn = document.getElementById('modal-close-btn');
    // MODIFIED: Removed old color container references
    const htmlColorPicker = document.getElementById('html-color-picker');
    const customColorBtn = document.getElementById('custom-color-btn');
    const hamburgerMenuBtn = document.getElementById('hamburger-menu-btn');
    const puzzleActionsTab = document.getElementById('puzzle-actions-tab');


    // --- SVG ICONS ---
    const STAR_SVG = `<svg class="w-full h-full p-1 star-svg" viewBox="0 0 24 24" fill="currentColor"><path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/></svg>`;
    const DOT_SVG = `<svg class="w-full h-full p-[30%] dot-svg" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="10"/></svg>`;
    const X_SVG = `<svg class="w-full h-full p-[20%] x-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M18 6L6 18M6 6l12 12"/></svg>`;

    // --- Color State ---
    const PRESET_COLORS = ['#EF4444', '#22C55E', '#3B82F6'];
    state.customColors = Array(1).fill(null);
    state.currentColor = PRESET_COLORS[0];
    let preActionState = null;

    // --- SCREEN MANAGEMENT ---
    function showScreen(screenName) {
        homeScreen.classList.toggle('hidden', screenName !== 'home');
        gameScreen.classList.toggle('hidden', screenName !== 'game');
        if (screenName === 'game') {
            setTimeout(resizeCanvas, 50);
        }
    }
    function showHomeScreen() {
        if(confirm("Are you sure you want to exit to the main menu? Your current progress will be lost unless saved.")) {
            showScreen('home');
        }
    }

    // --- RENDERING & DRAWING ---
    function renderGrid() {
		gridContainer.innerHTML = '';
		if (!state.gridDim || !state.regionGrid || state.regionGrid.length === 0) return;
		gridContainer.classList.toggle('bw-mode', state.isBwMode);
		gridContainer.style.gridTemplateColumns = `repeat(${state.gridDim}, 1fr)`;
		gridContainer.style.gridTemplateRows = `repeat(${state.gridDim}, 1fr)`;
		gridContainer.style.setProperty('--grid-dim', state.gridDim);
		for (let r = 0; r < state.gridDim; r++) {
			for (let c = 0; c < state.gridDim; c++) {
				const cell = document.createElement('div');
				cell.classList.add('grid-cell');
				cell.dataset.r = r; cell.dataset.c = c;
				if (!state.isBwMode) {
					const regionId = state.regionGrid[r][c];
					const hue = (regionId * 67) % 360; const isSaturated = regionId % 2 === 1;
					const sat = isSaturated ? 65 : 100; const light = isSaturated ? 77 : 90;
					cell.style.backgroundColor = `hsl(${hue}, ${sat}%, ${light}%)`;
				}
				if (c > 0 && state.regionGrid[r][c - 1] !== state.regionGrid[r][c]) cell.classList.add('region-border-l');
				if (c < state.gridDim - 1 && state.regionGrid[r][c + 1] !== state.regionGrid[r][c]) cell.classList.add('region-border-r');
				if (r > 0 && state.regionGrid[r - 1][c] !== state.regionGrid[r][c]) cell.classList.add('region-border-t');
				if (r < state.gridDim - 1 && state.regionGrid[r + 1][c] !== state.regionGrid[r][c]) cell.classList.add('region-border-b');
				updateCellMark(cell, state.playerGrid[r][c]);
				gridContainer.appendChild(cell);
			}
		}
		resizeCanvas();
		redrawAllOverlays();
	}
    function updateCellMark(cellElement, markState) {
        if (!cellElement) return;
        switch (markState) {
            case 1: cellElement.innerHTML = STAR_SVG; break;
            case 2: cellElement.innerHTML = state.markIsX ? X_SVG : DOT_SVG; break;
            default: cellElement.innerHTML = ''; break;
        }
    }
    function renderAllMarks() {
        for (let r = 0; r < state.gridDim; r++) {
            for (let c = 0; c < state.gridDim; c++) {
                const cell = gridContainer.querySelector(`[data-r='${r}'][data-c='${c}']`);
                updateCellMark(cell, state.playerGrid[r][c]);
            }
        }
    }
    function updateErrorHighlightingUI() {
		const invalidStarCoords = new Set();
		for (let r = 0; r < state.gridDim; r++) {
			for (let c = 0; c < state.gridDim; c++) {
				const cell = gridContainer.querySelector(`[data-r='${r}'][data-c='${c}']`);
				if (cell) cell.classList.remove('error-star');
			}
		}
		if (!state.highlightErrors || state.gridDim === 0) return;
		const stars = [];
		const rowCounts = Array(state.gridDim).fill(0);
		const colCounts = Array(state.gridDim).fill(0);
		const regionStars = {};
		for (let r = 0; r < state.gridDim; r++) {
			for (let c = 0; c < state.gridDim; c++) {
				if (state.playerGrid[r][c] === 1) {
					const starPos = { r, c };
					stars.push(starPos);
					rowCounts[r]++;
					colCounts[c]++;
					const regionId = state.regionGrid[r][c];
					if (!regionStars[regionId]) regionStars[regionId] = [];
					regionStars[regionId].push(starPos);
				}
			}
		}
		stars.forEach(star => {
			for (let dr = -1; dr <= 1; dr++) {
				for (let dc = -1; dc <= 1; dc++) {
					if (dr === 0 && dc === 0) continue;
					const nr = star.r + dr;
					const nc = star.c + dc;
					if (nr >= 0 && nr < state.gridDim && nc >= 0 && nc < state.gridDim && state.playerGrid[nr][nc] === 1) {
						invalidStarCoords.add(`${star.r},${star.c}`);
					}
				}
			}
		});
		for (let r = 0; r < state.gridDim; r++) {
			if (rowCounts[r] > state.starsPerRegion) {
				stars.forEach(star => {
					if (star.r === r) invalidStarCoords.add(`${star.r},${star.c}`);
				});
			}
		}
		for (let c = 0; c < state.gridDim; c++) {
			if (colCounts[c] > state.starsPerRegion) {
				stars.forEach(star => {
					if (star.c === c) invalidStarCoords.add(`${star.r},${star.c}`);
				});
			}
		}
		for (const regionId in regionStars) {
			if (regionStars[regionId].length > state.starsPerRegion) {
				regionStars[regionId].forEach(star => {
					invalidStarCoords.add(`${star.r},${star.c}`);
				});
			}
		}
		invalidStarCoords.forEach(coord => {
			const [r, c] = coord.split(',');
			const cellElement = gridContainer.querySelector(`[data-r='${r}'][data-c='${c}']`);
			if (cellElement) cellElement.classList.add('error-star');
		});
	}
    function resizeCanvas() {
        const tempCanvas = document.createElement('canvas');
        const tempCtx = tempCanvas.getContext('2d');
        const oldWidth = state.bufferCanvas.width;
        const oldHeight = state.bufferCanvas.height;

        if (oldWidth > 0 && oldHeight > 0) {
            tempCanvas.width = oldWidth;
            tempCanvas.height = oldHeight;
            tempCtx.drawImage(state.bufferCanvas, 0, 0);
        }

        const rect = gridContainer.getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0) {
            drawCanvas.width = rect.width;
            drawCanvas.height = rect.height;
            state.bufferCanvas.width = rect.width;
            state.bufferCanvas.height = rect.height;
            state.bufferCtx = state.bufferCanvas.getContext('2d');

            if (tempCanvas.width > 0) {
                state.bufferCtx.drawImage(tempCanvas, 0, 0, state.bufferCanvas.width, state.bufferCanvas.height);
            }
        }
        
        redrawAllOverlays();
    }
    function drawSolutionOverlay() {
        if (!state.solution) return;
        const cellWidth = drawCanvas.width / state.gridDim;
        const cellHeight = drawCanvas.height / state.gridDim;
        
        drawCtx.fillStyle = 'rgba(252, 211, 77, 0.7)';
        drawCtx.shadowColor = 'rgba(0, 0, 0, .7)';
        drawCtx.shadowBlur = 15;

        for (let r = 0; r < state.gridDim; r++) {
            for (let c = 0; c < state.gridDim; c++) {
                if (state.solution[r][c] === 1) {
                    const x = c * cellWidth + cellWidth / 2;
                    const y = r * cellHeight + cellHeight / 2;
                    const radius = cellWidth / 3.5;
                    
                    drawCtx.beginPath();
                    drawCtx.arc(x, y, radius, 0, 2 * Math.PI);
                    drawCtx.fill();
                }
            }
        }
        
        drawCtx.shadowBlur = 0;
    }
    function redrawAllOverlays() {
        if (!drawCanvas.width || !drawCanvas.height) return;
        drawCtx.clearRect(0, 0, drawCanvas.width, drawCanvas.height);
        if (state.bufferCtx) {
            drawCtx.drawImage(state.bufferCanvas, 0, 0);
        }
        drawCustomBorders();
        if (state.isViewingSolution) {
            drawSolutionOverlay();
        }
    }
    function drawCustomBorders() {
        if (!state.gridDim || state.gridDim === 0 || !drawCanvas.width) return;
        const cellWidth = drawCanvas.width / state.gridDim;
        const cellHeight = drawCanvas.height / state.gridDim;
        const thickness = 8;
        const allBorders = [...state.customBorders];
        if (state.currentBorderPath.size > 0) {
            allBorders.push({ path: state.currentBorderPath, color: state.currentColor });
        }
        allBorders.forEach(border => {
            drawCtx.fillStyle = border.color;
            border.path.forEach(cellPos => {
                const [r, c] = cellPos.split(',').map(Number);
                const x = c * cellWidth;
                const y = r * cellHeight;
                if (!border.path.has(`${r - 1},${c}`)) drawCtx.fillRect(x, y, cellWidth, thickness);
                if (!border.path.has(`${r + 1},${c}`)) drawCtx.fillRect(x, y + cellHeight - thickness, cellWidth, thickness);
                if (!border.path.has(`${r},${c - 1}`)) drawCtx.fillRect(x, y, thickness, cellHeight);
                if (!border.path.has(`${r},${c + 1}`)) drawCtx.fillRect(x + cellWidth - thickness, y, thickness, cellHeight);
            });
        });
    }

    // --- History and Marking Logic ---
    function placeStarAndAutoX(r, c) {
        const fromState = state.playerGrid[r][c];
        if (fromState === 1) return; 

        const changes = [];
        const tempGrid = JSON.parse(JSON.stringify(state.playerGrid));

        const addChange = (row, col, newMark) => {
            if (row >= 0 && row < state.gridDim && col >= 0 && col < state.gridDim) {
                const oldMark = tempGrid[row][col];
                if (oldMark === 0 && oldMark !== newMark) { 
                    changes.push({ r: row, c: col, from: oldMark, to: newMark });
                    tempGrid[row][col] = newMark;
                }
            }
        };

        changes.push({ r, c, from: fromState, to: 1 });
        tempGrid[r][c] = 1;

        if (state.autoXAroundStars) {
            for (let dr = -1; dr <= 1; dr++) {
                for (let dc = -1; dc <= 1; dc++) {
                    if (dr === 0 && dc === 0) continue;
                    addChange(r + dr, c + dc, 2);
                }
            }
        }
        
        const starPositions = [];
		for(let ri=0; ri<state.gridDim; ri++) {
			for(let ci=0; ci<state.gridDim; ci++) {
				if(tempGrid[ri][ci] === 1) starPositions.push({r: ri, c: ci});
			}
		}

		starPositions.forEach(starPos => {
			if (state.autoXOnMaxLines) {
				let rowStarCount = 0;
				for(let i=0; i<state.gridDim; i++) if(tempGrid[starPos.r][i] === 1) rowStarCount++;
				if (rowStarCount === state.starsPerRegion) {
					for (let i = 0; i < state.gridDim; i++) addChange(starPos.r, i, 2);
				}
				let colStarCount = 0;
				for(let i=0; i<state.gridDim; i++) if(tempGrid[i][starPos.c] === 1) colStarCount++;
				if (colStarCount === state.starsPerRegion) {
					for (let i = 0; i < state.gridDim; i++) addChange(i, starPos.c, 2);
				}
			}
			if (state.autoXOnMaxRegions) {
				const regionId = state.regionGrid[starPos.r][starPos.c];
				let regionStarCount = 0;
				const regionCells = [];
				for (let ri = 0; ri < state.gridDim; ri++) {
					for (let ci = 0; ci < state.gridDim; ci++) {
						if (state.regionGrid[ri][ci] === regionId) {
							regionCells.push({r: ri, c: ci});
							if(tempGrid[ri][ci] === 1) regionStarCount++;
						}
					}
				}
				if(regionStarCount === state.starsPerRegion) {
					regionCells.forEach(cell => addChange(cell.r, cell.c, 2));
				}
			}
		});
		
		const finalChanges = [];
		const seen = new Set();
		for (let i = changes.length - 1; i >= 0; i--) {
			const change = changes[i];
			const key = `${change.r},${change.c}`;
			if (!seen.has(key)) {
				seen.add(key);
				finalChanges.unshift(change);
			}
		}

        if (finalChanges.length > 0) {
            finalChanges.forEach(c => applyMarkChange(c.r, c.c, state.playerGrid[c.r][c.c], c.to));
            pushHistory({ type: 'compoundMark', changes: finalChanges });
            updateErrorHighlightingUI();
        }
    }

    function removeStarAndUndoAutoX(r, c) {
        if (state.playerGrid[r][c] !== 1) return;

        let starPlacingAction = null;
        for (let i = state.history.mark.pointer; i >= 0; i--) {
            const action = state.history.mark.stack[i];
            if (action.type === 'compoundMark' && action.changes.some(change => change.r === r && change.c === c && change.to === 1)) {
                starPlacingAction = action;
                break;
            }
            if (action.type === 'mark' && action.r === r && action.c === c && action.to === 1) {
                starPlacingAction = { type: 'compoundMark', changes: [action] };
                break;
            }
        }

        if (starPlacingAction) {
            const removalChanges = [];
            starPlacingAction.changes.forEach(originalChange => {
                if (state.playerGrid[originalChange.r][originalChange.c] === originalChange.to) {
                    let revertToState = originalChange.from;
                    if (originalChange.r === r && originalChange.c === c) {
                        revertToState = 0;
                    }
                    applyMarkChange(originalChange.r, originalChange.c, originalChange.to, revertToState);
                    removalChanges.push({ r: originalChange.r, c: originalChange.c, from: originalChange.to, to: revertToState });
                }
            });
            
            if (removalChanges.length > 0) {
                pushHistory({ type: 'compoundMark', changes: removalChanges });
            }
        } else {
            const change = { r, c, from: 1, to: 0 };
            if (applyMarkChange(r, c, 1, 0)) {
                pushHistory({ type: 'compoundMark', changes: [change] });
            }
        }
        updateErrorHighlightingUI();
    }

    // MODIFIED: This function now populates a single container
    function renderColorPicker() {
        const colorSlotsContainer = document.getElementById('color-slots-container');
        if (!colorSlotsContainer) return;

        let allSlotsHTML = '';

        // Add preset colors
        allSlotsHTML += PRESET_COLORS.map(color =>
            `<div class="color-slot" data-color="${color}" style="background-color: ${color};"></div>`
        ).join('');

        // Add custom colors
        allSlotsHTML += state.customColors.map((color, index) => {
            if (color) {
                return `<div class="color-slot" data-color="${color}" style="background-color: ${color};"></div>`;
            } else {
                return `<div class="color-slot empty" data-custom-index="${index}"></div>`;
            }
        }).join('');

        colorSlotsContainer.innerHTML = allSlotsHTML;

        // Update selection highlight on all slots
        document.querySelectorAll('#color-picker-wrapper .color-slot').forEach(slot => {
            slot.classList.toggle('selected', slot.dataset.color === state.currentColor);
        });
    }

    function selectColor(newColor) {
        state.currentColor = newColor;
        htmlColorPicker.value = newColor;
        renderColorPicker();
    }
    function saveCustomColor(newColor) {
        const replaceIndex = state.colorToReplace ? state.customColors.indexOf(state.colorToReplace) : -1;
        if (replaceIndex !== -1) {
            const oldColor = state.customColors[replaceIndex];
            state.customColors[replaceIndex] = newColor;
            state.customBorders.forEach(border => {
                if (border.color === oldColor) {
                    border.color = newColor;
                }
            });
            redrawAllOverlays();
        } else {
            const emptyIndex = state.customColors.findIndex(c => c === null);
            if (emptyIndex !== -1) {
                state.customColors[emptyIndex] = newColor;
            } else {
                state.customColors.shift();
                state.customColors.push(newColor);
            }
        }
        state.colorToReplace = null;
        selectColor(newColor);
    }

    // --- History Management ---
    function deepCopyBorders(borders) {
        return borders.map(border => ({
            color: border.color,
            path: new Set(border.path)
        }));
    }
    function pushHistory(change) {
        const modeHistory = state.history[state.activeMode];
        if (!modeHistory) return;
        if (modeHistory.pointer < modeHistory.stack.length - 1) {
            modeHistory.stack = modeHistory.stack.slice(0, modeHistory.pointer + 1);
        }
        modeHistory.stack.push(change);
        modeHistory.pointer++;
        updateUndoRedoButtons();
    }
    function applyMarkChange(r, c, fromState, toState) {
        if (r < 0 || r >= state.gridDim || c < 0 || c >= state.gridDim) return false;
        state.playerGrid[r][c] = toState;
        const cell = gridContainer.querySelector(`[data-r='${r}'][data-c='${c}']`);
        updateCellMark(cell, toState);
        return true;
    }

	function undo() {
		const modeHistory = state.history[state.activeMode];
		if (!modeHistory || modeHistory.pointer < 0) return;
		const change = modeHistory.stack[modeHistory.pointer];

		switch (change.type) {
			case 'mark':
				applyMarkChange(change.r, change.c, change.to, change.from);
                updateErrorHighlightingUI();
				break;
			case 'compoundMark': 
				[...change.changes].reverse().forEach(c => {
					applyMarkChange(c.r, c.c, c.to, c.from);
				});
                updateErrorHighlightingUI();
				break;
			case 'draw':
				state.bufferCtx.putImageData(change.before, 0, 0);
				redrawAllOverlays();
				break;
			case 'addBorder':
				state.customBorders.pop();
				redrawAllOverlays();
				break;
			case 'removeCellFromBorder':
				state.customBorders[change.borderIndex].path.add(change.cell);
				redrawAllOverlays();
				break;
			case 'clearMarks':
				state.playerGrid = change.before;
				renderAllMarks();
                updateErrorHighlightingUI();
				break;
			case 'clearDraw':
				state.bufferCtx.putImageData(change.before, 0, 0);
				redrawAllOverlays();
				break;
			case 'clearBorder':
				state.customBorders = deepCopyBorders(change.before);
				redrawAllOverlays();
				break;
		}
		modeHistory.pointer--;
		updateUndoRedoButtons();
    }
    
	function redo() {
		const modeHistory = state.history[state.activeMode];
		if (!modeHistory || modeHistory.pointer >= modeHistory.stack.length - 1) return;
		modeHistory.pointer++;
		const change = modeHistory.stack[modeHistory.pointer];

		switch (change.type) {
             case 'mark':
                applyMarkChange(change.r, change.c, change.from, change.to);
                updateErrorHighlightingUI();
                break;
			 case 'compoundMark':
				change.changes.forEach(c => {
					applyMarkChange(c.r, c.c, c.from, c.to);
				});
                updateErrorHighlightingUI();
				break;
			case 'draw':
				state.bufferCtx.putImageData(change.after, 0, 0);
				redrawAllOverlays();
				break;
			case 'addBorder':
				state.customBorders.push(change.border);
				redrawAllOverlays();
				break;
			case 'removeCellFromBorder':
				state.customBorders[change.borderIndex].path.delete(change.cell);
				redrawAllOverlays();
				break;
			case 'clearMarks':
				_internalClearMarks();
				renderAllMarks();
                updateErrorHighlightingUI();
				break;
			case 'clearDraw':
				if (state.bufferCtx) {
					state.bufferCtx.clearRect(0, 0, state.bufferCanvas.width, state.bufferCanvas.height);
				}
				redrawAllOverlays();
				break;
			case 'clearBorder':
				state.customBorders = [];
				redrawAllOverlays();
				break;
		}
		updateUndoRedoButtons();
	}

    function updateUndoRedoButtons() {
        const modeHistory = state.history[state.activeMode];
        if (!modeHistory) {
            undoBtn.disabled = true;
            redoBtn.disabled = true;
            return;
        }
        undoBtn.disabled = modeHistory.pointer < 0;
        redoBtn.disabled = modeHistory.pointer >= modeHistory.stack.length - 1;
    }
    function _internalClearMarks() {
         if (state.gridDim > 0) {
            state.playerGrid = Array(state.gridDim).fill(0).map(() => Array(state.gridDim).fill(0));
        }
    }
    function clearPuzzleState() {
        _internalClearMarks();
        state.customBorders = [];
        if (state.bufferCtx) {
            state.bufferCtx.clearRect(0, 0, state.bufferCanvas.width, state.bufferCanvas.height);
        }
        redrawAllOverlays();
        state.history = {
            mark: { stack: [], pointer: -1 },
            draw: { stack: [], pointer: -1 },
            border: { stack: [], pointer: -1 }
        };
        renderAllMarks();
        updateErrorHighlightingUI();
        updateUndoRedoButtons();
    }

    // --- MOUSE/TOUCH INPUT HANDLING ---
    function getEventPos(e) {
        const rect = gridContainer.getBoundingClientRect();
        const event = e.touches ? e.touches[0] : e;
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;

        const onGrid = x >= 0 && x < rect.width && y >= 0 && y < rect.height;
        if (!onGrid) return { onGrid: false };

        const col = Math.floor(x / (rect.width / state.gridDim));
        const row = Math.floor(y / (rect.height / state.gridDim));

        return { x, y, row, col, onGrid };
    }

    function handleInteractionStart(e) {
        const pos = getEventPos(e);
        if (!pos.onGrid) return;
        e.preventDefault();

        state.isLeftDown = true;
        state.isDragging = false; 
        state.lastPos = pos;
        state.currentDragChanges = []; 

        if (state.activeMode === 'draw') {
            preActionState = state.bufferCtx.getImageData(0, 0, state.bufferCanvas.width, state.bufferCanvas.height);
            const painter = (ctx) => {
                ctx.globalCompositeOperation = 'source-over';
                ctx.lineCap = 'round';
                ctx.lineJoin = 'round';
                ctx.strokeStyle = state.currentColor;
                ctx.lineWidth = state.brushSize;
                ctx.beginPath();
                ctx.moveTo(pos.x, pos.y);
            };
            painter(drawCtx);
            if (state.bufferCtx) painter(state.bufferCtx);
        } else if (state.activeMode === 'border') {
            state.currentBorderPath = new Set([`${pos.row},${pos.col}`]);
            redrawAllOverlays();
        }
    }

    function handleInteractionMove(e) {
        if (!state.isLeftDown) return;
    
        if (state.isDrawing) return;
    
        state.isDrawing = true;
        window.requestAnimationFrame(() => {
            const pos = getEventPos(e);
            if (!pos.onGrid) {
                handleInteractionEnd(e);
                state.isDrawing = false;
                return;
            }
            
            if (state.lastPos && pos.row === state.lastPos.row && pos.col === state.lastPos.col && state.activeMode !== 'draw') {
                 state.isDrawing = false;
                 return;
            }
    
            state.isDragging = true;
    
            if (state.activeMode === 'mark') {
                if (state.currentDragChanges.length === 0 && state.lastPos) {
                    const { row, col } = state.lastPos;
                    const fromState = state.playerGrid[row][col];
                    if (fromState === 0) {
                        if (applyMarkChange(row, col, state.playerGrid[row][col], 2)) {
                            state.currentDragChanges.push({ r: row, c: col, from: 0, to: 2 });
                        }
                    }
                }
    
                const { row, col } = pos;
                const fromState = state.playerGrid[row][col];
                if (fromState === 0) {
                    if (applyMarkChange(row, col, state.playerGrid[row][col], 2)) {
                        state.currentDragChanges.push({ r: row, c: col, from: 0, to: 2 });
                    }
                }
            } else if (state.activeMode === 'draw') {
                const painter = (ctx) => {
                    if (!state.lastPos) return;
                    ctx.lineTo(pos.x, pos.y);
                    ctx.stroke();
                    ctx.beginPath();
                    ctx.moveTo(pos.x, pos.y);
                };
                painter(drawCtx);
                if (state.bufferCtx) painter(state.bufferCtx);
            } else if (state.activeMode === 'border') {
                state.currentBorderPath.add(`${pos.row},${pos.col}`);
                redrawAllOverlays();
            }
    
            state.lastPos = pos;
            state.isDrawing = false;
        });
    }

	function handleInteractionEnd(e) {
        if (!state.isLeftDown) return;
        
        if (state.activeMode === 'mark') {
            if (!state.isDragging) {
                const { row, col } = state.lastPos;
                const fromState = state.playerGrid[row][col];

                if (fromState === 0) { 
                    const change = { r: row, c: col, from: 0, to: 2 };
                    applyMarkChange(row, col, fromState, 2);
                    pushHistory({ type: 'compoundMark', changes: [change] });
                } else if (fromState === 2) { 
                    placeStarAndAutoX(row, col);
                } else if (fromState === 1) { 
                    removeStarAndUndoAutoX(row, col);
                }
            } else {
                if (state.currentDragChanges.length > 0) {
                    pushHistory({ type: 'compoundMark', changes: state.currentDragChanges });
                }
            }
        } else if (state.activeMode === 'draw' && preActionState) {
            const afterState = state.bufferCtx.getImageData(0, 0, state.bufferCanvas.width, state.bufferCanvas.height);
            pushHistory({ type: 'draw', before: preActionState, after: afterState });
        } else if (state.activeMode === 'border' && state.currentBorderPath.size > 0) {
            const newBorder = { path: state.currentBorderPath, color: state.currentColor };
            state.customBorders.push(newBorder);
            pushHistory({ type: 'addBorder', border: newBorder });
        }

        state.isLeftDown = false;
        state.isDragging = false;
        state.lastPos = null;
        state.currentDragChanges = [];
        preActionState = null;
        state.currentBorderPath = new Set();
        drawCtx.globalCompositeOperation = 'source-over';
        if (state.bufferCtx) state.bufferCtx.globalCompositeOperation = 'source-over';
    }


    // --- UI UPDATE FUNCTIONS ---
    function setLoading(isLoading) {
        state.isLoading = isLoading;
        loadingSpinner.style.display = isLoading ? 'flex' : 'none';
        homeScreen.style.pointerEvents = isLoading ? 'none' : 'auto';
        homeScreen.style.opacity = isLoading ? '0.7' : '1';
    }
    function setStatus(message, isSuccess, duration = 3000) {
        solverStatus.textContent = message;
        solverStatus.classList.remove('text-green-400', 'text-red-400', 'text-yellow-400', 'opacity-0');
        if (isSuccess === true) solverStatus.classList.add('text-green-400');
        else if (isSuccess === false) solverStatus.classList.add('text-red-400');
        else solverStatus.classList.add('text-yellow-400');
        solverStatus.classList.remove('opacity-0');
        if (duration > 0) {
            setTimeout(() => solverStatus.classList.add('opacity-0'), duration);
        }
    }
    function populateSizeSelector() {
        sizeSelect.innerHTML = '';
        state.puzzleDefs.forEach((def, index) => {
            const option = document.createElement('option');
            option.value = index;
            option.textContent = def.text;
            sizeSelect.appendChild(option);
        });
        sizeSelect.value = 5;
    }
	function updateSolutionButtonUI() {
		if (state.solution) {
			if (state.isViewingSolution) {
				findSolutionBtn.textContent = 'Hide Solution';
			} else {
				findSolutionBtn.textContent = 'View Solution';
			}
			findSolutionBtn.classList.remove('bg-purple-600');
			findSolutionBtn.classList.add('bg-yellow-600');
		} else {
			findSolutionBtn.textContent = 'Solve';
            findSolutionBtn.classList.remove('bg-yellow-600');
			findSolutionBtn.classList.add('bg-purple-600');
		}
	}
	function handleSolutionToggle() {
        if (!state.solution) {
            findSolution();
        } else {
            state.isViewingSolution = !state.isViewingSolution;
            gridContainer.classList.toggle('solution-mode', state.isViewingSolution);
            updateSolutionButtonUI();
            redrawAllOverlays();
        }
    }
    function updateModeUI() {
		const isMarking = state.activeMode === 'mark';
        const isDrawing = state.activeMode === 'draw';
        const isBordering = state.activeMode === 'border';

        markModeBtn.classList.toggle('selected', isMarking);
        drawModeBtn.classList.toggle('selected', isDrawing);
        borderModeBtn.classList.toggle('selected', isBordering);

		toggleMarkBtn.style.display = isMarking ? 'block' : 'none';

        const showContextualControls = isDrawing || isBordering;

        if (showContextualControls) {
            contextualControls.classList.remove('hidden');
            colorPickerWrapper.classList.remove('hidden');
            if (isDrawing) {
                brushSizeWrapper.classList.remove('hidden');
            } else {
                brushSizeWrapper.classList.add('hidden');
            }
        } else {
            contextualControls.classList.add('hidden');
        }

        drawCanvas.style.pointerEvents = showContextualControls ? 'auto' : 'none';

        if (isDrawing) clearBtn.title = 'Clear all drawings';
        else if (isBordering) clearBtn.title = 'Clear all custom borders';
        else clearBtn.title = 'Clear all stars and marks';
    }

    // --- API & PUZZLE FUNCTIONS ---
    async function fetchNewPuzzle() {
        setLoading(true);
        const sizeId = sizeSelect.value;
        try {
            const response = await fetch(`${API_BASE_URL}/new_puzzle?size_id=${sizeId}`);
            if (!response.ok) throw new Error(`Server error: ${response.statusText}`);
            const data = await response.json();
            state.regionGrid = data.regionGrid;
            state.starsPerRegion = data.starsPerRegion;
            state.sourcePuzzleData = data.sourcePuzzleData;
            state.gridDim = data.regionGrid ? data.regionGrid.length : 0;
            state.solution = null;
            updateSolutionButtonUI();
            clearPuzzleState();
            renderGrid();
            showScreen('game');
        } catch (error) {
            console.error("Error fetching new puzzle:", error);
            setStatus("Failed to load puzzle.", false);
        } finally {
            setLoading(false);
        }
    }
    async function findSolution() {
        if (state.solution) return;
        setLoading(true);
        try {
            const response = await fetch(`${API_BASE_URL}/solve`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    regionGrid: state.regionGrid,
                    starsPerRegion: state.starsPerRegion,
                    sourcePuzzleData: state.sourcePuzzleData
                })
            });
            if (!response.ok) throw new Error(`Server error: ${response.statusText}`);
            const data = await response.json();
            if (data.solution) {
                setStatus("Solution found! Tap 'View' to see it.", true);
                state.solution = data.solution;
                updateSolutionButtonUI();
            } else {
                setStatus("No solution exists for this puzzle.", false);
            }
        } catch (error) {
            console.error("Error finding solution:", error);
            setStatus("Solver failed.", false);
        } finally {
            setLoading(false);
        }
    }
    async function checkSolution() {
        setLoading(true);
        try {
            const response = await fetch(`${API_BASE_URL}/check`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    regionGrid: state.regionGrid,
                    playerGrid: state.playerGrid,
                    starsPerRegion: state.starsPerRegion,
                    sourcePuzzleData: state.sourcePuzzleData
                })
            });
            if (!response.ok) throw new Error(`Server error: ${response.statusText}`);
            const data = await response.json();
            if (data.isCorrect) {
                let message = "Correct!";
                if (data.hashValidated) message += " (Hash Validated)";
                setStatus(message, true);
            } else {
                setStatus("Incorrect. Keep trying!", false);
            }
        } catch (error) {
            console.error("Error checking solution:", error);
            setStatus("Check failed.", false);
        } finally {
            setLoading(false);
        }
    }
    
    // --- FINALIZED: Import/Export/Save Logic ---
	async function importPuzzleString(importString) {
		if (!importString) return;
		setLoading(true);
		try {
			const response = await fetch(`${API_BASE_URL}/import`, {
				method: 'POST', headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ importString })
			});
			if (!response.ok) { const err = await response.json(); throw new Error(err.error || 'Invalid format'); }
			const data = await response.json();
			state.gridDim = data.regionGrid.length;
			state.starsPerRegion = data.starsPerRegion;
			state.regionGrid = data.regionGrid;
			state.sourcePuzzleData = data.sourcePuzzleData || {};
			state.solution = null;
			clearPuzzleState();
			
            if (data.history && data.history.changes && Array.isArray(data.history.changes)) {
				const importedMarkHistory = data.history.changes; 
                const newMarkStack = [];
                
				importedMarkHistory.forEach(change => {
					if (change.r < state.gridDim && change.c < state.gridDim) {
						newMarkStack.push({ type: 'mark', r: change.r, c: change.c, from: change.from, to: change.to });
					}
				});

                state.playerGrid = data.playerGrid;
                state.history.mark.stack = newMarkStack;
                state.history.mark.pointer = newMarkStack.length - 1;
			}
			
            renderGrid();
            updateErrorHighlightingUI();
			updateSolutionButtonUI();
			updateUndoRedoButtons();
			setStatus("Puzzle loaded successfully!", true);
            showScreen('game');
			return true;
		} catch (error) {
			console.error("Error importing puzzle:", error);
			setStatus(`Import failed: ${error.message}`, false);
			return false;
		} finally {
			setLoading(false);
		}
	}
    async function handleImport() {
        const importString = prompt("Paste your puzzle string (SBN or Web Task format):");
        await importPuzzleString(importString);
    }
    
    async function handleExport() {
        try {
            const historyForExport = [];
            const stackToExport = state.history.mark.stack.slice(0, state.history.mark.pointer + 1);
            
            stackToExport.forEach(action => {
                if (action.type === 'mark') {
                    historyForExport.push({ r: action.r, c: action.c, from: action.from, to: action.to });
                } 
                else if (action.type === 'compoundMark') {
                    action.changes.forEach(change => {
                        historyForExport.push({ r: change.r, c: change.c, from: change.from, to: change.to });
                    });
                }
            });

            const response = await fetch(`${API_BASE_URL}/export`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
					regionGrid: state.regionGrid,
					playerGrid: state.playerGrid,
					starsPerRegion: state.starsPerRegion,
					sourcePuzzleData: state.sourcePuzzleData,
					history: { changes: historyForExport }
                })
            });
            if (!response.ok) throw new Error(`Server error: ${response.statusText}`);
            const data = await response.json();
            navigator.clipboard.writeText(data.exportString).then(() => {
                setStatus("SBN string copied to clipboard!", true);
            }, () => {
                prompt("Could not auto-copy. Here is your SBN string:", data.exportString);
            });
        } catch (error) {
            console.error("Error exporting puzzle:", error);
            setStatus("Export failed.", false);
        }
    }
    async function handleSave() {
        const comment = prompt("Enter a comment for this save:", "");
        if (comment === null) {
            setStatus("Save cancelled.", null, 1500);
            return;
        }
        try {
            const historyForExport = [];
            const stackToExport = state.history.mark.stack.slice(0, state.history.mark.pointer + 1);
            
            stackToExport.forEach(action => {
                if (action.type === 'mark') {
                     historyForExport.push({ r: action.r, c: action.c, from: action.from, to: action.to });
                }
                else if (action.type === 'compoundMark') {
                    action.changes.forEach(change => {
                        historyForExport.push({ r: change.r, c: change.c, from: change.from, to: change.to });
                    });
                }
            });

            const response = await fetch(`${API_BASE_URL}/export`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    regionGrid: state.regionGrid,
                    playerGrid: state.playerGrid,
                    starsPerRegion: state.starsPerRegion,
                    sourcePuzzleData: state.sourcePuzzleData,
                    history: { changes: historyForExport }
                })
            });
            if (!response.ok) throw new Error(`Server error: ${response.statusText}`);
            const data = await response.json();
            const saves = JSON.parse(localStorage.getItem(LOCAL_STORAGE_KEY) || '[]');
            const newSave = {
                sbn: data.exportString,
                comment: comment || 'No comment',
                date: new Date().toISOString(),
                drawingData: state.bufferCanvas.toDataURL(),
                borderData: state.customBorders.map(border => ({
                    color: border.color,
                    path: Array.from(border.path)
                }))
            };
            saves.unshift(newSave);
            localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(saves));
            setStatus("Puzzle saved successfully!", true);
        } catch (error) {
            console.error("Error saving puzzle:", error);
            setStatus("Save failed.", false);
        }
    }
    function populateLoadModal() {
        const saves = JSON.parse(localStorage.getItem(LOCAL_STORAGE_KEY) || '[]');
        modalContent.innerHTML = '';
        if (saves.length === 0) {
            modalContent.innerHTML = '<p class="text-gray-400 text-center">No puzzles saved yet.</p>';
            return;
        }
        saves.forEach((save, index) => {
            const saveDate = new Date(save.date);
            const dateString = saveDate.toLocaleString();
            const item = document.createElement('div');
            item.className = 'save-item';
            item.dataset.sbn = save.sbn;
            item.dataset.index = index;
            item.innerHTML = `
                <div class="flex justify-between items-start">
                    <div>
                        <p class="font-semibold text-lg text-gray-200">${save.comment}</p>
                        <p class="save-date">${dateString}</p>
                    </div>
                    <button class="delete-save-btn text-red-500 hover:text-red-400 font-bold text-2xl" data-index="${index}">&times;</button>
                </div>
            `;
            modalContent.appendChild(item);
        });
    }

    // --- INITIALIZATION & EVENT LISTENERS ---
    function init() {
        function addResponsiveListener(element, callback) {
            if (!element) return;
            let touchHandled = false;
            const onTouchEnd = () => {
                element.classList.remove('btn-active');
            };
            element.addEventListener('touchstart', (e) => {
                element.classList.add('btn-active');
                e.preventDefault();
                touchHandled = true;
                callback(e);
                element.addEventListener('touchend', onTouchEnd, { once: true });
                element.addEventListener('touchcancel', onTouchEnd, { once: true });
            }, { passive: false });
            element.addEventListener('click', (e) => {
                if (touchHandled) {
                    touchHandled = false;
                    return;
                }
                callback(e);
            });
        }

		populateSizeSelector();
        addResponsiveListener(backToHomeBtn, showHomeScreen);

		addResponsiveListener(newPuzzleBtn, fetchNewPuzzle);
		addResponsiveListener(savePuzzleBtn, handleSave);
		addResponsiveListener(checkSolutionBtn, checkSolution);
		addResponsiveListener(importBtn, handleImport);
		addResponsiveListener(exportBtn, handleExport);
		addResponsiveListener(undoBtn, undo);
		addResponsiveListener(redoBtn, redo);
		addResponsiveListener(clearBtn, () => {
            let action = { type: null };
			switch (state.activeMode) {
				case 'draw':
					if (!state.bufferCtx || state.bufferCanvas.width === 0) return;
                    //if (confirm('Are you sure you want to clear all drawings? This CAN be undone.')) {
					    action = { type: 'clearDraw', before: state.bufferCtx.getImageData(0, 0, state.bufferCanvas.width, state.bufferCanvas.height) };
					    state.bufferCtx.clearRect(0, 0, state.bufferCanvas.width, state.bufferCanvas.height);
					    redrawAllOverlays();
                    //}
					break;
				case 'border':
					if (state.customBorders.length === 0) return;
                    //if (confirm('Are you sure you want to clear all custom borders? This CAN be undone.')) {
					    action = { type: 'clearBorder', before: deepCopyBorders(state.customBorders) };
					    state.customBorders = [];
					    redrawAllOverlays();
                    //}
					break;
				case 'mark':
					//if (confirm('Are you sure you want to clear all stars and marks? This CAN be undone.')) {
					    action = { type: 'clearMarks', before: JSON.parse(JSON.stringify(state.playerGrid)) };
					    _internalClearMarks();
					    renderAllMarks();
                        updateErrorHighlightingUI();
					//} 
					break;
			}
			if (action.type) pushHistory(action);
        });
		addResponsiveListener(toggleMarkBtn, () => {
            state.markIsX = !state.markIsX;
			toggleMarkBtn.textContent = state.markIsX ? "Dots" : "Xs";
			renderAllMarks();
            updateErrorHighlightingUI();
        });

		function switchMode(newMode) {
			state.activeMode = newMode;
			updateModeUI();
			updateUndoRedoButtons();
		}
		addResponsiveListener(markModeBtn, () => switchMode('mark'));
		addResponsiveListener(drawModeBtn, () => switchMode('draw'));
		addResponsiveListener(borderModeBtn, () => switchMode('border'));
		addResponsiveListener(findSolutionBtn, handleSolutionToggle);
		addResponsiveListener(loadPuzzleBtn, () => {
			populateLoadModal();
			loadModal.classList.remove('hidden');
		});
		addResponsiveListener(modalCloseBtn, () => loadModal.classList.add('hidden'));
		addResponsiveListener(settingsBtn, () => settingsModal.classList.remove('hidden'));
		addResponsiveListener(settingsModalCloseBtn, () => settingsModal.classList.add('hidden'));

        addResponsiveListener(hamburgerMenuBtn, (e) => {
            e.stopPropagation();
            puzzleActionsTab.classList.toggle('is-open');
        });
        puzzleActionsTab.addEventListener('click', (e) => e.stopPropagation());
        window.addEventListener('click', () => {
            if (puzzleActionsTab.classList.contains('is-open')) {
                puzzleActionsTab.classList.remove('is-open');
            }
        });


		bwModeToggle.addEventListener('change', (e) => { state.isBwMode = e.target.checked; renderGrid(); });
		highlightErrorsToggle.addEventListener('change', (e) => { state.highlightErrors = e.target.checked; updateErrorHighlightingUI(); });
		autoXAroundToggle.addEventListener('change', (e) => { state.autoXAroundStars = e.target.checked; });
		autoXMaxLinesToggle.addEventListener('change', (e) => { state.autoXOnMaxLines = e.target.checked; });
		autoXMaxRegionsToggle.addEventListener('change', (e) => { state.autoXOnMaxRegions = e.target.checked; });
		modalContent.addEventListener('click', async (e) => {
			const saveItem = e.target.closest('.save-item');
			const deleteBtn = e.target.closest('.delete-save-btn');
			if (deleteBtn) {
				e.stopPropagation();
				const indexToDelete = parseInt(deleteBtn.dataset.index, 10);
				if (confirm('Are you sure you want to delete this save?')) {
					let saves = JSON.parse(localStorage.getItem(LOCAL_STORAGE_KEY) || '[]');
					saves.splice(indexToDelete, 1);
					localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(saves));
					populateLoadModal();
				}
			} else if (saveItem) {
				const indexToLoad = parseInt(saveItem.dataset.index, 10);
				const saves = JSON.parse(localStorage.getItem(LOCAL_STORAGE_KEY) || '[]');
				const saveToLoad = saves[indexToLoad];
				if (!saveToLoad) return;
				const success = await importPuzzleString(saveToLoad.sbn);
				if (success) {
					if (saveToLoad.borderData) {
						state.customBorders = saveToLoad.borderData.map(border => ({
							color: border.color, path: new Set(border.path)
						}));
					}
					if (saveToLoad.drawingData) {
						const img = new Image();
						img.onload = () => {
							if (state.bufferCtx) state.bufferCtx.drawImage(img, 0, 0);
							redrawAllOverlays();
						};
						img.src = saveToLoad.drawingData;
					}
					redrawAllOverlays();
					loadModal.classList.add('hidden');
				}
			}
		});
		brushSizeSlider.addEventListener('input', (e) => {
            const newSize = parseInt(e.target.value, 10);
            state.brushSize = newSize;
			brushSizeValue.textContent = newSize;
        });
		addResponsiveListener(customColorBtn, () => { state.colorToReplace = state.currentColor; htmlColorPicker.click(); });
		htmlColorPicker.addEventListener('input', (e) => selectColor(e.target.value));
		htmlColorPicker.addEventListener('change', (e) => saveCustomColor(e.target.value));
        
        // MODIFIED: Event listener now targets the new container
		const colorSlotsContainer = document.getElementById('color-slots-container');
        if(colorSlotsContainer) {
            colorSlotsContainer.addEventListener('click', (e) => {
                const target = e.target.closest('.color-slot');
                if (!target) return;

                if (target.dataset.color) {
                    selectColor(target.dataset.color);
                } else if (target.dataset.customIndex) {
                    state.colorToReplace = null;
                    htmlColorPicker.click();
                }
            });
        }
		
		document.querySelectorAll('.setting-item .toggle-switch').forEach(toggleLabel => {
			addResponsiveListener(toggleLabel, (e) => {
				const input = toggleLabel.querySelector('input[type="checkbox"]');
				if (input) {
					input.checked = !input.checked;
					input.dispatchEvent(new Event('change', { bubbles: true }));
				}
			});
		});

        gridContainer.addEventListener('mousedown', handleInteractionStart);
        drawCanvas.addEventListener('mousedown', handleInteractionStart);
        gridContainer.addEventListener('touchstart', handleInteractionStart, { passive: false });
        drawCanvas.addEventListener('touchstart', handleInteractionStart, { passive: false });

        window.addEventListener('mousemove', handleInteractionMove);
        window.addEventListener('touchmove', handleInteractionMove, { passive: false });

        window.addEventListener('mouseup', handleInteractionEnd);
        window.addEventListener('touchend', handleInteractionEnd);
        window.addEventListener('touchcancel', handleInteractionEnd);

        gridContainer.addEventListener('contextmenu', e => e.preventDefault());
        drawCanvas.addEventListener('contextmenu', e => e.preventDefault());

        window.addEventListener('resize', resizeCanvas);

        showScreen('home');
		updateModeUI();
		renderColorPicker();
	}

    init();
});