/**
 * EL Solar Panel Cell Cropper - Client Application Logic
 */

document.addEventListener('DOMContentLoaded', () => {
    // Mode Switcher Elements
    const tabSingleMode = document.getElementById('tab-single-mode');
    const tabBatchMode = document.getElementById('tab-batch-mode');
    const singleModeContainer = document.getElementById('single-mode-container');
    const batchModeContainer = document.getElementById('batch-mode-container');
    const btnHeaderUpload = document.getElementById('btn-header-upload');

    // Single Mode Elements
    const fileInput = document.getElementById('file-input');
    const dropzoneCard = document.getElementById('dropzone-card');
    const dropzoneContainer = document.getElementById('dropzone-container');
    const workspaceSplit = document.getElementById('workspace-split');
    const loadingOverlay = document.getElementById('loading-overlay');
    const loadingMsg = document.getElementById('loading-msg');
    
    const currentCellId = document.getElementById('current-cell-id');
    const currentCellCoords = document.getElementById('current-cell-coords');
    const cellPreviewImg = document.getElementById('cell-preview-img');
    const cellLoader = document.getElementById('cell-loader');
    const btnPrevCell = document.getElementById('btn-prev-cell');
    const btnNextCell = document.getElementById('btn-next-cell');
    const cellSelectDropdown = document.getElementById('cell-select-dropdown');
    const matrixGrid = document.getElementById('matrix-grid');
    const cellCountBadge = document.getElementById('cell-count-badge');

    const statProcessTif = document.getElementById('stat-process-tif');
    const statOrigDim = document.getElementById('stat-orig-dim');
    const statModelDim = document.getElementById('stat-model-dim');
    const statPaddedDim = document.getElementById('stat-padded-dim');
    const statCH = document.getElementById('stat-ch');
    const statCW = document.getElementById('stat-cw');
    const statSL = document.getElementById('stat-sl');

    const btnExportZip = document.getElementById('btn-export-zip');
    const btnExportFolder = document.getElementById('btn-export-folder');
    const exportStatusMsg = document.getElementById('export-status-msg');

    const fullPanelImg = document.getElementById('full-panel-img');
    const gridCanvas = document.getElementById('grid-canvas');
    const toggleGridOverlay = document.getElementById('toggle-grid-overlay');
    const togglePaddingHighlight = document.getElementById('toggle-padding-highlight');

    // Batch Mode Elements
    const batchFolderPath = document.getElementById('batch-folder-path');
    const btnScanFolder = document.getElementById('btn-scan-folder');
    const btnRunBatch = document.getElementById('btn-run-batch');
    const batchSummaryCards = document.getElementById('batch-summary-cards');
    const summaryTotalPanels = document.getElementById('summary-total-panels');
    const summarySuccessPanels = document.getElementById('summary-success-panels');
    const summaryErrorPanels = document.getElementById('summary-error-panels');
    const batchLogSection = document.getElementById('batch-log-section');
    const batchLogTbody = document.getElementById('batch-log-tbody');

    // State Variables
    let currentSessionId = null;
    let currentCellList = [];
    let selectedCellIndex = 0;
    let gridOverlayData = [];
    let metadata = {};

    tabSingleMode.addEventListener('click', () => {
        tabSingleMode.classList.add('active');
        tabBatchMode.classList.remove('active');
        singleModeContainer.style.display = 'flex';
        batchModeContainer.style.display = 'none';
        btnHeaderUpload.style.display = 'inline-flex';
    });

    tabBatchMode.addEventListener('click', () => {
        tabBatchMode.classList.add('active');
        tabSingleMode.classList.remove('active');
        singleModeContainer.style.display = 'none';
        batchModeContainer.style.display = 'flex';
        btnHeaderUpload.style.display = 'none';
    });

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

    async function handleFileUpload(file) {
        showLoading("جاري تمرير الصورة عبر process_tif.py وتقطيعها...");
        
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

            statProcessTif.textContent = metadata.preprocessed_by_process_tif ? "نعم (مفعّل)" : "لا";
            statOrigDim.textContent = `${metadata.original_dimensions.width} × ${metadata.original_dimensions.height} px`;
            statModelDim.textContent = `${metadata.model_dimensions.width} × ${metadata.model_dimensions.height} px`;
            statPaddedDim.textContent = `${metadata.padded_dimensions.width} × ${metadata.padded_dimensions.height} px`;
            statCH.textContent = `${metadata.base_cell.CH.toFixed(2)} px`;
            statCW.textContent = `${metadata.base_cell.CW.toFixed(2)} px`;
            statSL.textContent = `${metadata.square_length_SL.toFixed(2)} px (${metadata.square_length_px} px)`;
            cellCountBadge.textContent = `${metadata.total_cells} خلية`;

            buildMatrixGridUI();
            buildDropdownUI();

            fullPanelImg.src = `/api/panel-image/${currentSessionId}`;
            fullPanelImg.onload = () => {
                resizeCanvasToImage();
                drawCanvasOverlay();
            };

            dropzoneContainer.style.display = 'none';
            workspaceSplit.style.display = 'flex';

            selectCellByIndex(0);
            hideLoading();

        } catch (err) {
            hideLoading();
            alert("حدث خطأ أثناء رفع وتحليل الصورة: " + err.message);
        }
    }

    function generateOrderedCellList(cellsSummary) {
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

    function selectCellByIndex(index) {
        if (index < 0 || index >= currentCellList.length) return;
        selectedCellIndex = index;
        const cell = currentCellList[selectedCellIndex];

        currentCellId.textContent = cell.id;
        currentCellCoords.textContent = `العمود ${cell.col} | السطر ${cell.row} (${selectedCellIndex + 1} من 144)`;

        cellSelectDropdown.value = selectedCellIndex;

        const buttons = matrixGrid.querySelectorAll('.matrix-cell-btn');
        buttons.forEach((btn, idx) => {
            if (idx === selectedCellIndex) {
                btn.classList.add('active');
                btn.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
            } else {
                btn.classList.remove('active');
            }
        });

        cellLoader.style.display = 'flex';
        cellPreviewImg.src = `/api/cell-image/${currentSessionId}/${cell.id}`;
        cellPreviewImg.onload = () => {
            cellLoader.style.display = 'none';
        };

        drawCanvasOverlay();
    }

    btnPrevCell.addEventListener('click', () => {
        if (selectedCellIndex > 0) {
            selectCellByIndex(selectedCellIndex - 1);
        } else {
            selectCellByIndex(currentCellList.length - 1);
        }
    });

    btnNextCell.addEventListener('click', () => {
        if (selectedCellIndex < currentCellList.length - 1) {
            selectCellByIndex(selectedCellIndex + 1);
        } else {
            selectCellByIndex(0);
        }
    });

    document.addEventListener('keydown', (e) => {
        if (singleModeContainer.style.display === 'none' || workspaceSplit.style.display === 'none') return;
        if (e.key === 'ArrowRight' || e.key === 'ArrowUp') {
            btnPrevCell.click();
        } else if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') {
            btnNextCell.click();
        }
    });

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

        if (togglePaddingHighlight.checked) {
            ctx.fillStyle = 'rgba(239, 68, 68, 0.15)';
            ctx.fillRect(0, 0, gridCanvas.width, padY);
            ctx.fillRect(0, gridCanvas.height - padY, gridCanvas.width, padY);
            ctx.fillRect(0, padY, padX, gridCanvas.height - 2 * padY);
            ctx.fillRect(gridCanvas.width - padX, padY, padX, gridCanvas.height - 2 * padY);

            ctx.strokeStyle = '#ef4444';
            ctx.lineWidth = 2;
            ctx.setLineDash([6, 6]);
            ctx.strokeRect(padX, padY, metadata.model_dimensions.width, metadata.model_dimensions.height);
            ctx.setLineDash([]);
        }

        if (toggleGridOverlay.checked && gridOverlayData.length > 0) {
            gridOverlayData.forEach((box) => {
                ctx.strokeStyle = 'rgba(56, 189, 248, 0.35)';
                ctx.lineWidth = 1;
                ctx.strokeRect(box.x, box.y, box.w, box.h);
            });
        }

        if (currentCellList.length > 0 && selectedCellIndex < currentCellList.length) {
            const activeCell = currentCellList[selectedCellIndex];
            const box = activeCell.bbox;

            ctx.fillStyle = 'rgba(6, 182, 212, 0.25)';
            ctx.fillRect(box.x, box.y, box.w, box.h);

            ctx.strokeStyle = '#06b6d4';
            ctx.lineWidth = 4;
            ctx.strokeRect(box.x, box.y, box.w, box.h);

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

    gridCanvas.addEventListener('click', (e) => {
        const rect = gridCanvas.getBoundingClientRect();
        const scaleX = gridCanvas.width / rect.width;
        const scaleY = gridCanvas.height / rect.height;

        const clickX = (e.clientX - rect.left) * scaleX;
        const clickY = (e.clientY - rect.top) * scaleY;

        for (let i = 0; i < currentCellList.length; i++) {
            const cell = currentCellList[i];
            const b = cell.bbox;
            if (clickX >= b.x && clickX <= b.x + b.w && clickY >= b.y && clickY <= b.y + b.h) {
                selectCellByIndex(i);
                break;
            }
        }
    });

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
                exportStatusMsg.textContent = `تم حفظ 144 خلية بنجاح في:\n${res.target_directory}`;
                exportStatusMsg.style.color = "var(--accent-green)";
            } else {
                throw new Error(res.detail || "فشل التصدير للمجلد");
            }
        } catch (err) {
            exportStatusMsg.textContent = "خطأ في التصدير: " + err.message;
            exportStatusMsg.style.color = "var(--accent-red)";
        }
    });

    // ----------------------------------------------------
    // MODE 2: BATCH FOLDER PROCESSING LOGIC (High Scale Optimized)
    // ----------------------------------------------------
    btnScanFolder.addEventListener('click', async () => {
        const path = batchFolderPath.value.trim();
        if (!path) {
            alert("يرجى إدخال مسار المجلد الرئيسي أولاً.");
            return;
        }

        showLoading("جاري فحص المجلد وإحصاء الألواح...");

        try {
            const res = await fetch(`/api/scan-folder?folder_path=${encodeURIComponent(path)}`);
            const data = await res.json();
            hideLoading();

            if (!res.ok) {
                throw new Error(data.detail || "فشل فحص المجلد");
            }

            summaryTotalPanels.textContent = Number(data.total_panels).toLocaleString();
            summarySuccessPanels.textContent = '0';
            summaryErrorPanels.textContent = '0';
            batchSummaryCards.style.display = 'grid';

            renderLogTable(data.panels.map(p => ({
                panel_name: p.panel_name,
                category: p.category,
                target_dir: `${p.panel_dir}/all cell`,
                status: 'PENDING'
            })));
            batchLogSection.style.display = 'flex';

            alert(`تم فحص المجلد بنجاح! العثور على ${data.total_panels.toLocaleString()} لوح شمسي جاهز للتقطيع.`);

        } catch (err) {
            hideLoading();
            alert("خطأ أثناء فحص المجلد: " + err.message);
        }
    });

    btnRunBatch.addEventListener('click', async () => {
        const path = batchFolderPath.value.trim();
        if (!path) {
            alert("يرجى إدخال مسار المجلد الرئيسي أولاً.");
            return;
        }

        showLoading("جاري التقطيع التلقائي للألواح وإنشاء مجلدات all cell (قد يستغرق بعض الوقت للكميات الضخمة)...");

        try {
            const formData = new FormData();
            formData.append('folder_path', path);

            const res = await fetch('/api/batch-process', {
                method: 'POST',
                body: formData
            });

            const data = await res.json();
            hideLoading();

            if (!res.ok) {
                throw new Error(data.detail || "خطأ أثناء المعالجة التلقائية");
            }

            const results = data.results;
            summaryTotalPanels.textContent = Number(results.total_panels).toLocaleString();
            summarySuccessPanels.textContent = Number(results.success_count).toLocaleString();
            summaryErrorPanels.textContent = Number(results.error_count).toLocaleString();
            batchSummaryCards.style.display = 'grid';

            renderLogTable(results.details);
            batchLogSection.style.display = 'flex';

            const totalCells = (results.success_count * 144).toLocaleString();
            alert(`🏁 اكتملت المعالجة الكلية بالدفعة!\n✅ تمت معالجة ${results.success_count.toLocaleString()} لوح بنجاح.\n📦 إجمالي الخلايا الناتجة: ${totalCells} صورة PNG.`);

        } catch (err) {
            hideLoading();
            alert("حدث خطأ أثناء معالجة الدفعة: " + err.message);
        }
    });

    // Efficient Table Log Rendering (limits DOM rendering for large lists like 17,000+ items)
    function renderLogTable(items) {
        batchLogTbody.innerHTML = '';
        const limit = Math.min(items.length, 500); // Display top 500 rows for fast browser UI rendering
        
        for (let idx = 0; idx < limit; idx++) {
            const d = items[idx];
            const tr = document.createElement('tr');
            
            let statusTag = `<span class="text-secondary">بانتظار التقطيع</span>`;
            if (d.status === 'SUCCESS') {
                statusTag = `<span class="tag-status-success"><i class="fa-solid fa-circle-check"></i> مكتمل (144 خلية)</span>`;
            } else if (d.status === 'ERROR') {
                statusTag = `<span class="tag-status-error"><i class="fa-solid fa-circle-xmark"></i> خطأ: ${d.error || ''}</span>`;
            }

            tr.innerHTML = `
                <td>${idx + 1}</td>
                <td><strong>${d.panel_name}</strong></td>
                <td><span class="badge">${d.category}</span></td>
                <td>${statusTag}</td>
                <td><code style="color:var(--accent-cyan)">${d.target_dir}</code></td>
            `;
            batchLogTbody.appendChild(tr);
        }

        if (items.length > 500) {
            const trNotice = document.createElement('tr');
            trNotice.innerHTML = `
                <td colspan="5" style="text-align:center; color: var(--accent-blue); padding: 12px;">
                    ℹ️ يتم عرض أول 500 لوح من إجمالي ${items.length.toLocaleString()} لوح للحفاظ على سرعة المتصفح. جميع المجلدات تم تقطيعها وحفظها على القرص الصلب.
                </td>
            `;
            batchLogTbody.appendChild(trNotice);
        }
    }

    function showLoading(msg) {
        loadingMsg.textContent = msg || "جاري المعالجة...";
        loadingOverlay.style.display = 'flex';
    }

    function hideLoading() {
        loadingOverlay.style.display = 'none';
    }
});
