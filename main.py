import os
import io
import uuid
import json
import zipfile
import cv2
from typing import Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, BackgroundTasks
from fastapi.responses import Response, FileResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from cropper_engine import SolarPanelCropperEngine
from batch_cropper import process_batch_directory, find_panel_folders, parse_panel_info

app = FastAPI(title="EL Solar Panel Cell Cropper API", version="2.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSION_CACHE: Dict[str, Dict[str, Any]] = {}

EXPORT_BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exported_cells")
os.makedirs(EXPORT_BASE_DIR, exist_ok=True)

@app.post("/api/upload")
async def upload_panel_image(file: UploadFile = File(...)):
    """
    Receives uploaded single panel image (.tif / .png / .jpg).
    Passes it through process_tif.py & cropping engine and caches output.
    """
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
    """
    Processes an entire local root folder containing Good_models / bad_models.
    Crops panels, creates 'all cell' and 'bad cells' per panel, and aggregates
    'all good cells' and 'all bad cells' at root level.
    """
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
    """Scans a local folder and returns the count and list of panel folders discovered."""
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
    """
    Returns the list and details of all defective panels found inside folder_path (bad_models).
    Includes info.json metadata, list of bad cells, and panel directory paths.
    """
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
    """Renders a panel TIF image file as PNG on the fly for browser preview."""
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
    """Serves a local cell PNG image file."""
    path = path.strip('"\'')
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, media_type="image/png")

@app.get("/api/panel-image/{session_id}")
async def get_panel_image(session_id: str):
    """Serves the full padded panel PNG image for visual preview."""
    if session_id not in SESSION_CACHE:
        raise HTTPException(status_code=404, detail="Session not found.")

    png_bytes = SESSION_CACHE[session_id]["result"]["full_panel_png"]
    return Response(content=png_bytes, media_type="image/png")

@app.get("/api/cell-image/{session_id}/{cell_id}")
async def get_cell_image(session_id: str, cell_id: str):
    """Serves the 224x224 cropped PNG image for a specific cell (A1 to F24)."""
    cell_id = cell_id.upper()
    if session_id not in SESSION_CACHE:
        raise HTTPException(status_code=404, detail="Session not found.")

    cells = SESSION_CACHE[session_id]["result"]["cells"]
    if cell_id not in cells:
        raise HTTPException(status_code=404, detail=f"Cell {cell_id} not found.")

    cell_png_bytes = cells[cell_id]["png_bytes"]
    return Response(content=cell_png_bytes, media_type="image/png")

@app.get("/api/export/zip/{session_id}")
async def export_zip(session_id: str):
    """Generates and downloads a ZIP file containing all 144 cell PNG images named '[PanelName]-[CellID].png'."""
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
    """Saves all 144 cell PNG images into a local workspace directory named '[PanelName]-[CellID].png'."""
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
