
// This script runs when the HTML page has finished loading
document.addEventListener('DOMContentLoaded', () => {

    // --- STATE MANAGEMENT (Client-side) ---
    const state = {
        gridDim: 0,
        starsPerRegion: 0,
        regionGrid: [],      // 2D array defining the puzzle regions
        playerGrid: [],      // 2D array for player's marks (0: empty, 1: star, 2: secondary)
        sourcePuzzleData: {},// Original data from server for hashing/export
        history: [],         // Array of change objects for undo/redo
        historyPointer: -1,
        markIsX: true,       // true for 'X', false for 'Dot'
        isLoading: true,
        isDrawMode: false,
        isBorderMode: false,
        isLeftDown: false,
        isRightDown: false,
        lastPos: null,
        currentBorderPath: new Set(),
        customBorders: [],
        currentColorIndex: 0,
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

    // --- DOM ELEMENT REFERENCES ---
    const gridContainer = document.getElementById('grid-container');
    const sizeSelect = document.getElementById('size-select');
    const solverStatus = document.getElementById('solver-status');
    const newPuzzleBtn = document.getElementById('new-puzzle-btn');
    const checkSolutionBtn = document.getElementById('check-solution-btn');
    const findSolutionBtn = document.getElementById('find-solution-btn');
    const importBtn = document.getElementById('import-btn');
    const exportBtn = document.getElementById('export-btn');
    const clearBtn = document.getElementById('clear-btn');
    const toggleMarkBtn = document.getElementById('toggle-mark-btn');
    const undoBtn = document.getElementById('undo-btn');
    const redoBtn = document.getElementById('redo-btn');
    const loadingSpinner = document.getElementById('loading-spinner');
    const drawModeBtn = document.getElementById('draw-mode-btn');
    const borderModeBtn = document.getElementById('border-mode-btn');
    const drawCanvas = document.getElementById('draw-canvas');
    const drawCtx = drawCanvas.getContext('2d');

    // --- Color Picker Elements ---
    const presetColorsContainer = document.getElementById('preset-colors');
    const customColorsContainer = document.getElementById('custom-colors');
    const htmlColorPicker = document.getElementById('html-color-picker');
    const customColorBtn = document.getElementById('custom-color-btn');

    // --- SVG ICONS for marks ---
    const STAR_SVG = `<svg class="w-full h-full p-1 star-svg" viewBox="0 0 24 24" fill="currentColor"><path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/></svg>`;
    const DOT_SVG = `<svg class="w-full h-full p-[30%] dot-svg" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="10"/></svg>`;
    const X_SVG = `<svg class="w-full h-full p-[20%] x-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M18 6L6 18M6 6l12 12"/></svg>`;
    const REGION_COLORS = ["#fecaca", "#d9f99d", "#fef08a", "#bfdbfe", "#fbcfe8", "#a5f3fc", "#fed7aa", "#e9d5ff", "#fde68a", "#d1fae5", "#fecdd3", "#e9d5ff"];
    
    // --- New Color State ---
    const PRESET_COLORS = ['#EF4444', '#F59E0B', '#22C55E', '#3B82F6', '#000000'];
    state.customColors = Array(5).fill(null);
    state.currentColor = PRESET_COLORS[0];

    // --- RENDERING & DRAWING FUNCTIONS ---
    function renderGrid() {
        gridContainer.innerHTML = '';
        if (!state.gridDim || !state.regionGrid || state.regionGrid.length === 0) return;
        
        gridContainer.style.gridTemplateColumns = `repeat(${state.gridDim}, 1fr)`;
        gridContainer.style.gridTemplateRows = `repeat(${state.gridDim}, 1fr)`;
        gridContainer.style.setProperty('--grid-dim', state.gridDim);

        for (let r = 0; r < state.gridDim; r++) {
            for (let c = 0; c < state.gridDim; c++) {
                const cell = document.createElement('div');
                cell.classList.add('grid-cell');
                cell.dataset.r = r;
                cell.dataset.c = c;
                const regionId = state.regionGrid[r][c];
                cell.style.backgroundColor = REGION_COLORS[regionId % REGION_COLORS.length];
                if (c > 0 && state.regionGrid[r][c - 1] !== regionId) cell.classList.add('region-border-l');
                if (c < state.gridDim - 1 && state.regionGrid[r][c + 1] !== regionId) cell.classList.add('region-border-r');
                if (r > 0 && state.regionGrid[r - 1][c] !== regionId) cell.classList.add('region-border-t');
                if (r < state.gridDim - 1 && state.regionGrid[r + 1][c] !== regionId) cell.classList.add('region-border-b');
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

    function resizeCanvas() {
        const rect = gridContainer.getBoundingClientRect();
        drawCanvas.width = rect.width;
        drawCanvas.height = rect.height;

        redrawAllOverlays();
    }

    function redrawAllOverlays() {
        drawCtx.clearRect(0, 0, drawCanvas.width, drawCanvas.height);
        drawCustomBorders();
    }

    function drawCustomBorders() {
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

    // --- COLOR PICKER LOGIC ---
    function renderColorPicker() {
        // Render Presets
        presetColorsContainer.innerHTML = PRESET_COLORS.map(color => 
            `<div class="color-slot" data-color="${color}" style="background-color: ${color};"></div>`
        ).join('');

        // Render Custom Color Slots
        customColorsContainer.innerHTML = state.customColors.map((color, index) => {
            if (color) {
                return `<div class="color-slot" data-color="${color}" style="background-color: ${color};"></div>`;
            } else {
                return `<div class="color-slot empty" data-custom-index="${index}"></div>`;
            }
        }).join('');

        // Update selected visual state
        document.querySelectorAll('#color-picker-wrapper .color-slot').forEach(slot => {
            slot.classList.toggle('selected', slot.dataset.color === state.currentColor);
        });
    }

    function selectColor(newColor) {
        state.currentColor = newColor;
        htmlColorPicker.value = newColor;
        renderColorPicker();
    }

    function saveCustomColor(color) {
        const emptyIndex = state.customColors.findIndex(c => c === null);
        if (emptyIndex !== -1) {
            state.customColors[emptyIndex] = color;
        } else {
            // If all slots are full, replace the oldest (first) custom color
            state.customColors.shift(); // Remove the first element
            state.customColors.push(color); // Add the new color to the end
        }
        renderColorPicker();
    }

    // --- HISTORY MANAGEMENT ---
    function pushHistory(change) {
        if (state.historyPointer < state.history.length - 1) {
            state.history = state.history.slice(0, state.historyPointer + 1);
        }
        state.history.push(change);
        state.historyPointer++;
        updateUndoRedoButtons();
    }
    
    function applyChange(r, c, fromState, toState) {
        if (state.playerGrid[r][c] === fromState) {
            state.playerGrid[r][c] = toState;
            const cell = gridContainer.querySelector(`[data-r='${r}'][data-c='${c}']`);
            updateCellMark(cell, toState);
            return true;
        }
        return false;
    }

    function undo() {
        if (state.historyPointer < 0) return;
        const { r, c, from, to } = state.history[state.historyPointer];
        applyChange(r, c, to, from);
        state.historyPointer--;
        updateUndoRedoButtons();
    }

    function redo() {
        if (state.historyPointer >= state.history.length - 1) return;
        state.historyPointer++;
        const { r, c, from, to } = state.history[state.historyPointer];
        applyChange(r, c, from, to);
        updateUndoRedoButtons();
    }

    function updateUndoRedoButtons() {
        undoBtn.disabled = state.historyPointer < 0;
        redoBtn.disabled = state.historyPointer >= state.history.length - 1;
    }

    function clearPlayerGrid() {
        if (state.gridDim > 0) {
            state.playerGrid = Array(state.gridDim).fill(0).map(() => Array(state.gridDim).fill(0));
        }
        state.history = [];
        state.historyPointer = -1;
        renderAllMarks();
        updateUndoRedoButtons();
    }

    // --- EVENT HANDLERS (NEW, ROBUST IMPLEMENTATION) ---
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

        state.isDragging = false;
        state.clickCell = { r: pos.row, c: pos.col };

        if (e.button === 0) { // Left-click
            state.isLeftDown = true;
            if (state.isDrawMode) {
                drawCtx.beginPath();
                drawCtx.moveTo(pos.x, pos.y);
            } else if (state.isBorderMode) {
                state.currentBorderPath = new Set([`${pos.row},${pos.col}`]);
                redrawAllOverlays(); // Draw the initial single-cell border immediately
            }
        } else if (e.button === 2) { // Right-click
            e.preventDefault();
            state.isRightDown = true;
            if (!state.isDrawMode && !state.isBorderMode) { // Mark Mode right-click
                const { row, col } = pos;
                const fromState = state.playerGrid[row][col];
                const toState = (fromState === 1) ? 0 : 1; // Toggle star
                applyChange(row, col, fromState, toState);
                pushHistory({ r: row, c: col, from: fromState, to: toState });
            } else if (state.isBorderMode) {
                const cellId = `${pos.row},${pos.col}`;
                state.customBorders.forEach(b => b.path.delete(cellId));
                state.customBorders = state.customBorders.filter(b => b.path.size > 0);
                redrawAllOverlays();
            }
        }
    }

    function handleMouseMove(e) {
        if (!state.isLeftDown && !state.isRightDown) return;
        state.isDragging = true;

        const pos = getMousePos(e);
        if (!pos.onGrid) {
            // If we drag off-grid, treat it like a mouseup to finalize the action
            handleMouseUp(e);
            return;
        }

        if (state.isLeftDown) {
            if (!state.isDrawMode && !state.isBorderMode) { // Mark Mode drag
                const { row, col } = pos;
                const fromState = state.playerGrid[row][col];
                if (fromState !== 2) { // 2 = secondary mark
                    applyChange(row, col, fromState, 2);
                    pushHistory({ r: row, c: col, from: fromState, to: 2 });
                }
            } else if (state.isDrawMode) {
                drawCtx.lineCap = 'round';
                drawCtx.lineJoin = 'round';
                drawCtx.strokeStyle = state.currentColor;
                drawCtx.lineWidth = 5;
                drawCtx.globalCompositeOperation = 'source-over';
                drawCtx.lineTo(pos.x, pos.y);
                drawCtx.stroke();
                drawCtx.beginPath(); // Start a new line segment
                drawCtx.moveTo(pos.x, pos.y);
            } else if (state.isBorderMode) {
                state.currentBorderPath.add(`${pos.row},${pos.col}`);
                redrawAllOverlays();
            }
        } else if (state.isRightDown) { // Right-click drag
            if (state.isDrawMode) { // Eraser functionality
                drawCtx.globalCompositeOperation = 'destination-out';
                drawCtx.lineWidth = 40; // Increased eraser size
                drawCtx.lineTo(pos.x, pos.y);
                drawCtx.stroke();
                drawCtx.beginPath();
                drawCtx.moveTo(pos.x, pos.y);
            } else if (state.isBorderMode) { // Erase single border cells on drag
                const cellId = `${pos.row},${pos.col}`;
                state.customBorders.forEach(b => b.path.delete(cellId));
                // Clean up any empty border paths
                state.customBorders = state.customBorders.filter(b => b.path.size > 0);
                redrawAllOverlays();
            }
        }
    }

    function handleMouseUp(e) {
        if (e.button === 0 && state.isLeftDown) { // Handle left-click release
            if (!state.isDragging && state.clickCell) {
                // This was a simple click, not a drag
                if (!state.isDrawMode && !state.isBorderMode) {
                    const { r, c } = state.clickCell;
                    const fromState = state.playerGrid[r][c];
                    const cycle = { 0: 2, 2: 1, 1: 0 }; // Empty -> X -> Star -> Empty
                    const toState = cycle[fromState];
                    applyChange(r, c, fromState, toState);
                    pushHistory({ r, c, from: fromState, to: toState });
                }
            } 
            // Finalize a border drag OR a single-click border
            if (state.isBorderMode && state.currentBorderPath.size > 0) {
                state.customBorders.push({ path: state.currentBorderPath, color: state.currentColor });
                state.currentBorderPath = new Set();
                redrawAllOverlays();
            }
        }
        // Reset all interaction states
        state.isLeftDown = false;
        state.isRightDown = false;
        state.isDragging = false;
        state.clickCell = null;
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
        
        setTimeout(() => solverStatus.classList.add('opacity-0'), duration);
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

    function updateActiveTools() {
        drawModeBtn.classList.toggle('selected', state.isDrawMode);
        borderModeBtn.classList.toggle('selected', state.isBorderMode);
        document.querySelectorAll('.color-swatch').forEach((swatch, i) => {
            swatch.classList.toggle('selected', i === state.currentColorIndex);
        });
        drawCanvas.style.pointerEvents = (state.isDrawMode || state.isBorderMode) ? 'auto' : 'none';
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
            
            clearPlayerGrid();
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
                console.log(data.solution.map(row => row.join(' ')).join('\n'));
                setStatus("Solution found and logged to console!", true);
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
                    sourcePuzzleData: state.sourcePuzzleData // Pass the source data
                })
            });
            if (!response.ok) throw new Error(`Server error: ${response.statusText}`);
            const data = await response.json();
            if (data.isCorrect) {
                let message = "Correct!";
                if (data.hashValidated) {
                    message += " (Hash Validated)";
                }
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
    async function handleImport() { const importString = prompt("Paste your puzzle string (SBN or Web Task format):"); if (!importString) return; setLoading(true); try { const response = await fetch(`${API_BASE_URL}/import`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ importString }) }); if (!response.ok) { const err = await response.json(); throw new Error(err.error || 'Invalid format'); } const data = await response.json(); Object.assign(state, { regionGrid: data.regionGrid, starsPerRegion: data.starsPerRegion, gridDim: data.regionGrid.length, playerGrid: data.playerGrid }); if (data.history) { state.history = data.history.changes; state.historyPointer = data.history.pointer; } else { state.history = []; state.historyPointer = -1; } renderGrid(); updateUndoRedoButtons(); setStatus("Puzzle imported successfully!", null); } catch (error) { console.error("Error importing puzzle:", error); setStatus(`Import failed: ${error.message}`, false); } finally { setLoading(false); } }
    async function handleExport() { try { const response = await fetch(`${API_BASE_URL}/export`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ regionGrid: state.regionGrid, playerGrid: state.playerGrid, starsPerRegion: state.starsPerRegion, history: { changes: state.history, pointer: state.historyPointer } }) }); if (!response.ok) throw new Error(`Server error: ${response.statusText}`); const data = await response.json(); navigator.clipboard.writeText(data.exportString).then(() => { setStatus("Export string copied to clipboard!", true); }, () => { prompt("Could not auto-copy. Here is your export string:", data.exportString); }); } catch (error) { console.error("Error exporting puzzle:", error); setStatus("Export failed.", false); } }

    // --- INITIALIZATION & EVENT LISTENERS ---
    function init() {
        populateSizeSelector();

        // --- Button Listeners ---
        newPuzzleBtn.addEventListener('click', fetchNewPuzzle);
        findSolutionBtn.addEventListener('click', findSolution);
        checkSolutionBtn.addEventListener('click', checkSolution);
        importBtn.addEventListener('click', handleImport);
        exportBtn.addEventListener('click', handleExport);
        undoBtn.addEventListener('click', undo);
        redoBtn.addEventListener('click', redo);

        clearBtn.addEventListener('click', () => {
            if (state.isDrawMode) {
                drawCtx.clearRect(0, 0, drawCanvas.width, drawCanvas.height);
            } else if (state.isBorderMode) {
                state.customBorders = [];
                redrawAllOverlays();
            } else {
                clearPlayerGrid();
            }
        });

        toggleMarkBtn.addEventListener('click', () => {
            state.markIsX = !state.markIsX;
            toggleMarkBtn.textContent = state.markIsX ? "Xs" : "Dots";
            renderAllMarks();
        });

        drawModeBtn.addEventListener('click', () => {
            state.isDrawMode = !state.isDrawMode;
            if (state.isDrawMode) state.isBorderMode = false;
            updateActiveTools();
        });

        borderModeBtn.addEventListener('click', () => {
            state.isBorderMode = !state.isBorderMode;
            if (state.isBorderMode) state.isDrawMode = false;
            updateActiveTools();
        });

        // --- Color Picker Listeners ---
        customColorBtn.addEventListener('click', () => htmlColorPicker.click());

        htmlColorPicker.addEventListener('input', (e) => selectColor(e.target.value));

        htmlColorPicker.addEventListener('change', (e) => saveCustomColor(e.target.value));

        presetColorsContainer.addEventListener('click', (e) => {
            if (e.target.dataset.color) selectColor(e.target.dataset.color);
        });

        customColorsContainer.addEventListener('click', (e) => {
            if (e.target.dataset.color) {
                selectColor(e.target.dataset.color);
            } else if (e.target.dataset.customIndex) {
                htmlColorPicker.click();
            }
        });

        // --- Global Mouse Listeners for Robust Interaction ---
        gridContainer.addEventListener('mousedown', handleMouseDown);
        drawCanvas.addEventListener('mousedown', handleMouseDown);
        window.addEventListener('mousemove', handleMouseMove);
        window.addEventListener('mouseup', handleMouseUp);
        gridContainer.addEventListener('contextmenu', e => e.preventDefault());
        drawCanvas.addEventListener('contextmenu', e => e.preventDefault());
        window.addEventListener('resize', resizeCanvas);
        
        fetchNewPuzzle();
        updateActiveTools();
        renderColorPicker(); // Initial render
    }

    init();
});


