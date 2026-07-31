import os
import io
import uuid
import json
import zipfile
import shutil
import re
import cv2
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, BackgroundTasks
from fastapi.responses import Response, FileResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from cropper_engine import SolarPanelCropperEngine
from batch_cropper import process_batch_directory, find_panel_folders, parse_panel_info

app = FastAPI(title="EL Solar Panel Cell Cropper API", version="3.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSION_CACHE: Dict[str, Dict[str, Any]] = {}
CATEGORIES = ["Cracks", "Ribbons", "Misalignment", "Impurity", "Missing", "other"]

# Generate ordered list of 144 positions: A1..A24, B1..B24, ..., F1..F24
ALL_POSITIONS = []
for c in ['A', 'B', 'C', 'D', 'E', 'F']:
    for r in range(1, 25):
        ALL_POSITIONS.append(f"{c}{r}")

def normalize_pos_id(cell_id: str) -> str:
    """Normalizes cell IDs like A01 -> A1, B09 -> B9, F24 -> F24."""
    cell_id = cell_id.strip()
    match = re.match(r'^([A-F])(0?(\d+))$', cell_id, re.IGNORECASE)
    if match:
        col = match.group(1).upper()
        num = int(match.group(3))
        return f"{col}{num}"
    return cell_id.upper()

EXPORT_BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exported_cells")
os.makedirs(EXPORT_BASE_DIR, exist_ok=True)

# ----------------- BALANCED GOOD CELLS SORTER (3168 & not good) API -----------------

@app.post("/api/good-sorter/init")
async def init_good_cells_sorter(folder_path: str = Form(...)):
    """
    Initializes Balanced Good Cells Filter for 'all good cells' folder:
    1. Creates subfolders '3168' and 'not good'.
    2. Scans all PNG cell images in 'all good cells' (root, 3168, not good).
    3. Groups files by normalized cell position (A1..A24, B1..B24, ..., F24).
    4. Calculates accepted count per position (target 22 per position A1-F24).
    5. Determines active position (A1 -> A2 -> ... -> F24) and returns cell queue.
    """
    folder_path = folder_path.strip('"\'')
    if not os.path.exists(folder_path):
        raise HTTPException(status_code=404, detail=f"المجلد غير موجود: {folder_path}")

    dir_3168 = os.path.join(folder_path, "3168")
    dir_not_good = os.path.join(folder_path, "not good")
    os.makedirs(dir_3168, exist_ok=True)
    os.makedirs(dir_not_good, exist_ok=True)

    pos_accepted_counts = {p: 0 for p in ALL_POSITIONS}
    pos_rejected_counts = {p: 0 for p in ALL_POSITIONS}

    # Count files in '3168' (accepted)
    for f in os.listdir(dir_3168):
        if f.lower().endswith(('.png', '.jpg', '.jpeg')):
            parts = f.replace('.png', '').replace('.jpg', '').replace('.jpeg', '').split('-')
            raw_id = parts[-1] if len(parts) > 1 else ""
            cell_id = normalize_pos_id(raw_id)
            if cell_id in pos_accepted_counts:
                pos_accepted_counts[cell_id] += 1

    # Count files in 'not good' (rejected)
    for f in os.listdir(dir_not_good):
        if f.lower().endswith(('.png', '.jpg', '.jpeg')):
            parts = f.replace('.png', '').replace('.jpg', '').replace('.jpeg', '').split('-')
            raw_id = parts[-1] if len(parts) > 1 else ""
            cell_id = normalize_pos_id(raw_id)
            if cell_id in pos_rejected_counts:
                pos_rejected_counts[cell_id] += 1

    all_cells_list = []

    # 1. Unclassified files in root
    for f in sorted(os.listdir(folder_path)):
        full_p = os.path.join(folder_path, f)
        if os.path.isfile(full_p) and f.lower().endswith(('.png', '.jpg', '.jpeg')):
            parts = f.replace('.png', '').replace('.jpg', '').replace('.jpeg', '').split('-')
            raw_id = parts[-1] if len(parts) > 1 else "A1"
            cell_id = normalize_pos_id(raw_id)
            panel_name = "-".join(parts[:-1]) if len(parts) > 1 else "Unknown"

            all_cells_list.append({
                "filename": f,
                "full_path": full_p,
                "panel_name": panel_name,
                "cell_id": cell_id,
                "status": "unclassified",
                "rel_folder": "all good cells/"
            })

    # 2. Accepted files in '3168'
    for f in sorted(os.listdir(dir_3168)):
        full_p = os.path.join(dir_3168, f)
        if os.path.isfile(full_p) and f.lower().endswith(('.png', '.jpg', '.jpeg')):
            parts = f.replace('.png', '').replace('.jpg', '').replace('.jpeg', '').split('-')
            raw_id = parts[-1] if len(parts) > 1 else "A1"
            cell_id = normalize_pos_id(raw_id)
            panel_name = "-".join(parts[:-1]) if len(parts) > 1 else "Unknown"

            all_cells_list.append({
                "filename": f,
                "full_path": full_p,
                "panel_name": panel_name,
                "cell_id": cell_id,
                "status": "accepted",
                "rel_folder": "all good cells/3168/"
            })

    # 3. Rejected files in 'not good'
    for f in sorted(os.listdir(dir_not_good)):
        full_p = os.path.join(dir_not_good, f)
        if os.path.isfile(full_p) and f.lower().endswith(('.png', '.jpg', '.jpeg')):
            parts = f.replace('.png', '').replace('.jpg', '').replace('.jpeg', '').split('-')
            raw_id = parts[-1] if len(parts) > 1 else "A1"
            cell_id = normalize_pos_id(raw_id)
            panel_name = "-".join(parts[:-1]) if len(parts) > 1 else "Unknown"

            all_cells_list.append({
                "filename": f,
                "full_path": full_p,
                "panel_name": panel_name,
                "cell_id": cell_id,
                "status": "rejected",
                "rel_folder": "all good cells/not good/"
            })

    total_accepted = sum(pos_accepted_counts.values())
    total_rejected = sum(pos_rejected_counts.values())

    # Determine active position sequentially (first position where accepted < 22)
    active_position = ALL_POSITIONS[0]
    for pos in ALL_POSITIONS:
        if pos_accepted_counts[pos] < 22:
            active_position = pos
            break

    return JSONResponse({
        "folder_path": folder_path,
        "total_cells": len(all_cells_list),
        "total_accepted": total_accepted,
        "total_rejected": total_rejected,
        "target_total": 3168,
        "target_per_position": 22,
        "active_position": active_position,
        "pos_accepted_counts": pos_accepted_counts,
        "pos_rejected_counts": pos_rejected_counts,
        "cells": all_cells_list,
        "all_positions": ALL_POSITIONS
    })

@app.post("/api/good-sorter/action")
async def good_cells_sorter_action(
    folder_path: str = Form(...),
    file_path: str = Form(...),
    action: str = Form(...) # 'accepted' or 'rejected'
):
    """
    Moves cell image to '3168' if accepted or 'not good' if rejected.
    Returns updated position counts and active position.
    """
    folder_path = folder_path.strip('"\'')
    file_path = file_path.strip('"\'')
    action = action.strip().lower()

    if action not in ['accepted', 'rejected']:
        raise HTTPException(status_code=400, detail="Action must be 'accepted' or 'rejected'")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    filename = os.path.basename(file_path)
    target_sub = "3168" if action == "accepted" else "not good"
    target_dir = os.path.join(folder_path, target_sub)
    os.makedirs(target_dir, exist_ok=True)

    new_full_path = os.path.join(target_dir, filename)
    if file_path != new_full_path:
        shutil.move(file_path, new_full_path)

    dir_3168 = os.path.join(folder_path, "3168")
    dir_not_good = os.path.join(folder_path, "not good")

    pos_accepted_counts = {p: 0 for p in ALL_POSITIONS}
    pos_rejected_counts = {p: 0 for p in ALL_POSITIONS}

    if os.path.exists(dir_3168):
        for f in os.listdir(dir_3168):
            if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                parts = f.replace('.png', '').replace('.jpg', '').replace('.jpeg', '').split('-')
                raw_id = parts[-1] if len(parts) > 1 else ""
                cell_id = normalize_pos_id(raw_id)
                if cell_id in pos_accepted_counts:
                    pos_accepted_counts[cell_id] += 1

    if os.path.exists(dir_not_good):
        for f in os.listdir(dir_not_good):
            if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                parts = f.replace('.png', '').replace('.jpg', '').replace('.jpeg', '').split('-')
                raw_id = parts[-1] if len(parts) > 1 else ""
                cell_id = normalize_pos_id(raw_id)
                if cell_id in pos_rejected_counts:
                    pos_rejected_counts[cell_id] += 1

    total_accepted = sum(pos_accepted_counts.values())
    total_rejected = sum(pos_rejected_counts.values())

    active_position = ALL_POSITIONS[0]
    for pos in ALL_POSITIONS:
        if pos_accepted_counts[pos] < 22:
            active_position = pos
            break

    return JSONResponse({
        "status": "success",
        "old_path": file_path,
        "new_path": new_full_path,
        "action": action,
        "target_subfolder": target_sub,
        "total_accepted": total_accepted,
        "total_rejected": total_rejected,
        "active_position": active_position,
        "pos_accepted_counts": pos_accepted_counts,
        "pos_rejected_counts": pos_rejected_counts
    })

# ----------------- BAD CELLS SORTER API -----------------

@app.post("/api/sorter/init")
async def init_bad_cells_sorter(folder_path: str = Form(...)):
    folder_path = folder_path.strip('"\'')
    if not os.path.exists(folder_path):
        raise HTTPException(status_code=404, detail=f"المجلد غير موجود: {folder_path}")

    category_counts = {}
    for cat in CATEGORIES:
        cat_dir = os.path.join(folder_path, cat)
        os.makedirs(cat_dir, exist_ok=True)
        category_counts[cat] = 0

    cell_files_list = []
    
    for f in sorted(os.listdir(folder_path)):
        full_p = os.path.join(folder_path, f)
        if os.path.isfile(full_p) and f.lower().endswith(('.png', '.jpg', '.jpeg')):
            filename_clean = f.replace('.png', '').replace('.jpg', '').replace('.jpeg', '')
            parts = filename_clean.split('-')
            cell_id = parts[-1] if len(parts) > 1 else filename_clean
            panel_name = "-".join(parts[:-1]) if len(parts) > 1 else "Unknown"

            cell_files_list.append({
                "filename": f,
                "full_path": full_p,
                "panel_name": panel_name,
                "cell_id": cell_id,
                "category": "unclassified",
                "rel_folder": "all bad cells/"
            })

    for cat in CATEGORIES:
        cat_dir = os.path.join(folder_path, cat)
        if os.path.exists(cat_dir):
            cat_files = [f for f in sorted(os.listdir(cat_dir)) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            category_counts[cat] = len(cat_files)
            for f in cat_files:
                full_p = os.path.join(cat_dir, f)
                filename_clean = f.replace('.png', '').replace('.jpg', '').replace('.jpeg', '')
                parts = filename_clean.split('-')
                cell_id = parts[-1] if len(parts) > 1 else filename_clean
                panel_name = "-".join(parts[:-1]) if len(parts) > 1 else "Unknown"

                cell_files_list.append({
                    "filename": f,
                    "full_path": full_p,
                    "panel_name": panel_name,
                    "cell_id": cell_id,
                    "category": cat,
                    "rel_folder": f"all bad cells/{cat}/"
                })

    total_cells = len(cell_files_list)
    sorted_cells = sum(category_counts.values())
    remaining_cells = total_cells - sorted_cells

    return JSONResponse({
        "folder_path": folder_path,
        "total_cells": total_cells,
        "sorted_cells": sorted_cells,
        "remaining_cells": remaining_cells,
        "category_counts": category_counts,
        "cells": cell_files_list
    })

@app.post("/api/sorter/move")
async def move_cell_to_category(
    folder_path: str = Form(...),
    file_path: str = Form(...),
    target_category: str = Form(...)
):
    folder_path = folder_path.strip('"\'')
    file_path = file_path.strip('"\'')
    target_category = target_category.strip()

    if target_category not in CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category: {target_category}")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    filename = os.path.basename(file_path)
    target_dir = os.path.join(folder_path, target_category)
    os.makedirs(target_dir, exist_ok=True)
    new_full_path = os.path.join(target_dir, filename)

    if file_path != new_full_path:
        shutil.move(file_path, new_full_path)

    category_counts = {}
    total_sorted = 0
    for cat in CATEGORIES:
        cat_dir = os.path.join(folder_path, cat)
        if os.path.exists(cat_dir):
            count = len([f for f in os.listdir(cat_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
            category_counts[cat] = count
            total_sorted += count
        else:
            category_counts[cat] = 0

    return JSONResponse({
        "status": "success",
        "old_path": file_path,
        "new_path": new_full_path,
        "category": target_category,
        "category_counts": category_counts,
        "total_sorted": total_sorted
    })

# ----------------- BASE API -----------------

@app.post("/api/upload")
async def upload_panel_image(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected.")
    try:
        contents = await file.read()
        image_bgr = SolarPanelCropperEngine.load_image(contents)
        result = SolarPanelCropperEngine.process_panel(image_bgr)

        session_id = str(uuid.uuid4())
        SESSION_CACHE[session_id] = {
            "filename": file.filename,
            "result": result
        }

        cell_summary = []
        for cell_id, cell_data in result["cells"].items():
            cell_summary.append({
                "id": cell_id,
                "col": cell_data["col"],
                "row": cell_data["row"],
                "bbox": cell_data["bbox_padded"],
                "center": cell_data["center"]
            })

        return JSONResponse({
            "status": "success",
            "session_id": session_id,
            "filename": file.filename,
            "metadata": result["metadata"],
            "grid_overlay": result["grid_overlay"],
            "cells": cell_summary
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image processing error: {str(e)}")

@app.post("/api/batch-process")
async def batch_process_folder(folder_path: str = Form(...)):
    folder_path = folder_path.strip('"\'')
    if not os.path.exists(folder_path):
        raise HTTPException(status_code=404, detail=f"المجلد غير موجود: {folder_path}")
    try:
        results = process_batch_directory(folder_path)
        return JSONResponse({
            "status": "success",
            "message": f"تمت معالجة {results['success_count']} لوح من إجمالي {results['total_panels']} بنجاح.",
            "results": results
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ أثناء معالجة الدفعة: {str(e)}")

@app.get("/api/scan-folder")
async def scan_folder_info(folder_path: str):
    folder_path = folder_path.strip('"\'')
    if not os.path.exists(folder_path):
        raise HTTPException(status_code=404, detail=f"المجلد غير موجود: {folder_path}")
    panels = find_panel_folders(folder_path)
    return JSONResponse({
        "folder_path": folder_path,
        "total_panels": len(panels),
        "panels": panels
    })

@app.get("/api/bad-panels-list")
async def get_bad_panels_list(folder_path: str):
    folder_path = folder_path.strip('"\'')
    if not os.path.exists(folder_path):
        raise HTTPException(status_code=404, detail=f"المجلد غير موجود: {folder_path}")

    all_panels = find_panel_folders(folder_path)
    bad_panels = []

    for panel in all_panels:
        category = panel["category"]
        panel_dir = panel["panel_dir"]
        info = parse_panel_info(panel_dir)

        if category == "bad_models" or info["is_defective"] or len(info["defective_cell_ids"]) > 0:
            bad_cell_dir = os.path.join(panel_dir, "bad cells")
            bad_cell_files = []
            if os.path.exists(bad_cell_dir):
                bad_cell_files = [
                    {"filename": f, "path": os.path.join(bad_cell_dir, f)}
                    for f in sorted(os.listdir(bad_cell_dir)) if f.endswith(".png")
                ]

            raw_json = {}
            json_path = os.path.join(panel_dir, "info.json")
            if os.path.exists(json_path):
                try:
                    with open(json_path, "r", encoding="utf-8", errors="ignore") as f:
                        raw_json = json.load(f)
                except Exception:
                    pass

            bad_panels.append({
                "panel_name": panel["panel_name"],
                "panel_dir": panel_dir,
                "tif_path": panel["tif_path"],
                "category": category,
                "info": {
                    "is_defective": info["is_defective"],
                    "defects": info["defects"],
                    "defective_cell_ids": sorted(list(info["defective_cell_ids"]))
                },
                "raw_json": raw_json,
                "bad_cell_files": bad_cell_files
            })

    return JSONResponse({
        "folder_path": folder_path,
        "total_bad_panels": len(bad_panels),
        "bad_panels": bad_panels
    })

@app.get("/api/panel-file-preview")
async def preview_panel_file(path: str):
    path = path.strip('"\'')
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    try:
        with open(path, "rb") as f:
            file_bytes = f.read()
        image_bgr = SolarPanelCropperEngine.load_image(file_bytes)
        _, png_buf = cv2.imencode('.png', image_bgr)
        return Response(content=png_buf.tobytes(), media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/cell-file-preview")
async def preview_cell_file(path: str):
    path = path.strip('"\'')
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, media_type="image/png")

@app.get("/api/panel-image/{session_id}")
async def get_panel_image(session_id: str):
    if session_id not in SESSION_CACHE:
        raise HTTPException(status_code=404, detail="Session not found.")
    png_bytes = SESSION_CACHE[session_id]["result"]["full_panel_png"]
    return Response(content=png_bytes, media_type="image/png")

@app.get("/api/cell-image/{session_id}/{cell_id}")
async def get_cell_image(session_id: str, cell_id: str):
    cell_id = cell_id.upper()
    if session_id not in SESSION_CACHE:
        raise HTTPException(status_code=404, detail="Session not found.")
    cells = SESSION_CACHE[session_id]["result"]["cells"]
    if cell_id not in cells:
        raise HTTPException(status_code=404, detail=f"Cell {cell_id} not found.")
    return Response(content=cells[cell_id]["png_bytes"], media_type="image/png")

@app.get("/api/export/zip/{session_id}")
async def export_zip(session_id: str):
    if session_id not in SESSION_CACHE:
        raise HTTPException(status_code=404, detail="Session not found.")
    session_data = SESSION_CACHE[session_id]
    orig_filename = os.path.splitext(session_data["filename"])[0]
    cells = session_data["result"]["cells"]

    zip_io = io.BytesIO()
    with zipfile.ZipFile(zip_io, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
        for cell_id, cell_data in cells.items():
            file_name_in_zip = f"{orig_filename}-{cell_id}.png"
            zf.writestr(file_name_in_zip, cell_data["png_bytes"])

    zip_io.seek(0)
    zip_filename = f"{orig_filename}_cells_A1-F24.zip"
    return StreamingResponse(
        zip_io,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'}
    )

@app.post("/api/export/folder/{session_id}")
async def export_to_folder(session_id: str, custom_path: str = Form(None)):
    if session_id not in SESSION_CACHE:
        raise HTTPException(status_code=404, detail="Session not found.")
    session_data = SESSION_CACHE[session_id]
    orig_filename = os.path.splitext(session_data["filename"])[0]
    cells = session_data["result"]["cells"]

    if custom_path and custom_path.strip():
        target_dir = os.path.abspath(custom_path.strip())
    else:
        target_dir = os.path.join(EXPORT_BASE_DIR, orig_filename)

    os.makedirs(target_dir, exist_ok=True)
    saved_count = 0
    for cell_id, cell_data in cells.items():
        file_path = os.path.join(target_dir, f"{orig_filename}-{cell_id}.png")
        with open(file_path, "wb") as f:
            f.write(cell_data["png_bytes"])
        saved_count += 1

    return JSONResponse({
        "status": "success",
        "message": f"تم حفظ {saved_count} خلية بنجاح.",
        "target_directory": target_dir,
        "saved_count": saved_count
    })

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(STATIC_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def read_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return Response(content="<h1>EL Cell Cropper App</h1>", media_type="text/html")
