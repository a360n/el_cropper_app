import os
import sys
import re
from collections import defaultdict

def extract_position_id(filename: str) -> str:
    """
    Extracts cell position ID (e.g. A1, A01, E11, F24) from filename.
    Example: '2026-01-07_12-59-28-A1.png' -> 'A1'
    """
    clean_name = filename.replace('.png', '').replace('.jpg', '').replace('.jpeg', '')
    parts = clean_name.split('-')
    last_part = parts[-1]
    
    match = re.search(r'([A-F])(0?[1-9]|1[0-9]|2[0-4])$', last_part, re.IGNORECASE)
    if match:
        col = match.group(1).upper()
        num = int(match.group(2))
        return f"{col}{num}"
    
    match_any = re.search(r'\b([A-F])(0?[1-9]|1[0-9]|2[0-4])\b', clean_name, re.IGNORECASE)
    if match_any:
        col = match_any.group(1).upper()
        num = int(match_any.group(2))
        return f"{col}{num}"
        
    return "UNKNOWN"

def check_3168_folder(folder_path: str):
    folder_path = folder_path.strip('"\'')
    if not os.path.exists(folder_path):
        print(f"❌ خطأ: المجلد غير موجود: {folder_path}")
        return

    print(f"\n========================================================")
    print(f"🔍 فحص وتفتيش شامل لجميع الملفات في الويندوز: {folder_path}")
    print(f"========================================================\n")

    cols = ['A', 'B', 'C', 'D', 'E', 'F']
    all_positions = [f"{c}{r}" for c in cols for r in range(1, 25)] # 144 positions

    all_files_list = []
    image_files_list = []
    non_image_files_list = []
    position_files = defaultdict(list)
    unmatched_files = []

    for root, dirs, files in os.walk(folder_path):
        for f in files:
            full_p = os.path.join(root, f)
            all_files_list.append((f, full_p))

            if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                image_files_list.append((f, full_p))
                pos = extract_position_id(f)
                if pos != "UNKNOWN":
                    position_files[pos].append({"filename": f, "path": full_p})
                else:
                    unmatched_files.append({"filename": f, "path": full_p})
            else:
                non_image_files_list.append((f, full_p))

    total_all_files = len(all_files_list)
    total_images = len(image_files_list)
    total_non_images = len(non_image_files_list)

    print(f"📁 إجمالي كافة الملفات بمدير ملفات الويندوز (مع المخفية): {total_all_files:,} ملف")
    print(f"🖼️ إجمالي صور الخلايا الناتجة (PNG/JPG): {total_images:,} صورة")
    print(f"📄 إجمالي الملفات غير الصور (مثل desktop.ini أو .DS_Store): {total_non_images:,} ملف\n")

    # HIGHLIGHT NON-IMAGE OR HIDDEN FILES (Root cause of Windows showing 3169)
    if non_image_files_list:
        print("🚨 ========================================================")
        print("🚨 كشف الملف الزائد غير الصورة التابع للنظام بمدير الملفات:")
        print("🚨 ========================================================")
        for idx, (f, p) in enumerate(non_image_files_list, 1):
            print(f"⚠️ {idx}. اسم الملف الزائد: [{f}]")
            print(f"   المسار الكامل: {p}")
        print("--------------------------------------------------------\n")

    # Find positions with extra files (> 22) or missing files (< 22)
    extra_positions = {}
    missing_positions = {}

    for pos in all_positions:
        count = len(position_files[pos])
        if count > 22:
            extra_positions[pos] = count
        elif count < 22:
            missing_positions[pos] = count

    if extra_positions:
        print("🚨 ========================================================")
        print("🚨 تنبيه: تحديد مواقع الخلايا التي تحتوي على زيادة صور:")
        print("🚨 ========================================================")
        for pos, count in extra_positions.items():
            diff = count - 22
            print(f"⚠️ الموقع [{pos}]: يحتوي على {count} صورة (يوجد {diff} زيادة فوق الـ 22)")
            print(f"   📋 قائمة الصور في الموقع [{pos}]:")
            for idx, file_info in enumerate(position_files[pos], 1):
                print(f"      {idx}. {file_info['filename']}")
            print("--------------------------------------------------------")

    if missing_positions:
        print("\n⚠️ مواضع خلايا بها نقص (أقل من 22 صورة):")
        for pos, count in missing_positions.items():
            print(f"   - الموقع [{pos}]: يحتوي على {count} صورة فقط (ينقصه {22 - count})")

    if unmatched_files:
        print(f"\n⚠️ صور لم يتم التعرف على موقعها ({len(unmatched_files)} صورة):")
        for f_info in unmatched_files[:10]:
            print(f"   - {f_info['filename']}")

    # SUMMARY GRID MATRIX TABLE
    print("\n========================================================")
    print("📊 ملخص أعداد الصور لكافة المواقع الـ 144 (A1 إلى F24):")
    print("========================================================")
    print("الموقع | العدد | الحالة")
    print("-------|-------|-----------------------------")
    
    for pos in all_positions:
        cnt = len(position_files[pos])
        status = "✅ سليم (22)"
        if cnt > 22:
            status = f"🚨 زيادة! ({cnt})"
        elif cnt < 22:
            status = f"⚠️ نقص ({cnt})"
        print(f"  {pos:<4} |  {cnt:<4} | {status}")

    print("\n========================================================")
    print("🏁 انتهى التقرير الشامل.")
    print("========================================================\n")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_path = sys.argv[1]
    else:
        target_path = input("أدخل أو الصق مسار مجلد 3168 هنا: ").strip('"\'')
    
    check_3168_folder(target_path)
