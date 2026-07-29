import cv2
import numpy as np
from PIL import Image
import io
import os
from typing import Dict, Any, List, Tuple

class SolarPanelCropperEngine:
    """
    Solar Panel EL Image Cropper Engine
    Implements the exact 7-step cropping algorithm with perfected 4-sided reflection padding:
    1. Ensure even height.
    2. Aspect ratio correction (MH = 2 * MW) via equal cropping.
    3. Calculate CH = MW / 6, CW = MH / 24.
    4. Add reflection padding on all 4 sides so top/bottom reflection perfectly matches left/right:
       - pad_x = (SL - CH) / 2 = 0.15 * CH
       - pad_y = (SL - CW) / 2 = 0.80 * CW (since SL = 1.3 * CH = 2.6 * CW)
       - Padded dimensions: NMW = MW + 0.3 * CH, NMH = MH + 1.6 * CW.
    5. Calculate square cell size SL = CH + 0.3*CH = 1.3*CH.
    6. Extract 144 square cell patches (A1-F24) with complete, non-distorted reflection.
    7. Resize patches to 224x224 PNG.
    """

    @staticmethod
    def load_image(file_bytes: bytes) -> np.ndarray:
        """Loads an image from raw bytes (supports TIF, PNG, JPG)."""
        try:
            pil_img = Image.open(io.BytesIO(file_bytes))
            if pil_img.mode != 'RGB':
                pil_img = pil_img.convert('RGB')
            img_np = np.array(pil_img)
            return cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        except Exception:
            np_arr = np.frombuffer(file_bytes, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Could not decode image bytes. Supported formats: TIF, PNG, JPG.")
            return img

    @classmethod
    def process_panel(cls, image_bgr: np.ndarray, target_cell_size: Tuple[int, int] = (224, 224)) -> Dict[str, Any]:
        """
        Executes the full pipeline on a panel image.
        Returns metadata, full processed panel, grid boundaries, and 144 cell images.
        """
        orig_h, orig_w = image_bgr.shape[:2]

        # Step 1: Ensure height is even
        if orig_h % 2 != 0:
            image_step1 = image_bgr[0:orig_h - 1, :]
        else:
            image_step1 = image_bgr.copy()
        
        h1, w1 = image_step1.shape[:2]

        # Step 2: Aspect ratio correction (MH = 2 * MW)
        if (h1 / 2.0) < w1:
            target_mw = int(round(h1 / 2.0))
            crop_diff = w1 - target_mw
            left_crop = crop_diff // 2
            right_crop = left_crop + target_mw
            model_img = image_step1[:, left_crop:right_crop]
        elif (h1 / 2.0) > w1:
            target_mh = int(round(2.0 * w1))
            crop_diff = h1 - target_mh
            top_crop = crop_diff // 2
            bottom_crop = top_crop + target_mh
            model_img = image_step1[top_crop:bottom_crop, :]
        else:
            model_img = image_step1.copy()

        mh, mw = model_img.shape[:2]

        # Step 3: Base cell calculations
        ch = mw / 6.0   # Horizontal cell length along X axis (6 cols A-F)
        cw = mh / 24.0  # Vertical cell length along Y axis (24 rows 1-24)

        # Step 5: Square side length SL = 1.3 * CH
        sl_float = 1.3 * ch
        sl_px = int(round(sl_float))

        # Step 4: Perfected 4-sided reflection padding
        # To make top & bottom reflection as ideal and complete as left & right:
        # pad_x = (SL - CH) / 2 = 0.15 * CH
        # pad_y = (SL - CW) / 2 = 0.80 * CW
        pad_x_float = (sl_float - ch) / 2.0
        pad_y_float = (sl_float - cw) / 2.0

        pad_x = int(round(pad_x_float))
        pad_y = int(round(pad_y_float))

        padded_img = cv2.copyMakeBorder(
            model_img,
            top=pad_y,
            bottom=pad_y,
            left=pad_x,
            right=pad_x,
            borderType=cv2.BORDER_REFLECT_101
        )

        nmh, nmw = padded_img.shape[:2]

        # Step 6 & 7: Grid slicing and resizing
        cols = ['A', 'B', 'C', 'D', 'E', 'F']
        cells_dict = {}
        grid_overlay_info = []

        for r_idx in range(24):      # Rows 1 to 24
            for c_idx in range(6):   # Cols A to F
                col_name = cols[c_idx]
                row_name = r_idx + 1
                cell_id = f"{col_name}{row_name}"

                # Cell center in padded image coordinates
                cx = pad_x_float + (c_idx + 0.5) * ch
                cy = pad_y_float + (r_idx + 0.5) * cw

                # Square crop box boundaries
                x_start = int(round(cx - sl_float / 2.0))
                y_start = int(round(cy - sl_float / 2.0))
                x_end = x_start + sl_px
                y_end = y_start + sl_px

                # Clamp safely to padded image bounds
                x_start_clamped = max(0, x_start)
                y_start_clamped = max(0, y_start)
                x_end_clamped = min(nmw, x_end)
                y_end_clamped = min(nmh, y_end)

                # Extract patch
                patch = padded_img[y_start_clamped:y_end_clamped, x_start_clamped:x_end_clamped]

                # Resize patch directly to target_cell_size (224x224)
                if patch.size > 0:
                    resized_patch = cv2.resize(patch, target_cell_size, interpolation=cv2.INTER_CUBIC)
                else:
                    resized_patch = np.zeros((target_cell_size[1], target_cell_size[0], 3), dtype=np.uint8)

                # Encode cell image to PNG bytes
                _, png_buf = cv2.imencode('.png', resized_patch)
                cell_png_bytes = png_buf.tobytes()

                cells_dict[cell_id] = {
                    "id": cell_id,
                    "col": col_name,
                    "row": row_name,
                    "col_idx": c_idx,
                    "row_idx": r_idx,
                    "bbox_padded": {
                        "x": x_start_clamped,
                        "y": y_start_clamped,
                        "w": x_end_clamped - x_start_clamped,
                        "h": y_end_clamped - y_start_clamped
                    },
                    "center": {"x": cx, "y": cy},
                    "png_bytes": cell_png_bytes
                }

                grid_overlay_info.append({
                    "id": cell_id,
                    "x": x_start_clamped,
                    "y": y_start_clamped,
                    "w": x_end_clamped - x_start_clamped,
                    "h": y_end_clamped - y_start_clamped,
                    "cx": cx,
                    "cy": cy
                })

        # Encode full padded panel image to PNG for frontend preview
        _, full_png_buf = cv2.imencode('.png', padded_img)
        full_panel_png_bytes = full_png_buf.tobytes()

        # Encode unpadded model image
        _, model_png_buf = cv2.imencode('.png', model_img)
        model_panel_png_bytes = model_png_buf.tobytes()

        metadata = {
            "original_dimensions": {"width": orig_w, "height": orig_h},
            "model_dimensions": {"width": mw, "height": mh},
            "padded_dimensions": {"width": nmw, "height": nmh},
            "base_cell": {"CH": ch, "CW": cw},
            "padding": {"pad_x": pad_x_float, "pad_y": pad_y_float},
            "square_length_SL": sl_float,
            "square_length_px": sl_px,
            "total_cells": len(cells_dict),
            "target_cell_size": f"{target_cell_size[0]}x{target_cell_size[1]}"
        }

        return {
            "metadata": metadata,
            "full_panel_png": full_panel_png_bytes,
            "model_panel_png": model_panel_png_bytes,
            "grid_overlay": grid_overlay_info,
            "cells": cells_dict
        }

if __name__ == "__main__":
    print("Testing perfected SolarPanelCropperEngine...")
    dummy = np.zeros((1000, 600, 3), dtype=np.uint8)
    res = SolarPanelCropperEngine.process_panel(dummy)
    print("Engine Test Success!")
    print(res["metadata"])
