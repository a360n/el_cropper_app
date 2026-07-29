/**
 * EL Solar Panel Cell Cropper - Client Application Logic
 */

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const fileInput = document.getElementById('file-input');
    const dropzoneCard = document.getElementById('dropzone-card');
    const dropzoneContainer = document.getElementById('dropzone-container');
    const workspaceSplit = document.getElementById('workspace-split');
    const loadingOverlay = document.getElementById('loading-overlay');
    const loadingMsg = document.getElementById('loading-msg');
    
    // Cell Inspector Elements
    const currentCellId = document.getElementById('current-cell-id');
    const currentCellCoords = document.getElementById('current-cell-coords');
    const cellPreviewImg = document.getElementById('cell-preview-img');
    const cellLoader = document.getElementById('cell-loader');
    const btnPrevCell = document.getElementById('btn-prev-cell');
    const btnNextCell = document.getElementById('btn-next-cell');
    const cellSelectDropdown = document.getElementById('cell-select-dropdown');
    const matrixGrid = document.getElementById('matrix-grid');
    const cellCountBadge = document.getElementById('cell-count-badge');

    // Stats Elements
    const statOrigDim = document.getElementById('stat-orig-dim');
    const statModelDim = document.getElementById('stat-model-dim');
    const statPaddedDim = document.getElementById('stat-padded-dim');
    const statCH = document.getElementById('stat-ch');
    const statCW = document.getElementById('stat-cw');
    const statSL = document.getElementById('stat-sl');

    // Export Elements
    const btnExportZip = document.getElementById('btn-export-zip');
    const btnExportFolder = document.getElementById('btn-export-folder');
    const exportStatusMsg = document.getElementById('export-status-msg');

    // Canvas & Panel Elements
    const fullPanelImg = document.getElementById('full-panel-img');
    const gridCanvas = document.getElementById('grid-canvas');
    const toggleGridOverlay = document.getElementById('toggle-grid-overlay');
    const togglePaddingHighlight = document.getElementById('toggle-padding-highlight');
    const canvasWrapper = document.getElementById('canvas-wrapper');

    // State Variables
    let currentSessionId = null;
    let currentCellList = []; // Array of cell objects [{id: 'A1', col: 'A', row: 1, ...}]
    let selectedCellIndex = 0;
    let gridOverlayData = [];
    let metadata = {};

    // ----------------------------------------------------
    // Drag & Drop File Handlers
    // ----------------------------------------------------
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileUpload(e.target.files[0]);
        }
    });

    ['dragenter', 'dragover'].forEach(eventName => {
        dropzoneCard.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzoneCard.classList.add('drag-over');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzoneCard.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzoneCard.classList.remove('drag-over');
        });
    });

    dropzoneCard.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileUpload(files[0]);
        }
    });

    // ----------------------------------------------------
    // Upload Processing API Call
    // ----------------------------------------------------
    async function handleFileUpload(file) {
        showLoading("جاري تحليل وتقطيع اللوح حسب الخوارزمية...");
        
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || "خطأ في المعالجة");
            }

            currentSessionId = data.session_id;
            metadata = data.metadata;
            gridOverlayData = data.grid_overlay;
            currentCellList = generateOrderedCellList(data.cells);

            // Populate Stats
            statOrigDim.textContent = `${metadata.original_dimensions.width} × ${metadata.original_dimensions.height} px`;
            statModelDim.textContent = `${metadata.model_dimensions.width} × ${metadata.model_dimensions.height} px`;
            statPaddedDim.textContent = `${metadata.padded_dimensions.width} × ${metadata.padded_dimensions.height} px`;
            statCH.textContent = `${metadata.base_cell.CH.toFixed(2)} px`;
            statCW.textContent = `${metadata.base_cell.CW.toFixed(2)} px`;
            statSL.textContent = `${metadata.square_length_SL.toFixed(2)} px (${metadata.square_length_px} px)`;
            cellCountBadge.textContent = `${metadata.total_cells} خلية`;

            // Build Matrix Grid & Dropdown
            buildMatrixGridUI();
            buildDropdownUI();

            // Load Full Panel Image
            fullPanelImg.src = `/api/panel-image/${currentSessionId}`;
            fullPanelImg.onload = () => {
                resizeCanvasToImage();
                drawCanvasOverlay();
            };

            // Switch view
            dropzoneContainer.style.display = 'none';
            workspaceSplit.style.display = 'flex';

            // Select initial cell A1
            selectCellByIndex(0);

            hideLoading();

        } catch (err) {
            hideLoading();
            alert("حدث خطأ أثناء رفع وتحليل الصورة: " + err.message);
        }
    }

    // Generates A1 to F24 ordered cell list
    function generateOrderedCellList(cellsSummary) {
        // Map dictionary by ID
        const map = {};
        cellsSummary.forEach(c => map[c.id] = c);

        const list = [];
        const cols = ['A', 'B', 'C', 'D', 'E', 'F'];
        for (let r = 1; r <= 24; r++) {
            for (let c = 0; c < 6; c++) {
                const id = `${cols[c]}${r}`;
                if (map[id]) list.push(map[id]);
            }
        }
        return list;
    }

    // ----------------------------------------------------
    // UI Builders: Matrix Grid & Dropdown
    // ----------------------------------------------------
    function buildMatrixGridUI() {
        matrixGrid.innerHTML = '';
        currentCellList.forEach((cell, idx) => {
            const btn = document.createElement('button');
            btn.className = 'matrix-cell-btn';
            btn.textContent = cell.id;
            btn.dataset.index = idx;
            btn.addEventListener('click', () => selectCellByIndex(idx));
            matrixGrid.appendChild(btn);
        });
    }

    function buildDropdownUI() {
        cellSelectDropdown.innerHTML = '';
        currentCellList.forEach((cell, idx) => {
            const opt = document.createElement('option');
            opt.value = idx;
            opt.textContent = `${cell.id} (سطر ${cell.row})`;
            cellSelectDropdown.appendChild(opt);
        });
    }

    cellSelectDropdown.addEventListener('change', (e) => {
        selectCellByIndex(parseInt(e.target.value));
    });

    // ----------------------------------------------------
    // Cell Selection Logic
    // ----------------------------------------------------
    function selectCellByIndex(index) {
        if (index < 0 || index >= currentCellList.length) return;
        selectedCellIndex = index;
        const cell = currentCellList[selectedCellIndex];

        // Update ID and Coords Labels
        currentCellId.textContent = cell.id;
        currentCellCoords.textContent = `العمود ${cell.col} | السطر ${cell.row} (${selectedCellIndex + 1} من 144)`;

        // Update Dropdown selection
        cellSelectDropdown.value = selectedCellIndex;

        // Highlight Matrix Grid Button
        const buttons = matrixGrid.querySelectorAll('.matrix-cell-btn');
        buttons.forEach((btn, idx) => {
            if (idx === selectedCellIndex) {
                btn.classList.add('active');
                btn.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
            } else {
                btn.classList.remove('active');
            }
        });

        // Load 224x224 Cell Image
        cellLoader.style.display = 'flex';
        cellPreviewImg.src = `/api/cell-image/${currentSessionId}/${cell.id}`;
        cellPreviewImg.onload = () => {
            cellLoader.style.display = 'none';
        };

        // Redraw Canvas to highlight selected cell box
        drawCanvasOverlay();
    }

    // Navigation Buttons
    btnPrevCell.addEventListener('click', () => {
        if (selectedCellIndex > 0) {
            selectCellByIndex(selectedCellIndex - 1);
        } else {
            selectCellByIndex(currentCellList.length - 1); // Wrap around
        }
    });

    btnNextCell.addEventListener('click', () => {
        if (selectedCellIndex < currentCellList.length - 1) {
            selectCellByIndex(selectedCellIndex + 1);
        } else {
            selectCellByIndex(0); // Wrap around
        }
    });

    // Keyboard Navigation (Arrow Keys)
    document.addEventListener('keydown', (e) => {
        if (workspaceSplit.style.display === 'none') return;
        if (e.key === 'ArrowRight' || e.key === 'ArrowUp') {
            btnPrevCell.click();
        } else if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') {
            btnNextCell.click();
        }
    });

    // ----------------------------------------------------
    // Canvas & Overlay Drawing
    // ----------------------------------------------------
    function resizeCanvasToImage() {
        gridCanvas.width = fullPanelImg.naturalWidth;
        gridCanvas.height = fullPanelImg.naturalHeight;
        gridCanvas.style.width = fullPanelImg.clientWidth + 'px';
        gridCanvas.style.height = fullPanelImg.clientHeight + 'px';
    }

    window.addEventListener('resize', () => {
        if (fullPanelImg.complete && fullPanelImg.naturalWidth > 0) {
            resizeCanvasToImage();
            drawCanvasOverlay();
        }
    });

    toggleGridOverlay.addEventListener('change', drawCanvasOverlay);
    togglePaddingHighlight.addEventListener('change', drawCanvasOverlay);

    function drawCanvasOverlay() {
        if (!gridCanvas.width || !gridCanvas.height) return;
        const ctx = gridCanvas.getContext('2d');
        ctx.clearRect(0, 0, gridCanvas.width, gridCanvas.height);

        const padX = metadata.padding.pad_x;
        const padY = metadata.padding.pad_y;

        // 1. Draw 15% Padding Border Highlight (if enabled)
        if (togglePaddingHighlight.checked) {
            ctx.fillStyle = 'rgba(239, 68, 68, 0.15)'; // Red tint for reflected padding
            // Top padding bar
            ctx.fillRect(0, 0, gridCanvas.width, padY);
            // Bottom padding bar
            ctx.fillRect(0, gridCanvas.height - padY, gridCanvas.width, padY);
            // Left padding bar
            ctx.fillRect(0, padY, padX, gridCanvas.height - 2 * padY);
            // Right padding bar
            ctx.fillRect(gridCanvas.width - padX, padY, padX, gridCanvas.height - 2 * padY);

            // Dash line around original unpadded board area
            ctx.strokeStyle = '#ef4444';
            ctx.lineWidth = 2;
            ctx.setLineDash([6, 6]);
            ctx.strokeRect(padX, padY, metadata.model_dimensions.width, metadata.model_dimensions.height);
            ctx.setLineDash([]);
        }

        // 2. Draw Cell Grid Boxes (if enabled)
        if (toggleGridOverlay.checked && gridOverlayData.length > 0) {
            gridOverlayData.forEach((box) => {
                ctx.strokeStyle = 'rgba(56, 189, 248, 0.35)';
                ctx.lineWidth = 1;
                ctx.strokeRect(box.x, box.y, box.w, box.h);
            });
        }

        // 3. Highlight currently selected cell box
        if (currentCellList.length > 0 && selectedCellIndex < currentCellList.length) {
            const activeCell = currentCellList[selectedCellIndex];
            const box = activeCell.bbox;

            // Semi-transparent fill highlight
            ctx.fillStyle = 'rgba(6, 182, 212, 0.25)';
            ctx.fillRect(box.x, box.y, box.w, box.h);

            // Glowing cyan border
            ctx.strokeStyle = '#06b6d4';
            ctx.lineWidth = 4;
            ctx.strokeRect(box.x, box.y, box.w, box.h);

            // Cell ID Tag Box
            ctx.fillStyle = '#06b6d4';
            const tagW = 50;
            const tagH = 26;
            ctx.fillRect(box.x, box.y, tagW, tagH);

            ctx.fillStyle = '#0f172a';
            ctx.font = 'bold 16px Inter, sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(activeCell.id, box.x + tagW / 2, box.y + tagH / 2);
        }
    }

    // Canvas Click Interaction: Clicking on any cell selects it
    gridCanvas.addEventListener('click', (e) => {
        const rect = gridCanvas.getBoundingClientRect();
        const scaleX = gridCanvas.width / rect.width;
        const scaleY = gridCanvas.height / rect.height;

        const clickX = (e.clientX - rect.left) * scaleX;
        const clickY = (e.clientY - rect.top) * scaleY;

        // Find cell containing click coordinates
        for (let i = 0; i < currentCellList.length; i++) {
            const cell = currentCellList[i];
            const b = cell.bbox;
            if (clickX >= b.x && clickX <= b.x + b.w && clickY >= b.y && clickY <= b.y + b.h) {
                selectCellByIndex(i);
                break;
            }
        }
    });

    // ----------------------------------------------------
    // Export Handlers
    // ----------------------------------------------------
    btnExportZip.addEventListener('click', () => {
        if (!currentSessionId) return;
        window.location.href = `/api/export/zip/${currentSessionId}`;
    });

    btnExportFolder.addEventListener('click', async () => {
        if (!currentSessionId) return;
        
        exportStatusMsg.textContent = "جاري حفظ الصور في المجلد المحلي...";
        exportStatusMsg.style.color = "var(--accent-blue)";

        try {
            const response = await fetch(`/api/export/folder/${currentSessionId}`, {
                method: 'POST'
            });
            const res = await response.json();

            if (response.ok) {
                exportStatusMsg.textContent = `تم تم حفظ 144 خلية بنجاح في:\n${res.target_directory}`;
                exportStatusMsg.style.color = "var(--accent-green)";
            } else {
                throw new Error(res.detail || "فشل التصدير للمجلد");
            }
        } catch (err) {
            exportStatusMsg.textContent = "خطأ في التصدير: " + err.message;
            exportStatusMsg.style.color = "var(--accent-red)";
        }
    });

    // Loading overlay helpers
    function showLoading(msg) {
        loadingMsg.textContent = msg || "جاري المعالجة...";
        loadingOverlay.style.display = 'flex';
    }

    function hideLoading() {
        loadingOverlay.style.display = 'none';
    }
});
