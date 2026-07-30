import os
import sys
import time
import json
import re
import gc
import shutil
from typing import Dict, Any, List, Set, Callable, Optional
from cropper_engine import SolarPanelCropperEngine

def parse_defect_cell_ids(defects_list: List[str]) -> Set[str]:
    """
    Extracts cell IDs (e.g. A1..F24, A01..F24) from a defects array of strings.
    Example input: ["B03 CellDefect_Microcrack", "C05 CellDefect_BlackCore"]
    Returns set: {'B3', 'B03', 'C5', 'C05'}
    """
    cell_ids = set()
    for item in defects_list:
        match = re.search(r'\b([A-F])(0?[1-9]|1[0-9]|2[0-4])\b', item, re.IGNORECASE)
        if match:
            col = match.group(1).upper()
            num = int(match.group(2))
            cell_ids.add(f"{col}{num}")         # e.g. B3
            cell_ids.add(f"{col}{num:02d}")      # e.g. B03
    return cell_ids

def parse_panel_info(panel_dir: str) -> Dict[str, Any]:
    """
    Parses info.json if present, or falls back to reading .el file or folder metadata.
    Returns dict: {'is_defective': bool, 'defects': list, 'defective_cell_ids': set}
    """
    json_path = os.path.join(panel_dir, "info.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)
            defects = data.get("defects", [])
            is_defective = data.get("isDefective", False) or "FAIL" in str(data.get("status", "")).upper()
            cell_ids = parse_defect_cell_ids(defects)
            return {
                "is_defective": is_defective,
                "defects": defects,
                "defective_cell_ids": cell_ids
            }
        except Exception as e:
            print(f"⚠️ Warning: Could not parse {json_path}: {e}")

    # Fallback to .el file parsing if info.json is absent
    el_files = [f for f in os.listdir(panel_dir) if f.lower().endswith('.el')]
    if el_files:
        el_path = os.path.join(panel_dir, el_files[0])
        try:
            with open(el_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            defects = []
            defect_entries = re.findall(r'\|18\|(?:(?!\|18\|).)*?\|2\|([^|]+)\|3\|(\d+)', content, re.DOTALL)
            cols = ["A", "B", "C", "D", "E", "F"]
            for tag, cidx_str in defect_entries:
                if tag not in ["View_1", "Segment_1"]:
                    try:
                        cidx = int(cidx_str)
                        if 0 <= cidx < 144:
                            row_letter = cols[cidx // 24]
                            col_num = (cidx % 24) + 1
                            defects.append(f"{row_letter}{col_num:02d} {tag}")
                    except Exception:
                        pass
            cell_ids = parse_defect_cell_ids(defects)
            return {
                "is_defective": len(cell_ids) > 0,
                "defects": defects,
                "defective_cell_ids": cell_ids
            }
        except Exception:
            pass

    return {"is_defective": False, "defects": [], "defective_cell_ids": set()}

def find_panel_folders(root_dir: str) -> List[Dict[str, str]]:
    """
    Scans root_dir (which typically contains Good_models/ and bad_models/)
    and finds all panel folders containing .tif / .tiff / .pfile files.
    """
    panel_list = []
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        base_folder = os.path.basename(dirpath).lower()
        if base_folder in ['all cell', 'all_cell', 'all cells', 'bad cells', 'bad_cells', 'all good cells', 'all bad cells', 'exported_cells']:
            continue

        tif_files = [f for f in filenames if f.lower().endswith(('.tif', '.tiff', '.tif.pfile', '.tiff.pfile'))]
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
    1. Crops each panel into 144 cells and saves inside '[Panel_Dir]/all cell/' as '[PanelName]-[CellID].png'.
    2. For bad_models panels, extracts defective cells from info.json / .el and saves inside '[Panel_Dir]/bad cells/'.
    3. At root level, creates '[Root]/all good cells/' and '[Root]/all bad cells/' datasets aggregating all cells.
    """
    if not os.path.exists(root_dir):
        raise FileNotFoundError(f"Directory not found: {root_dir}")

    panels = find_panel_folders(root_dir)
    total_panels = len(panels)

    # Root-level aggregate dataset directories
    all_good_cells_dir = os.path.join(root_dir, "all good cells")
    all_bad_cells_dir = os.path.join(root_dir, "all bad cells")
    
    os.makedirs(all_good_cells_dir, exist_ok=True)
    os.makedirs(all_bad_cells_dir, exist_ok=True)

    results = {
        "root_dir": root_dir,
        "total_panels": total_panels,
        "success_count": 0,
        "error_count": 0,
        "total_good_cells_aggregated": 0,
        "total_bad_cells_aggregated": 0,
        "all_good_cells_dir": all_good_cells_dir,
        "all_bad_cells_dir": all_bad_cells_dir,
        "details": []
    }

    print(f"\n==========================================")
    print(f"🚀 بدء معالجة مجلد الألواح وتجهيز البيانات: {root_dir}")
    print(f"📊 إجمالي عدد الألواح المكتشفة: {total_panels:,} لوح")
    print(f"📁 مجلد تجميع الألواح السليمة: {all_good_cells_dir}")
    print(f"📁 مجلد تجميع خلايا العيوب: {all_bad_cells_dir}")
    print(f"==========================================\n")

    start_time = time.time()

    for idx, panel in enumerate(panels, 1):
        panel_dir = panel["panel_dir"]
        tif_path = panel["tif_path"]
        panel_name = panel["panel_name"]
        category = panel["category"]

        target_cell_dir = os.path.join(panel_dir, "all cell")
        target_bad_cell_dir = os.path.join(panel_dir, "bad cells")

        try:
            if tif_path.lower().endswith('.pfile'):
                raise ValueError(f"الملف مشفر بنظام PFILE: {os.path.basename(tif_path)}")

            # Parse panel info JSON / EL
            panel_info = parse_panel_info(panel_dir)
            defective_cell_ids = panel_info["defective_cell_ids"]

            with open(tif_path, 'rb') as f:
                file_bytes = f.read()

            image_bgr = SolarPanelCropperEngine.load_image(file_bytes)
            crop_res = SolarPanelCropperEngine.process_panel(image_bgr)

            os.makedirs(target_cell_dir, exist_ok=True)
            if category == "bad_models" or panel_info["is_defective"]:
                os.makedirs(target_bad_cell_dir, exist_ok=True)

            cells_dict = crop_res["cells"]
            saved_cells_count = 0
            saved_bad_cells_count = 0

            for cell_id, cell_data in cells_dict.items():
                cell_file_name = f"{panel_name}-{cell_id}.png"
                cell_file_path = os.path.join(target_cell_dir, cell_file_name)
                
                # Write to 'all cell/'
                with open(cell_file_path, "wb") as cf:
                    cf.write(cell_data["png_bytes"])
                saved_cells_count += 1

                # If panel is Good_models: copy to root 'all good cells/'
                if category == "Good_models":
                    dest_good_path = os.path.join(all_good_cells_dir, cell_file_name)
                    shutil.copyfile(cell_file_path, dest_good_path)
                    results["total_good_cells_aggregated"] += 1

                # If cell is defective (or panel in bad_models with defects):
                if category == "bad_models" or panel_info["is_defective"]:
                    # Match cell_id in defective_cell_ids (e.g. B3 or B03)
                    if cell_id in defective_cell_ids or any(cell_id == cid or cell_id == f"{cid[0]}{int(cid[1:]):02d}" for cid in defective_cell_ids if cid[1:].isdigit()):
                        bad_cell_path = os.path.join(target_bad_cell_dir, cell_file_name)
                        shutil.copyfile(cell_file_path, bad_cell_path)
                        saved_bad_cells_count += 1

                        # Copy to root 'all bad cells/'
                        dest_bad_path = os.path.join(all_bad_cells_dir, cell_file_name)
                        shutil.copyfile(cell_file_path, dest_bad_path)
                        results["total_bad_cells_aggregated"] += 1

            results["success_count"] += 1
            status_info = {
                "panel_name": panel_name,
                "category": category,
                "target_dir": target_cell_dir,
                "bad_cells_dir": target_bad_cell_dir if (category == "bad_models" or panel_info["is_defective"]) else None,
                "cells_count": saved_cells_count,
                "bad_cells_count": saved_bad_cells_count,
                "status": "SUCCESS"
            }
            results["details"].append(status_info)

            if idx % 50 == 0 or idx == total_panels:
                elapsed = time.time() - start_time
                rate = idx / elapsed if elapsed > 0 else 0
                remaining = (total_panels - idx) / rate if rate > 0 else 0
                print(f"⏳ [{idx:,}/{total_panels:,}] - نجاح: {results['success_count']:,} | Good خلايا: {results['total_good_cells_aggregated']:,} | Bad خلايا: {results['total_bad_cells_aggregated']:,} | السرعة: {rate:.1f} لوح/ثانية")

        except Exception as e:
            results["error_count"] += 1
            status_info = {
                "panel_name": panel_name,
                "category": category,
                "target_dir": target_cell_dir,
                "error": str(e),
                "status": "ERROR"
            }
            results["details"].append(status_info)
            print(f"❌ [{idx:,}/{total_panels:,}] خطأ في اللوح [{panel_name}]: {e}")

        if idx % 50 == 0:
            gc.collect()

        if progress_callback:
            progress_callback(idx, total_panels, status_info)

    elapsed = time.time() - start_time
    print(f"\n==========================================")
    print(f"🏁 اكتملت المعالجة الكلية وتجميع البيانات!")
    print(f"⏱️ الوقت الإجمالي: {elapsed/60:.2f} دقيقة")
    print(f"✅ ألواح ناجحة: {results['success_count']:,} لوح")
    print(f"📁 إجمالي خلايا all good cells: {results['total_good_cells_aggregated']:,} صورة PNG")
    print(f"📁 إجمالي خلايا all bad cells : {results['total_bad_cells_aggregated']:,} صورة PNG")
    print(f"⚠️ أخطاء: {results['error_count']}")
    print(f"==========================================\n")

    return results

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_dir = sys.argv[1]
    else:
        target_dir = input("أدخل مسار المجلد الرئيسي الذي يحتوي على Good_models / bad_models: ").strip('"\'')

    process_batch_directory(target_dir)
