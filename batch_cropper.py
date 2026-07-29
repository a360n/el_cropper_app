import os
import sys
import time
from typing import Dict, Any, List, Callable, Optional
from cropper_engine import SolarPanelCropperEngine

def find_panel_folders(root_dir: str) -> List[Dict[str, str]]:
    """
    Scans root_dir (which typically contains Good_models/ and bad_models/)
    and finds all panel folders containing .tif / .tiff / .pfile files.
    Returns a list of dicts: [{'panel_dir': ..., 'tif_path': ..., 'category': ...}]
    """
    panel_list = []
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Skip 'all cell' directories from recursive scanning
        if os.path.basename(dirpath).lower() in ['all cell', 'all_cell', 'all cells', 'exported_cells']:
            continue

        tif_files = [f for f in filenames if f.lower().endswith(('.tif', '.tiff', '.tif.pfile', '.tiff.pfile'))]
        
        # Fallback: check if any file has .pfile extension
        if not tif_files:
            tif_files = [f for f in filenames if f.lower().endswith('.pfile') and not f.startswith('$')]

        if tif_files:
            primary_tif = tif_files[0]
            for f in tif_files:
                if 'row' in f.lower() or 'marked' in f.lower():
                    primary_tif = f
                    break

            full_tif_path = os.path.join(dirpath, primary_tif)

            rel_path = os.path.relpath(dirpath, root_dir)
            category = "Unknown"
            if "good_models" in rel_path.lower():
                category = "Good_models"
            elif "bad_models" in rel_path.lower():
                category = "bad_models"

            panel_name = os.path.basename(dirpath)

            panel_list.append({
                "panel_name": panel_name,
                "panel_dir": dirpath,
                "tif_path": full_tif_path,
                "category": category,
                "rel_path": rel_path
            })

    return panel_list

def process_batch_directory(
    root_dir: str,
    progress_callback: Optional[Callable[[int, int, Dict[str, Any]], None]] = None
) -> Dict[str, Any]:
    """
    Processes all panel folders inside root_dir:
    1. Finds all panel folders containing .tif / .pfile images.
    2. Runs each panel image through process_tif + cropper engine.
    3. Saves 144 cell PNG images inside 'all cell/' inside each panel folder.
    """
    if not os.path.exists(root_dir):
        raise FileNotFoundError(f"Directory not found: {root_dir}")

    panels = find_panel_folders(root_dir)
    total_panels = len(panels)

    results = {
        "root_dir": root_dir,
        "total_panels": total_panels,
        "success_count": 0,
        "error_count": 0,
        "details": []
    }

    print(f"\n==========================================")
    print(f"🚀 بدء معالجة مجلد الألواح: {root_dir}")
    print(f"📊 إجمالي عدد الألواح المكتشفة: {total_panels}")
    print(f"==========================================\n")

    for idx, panel in enumerate(panels, 1):
        panel_dir = panel["panel_dir"]
        tif_path = panel["tif_path"]
        panel_name = panel["panel_name"]

        target_cell_dir = os.path.join(panel_dir, "all cell")

        try:
            if tif_path.lower().endswith('.pfile'):
                raise ValueError(f"الملف مشفر بنظام التشفير (RMS/PFILE): {os.path.basename(tif_path)}")

            with open(tif_path, 'rb') as f:
                file_bytes = f.read()

            image_bgr = SolarPanelCropperEngine.load_image(file_bytes)
            crop_res = SolarPanelCropperEngine.process_panel(image_bgr)

            os.makedirs(target_cell_dir, exist_ok=True)

            cells_dict = crop_res["cells"]
            saved_cells_count = 0
            for cell_id, cell_data in cells_dict.items():
                cell_file_path = os.path.join(target_cell_dir, f"{cell_id}.png")
                with open(cell_file_path, "wb") as cf:
                    cf.write(cell_data["png_bytes"])
                saved_cells_count += 1

            results["success_count"] += 1
            status_info = {
                "panel_name": panel_name,
                "category": panel["category"],
                "target_dir": target_cell_dir,
                "cells_count": saved_cells_count,
                "status": "SUCCESS"
            }
            results["details"].append(status_info)

            print(f"✅ [{idx}/{total_panels}] تم تقطيع اللوح [{panel_name}] -> وحفظ 144 خلية في '{target_cell_dir}'")

        except Exception as e:
            results["error_count"] += 1
            status_info = {
                "panel_name": panel_name,
                "category": panel["category"],
                "target_dir": target_cell_dir,
                "error": str(e),
                "status": "ERROR"
            }
            results["details"].append(status_info)
            print(f"❌ [{idx}/{total_panels}] خطأ في معالجة اللوح [{panel_name}]: {e}")

        if progress_callback:
            progress_callback(idx, total_panels, status_info)

    print(f"\n==========================================")
    print(f"🏁 اكتملت المعالجة التلقائية دفعة واحدة!")
    print(f"✅ ناجحة: {results['success_count']}")
    print(f"⚠️ أخطاء: {results['error_count']}")
    print(f"==========================================\n")

    return results

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_dir = sys.argv[1]
    else:
        target_dir = input("أدخل مسار المجلد الرئيسي الذي يحتوي على Good_models / bad_models: ").strip('"\'')

    process_batch_directory(target_dir)
