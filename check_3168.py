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
    
    # Fallback search anywhere in filename
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
    print(f"🔍 فحص وتحليل مجلد الخلايا: {folder_path}")
    print(f"========================================================\n")

    cols = ['A', 'B', 'C', 'D', 'E', 'F']
    all_positions = [f"{c}{r}" for c in cols for r in range(1, 25)] # 144 positions

    position_files = defaultdict(list)
    unmatched_files = []
    total_images = 0

    for root, dirs, files in os.walk(folder_path):
        for f in files:
            if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                total_images += 1
                full_p = os.path.join(root, f)
                pos = extract_position_id(f)
                if pos != "UNKNOWN":
                    position_files[pos].append({"filename": f, "path": full_p})
                else:
                    unmatched_files.append({"filename": f, "path": full_p})

    print(f"📊 إجمالي عدد صور الخلايا الموجودة في المجلد: {total_images:,} صورة\n")

    # Find positions with extra files (> 22) or missing files (< 22)
    extra_positions = {}
    missing_positions = {}
    normal_positions = {}

    for pos in all_positions:
        count = len(position_files[pos])
        if count > 22:
            extra_positions[pos] = count
        elif count < 22 and count > 0:
            missing_positions[pos] = count
        elif count == 22:
            normal_positions[pos] = count

    # DISPLAY HIGHLIGHTED RESULTS
    if extra_positions:
        print("🚨 ========================================================")
        print("🚨 تنبيه: التحديد المباشر للموقع الذي يحتوي على الزيادة:")
        print("🚨 ========================================================")
        for pos, count in extra_positions.items():
            diff = count - 22
            print(f"⚠️ الموقع [{pos}]: يحتوي على {count} ملف (يوجد {diff} ملف زائد فوق الـ 22 المطلوب!)")
            print(f"   📋 قائمة الصور الموجودة في هذا الموقع [{pos}]:")
            for idx, file_info in enumerate(position_files[pos], 1):
                print(f"      {idx}. {file_info['filename']}")
            print("--------------------------------------------------------")
    else:
        print("✅ لا توجد أي مواضع تحتوي على زيادة فوق 22 ملف.")

    if missing_positions:
        print("\n⚠️ المواضع التي تحتوي على نقص (أقل من 22):")
        for pos, count in missing_positions.items():
            print(f"   - الموقع [{pos}]: يحتوي على {count} ملف فقط (ينقصه {22 - count} ملف)")

    if unmatched_files:
        print(f"\n⚠️ ملفات لم يتم التعرف على موقعها ({len(unmatched_files)} ملف):")
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
    print("🏁 انتهى التقرير.")
    print("========================================================\n")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_path = sys.argv[1]
    else:
        target_path = input("أدخل أو الصق مسار مجلد 3168 هنا: ").strip('"\'')
    
    check_3168_folder(target_path)
