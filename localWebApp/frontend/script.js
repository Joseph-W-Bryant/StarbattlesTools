// This script runs when the HTML page has finished loading
document.addEventListener('DOMContentLoaded', () => {

    // --- STATE MANAGEMENT (Client-side) ---
    const state = {
        gridDim: 0,
        starsPerRegion: 0,
        regionGrid: [],      // 2D array defining the puzzle regions
        playerGrid: [],      // 2D array for player's marks (0: empty, 1: star, 2: secondary)
        sourcePuzzleData: {},// Original data from server for hashing/export
        history: {          // Each mode has its own history stack
            mark: { stack: [], pointer: -1 },
            draw: { stack: [], pointer: -1 },
            border: { stack: [], pointer: -1 },
        },
        markIsX: true,       // true for 'X', false for 'Dot'
        isLoading: true,
        solution: null,      // Holds the puzzle solution grid
        isViewingSolution: false, // Flag for press-and-hold view
        activeMode: 'mark',  // can be 'mark', 'draw', or 'border'
        isLeftDown: false,
        isRightDown: false,
        isDragging: false,   // Flag to distinguish a click from a drag
        lastPos: null,
        currentBorderPath: new Set(),
        customBorders: [],
        colorToReplace: null,
        currentColorIndex: 0,
        brushSize: 5,
        isBwMode: false,
		highlightErrors: true,
        autoXAroundStars: false,
        autoXOnMaxLines: false,
        autoXOnMaxRegions: false,
        bufferCanvas: document.createElement('canvas'), // Buffer to preserve free-form drawings
        bufferCtx: null,                               // Buffer's context
        puzzleDefs: [ // Matches backend `constants.py` for the dropdown
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
    const API_BASE_URL = 'http://127.0.0.1:5001/api';
    //const API_BASE_URL = 'https://StarBattle.pythonanywhere.com/api';
    const LOCAL_STORAGE_KEY = 'starBattleSaves';

    // --- DOM ELEMENT REFERENCES ---
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
	
	const settingsBtn = document.getElementById('settings-btn');
	const settingsModal = document.getElementById('settings-modal');
	const settingsModalCloseBtn = document.getElementById('settings-modal-close-btn');
	const bwModeToggle = document.getElementById('bw-mode-toggle');
	const autoXAroundToggle = document.getElementById('auto-x-around-toggle');
	const autoXMaxLinesToggle = document.getElementById('auto-x-max-lines-toggle');
	const autoXMaxRegionsToggle = document.getElementById('auto-x-max-regions-toggle');

    // --- Modal Elements ---
    const loadModal = document.getElementById('load-modal');
    const modalContent = document.getElementById('modal-content');
    const modalCloseBtn = document.getElementById('modal-close-btn');

    // --- Color Picker Elements ---
    const presetColorsContainer = document.getElementById('preset-colors');
    const customColorsContainer = document.getElementById('custom-colors');
    const htmlColorPicker = document.getElementById('html-color-picker');
    const customColorBtn = document.getElementById('custom-color-btn');

    // --- SVG ICONS for marks ---
    const STAR_SVG = `<svg class="w-full h-full p-1 star-svg" viewBox="0 0 24 24" fill="currentColor"><path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/></svg>`;
    const DOT_SVG = `<svg class="w-full h-full p-[30%] dot-svg" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="10"/></svg>`;
    const X_SVG = `<svg class="w-full h-full p-[20%] x-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M18 6L6 18M6 6l12 12"/></svg>`;
    
    // --- New Color State ---
    const PRESET_COLORS = ['#EF4444', '#F59E0B', '#22C55E', '#3B82F6', '#000000'];
    state.customColors = Array(5).fill(null);
    state.currentColor = PRESET_COLORS[0];

    // --- State for Undo/Redo ---
    let preActionState = null; // Used to store state before an action begins

    // --- RENDERING & DRAWING FUNCTIONS ---
    function renderGrid() {
		gridContainer.innerHTML = '';
		if (!state.gridDim || !state.regionGrid || state.regionGrid.length === 0) return;
		
		gridContainer.classList.toggle('bw-mode', state.isBwMode); // Toggle class for CSS
		gridContainer.style.gridTemplateColumns = `repeat(${state.gridDim}, 1fr)`;
		gridContainer.style.gridTemplateRows = `repeat(${state.gridDim}, 1fr)`;
		gridContainer.style.setProperty('--grid-dim', state.gridDim);

		for (let r = 0; r < state.gridDim; r++) {
			for (let c = 0; c < state.gridDim; c++) {
				const cell = document.createElement('div');
				cell.classList.add('grid-cell');
				cell.dataset.r = r;
				cell.dataset.c = c;
				
				if (!state.isBwMode) {
					const regionId = state.regionGrid[r][c];
					const hue = (regionId * 67) % 360;
					const isSaturated = regionId % 2 === 1;
					const sat = isSaturated ? 65 : 100;
					const light = isSaturated ? 77 : 90;
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

    // --- NEW: Function to handle adjacent star styling ---
	function updateErrorHighlightingUI() {
		// A set to store the string coordinates 'r,c' of stars that are invalid.
		const invalidStarCoords = new Set();

		// First, clear all existing error highlights from every cell.
		for (let r = 0; r < state.gridDim; r++) {
			for (let c = 0; c < state.gridDim; c++) {
				const cell = gridContainer.querySelector(`[data-r='${r}'][data-c='${c}']`);
				if (cell) cell.classList.remove('error-star');
			}
		}

		// If the setting is turned off, exit early after clearing highlights.
		if (!state.highlightErrors || state.gridDim === 0) {
			return;
		}

		const stars = [];
		const rowCounts = Array(state.gridDim).fill(0);
		const colCounts = Array(state.gridDim).fill(0);
		const regionStars = {}; // { regionId: [{r, c}, ...] }

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

		// RULE 1: Check for adjacent stars
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

		// RULE 2: Check for too many stars in a row
		for (let r = 0; r < state.gridDim; r++) {
			if (rowCounts[r] > state.starsPerRegion) {
				stars.forEach(star => {
					if (star.r === r) invalidStarCoords.add(`${star.r},${star.c}`);
				});
			}
		}

		// RULE 3: Check for too many stars in a column
		for (let c = 0; c < state.gridDim; c++) {
			if (colCounts[c] > state.starsPerRegion) {
				stars.forEach(star => {
					if (star.c === c) invalidStarCoords.add(`${star.r},${star.c}`);
				});
			}
		}
		
		// RULE 4: Check for too many stars in a region
		for (const regionId in regionStars) {
			if (regionStars[regionId].length > state.starsPerRegion) {
				regionStars[regionId].forEach(star => {
					invalidStarCoords.add(`${star.r},${star.c}`);
				});
			}
		}

		// Finally, apply the 'error-star' class to all invalid stars
		invalidStarCoords.forEach(coord => {
			const [r, c] = coord.split(',');
			const cellElement = gridContainer.querySelector(`[data-r='${r}'][data-c='${c}']`);
			if (cellElement) {
				cellElement.classList.add('error-star');
			}
		});
	}


    function resizeCanvas() {
        const rect = gridContainer.getBoundingClientRect();
        drawCanvas.width = rect.width;
        drawCanvas.height = rect.height;

        state.bufferCanvas.width = rect.width;
        state.bufferCanvas.height = rect.height;
        state.bufferCtx = state.bufferCanvas.getContext('2d');
        if(drawCanvas.width > 0 && drawCanvas.height > 0) {
            state.bufferCtx.drawImage(drawCanvas, 0, 0);
        }
        
        redrawAllOverlays();
    }

    function drawSolutionOverlay() {
        if (!state.solution) return;
    
        const cellWidth = drawCanvas.width / state.gridDim;
        const cellHeight = drawCanvas.height / state.gridDim;
        
        drawCtx.fillStyle = 'rgba(252, 211, 77, 0.7)'; // Semi-transparent amber color
        drawCtx.shadowColor = 'white';
        drawCtx.shadowBlur = 15;
    
        for (let r = 0; r < state.gridDim; r++) {
            for (let c = 0; c < state.gridDim; c++) {
                if (state.solution[r][c] === 1) {
                    const x = c * cellWidth + cellWidth / 2;
                    const y = r * cellHeight + cellHeight / 2;
                    const radius = cellWidth / 4;
                    
                    drawCtx.beginPath();
                    drawCtx.arc(x, y, radius, 0, 2 * Math.PI);
                    drawCtx.fill();
                }
            }
        }
        drawCtx.shadowBlur = 0;
    }

    function redrawAllOverlays() {
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
        if (!state.gridDim || state.gridDim === 0) return;
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

    function placeStarAndAutoX(r, c) {
		const fromState = state.playerGrid[r][c];
		if (fromState === 1) return;

		const changes = [];
		const tempGrid = JSON.parse(JSON.stringify(state.playerGrid));

		const addChange = (row, col, newMark) => {
			if (row >= 0 && row < state.gridDim && col >= 0 && col < state.gridDim) {
				const oldMark = tempGrid[row][col];
				if (oldMark !== newMark && oldMark === 0) {
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
			finalChanges.forEach(c => state.playerGrid[c.r][c.c] = c.to);
			pushHistory({ type: 'compoundMark', changes: finalChanges });
			renderAllMarks();
            updateErrorHighlightingUI(); // Update styles after placing stars
		}
	}

    function removeStarAndAutoX(r, c) {
        if (state.playerGrid[r][c] !== 1) return;

        let starPlacingAction = null;
        for (let i = state.history.mark.pointer; i >= 0; i--) {
            const action = state.history.mark.stack[i];
            if (action.type === 'compoundMark' && action.changes.some(change => change.r === r && change.c === c && change.to === 1)) {
                starPlacingAction = action;
                break;
            }
        }

        if (starPlacingAction) {
            const removalChanges = [];
            starPlacingAction.changes.forEach(originalChange => {
                if (state.playerGrid[originalChange.r][originalChange.c] === originalChange.to) {
                    const toState = (originalChange.r === r && originalChange.c === c) ? 0 : originalChange.from;
                    applyMarkChange(originalChange.r, originalChange.c, originalChange.to, toState);
                    removalChanges.push({ r: originalChange.r, c: originalChange.c, from: originalChange.to, to: toState });
                }
            });
            
            if (removalChanges.length > 0) {
                pushHistory({ type: 'compoundMark', changes: removalChanges });
            }

        } else {
            if (applyMarkChange(r, c, 1, 0)) {
                pushHistory({ type: 'mark', r, c, from: 1, to: 0 });
            }
        }
        updateErrorHighlightingUI(); // Update styles after removing a star
    }

    function renderColorPicker() {
        presetColorsContainer.innerHTML = PRESET_COLORS.map(color => 
            `<div class="color-slot" data-color="${color}" style="background-color: ${color};"></div>`
        ).join('');

        customColorsContainer.innerHTML = state.customColors.map((color, index) => {
            if (color) {
                return `<div class="color-slot" data-color="${color}" style="background-color: ${color};"></div>`;
            } else {
                return `<div class="color-slot empty" data-custom-index="${index}"></div>`;
            }
        }).join('');

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

    // --- HISTORY MANAGEMENT ---
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
        if (state.playerGrid[r][c] === fromState) {
            state.playerGrid[r][c] = toState;
            const cell = gridContainer.querySelector(`[data-r='${r}'][data-c='${c}']`);
            updateCellMark(cell, toState);
            return true;
        }
        return false;
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

    // --- EVENT HANDLERS ---
    function getMousePos(e) {
        const rect = gridContainer.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        const onGrid = x >= 0 && x < rect.width && y >= 0 && y < rect.height;
        if (!onGrid) return { onGrid: false };

        const col = Math.floor(x / (rect.width / state.gridDim));
        const row = Math.floor(y / (rect.height / state.gridDim));
        return { x, y, row, col, onGrid };
    }

    function handleMouseDown(e) {
		const pos = getMousePos(e);
		if (!pos.onGrid) return;
		state.isDragging = false; // Reset dragging state on new mousedown
		state.clickCell = { r: pos.row, c: pos.col };

		if (e.button === 0) { // Left-click
			state.isLeftDown = true;
			if (state.activeMode === 'draw') {
				preActionState = state.bufferCtx.getImageData(0, 0, state.bufferCanvas.width, state.bufferCanvas.height);
				const painter = (ctx) => {
					ctx.beginPath();
					ctx.moveTo(pos.x, pos.y);
				};
				painter(drawCtx);
				if(state.bufferCtx) painter(state.bufferCtx);
			} else if (state.activeMode === 'border') {
				state.currentBorderPath = new Set([`${pos.row},${pos.col}`]);
				redrawAllOverlays();
			}
		} else if (e.button === 2) { // Right-click
			e.preventDefault();
			state.isRightDown = true;
			if (state.activeMode === 'mark') {
				const { row, col } = pos;
				const fromState = state.playerGrid[row][col];
				if (fromState === 1) {
					removeStarAndAutoX(row, col);
				} else {
					placeStarAndAutoX(row, col);
				}
			} else if (state.activeMode === 'border') {
				const { row, col } = pos;
				const cellPos = `${row},${col}`;
				const borderIndex = state.customBorders.findIndex(b => b.path.has(cellPos));

				if (borderIndex > -1) {
					pushHistory({
						type: 'removeCellFromBorder',
						cell: cellPos,
						borderIndex: borderIndex
					});
					state.customBorders[borderIndex].path.delete(cellPos);
					redrawAllOverlays();
				}
			} else if (state.activeMode === 'draw') {
				preActionState = state.bufferCtx.getImageData(0, 0, state.bufferCanvas.width, state.bufferCanvas.height);
				if (state.bufferCtx) {
					state.bufferCtx.arc(pos.x, pos.y, (state.brushSize/10)+9.5, 0, 2 * Math.PI);
					state.bufferCtx.globalCompositeOperation = 'destination-out';
					state.bufferCtx.beginPath();
					state.bufferCtx.arc(pos.x, pos.y, (state.brushSize/5)+9.5, 0, 2 * Math.PI);
					state.bufferCtx.fill();
				}
				redrawAllOverlays();
			}
		}
    }

	function handleMouseMove(e) {
		if (!state.isLeftDown && !state.isRightDown) return;
		
		const pos = getMousePos(e);

		// This is the key change. We check if a drag is *starting*.
		if (state.clickCell && pos.onGrid && (pos.row !== state.clickCell.r || pos.col !== state.clickCell.c)) {
			// If this is the first moment we detect a drag...
			if (!state.isDragging) {
				state.isDragging = true; // Set dragging to true first

				// ...and if we are in 'mark' mode, mark the STARTING cell.
				if (state.activeMode === 'mark') {
					const { r, c } = state.clickCell; // Use the original cell from mousedown
					if (state.playerGrid[r][c] === 0) { // Only mark if it's empty
						if (applyMarkChange(r, c, 0, 2)) {
							pushHistory({ type: 'mark', r, c, from: 0, to: 2 });
						}
					}
				}
			}
		}

		// If we're not dragging, don't do anything else.
		if (!state.isDragging) return;
		
		if (!pos.onGrid) {
			handleMouseUp(e);
			return;
		}

		if (state.isLeftDown) {
			if (state.activeMode === 'mark') {
				// This part is the same, marking the cell the mouse is currently over.
				const { row, col } = pos;
				if (state.playerGrid[row][col] === 0) { // Only place X on empty cells
					if (applyMarkChange(row, col, 0, 2)) {
						pushHistory({ type: 'mark', r: row, c: col, from: 0, to: 2 });
					}
				}
			} else if (state.activeMode === 'draw') {
				const painter = (ctx) => {
					ctx.globalCompositeOperation = 'source-over';
					ctx.lineCap = 'round';
					ctx.lineJoin = 'round';
					ctx.strokeStyle = state.currentColor;
					ctx.lineWidth = state.brushSize;
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
		} else if (state.isRightDown) {
			 if (state.activeMode === 'draw') {
				if (state.bufferCtx) {
					state.bufferCtx.globalCompositeOperation = 'destination-out';
					state.bufferCtx.beginPath();
					state.bufferCtx.arc(pos.x, pos.y, (state.brushSize/20)+(5*2), 0, 2 * Math.PI);
					state.bufferCtx.fill();
				}
				redrawAllOverlays();
			}
		}
    }

    function handleMouseUp(e) {
		 if (e.button === 0 && state.isLeftDown) { // Left-click release
			if (!state.isDragging && state.clickCell) { 
				if (state.activeMode === 'mark') {
					const { r, c } = state.clickCell;
					const fromState = state.playerGrid[r][c];
					
					if (fromState === 0) {
						if (applyMarkChange(r, c, 0, 2)) {
							pushHistory({ type: 'mark', r, c, from: 0, to: 2 });
						}
					} else if (fromState === 2) {
						placeStarAndAutoX(r, c);
					} else if (fromState === 1) {
						removeStarAndAutoX(r, c);
					}
				}
			} 
			if (state.activeMode === 'draw' && preActionState) {
				const afterState = state.bufferCtx.getImageData(0, 0, state.bufferCanvas.width, state.bufferCanvas.height);
				pushHistory({ type: 'draw', before: preActionState, after: afterState });
			}
			if (state.activeMode === 'border' && state.currentBorderPath.size > 0) {
				const newBorder = { path: state.currentBorderPath, color: state.currentColor };
				state.customBorders.push(newBorder);
				pushHistory({ type: 'addBorder', border: newBorder });
				state.currentBorderPath = new Set();
				redrawAllOverlays();
			}
		} else if (e.button === 2 && state.isRightDown) {
			if (state.activeMode === 'draw' && preActionState) {
				const afterState = state.bufferCtx.getImageData(0, 0, state.bufferCanvas.width, state.bufferCanvas.height);
				pushHistory({ type: 'draw', before: preActionState, after: afterState });
			}
		}

		// Reset all temporary states
		state.isLeftDown = false;
		state.isRightDown = false;
		state.isDragging = false;
		state.clickCell = null;
		preActionState = null;
		drawCtx.globalCompositeOperation = 'source-over';
		if (state.bufferCtx) {
			state.bufferCtx.globalCompositeOperation = 'source-over';
		}
    }

    // --- UI Update Functions ---
    function setLoading(isLoading) {
        state.isLoading = isLoading;
        loadingSpinner.style.display = isLoading ? 'flex' : 'none';
    }

    function setStatus(message, isSuccess, duration = 3000) {
        solverStatus.textContent = message;
        solverStatus.classList.remove('text-green-400', 'text-red-400', 'text-yellow-400', 'opacity-0');
        if (isSuccess === true) solverStatus.classList.add('text-green-400');
        else if (isSuccess === false) solverStatus.classList.add('text-red-400');
        else solverStatus.classList.add('text-yellow-400');
        if (duration > 0) {
            setTimeout(() => solverStatus.classList.add('opacity-0'), duration);
        }
    }
    
    function populateSizeSelector() {
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
			findSolutionBtn.textContent = 'View Solution';
			findSolutionBtn.style.backgroundColor = '#b5b538'; // A yellow-ish color for view
		} else {
			findSolutionBtn.textContent = 'Find Solution';
			findSolutionBtn.style.backgroundColor = 'rgb(147 51 234)'; // Original purple
		}
	}

    function updateModeUI() {
		const isMarking = state.activeMode === 'mark';
        const isDrawing = state.activeMode === 'draw';
        const isBordering = state.activeMode === 'border';
    
        markModeBtn.classList.toggle('selected', state.activeMode === 'mark');
        drawModeBtn.classList.toggle('selected', isDrawing);
        borderModeBtn.classList.toggle('selected', isBordering);
		
		toggleMarkBtn.style.display = isMarking ? 'block' : 'none';
		
        document.getElementById('color-picker-wrapper').style.display = (isDrawing || isBordering) ? 'block' : 'none';
        document.getElementById('brush-size-wrapper').style.display = isDrawing ? 'block' : 'none';
    
        drawCanvas.style.pointerEvents = (isDrawing || isBordering) ? 'auto' : 'none';
    
        if (isDrawing) {
            clearBtn.title = 'Clear all drawings from the canvas (Undoable)';
        } else if (isBordering) {
            clearBtn.title = 'Clear all custom borders (Undoable)';
        } else {
            clearBtn.title = 'Clear all stars and marks (Undoable)';
        }
    }

    // --- API CALL HANDLERS ---
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
        } catch (error) {
            console.error("Error fetching new puzzle:", error);
            setStatus("Failed to load puzzle.", false);
        } finally {
            setLoading(false);
        }
    }
    
    async function findSolution() {
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
                console.log("--- Solution Found ---");
                setStatus("Solution found!", true);
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

	async function importPuzzleString(importString) {
		if (!importString) return;
		setLoading(true);
		try {
			const response = await fetch(`${API_BASE_URL}/import`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ importString })
			});
			if (!response.ok) {
				const err = await response.json();
				throw new Error(err.error || 'Invalid format');
			}
			const data = await response.json();

			state.gridDim = data.regionGrid.length;
			state.starsPerRegion = data.starsPerRegion;
			state.regionGrid = data.regionGrid;
			state.sourcePuzzleData = data.sourcePuzzleData || {};
			state.solution = null; 

			clearPuzzleState();
			
			if (data.history && data.history.changes && Array.isArray(data.history.changes)) {
				const importedMarkHistory = data.history.changes;
				const markHistoryStack = [];

				importedMarkHistory.forEach(change => {
					if (change.r < state.gridDim && change.c < state.gridDim) {
						state.playerGrid[change.r][change.c] = change.to;
						markHistoryStack.push({
							type: 'mark',
							r: change.r,
							c: change.c,
							from: change.from,
							to: change.to
						});
					}
				});

				state.history.mark.stack = markHistoryStack;
				state.history.mark.pointer = markHistoryStack.length - 1;
			} 

			renderGrid();
            updateErrorHighlightingUI();

			updateSolutionButtonUI();
			updateUndoRedoButtons();
			setStatus("Puzzle loaded successfully!", true);
			return true;
		} catch (error) {
			console.error("Error importing puzzle:", error);
			setStatus(`Import failed: ${error.message}`, false);
			await fetchNewPuzzle();
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
            // 1. Create a flat list of history changes suitable for export.
            const historyForExport = [];
            // We only want to export the actions up to the current pointer.
            const stackToExport = state.history.mark.stack.slice(0, state.history.mark.pointer + 1);

            stackToExport.forEach(action => {
                // If it's a simple mark, just add the core data.
                if (action.type === 'mark') {
                    historyForExport.push({
                        r: action.r,
                        c: action.c,
                        from: action.from,
                        to: action.to
                    });
                // If it's a compound mark, loop through its inner changes.
                } else if (action.type === 'compoundMark') {
                    action.changes.forEach(change => {
                        historyForExport.push({
                            r: change.r,
                            c: change.c,
                            from: change.from,
                            to: change.to
                        });
                    });
                }
                // 'clearMarks' actions won't be exported, which is fine.
                // The final state of the playerGrid already reflects the clear.
            });

            const response = await fetch(`${API_BASE_URL}/export`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
					regionGrid: state.regionGrid,
					playerGrid: state.playerGrid,
					starsPerRegion: state.starsPerRegion,
					sourcePuzzleData: state.sourcePuzzleData,
                    // 2. Send the newly created flat history list.
					history: {
						changes: historyForExport 
					}
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
            // 1. Create the same flat history list as we did for handleExport.
            const historyForExport = [];
            const stackToExport = state.history.mark.stack.slice(0, state.history.mark.pointer + 1);

            stackToExport.forEach(action => {
                if (action.type === 'mark') {
                    historyForExport.push({
                        r: action.r, c: action.c, from: action.from, to: action.to
                    });
                } else if (action.type === 'compoundMark') {
                    action.changes.forEach(change => {
                        historyForExport.push({
                            r: change.r, c: change.c, from: change.from, to: change.to
                        });
                    });
                }
            });

            // 2. Call the /export endpoint with the corrected, flat history.
            const response = await fetch(`${API_BASE_URL}/export`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    regionGrid: state.regionGrid,
                    playerGrid: state.playerGrid,
                    starsPerRegion: state.starsPerRegion,
                    sourcePuzzleData: state.sourcePuzzleData, // sourcePuzzleData is fine to include
                    history: { changes: historyForExport }
                })
            });
            if (!response.ok) throw new Error(`Server error: ${response.statusText}`);
            const data = await response.json();

            // 3. The rest of the function remains the same.
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
		populateSizeSelector();

		// Button Listeners
		newPuzzleBtn.addEventListener('click', fetchNewPuzzle);
		savePuzzleBtn.addEventListener('click', handleSave);
		checkSolutionBtn.addEventListener('click', checkSolution);
		importBtn.addEventListener('click', handleImport);
		exportBtn.addEventListener('click', handleExport);
		undoBtn.addEventListener('click', undo);
		redoBtn.addEventListener('click', redo);

		clearBtn.addEventListener('click', () => {
			let action = { type: null };
			switch (state.activeMode) {
				case 'draw':
					if (!state.bufferCtx || state.bufferCanvas.width === 0) return;
					action = {
						type: 'clearDraw',
						before: state.bufferCtx.getImageData(0, 0, state.bufferCanvas.width, state.bufferCanvas.height)
					};
					state.bufferCtx.clearRect(0, 0, state.bufferCanvas.width, state.bufferCanvas.height);
					redrawAllOverlays();
					break;
				case 'border':
					if (state.customBorders.length === 0) return;
					action = {
						type: 'clearBorder',
						before: deepCopyBorders(state.customBorders)
					};
					state.customBorders = [];
					redrawAllOverlays();
					break;
				case 'mark':
					if (confirm('Are you sure you want to clear all stars and marks? This CAN be undone. (click Undo)')) {
					   action = {
						   type: 'clearMarks',
						   before: JSON.parse(JSON.stringify(state.playerGrid))
					   };
					   _internalClearMarks();
					   renderAllMarks();
                       updateErrorHighlightingUI();
					}
					break;
			}

			if (action.type) {
				pushHistory(action);
			}
		});

		toggleMarkBtn.addEventListener('click', () => {
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
		markModeBtn.addEventListener('click', () => switchMode('mark'));
		drawModeBtn.addEventListener('click', () => switchMode('draw'));
		borderModeBtn.addEventListener('click', () => switchMode('border'));
		
		findSolutionBtn.addEventListener('mousedown', () => {
			if (state.solution) {
				state.isViewingSolution = true;
				redrawAllOverlays();
			} else {
				findSolution();
			}
		});
		const stopViewingSolution = () => {
			if (state.isViewingSolution) {
				state.isViewingSolution = false;
				redrawAllOverlays();
			}
		};
		findSolutionBtn.addEventListener('mouseup', stopViewingSolution);
		findSolutionBtn.addEventListener('mouseleave', stopViewingSolution);

		loadPuzzleBtn.addEventListener('click', () => {
			populateLoadModal();
			loadModal.classList.remove('hidden');
		});

		modalCloseBtn.addEventListener('click', () => {
			loadModal.classList.add('hidden');
		});

		settingsBtn.addEventListener('click', () => {
			settingsModal.classList.remove('hidden');
		});
		settingsModalCloseBtn.addEventListener('click', () => {
			settingsModal.classList.add('hidden');
		});
		bwModeToggle.addEventListener('change', (e) => {
			state.isBwMode = e.target.checked;
			renderGrid();
		});
		highlightErrorsToggle.addEventListener('change', (e) => {
			state.highlightErrors = e.target.checked;
			updateErrorHighlightingUI(); // Re-run the check when the setting changes
		});
		autoXAroundToggle.addEventListener('change', (e) => {
			state.autoXAroundStars = e.target.checked;
		});
		autoXMaxLinesToggle.addEventListener('change', (e) => {
			state.autoXOnMaxLines = e.target.checked;
		});
		autoXMaxRegionsToggle.addEventListener('change', (e) => {
			state.autoXOnMaxRegions = e.target.checked;
		});

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
							color: border.color,
							path: new Set(border.path)
						}));
					}

					if (saveToLoad.drawingData) {
						const img = new Image();
						img.onload = () => {
							if (state.bufferCtx) {
								state.bufferCtx.drawImage(img, 0, 0);
							}
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

		customColorBtn.addEventListener('click', () => {
			state.colorToReplace = state.currentColor;
			htmlColorPicker.click();
		});
		htmlColorPicker.addEventListener('input', (e) => selectColor(e.target.value));
		htmlColorPicker.addEventListener('change', (e) => saveCustomColor(e.target.value));
		presetColorsContainer.addEventListener('click', (e) => {
			if (e.target.dataset.color) selectColor(e.target.dataset.color);
		});
		customColorsContainer.addEventListener('click', (e) => {
			if (e.target.dataset.color) {
				selectColor(e.target.dataset.color);
			} else if (e.target.dataset.customIndex) {
				state.colorToReplace = null;
				htmlColorPicker.click();
			}
		});

		gridContainer.addEventListener('mousedown', handleMouseDown);
		drawCanvas.addEventListener('mousedown', handleMouseDown);
		window.addEventListener('mousemove', handleMouseMove);
		window.addEventListener('mouseup', handleMouseUp);
		gridContainer.addEventListener('contextmenu', e => e.preventDefault());
		drawCanvas.addEventListener('contextmenu', e => e.preventDefault());
		window.addEventListener('resize', resizeCanvas);
		
		fetchNewPuzzle();
		updateModeUI();
		renderColorPicker();
	}

    init();
});
