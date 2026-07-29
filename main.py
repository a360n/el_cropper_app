import os
import io
import uuid
import zipfile
from typing import Dict, Any
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import Response, FileResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from cropper_engine import SolarPanelCropperEngine

app = FastAPI(title="EL Solar Panel Cell Cropper API", version="1.0.0")

# Enable CORS for local development flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for active sessions
# In production / local dev, holds the processed result dictionary keyed by session_id
SESSION_CACHE: Dict[str, Dict[str, Any]] = {}

# Directory for saving exported cell folders
EXPORT_BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exported_cells")
os.makedirs(EXPORT_BASE_DIR, exist_ok=True)

@app.post("/api/upload")
async def upload_panel_image(file: UploadFile = File(...)):
    """
    Receives uploaded .tif, .png, or .jpg panel image.
    Processes it through the 7-step cropping algorithm and caches the output.
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

        # Prepare cell overview metadata for frontend (without heavy binary payload)
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
    """Generates and downloads a ZIP file containing all 144 cell PNG images."""
    if session_id not in SESSION_CACHE:
        raise HTTPException(status_code=404, detail="Session not found.")

    session_data = SESSION_CACHE[session_id]
    orig_filename = os.path.splitext(session_data["filename"])[0]
    cells = session_data["result"]["cells"]

    zip_io = io.BytesIO()
    with zipfile.ZipFile(zip_io, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
        for cell_id, cell_data in cells.items():
            file_name_in_zip = f"{orig_filename}_{cell_id}.png"
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
    """Saves all 144 cell PNG images into a local workspace directory."""
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
        file_path = os.path.join(target_dir, f"{cell_id}.png")
        with open(file_path, "wb") as f:
            f.write(cell_data["png_bytes"])
        saved_count += 1

    return JSONResponse({
        "status": "success",
        "message": f"Successfully exported {saved_count} cells to directory.",
        "target_directory": target_dir,
        "saved_count": saved_count
    })

# Mount static web directory
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(STATIC_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def read_index():
    """Serves the main web UI page."""
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return Response(content="<h1>EL Cell Cropper App</h1><p>Static index.html loading...</p>", media_type="text/html")
