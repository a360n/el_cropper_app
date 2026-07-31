document.addEventListener('DOMContentLoaded', () => {
    // State Variables - Single Panel Mode
    let currentSessionId = null;
    let metadata = null;
    let gridOverlay = [];
    let cellsList = [];
    let currentCellIndex = 0;
    let isGridVisible = true;
    let isPaddingHighlightVisible = true;

    // State Variables - Bad Panels Inspector Modal
    let badPanelsList = [];
    let currentBadPanelIndex = 0;

    // State Variables - Bad Cells Classifier & Sorter (Tab 3)
    let sorterFolderPath = "";
    let sorterCellsList = [];
    let sorterIndex = 0;
    let sorterCategoryCounts = {
        "Cracks": 0, "Ribbons": 0, "Misalignment": 0,
        "Impurity": 0, "Missing": 0, "other": 0
    };

    // State Variables - Balanced Good Cells Sorter (Tab 4: 3168 & not good)
    let goodFolderPath = "";
    let goodCellsList = [];
    let goodActivePosition = "A1";
    let goodPosAcceptedCounts = {};
    let goodPosRejectedCounts = {};
    let allPositions = [];
    let goodPosSubIndex = 0; // Index within the active position's queue

    // DOM Elements - Mode Switching
    const tabSingleMode = document.getElementById('tab-single-mode');
    const tabBatchMode = document.getElementById('tab-batch-mode');
    const tabSorterMode = document.getElementById('tab-sorter-mode');
    const tabGoodSorterMode = document.getElementById('tab-good-sorter-mode');

    const singleModeContainer = document.getElementById('single-mode-container');
    const batchModeContainer = document.getElementById('batch-mode-container');
    const sorterModeContainer = document.getElementById('sorter-mode-container');
    const goodSorterModeContainer = document.getElementById('good-sorter-mode-container');

    // DOM Elements - Single Mode
    const fileInput = document.getElementById('file-input');
    const dropzoneCard = document.getElementById('dropzone-card');
    const workspaceSplit = document.getElementById('workspace-split');
    const dropzoneContainer = document.getElementById('dropzone-container');
    const loadingOverlay = document.getElementById('loading-overlay');
    const loadingMsg = document.getElementById('loading-msg');

    const cellPreviewImg = document.getElementById('cell-preview-img');
    const cellLoader = document.getElementById('cell-loader');
    const currentCellId = document.getElementById('current-cell-id');
    const currentCellCoords = document.getElementById('current-cell-coords');
    const cellSelectDropdown = document.getElementById('cell-select-dropdown');
    const btnPrevCell = document.getElementById('btn-prev-cell');
    const btnNextCell = document.getElementById('btn-next-cell');
    const matrixGrid = document.getElementById('matrix-grid');

    const fullPanelImg = document.getElementById('full-panel-img');
    const gridCanvas = document.getElementById('grid-canvas');
    const toggleGridOverlay = document.getElementById('toggle-grid-overlay');
    const togglePaddingHighlight = document.getElementById('toggle-padding-highlight');

    const btnExportZip = document.getElementById('btn-export-zip');
    const btnExportFolder = document.getElementById('btn-export-folder');
    const exportStatusMsg = document.getElementById('export-status-msg');

    // DOM Elements - Stats
    const statProcessTif = document.getElementById('stat-process-tif');
    const statOrigDim = document.getElementById('stat-orig-dim');
    const statModelDim = document.getElementById('stat-model-dim');
    const statPaddedDim = document.getElementById('stat-padded-dim');
    const statCh = document.getElementById('stat-ch');
    const statCw = document.getElementById('stat-cw');
    const statSl = document.getElementById('stat-sl');

    // DOM Elements - Batch Mode
    const batchFolderPath = document.getElementById('batch-folder-path');
    const btnScanFolder = document.getElementById('btn-scan-folder');
    const btnRunBatch = document.getElementById('btn-run-batch');
    const btnInspectBadPanels = document.getElementById('btn-inspect-bad-panels');
    const batchSummaryCards = document.getElementById('batch-summary-cards');
    const batchLogSection = document.getElementById('batch-log-section');
    const summaryTotalPanels = document.getElementById('summary-total-panels');
    const summaryGoodCells = document.getElementById('summary-good-cells');
    const summaryBadCells = document.getElementById('summary-bad-cells');
    const summaryErrorPanels = document.getElementById('summary-error-panels');
    const batchLogTbody = document.getElementById('batch-log-tbody');

    // DOM Elements - Bad Panels Modal
    const badPanelsModal = document.getElementById('bad-panels-modal');
    const btnCloseBadModal = document.getElementById('btn-close-bad-modal');
    const badPanelCounter = document.getElementById('bad-panel-counter');
    const badPanelDropdown = document.getElementById('bad-panel-dropdown');
    const badPanelNameHeading = document.getElementById('bad-panel-name-heading');
    const badPanelStatusTag = document.getElementById('bad-panel-status-tag');
    const jsonSerial = document.getElementById('json-serial');
    const jsonTimestamp = document.getElementById('json-timestamp');
    const jsonDefectsList = document.getElementById('json-defects-list');
    const badCellsGrid = document.getElementById('bad-cells-grid');
    const modalFullPanelImg = document.getElementById('modal-full-panel-img');
    const modalPanelLoader = document.getElementById('modal-panel-loader');
    const btnPrevBadPanel = document.getElementById('btn-prev-bad-panel');
    const btnNextBadPanel = document.getElementById('btn-next-bad-panel');

    // DOM Elements - Sorter Mode (Tab 3)
    const sorterFolderPathInput = document.getElementById('sorter-folder-path');
    const btnLoadSorter = document.getElementById('btn-load-sorter');
    const sorterDashboard = document.getElementById('sorter-dashboard');
    const sorterInfoPanel = document.getElementById('sorter-info-panel');
    const sorterInfoCell = document.getElementById('sorter-info-cell');
    const sorterInfoFolder = document.getElementById('sorter-info-folder');
    const sorterStatSorted = document.getElementById('sorter-stat-sorted');
    const sorterStatTotal = document.getElementById('sorter-stat-total');
    const sorterStatRemaining = document.getElementById('sorter-stat-remaining');
    const sorterCellImg = document.getElementById('sorter-cell-img');
    const sorterImgBadge = document.getElementById('sorter-img-badge');
    const sorterImgLoader = document.getElementById('sorter-img-loader');
    const btnSorterPrev = document.getElementById('btn-sorter-prev');
    const btnSorterNext = document.getElementById('btn-sorter-next');

    // DOM Elements - Balanced Good Cells Sorter (Tab 4)
    const goodSorterPathInput = document.getElementById('good-sorter-path');
    const btnLoadGoodSorter = document.getElementById('btn-load-good-sorter');
    const goodSorterDashboard = document.getElementById('good-sorter-dashboard');
    const goodActivePosBadge = document.getElementById('good-active-pos-badge');
    const goodPosAcceptedCount = document.getElementById('good-pos-accepted-count');
    const goodTotalAcceptedCount = document.getElementById('good-total-accepted-count');
    const goodTotalRejectedCount = document.getElementById('good-total-rejected-count');

    const goodCellFilenameTxt = document.getElementById('good-cell-filename-txt');
    const goodCellFolderTag = document.getElementById('good-cell-folder-tag');
    const goodCellImg = document.getElementById('good-cell-img');
    const goodImgBadge = document.getElementById('good-img-badge');
    const goodImgLoader = document.getElementById('good-img-loader');
    const btnGoodPrev = document.getElementById('btn-good-prev');
    const btnGoodNext = document.getElementById('btn-good-next');

    const btnGoodAccept = document.getElementById('btn-good-accept');
    const btnGoodReject = document.getElementById('btn-good-reject');
    const positionMapGrid = document.getElementById('position-map-grid');

    // Celebration Modal Elements
    const celebrationModal = document.getElementById('celebration-modal');
    const btnCloseCelebration = document.getElementById('btn-close-celebration');
    const finalStatsGrid = document.getElementById('final-stats-grid');

    // Tab Navigation
    tabSingleMode.addEventListener('click', () => switchTab('single'));
    tabBatchMode.addEventListener('click', () => switchTab('batch'));
    tabGoodSorterMode.addEventListener('click', () => switchTab('good-sorter'));
    tabSorterMode.addEventListener('click', () => switchTab('sorter'));

    function switchTab(mode) {
        [tabSingleMode, tabBatchMode, tabGoodSorterMode, tabSorterMode].forEach(btn => btn.classList.remove('active'));
        [singleModeContainer, batchModeContainer, goodSorterModeContainer, sorterModeContainer].forEach(c => c.style.display = 'none');

        if (mode === 'single') {
            tabSingleMode.classList.add('active');
            singleModeContainer.style.display = 'block';
        } else if (mode === 'batch') {
            tabBatchMode.classList.add('active');
            batchModeContainer.style.display = 'block';
        } else if (mode === 'good-sorter') {
            tabGoodSorterMode.classList.add('active');
            goodSorterModeContainer.style.display = 'block';
        } else if (mode === 'sorter') {
            tabSorterMode.classList.add('active');
            sorterModeContainer.style.display = 'block';
        }
    }

    // File Drag & Drop Handlers
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropzoneCard.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropzoneCard.addEventListener(eventName, () => dropzoneCard.classList.add('drag-over'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzoneCard.addEventListener(eventName, () => dropzoneCard.classList.remove('drag-over'), false);
    });

    dropzoneCard.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) handleFileUpload(files[0]);
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) handleFileUpload(e.target.files[0]);
    });

    async function handleFileUpload(file) {
        showLoading('جاري معالجة وتمرير الصورة عبر process_tif وتقطيع 144 خلية...');
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'خطأ في معالجة الملف.');
            }

            const data = await response.json();
            currentSessionId = data.session_id;
            metadata = data.metadata;
            gridOverlay = data.grid_overlay;
            cellsList = data.cells;

            renderWorkspace();
        } catch (err) {
            alert(`❌ فشل معالجة الصورة: ${err.message}`);
        } finally {
            hideLoading();
        }
    }

    function renderWorkspace() {
        dropzoneContainer.style.display = 'none';
        workspaceSplit.style.display = 'flex';

        statProcessTif.innerText = metadata.preprocessed_by_process_tif ? 'نعم (مفعّل)' : 'لا';
        statOrigDim.innerText = `${metadata.original_dimensions.width} × ${metadata.original_dimensions.height} px`;
        statModelDim.innerText = `${metadata.model_dimensions.width} × ${metadata.model_dimensions.height} px`;
        statPaddedDim.innerText = `${metadata.padded_dimensions.width} × ${metadata.padded_dimensions.height} px`;
        statCh.innerText = `${metadata.base_cell.CH.toFixed(2)} px`;
        statCw.innerText = `${metadata.base_cell.CW.toFixed(2)} px`;
        statSl.innerText = `${metadata.square_length_SL.toFixed(2)} px (${metadata.square_length_px}px)`;

        fullPanelImg.src = `/api/panel-image/${currentSessionId}`;
        fullPanelImg.onload = () => drawOverlayCanvas();

        buildMatrixGrid();
        populateCellDropdown();

        currentCellIndex = 0;
        selectCellByIndex(0);
    }

    function populateCellDropdown() {
        cellSelectDropdown.innerHTML = '';
        cellsList.forEach((cell, idx) => {
            const opt = document.createElement('option');
            opt.value = idx;
            opt.innerText = `خلية ${cell.id} (${cell.col}${cell.row})`;
            cellSelectDropdown.appendChild(opt);
        });
    }

    function buildMatrixGrid() {
        matrixGrid.innerHTML = '';
        cellsList.forEach((cell, idx) => {
            const btn = document.createElement('button');
            btn.className = 'matrix-cell-btn';
            btn.innerText = cell.id;
            btn.dataset.index = idx;
            btn.addEventListener('click', () => selectCellByIndex(idx));
            matrixGrid.appendChild(btn);
        });
    }

    function selectCellByIndex(index) {
        if (index < 0 || index >= cellsList.length) return;
        currentCellIndex = index;
        const cell = cellsList[index];

        currentCellId.innerText = cell.id;
        currentCellCoords.innerText = `السطر ${cell.row} | العمود ${cell.col}`;
        cellSelectDropdown.value = index;

        cellLoader.style.display = 'block';
        cellPreviewImg.src = `/api/cell-image/${currentSessionId}/${cell.id}`;
        cellPreviewImg.onload = () => cellLoader.style.display = 'none';

        document.querySelectorAll('.matrix-cell-btn').forEach((btn, idx) => {
            btn.classList.toggle('active', idx === index);
        });

        drawOverlayCanvas();
    }

    btnPrevCell.addEventListener('click', () => {
        if (currentCellIndex > 0) selectCellByIndex(currentCellIndex - 1);
    });

    btnNextCell.addEventListener('click', () => {
        if (currentCellIndex < cellsList.length - 1) selectCellByIndex(currentCellIndex + 1);
    });

    cellSelectDropdown.addEventListener('change', (e) => {
        selectCellByIndex(parseInt(e.target.value, 10));
    });

    function drawOverlayCanvas() {
        if (!metadata || !fullPanelImg.complete) return;

        const nw = metadata.padded_dimensions.width;
        const nh = metadata.padded_dimensions.height;

        gridCanvas.width = fullPanelImg.clientWidth;
        gridCanvas.height = fullPanelImg.clientHeight;

        const ctx = gridCanvas.getContext('2d');
        ctx.clearRect(0, 0, gridCanvas.width, gridCanvas.height);

        const scaleX = gridCanvas.width / nw;
        const scaleY = gridCanvas.height / nh;

        const px = metadata.padding.pad_x * scaleX;
        const py = metadata.padding.pad_y * scaleY;
        const pw = metadata.model_dimensions.width * scaleX;
        const ph = metadata.model_dimensions.height * scaleY;

        if (isPaddingHighlightVisible) {
            ctx.fillStyle = 'rgba(255, 171, 0, 0.18)';
            ctx.fillRect(0, 0, gridCanvas.width, py);
            ctx.fillRect(0, gridCanvas.height - py, gridCanvas.width, py);
            ctx.fillRect(0, py, px, ph);
            ctx.fillRect(gridCanvas.width - px, py, px, ph);

            ctx.strokeStyle = '#ffab00';
            ctx.lineWidth = 1.5;
            ctx.setLineDash([4, 4]);
            ctx.strokeRect(px, py, pw, ph);
            ctx.setLineDash([]);
        }

        if (isGridVisible) {
            ctx.strokeStyle = 'rgba(0, 229, 255, 0.45)';
            ctx.lineWidth = 1;

            gridOverlay.forEach((cell, idx) => {
                const x = cell.x * scaleX;
                const y = cell.y * scaleY;
                const w = cell.w * scaleX;
                const h = cell.h * scaleY;

                if (idx === currentCellIndex) {
                    ctx.fillStyle = 'rgba(0, 230, 118, 0.25)';
                    ctx.fillRect(x, y, w, h);
                    ctx.strokeStyle = '#00e676';
                    ctx.lineWidth = 2.5;
                    ctx.strokeRect(x, y, w, h);
                } else {
                    ctx.strokeStyle = 'rgba(0, 229, 255, 0.45)';
                    ctx.lineWidth = 1;
                    ctx.strokeRect(x, y, w, h);
                }
            });
        }
    }

    toggleGridOverlay.addEventListener('change', (e) => {
        isGridVisible = e.target.checked;
        drawOverlayCanvas();
    });

    togglePaddingHighlight.addEventListener('change', (e) => {
        isPaddingHighlightVisible = e.target.checked;
        drawOverlayCanvas();
    });

    window.addEventListener('resize', () => drawOverlayCanvas());

    btnExportZip.addEventListener('click', () => {
        if (!currentSessionId) return;
        window.location.href = `/api/export/zip/${currentSessionId}`;
    });

    btnExportFolder.addEventListener('click', async () => {
        if (!currentSessionId) return;
        showLoading('جاري الحفظ في مجلد exported_cells المحلي...');
        try {
            const res = await fetch(`/api/export/folder/${currentSessionId}`, { method: 'POST' });
            const data = await res.json();
            exportStatusMsg.style.color = '#00e676';
            exportStatusMsg.innerText = `✅ ${data.message} (في ${data.target_directory})`;
        } catch (err) {
            exportStatusMsg.style.color = '#ff5252';
            exportStatusMsg.innerText = `❌ خطأ في الحفظ: ${err.message}`;
        } finally {
            hideLoading();
        }
    });

    // BATCH MODE HANDLERS & SCANNER
    btnScanFolder.addEventListener('click', async () => {
        const folderPath = batchFolderPath.value.trim();
        if (!folderPath) {
            alert('يرجى كتابة أو لصق مسار المجلد الرئيسي أولاً.');
            return;
        }

        showLoading('جاري فحص المجلد الرئيسي واكتشاف الألواح ومجلدات Good_models / bad_models...');
        try {
            const res = await fetch(`/api/scan-folder?folder_path=${encodeURIComponent(folderPath)}`);
            if (!res.ok) throw new Error('تعذر العثور على المجلد المدمج.');

            const data = await res.json();
            batchSummaryCards.style.display = 'grid';
            summaryTotalPanels.innerText = data.total_panels.toLocaleString();
            summaryGoodCells.innerText = '0';
            summaryBadCells.innerText = '0';
            summaryErrorPanels.innerText = '0';

            batchLogSection.style.display = 'block';
            batchLogTbody.innerHTML = '';

            const previewPanels = data.panels.slice(0, 500);
            previewPanels.forEach((p, idx) => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${idx + 1}</td>
                    <td><strong>${p.panel_name}</strong></td>
                    <td><span class="badge ${p.category === 'Good_models' ? 'badge-good' : 'badge-bad'}">${p.category}</span></td>
                    <td><span class="status-tag status-pending">في الانتظار</span></td>
                    <td>all cell/</td>
                    <td>${p.category === 'bad_models' ? 'bad cells/' : '-'}</td>
                `;
                batchLogTbody.appendChild(tr);
            });

            alert(`✅ اكتمل الفحص! تم إيجاد ${data.total_panels.toLocaleString()} لوح جاهز للمعالجة.`);
        } catch (err) {
            alert(`❌ خطأ في فحص المجلد: ${err.message}`);
        } finally {
            hideLoading();
        }
    });

    btnRunBatch.addEventListener('click', async () => {
        const folderPath = batchFolderPath.value.trim();
        if (!folderPath) {
            alert('يرجى كتابة أو لصق مسار المجلد الرئيسي أولاً.');
            return;
        }

        showLoading('جاري بدء التقطيع الشامل، وتوليد مجلدات all cell و bad cells وتجميع all good/bad cells...');

        try {
            const formData = new FormData();
            formData.append('folder_path', folderPath);

            const res = await fetch('/api/batch-process', {
                method: 'POST',
                body: formData
            });

            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.detail || 'حدث خطأ في معالجة الدفعة.');
            }

            const data = await res.json();
            const results = data.results;

            batchSummaryCards.style.display = 'grid';
            summaryTotalPanels.innerText = results.total_panels.toLocaleString();
            summaryGoodCells.innerText = results.total_good_cells_aggregated.toLocaleString();
            summaryBadCells.innerText = results.total_bad_cells_aggregated.toLocaleString();
            summaryErrorPanels.innerText = results.error_count;

            batchLogSection.style.display = 'block';
            batchLogTbody.innerHTML = '';

            const logItems = results.details.slice(0, 500);
            logItems.forEach((item, idx) => {
                const tr = document.createElement('tr');
                const isSuccess = item.status === 'SUCCESS';
                tr.innerHTML = `
                    <td>${idx + 1}</td>
                    <td><strong>${item.panel_name}</strong></td>
                    <td><span class="badge ${item.category === 'Good_models' ? 'badge-good' : 'badge-bad'}">${item.category}</span></td>
                    <td><span class="status-tag ${isSuccess ? 'status-success' : 'status-error'}">${isSuccess ? 'تمت بنجاح ✅' : 'خطأ ❌'}</span></td>
                    <td>${isSuccess ? `${item.cells_count} صورة` : '-'}</td>
                    <td>${item.bad_cells_count > 0 ? `<span class="badge badge-bad">${item.bad_cells_count} خلايا معيبة</span>` : '-'}</td>
                `;
                batchLogTbody.appendChild(tr);
            });

            if (results.all_bad_cells_dir) sorterFolderPathInput.value = results.all_bad_cells_dir;
            if (results.all_good_cells_dir) goodSorterPathInput.value = results.all_good_cells_dir;

            alert(`🏁 اكتملت المعالجة وتجميع البيانات بنجاح!\n\n✅ الألواح الناجحة: ${results.success_count.toLocaleString()}\n📁 إجمالي all good cells: ${results.total_good_cells_aggregated.toLocaleString()}\n📁 إجمالي all bad cells: ${results.total_bad_cells_aggregated.toLocaleString()}`);

        } catch (err) {
            alert(`❌ خطأ أثناء تشغيل الدفعة: ${err.message}`);
        } finally {
            hideLoading();
        }
    });

    // BAD PANELS INSPECTOR MODAL LOGIC
    btnInspectBadPanels.addEventListener('click', async () => {
        const folderPath = batchFolderPath.value.trim();
        if (!folderPath) {
            alert('يرجى كتابة أو لصق مسار المجلد الرئيسي أولاً.');
            return;
        }

        showLoading('جاري تحميل قائمة الألواح المعيبة (bad_models) وتفاصيل الـ JSON...');
        try {
            const res = await fetch(`/api/bad-panels-list?folder_path=${encodeURIComponent(folderPath)}`);
            if (!res.ok) throw new Error('تعذر تحميل بيانات الألواح المعيبة.');

            const data = await res.json();
            badPanelsList = data.bad_panels;

            if (badPanelsList.length === 0) {
                alert('ℹ️ لا توجد ألواح معيبة أو عيوب في هذا المجلد.');
                return;
            }

            populateBadPanelDropdown();
            currentBadPanelIndex = 0;
            renderBadPanelModal(0);

            badPanelsModal.style.display = 'flex';
        } catch (err) {
            alert(`❌ خطأ في فتح معاينة الألواح المعيبة: ${err.message}`);
        } finally {
            hideLoading();
        }
    });

    function populateBadPanelDropdown() {
        badPanelDropdown.innerHTML = '';
        badPanelsList.forEach((p, idx) => {
            const opt = document.createElement('option');
            opt.value = idx;
            opt.innerText = `[${idx + 1}/${badPanelsList.length}] ${p.panel_name}`;
            badPanelDropdown.appendChild(opt);
        });
    }

    function renderBadPanelModal(index) {
        if (index < 0 || index >= badPanelsList.length) return;
        currentBadPanelIndex = index;
        const panel = badPanelsList[index];

        badPanelCounter.innerText = `اللوح ${index + 1} من ${badPanelsList.length}`;
        badPanelDropdown.value = index;

        badPanelNameHeading.innerText = `اللوح: ${panel.panel_name}`;
        
        const rawJson = panel.raw_json || {};
        const jsonKeys = {};
        Object.keys(rawJson).forEach(k => jsonKeys[k.toLowerCase()] = rawJson[k]);

        jsonSerial.innerText = jsonKeys['serialnumber'] || jsonKeys['panelid'] || panel.panel_name;
        jsonTimestamp.innerText = jsonKeys['timestamp'] || '-';

        jsonDefectsList.innerHTML = '';
        const defects = panel.info.defects || jsonKeys['defects'] || [];
        if (defects.length > 0) {
            defects.forEach(d => {
                const tag = document.createElement('span');
                tag.className = 'defect-tag-badge';
                tag.innerText = d;
                jsonDefectsList.appendChild(tag);
            });
        } else {
            jsonDefectsList.innerText = 'لا توجد عيوب مدونة';
        }

        badCellsGrid.innerHTML = '';
        if (panel.bad_cell_files && panel.bad_cell_files.length > 0) {
            panel.bad_cell_files.forEach(cellFile => {
                const card = document.createElement('div');
                card.className = 'bad-cell-card';

                const filenameParts = cellFile.filename.replace('.png', '').split('-');
                const cellId = filenameParts[filenameParts.length - 1];

                const img = document.createElement('img');
                img.src = `/api/cell-file-preview?path=${encodeURIComponent(cellFile.path)}`;
                img.alt = cellFile.filename;

                const tag = document.createElement('span');
                tag.className = 'bad-cell-tag';
                tag.innerText = cellId;

                card.appendChild(img);
                card.appendChild(tag);
                badCellsGrid.appendChild(card);
            });
        } else {
            badCellsGrid.innerHTML = '<p style="color:var(--text-muted); font-size:12px;">لم يتم العثور على صور خلايا معيبة متطابقة في هذا المجلد.</p>';
        }

        modalPanelLoader.style.display = 'block';
        modalFullPanelImg.src = `/api/panel-file-preview?path=${encodeURIComponent(panel.tif_path)}`;
        modalFullPanelImg.onload = () => modalPanelLoader.style.display = 'none';
        modalFullPanelImg.onerror = () => modalPanelLoader.style.display = 'none';
    }

    btnPrevBadPanel.addEventListener('click', () => {
        if (currentBadPanelIndex > 0) renderBadPanelModal(currentBadPanelIndex - 1);
    });

    btnNextBadPanel.addEventListener('click', () => {
        if (currentBadPanelIndex < badPanelsList.length - 1) renderBadPanelModal(currentBadPanelIndex + 1);
    });

    badPanelDropdown.addEventListener('change', (e) => {
        renderBadPanelModal(parseInt(e.target.value, 10));
    });

    btnCloseBadModal.addEventListener('click', () => {
        badPanelsModal.style.display = 'none';
    });

    badPanelsModal.addEventListener('click', (e) => {
        if (e.target === badPanelsModal) badPanelsModal.style.display = 'none';
    });

    // ---------------- BALANCED GOOD CELLS SORTER (TAB 4: 3168 & NOT GOOD) ----------------

    btnLoadGoodSorter.addEventListener('click', async () => {
        const folderPath = goodSorterPathInput.value.trim();
        if (!folderPath) {
            alert('يرجى أدخال أو لصق مسار مجلد all good cells أولاً.');
            return;
        }

        showLoading('جاري فتح وإنشاء مجلدي 3168 و not good وحساب مصفوفة الخلايا الـ 144...');

        try {
            const formData = new FormData();
            formData.append('folder_path', folderPath);

            const res = await fetch('/api/good-sorter/init', {
                method: 'POST',
                body: formData
            });

            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.detail || 'حدث خطأ في تحميل مجلد الخلايا السليمة.');
            }

            const data = await res.json();
            goodFolderPath = data.folder_path;
            goodCellsList = data.cells;
            goodPosAcceptedCounts = data.pos_accepted_counts;
            goodPosRejectedCounts = data.pos_rejected_counts;
            goodActivePosition = data.active_position;
            allPositions = data.all_positions;

            if (goodCellsList.length === 0) {
                alert('ℹ️ المجلد فارغ! لا توجد صور خلايا سليمة في هذا المجلد.');
                return;
            }

            buildPositionMapGrid();
            goodSorterDashboard.style.display = 'flex';
            goodPosSubIndex = 0;
            renderGoodSorterCell();

            alert(`✅ تم تجهيز الفرز المتوازن بنجاح!\n\n📁 المجلدان 3168 و not good جاهزان.\n🎯 الموقع النشط الحالي: ${goodActivePosition}`);

        } catch (err) {
            alert(`❌ خطأ في تشغيل الفرز المتوازن: ${err.message}`);
        } finally {
            hideLoading();
        }
    });

    function buildPositionMapGrid() {
        positionMapGrid.innerHTML = '';
        allPositions.forEach((pos) => {
            const btn = document.createElement('div');
            btn.className = 'pos-map-btn';
            btn.dataset.pos = pos;
            btn.innerHTML = `
                <span class="id-txt">${pos}</span>
                <span class="cnt-txt" id="map-cnt-${pos}">0/22</span>
            `;
            btn.addEventListener('click', () => {
                goodActivePosition = pos;
                goodPosSubIndex = 0;
                renderGoodSorterCell();
            });
            positionMapGrid.appendChild(btn);
        });
    }

    function updatePositionMapGrid() {
        allPositions.forEach(pos => {
            const cnt = goodPosAcceptedCounts[pos] || 0;
            const cntEl = document.getElementById(`map-cnt-${pos}`);
            if (cntEl) cntEl.innerText = `${cnt}/22`;

            const btnEl = document.querySelector(`.pos-map-btn[data-pos="${pos}"]`);
            if (btnEl) {
                btnEl.classList.toggle('active-pos', pos === goodActivePosition);
                btnEl.classList.toggle('completed-pos', cnt >= 22);
            }
        });
    }

    // Returns unclassified cells queue specifically matching current active position
    function getActivePositionQueue() {
        const queue = goodCellsList.filter(c => c.cell_id === goodActivePosition && c.status === 'unclassified');
        if (queue.length > 0) return queue;
        // Fallback: return any cells for that position (even if evaluated, for viewing)
        return goodCellsList.filter(c => c.cell_id === goodActivePosition);
    }

    function renderGoodSorterCell() {
        // Check if current active position reached 22 target
        const currentPosAccepted = goodPosAcceptedCounts[goodActivePosition] || 0;
        if (currentPosAccepted >= 22) {
            // Find next position in ALL_POSITIONS that needs cells (< 22)
            const currentIdx = allPositions.indexOf(goodActivePosition);
            for (let i = 0; i < allPositions.length; i++) {
                const nextPos = allPositions[(currentIdx + i) % allPositions.length];
                if ((goodPosAcceptedCounts[nextPos] || 0) < 22) {
                    goodActivePosition = nextPos;
                    goodPosSubIndex = 0;
                    break;
                }
            }
        }

        const posQueue = getActivePositionQueue();

        if (posQueue.length === 0) {
            // No unclassified cells left for this position, move to next incomplete position
            let foundNext = false;
            for (let pos of allPositions) {
                if ((goodPosAcceptedCounts[pos] || 0) < 22) {
                    const testQueue = goodCellsList.filter(c => c.cell_id === pos && c.status === 'unclassified');
                    if (testQueue.length > 0) {
                        goodActivePosition = pos;
                        goodPosSubIndex = 0;
                        foundNext = true;
                        break;
                    }
                }
            }
            if (!foundNext && Object.values(goodPosAcceptedCounts).reduce((a, b) => a + b, 0) >= 3168) {
                triggerCelebrationSurprise();
                return;
            }
        }

        const activeQueue = getActivePositionQueue();
        if (activeQueue.length === 0) return;

        if (goodPosSubIndex < 0) goodPosSubIndex = 0;
        if (goodPosSubIndex >= activeQueue.length) goodPosSubIndex = activeQueue.length - 1;

        const cell = activeQueue[goodPosSubIndex];

        // 1. Update Active Position Header Badge
        const activePosIdx = allPositions.indexOf(goodActivePosition) + 1;
        goodActivePosBadge.innerText = `الموقع الحالي: ${goodActivePosition} (${activePosIdx} من 144)`;

        // 2. Update Header Progress Counters
        const acceptedForPos = goodPosAcceptedCounts[goodActivePosition] || 0;
        const totalAccepted = Object.values(goodPosAcceptedCounts).reduce((a, b) => a + b, 0);
        const totalRejected = Object.values(goodPosRejectedCounts).reduce((a, b) => a + b, 0);

        goodPosAcceptedCount.innerText = `${acceptedForPos} / 22`;
        goodTotalAcceptedCount.innerText = `${totalAccepted} / 3168`;
        goodTotalRejectedCount.innerText = `${totalRejected}`;

        // 3. Update Image Frame & Details
        goodCellFilenameTxt.innerText = cell.filename;
        goodCellFolderTag.innerText = cell.rel_folder;

        goodImgLoader.style.display = 'block';
        goodCellImg.src = `/api/cell-file-preview?path=${encodeURIComponent(cell.full_path)}`;
        goodCellImg.onload = () => goodImgLoader.style.display = 'none';
        goodCellImg.onerror = () => goodImgLoader.style.display = 'none';

        goodImgBadge.innerText = `${cell.cell_id} (${goodPosSubIndex + 1}/${activeQueue.length})`;

        // Update Position Map Grid
        updatePositionMapGrid();

        // Check if 3,168 completed
        if (totalAccepted >= 3168) {
            triggerCelebrationSurprise();
        }
    }

    async function handleGoodCellAction(action) {
        const activeQueue = getActivePositionQueue();
        if (activeQueue.length === 0 || goodPosSubIndex >= activeQueue.length) return;
        const currentCell = activeQueue[goodPosSubIndex];

        try {
            const formData = new FormData();
            formData.append('folder_path', goodFolderPath);
            formData.append('file_path', currentCell.full_path);
            formData.append('action', action);

            const res = await fetch('/api/good-sorter/action', {
                method: 'POST',
                body: formData
            });

            if (!res.ok) throw new Error('فشل تنفيذ العملية.');

            const data = await res.json();
            currentCell.full_path = data.new_path;
            currentCell.status = action;
            currentCell.rel_folder = `all good cells/${data.target_subfolder}/`;

            goodPosAcceptedCounts = data.pos_accepted_counts;
            goodPosRejectedCounts = data.pos_rejected_counts;
            goodActivePosition = data.active_position;

            // Render next cell for active position
            renderGoodSorterCell();

        } catch (err) {
            alert(`❌ خطأ أثناء الفرز: ${err.message}`);
        }
    }

    btnGoodAccept.addEventListener('click', () => handleGoodCellAction('accepted'));
    btnGoodReject.addEventListener('click', () => handleGoodCellAction('rejected'));

    btnGoodPrev.addEventListener('click', () => {
        if (goodPosSubIndex > 0) {
            goodPosSubIndex--;
            renderGoodSorterCell();
        }
    });

    btnGoodNext.addEventListener('click', () => {
        const activeQueue = getActivePositionQueue();
        if (goodPosSubIndex < activeQueue.length - 1) {
            goodPosSubIndex++;
            renderGoodSorterCell();
        }
    });

    // ---------------- BAD CELLS CLASSIFIER & SORTER (TAB 3) ----------------

    btnLoadSorter.addEventListener('click', async () => {
        const folderPath = sorterFolderPathInput.value.trim();
        if (!folderPath) {
            alert('يرجى أدخال أو لصق مسار مجلد all bad cells أولاً.');
            return;
        }

        showLoading('جاري فتح وإنشاء المجلدات الفرعية 6 (Cracks, Ribbons...) ومسح خلايا العيوب...');

        try {
            const formData = new FormData();
            formData.append('folder_path', folderPath);

            const res = await fetch('/api/sorter/init', {
                method: 'POST',
                body: formData
            });

            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.detail || 'حدث خطأ في تحميل مجلد الخلايا السيئة.');
            }

            const data = await res.json();
            sorterFolderPath = data.folder_path;
            sorterCellsList = data.cells;
            sorterCategoryCounts = data.category_counts;

            if (sorterCellsList.length === 0) {
                alert('ℹ️ المجلد فارغ! لا توجد صور خلايا معيبة للفرز في هذا المجلد.');
                return;
            }

            sorterDashboard.style.display = 'flex';
            sorterIndex = 0;
            renderSorterCell(0);

            alert(`✅ تم تجهيز الفرز بنجاح!\n\n📁 المجلدات الـ 6 جاهزة للاستقبال.\n📦 إجمالي الخلايا: ${data.total_cells}`);

        } catch (err) {
            alert(`❌ خطأ في تشغيل مصنف الفرز: ${err.message}`);
        } finally {
            hideLoading();
        }
    });

    function renderSorterCell(index) {
        if (index < 0 || index >= sorterCellsList.length) return;
        sorterIndex = index;
        const cell = sorterCellsList[index];

        sorterInfoPanel.innerText = cell.panel_name;
        sorterInfoCell.innerText = cell.cell_id;
        sorterInfoFolder.innerText = cell.rel_folder;

        const sortedCount = Object.values(sorterCategoryCounts).reduce((a, b) => a + b, 0);
        const totalCount = sorterCellsList.length;
        const remainingCount = Math.max(0, totalCount - sortedCount);

        sorterStatSorted.innerText = sortedCount.toLocaleString();
        sorterStatTotal.innerText = totalCount.toLocaleString();
        sorterStatRemaining.innerText = remainingCount.toLocaleString();

        sorterImgLoader.style.display = 'block';
        sorterCellImg.src = `/api/cell-file-preview?path=${encodeURIComponent(cell.full_path)}`;
        sorterCellImg.onload = () => sorterImgLoader.style.display = 'none';
        sorterCellImg.onerror = () => sorterImgLoader.style.display = 'none';

        sorterImgBadge.innerText = `الخلية ${index + 1} من ${totalCount}`;

        Object.keys(sorterCategoryCounts).forEach(cat => {
            const cntEl = document.getElementById(`cnt-${cat}`);
            if (cntEl) cntEl.innerText = `${sorterCategoryCounts[cat]} صورة`;
        });

        document.querySelectorAll('.btn-category').forEach(btn => {
            const cat = btn.dataset.cat;
            btn.classList.toggle('active-cat', cell.category === cat);
        });

        if (remainingCount === 0 && totalCount > 0) {
            triggerCelebrationSurprise();
        }
    }

    document.querySelectorAll('.btn-category').forEach(btn => {
        btn.addEventListener('click', async () => {
            if (sorterCellsList.length === 0 || sorterIndex >= sorterCellsList.length) return;

            const category = btn.dataset.cat;
            const currentCell = sorterCellsList[sorterIndex];

            try {
                const formData = new FormData();
                formData.append('folder_path', sorterFolderPath);
                formData.append('file_path', currentCell.full_path);
                formData.append('target_category', category);

                const res = await fetch('/api/sorter/move', {
                    method: 'POST',
                    body: formData
                });

                if (!res.ok) throw new Error('فشل نقل الصورة.');

                const data = await res.json();
                currentCell.full_path = data.new_path;
                currentCell.category = category;
                currentCell.rel_folder = `all bad cells/${category}/`;
                sorterCategoryCounts = data.category_counts;

                if (sorterIndex < sorterCellsList.length - 1) {
                    renderSorterCell(sorterIndex + 1);
                } else {
                    renderSorterCell(sorterIndex);
                }

            } catch (err) {
                alert(`❌ خطأ أثناء التصنيف: ${err.message}`);
            }
        });
    });

    btnSorterPrev.addEventListener('click', () => {
        if (sorterIndex > 0) renderSorterCell(sorterIndex - 1);
    });

    btnSorterNext.addEventListener('click', () => {
        if (sorterIndex < sorterCellsList.length - 1) renderSorterCell(sorterIndex + 1);
    });

    // Global Keyboard Shortcuts
    document.addEventListener('keydown', (e) => {
        // Mode 4 Keyboard Shortcuts (Good Cells Sorter)
        if (goodSorterModeContainer.style.display !== 'none' && goodSorterDashboard.style.display !== 'none') {
            if (e.key === '1' || e.key === 'Enter') {
                btnGoodAccept.click();
            } else if (e.key === '2' || e.key === 'Backspace') {
                btnGoodReject.click();
            } else if (e.key === 'ArrowRight') {
                btnGoodPrev.click();
            } else if (e.key === 'ArrowLeft') {
                btnGoodNext.click();
            }
            return;
        }

        // Mode 3 Keyboard Shortcuts (Bad Cells Sorter)
        if (sorterModeContainer.style.display !== 'none' && sorterDashboard.style.display !== 'none') {
            const categoryKeys = {
                '1': 'Cracks', '2': 'Ribbons', '3': 'Misalignment',
                '4': 'Impurity', '5': 'Missing', '6': 'other'
            };

            if (categoryKeys[e.key]) {
                const cat = categoryKeys[e.key];
                const btn = document.querySelector(`.btn-category[data-cat="${cat}"]`);
                if (btn) btn.click();
            } else if (e.key === 'ArrowRight') {
                if (sorterIndex < sorterCellsList.length - 1) renderSorterCell(sorterIndex + 1);
            } else if (e.key === 'ArrowLeft') {
                if (sorterIndex > 0) renderSorterCell(sorterIndex - 1);
            }
        }
    });

    function triggerCelebrationSurprise() {
        finalStatsGrid.innerHTML = '';
        const catIcons = {
            "Cracks": "fa-bolt-lightning text-red",
            "Ribbons": "fa-grip-lines-vertical text-gold",
            "Misalignment": "fa-arrows-rotate text-blue",
            "Impurity": "fa-bahai text-green",
            "Missing": "fa-square-minus text-purple",
            "other": "fa-cubes-stacked"
        };

        Object.keys(sorterCategoryCounts).forEach(cat => {
            const count = sorterCategoryCounts[cat];
            const iconClass = catIcons[cat] || "fa-folder";
            const item = document.createElement('div');
            item.className = 'final-stat-item';
            item.innerHTML = `
                <div class="lbl"><i class="fa-solid ${iconClass}"></i> ${cat}</div>
                <div class="val">${count.toLocaleString()}</div>
            `;
            finalStatsGrid.appendChild(item);
        });

        celebrationModal.style.display = 'flex';
    }

    btnCloseCelebration.addEventListener('click', () => {
        celebrationModal.style.display = 'none';
    });

    celebrationModal.addEventListener('click', (e) => {
        if (e.target === celebrationModal) celebrationModal.style.display = 'none';
    });

    // Helpers
    function showLoading(msg) {
        loadingMsg.innerText = msg;
        loadingOverlay.style.display = 'flex';
    }

    function hideLoading() {
        loadingOverlay.style.display = 'none';
    }
});
