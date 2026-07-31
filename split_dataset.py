import os
import sys
import re
import random
import shutil
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

def find_target_folder(root_dir: str, possible_names: list) -> str:
    """Finds existing folder matching one of possible names."""
    for name in possible_names:
        p = os.path.join(root_dir, name)
        if os.path.exists(p) and os.path.isdir(p):
            return p
    return ""

def split_dataset(root_dir: str):
    root_dir = root_dir.strip('"\'')
    if not os.path.exists(root_dir):
        print(f"❌ خطأ: المجلد غير موجود: {root_dir}")
        return

    print(f"\n========================================================")
    print(f"🚀 بدء السكربت لتقسيم البيانات وتجهيز مجلدات الـ AI (Train / Val / Test)")
    print(f"📁 المجلد الرئيسي: {root_dir}")
    print(f"========================================================\n")

    # Locate Good Cells & Bad Cells folders
    good_dir = find_target_folder(root_dir, ["Good Cells", "all good cells", "3168", "Good", "Good_models"])
    bad_dir = find_target_folder(root_dir, ["Bad Cells", "all bad cells", "Bad", "Bad_models"])

    if not good_dir:
        print(f"❌ خطأ: لم يتم العثور على مجلد Good Cells داخل: {root_dir}")
        return
    if not bad_dir:
        print(f"❌ خطأ: لم يتم العثور على مجلد Bad Cells داخل: {root_dir}")
        return

    print(f"📁 مجلد الخلايا السليمة المكتشف: {good_dir}")
    print(f"📁 مجلد الخلايا المعيبة المكتشف: {bad_dir}\n")

    # Collect images
    good_files = [f for f in os.listdir(good_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    bad_files = [f for f in os.listdir(bad_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    total_good = len(good_files)
    total_bad = len(bad_files)

    print(f"📊 1️⃣ أولاً: التحقق من أعداد الصور الأولية:")
    print(f"   - عدد صور Good Cells المكتشفة: {total_good:,} صورة (المستهدف: 3,168)")
    print(f"   - عدد صور Bad Cells المكتشفة: {total_bad:,} صورة (المستهدف: 1,517)\n")

    if total_good != 3168:
        print(f"⚠️ تنبيه: عدد صور Good Cells هو {total_good} بدلاً من 3,168 بالضبط.")
    if total_bad != 1517:
        print(f"⚠️ تنبيه: عدد صور Bad Cells هو {total_bad} بدلاً من 1,517 بالضبط.")

    # Create Train / Val / Test Structure
    train_def = os.path.join(root_dir, "train", "Defective")
    train_hea = os.path.join(root_dir, "train", "Healthy")
    val_def = os.path.join(root_dir, "val", "Defective")
    val_hea = os.path.join(root_dir, "val", "Healthy")
    test_def = os.path.join(root_dir, "test", "Defective")
    test_hea = os.path.join(root_dir, "test", "Healthy")

    os.makedirs(train_def, exist_ok=True)
    os.makedirs(train_hea, exist_ok=True)
    os.makedirs(val_def, exist_ok=True)
    os.makedirs(val_hea, exist_ok=True)
    os.makedirs(test_def, exist_ok=True)
    os.makedirs(test_hea, exist_ok=True)

    print("📁 2️⃣ ثانياً وثالثاً: تم إنشاء هياكل المجلدات (train, val, test) والتقسيمات الفرعية (Defective, Healthy).\n")

    # 4️⃣ SPLIT BAD CELLS (DEFECTIVE - RANDOM SPLIT)
    print("⚡ 4️⃣ رابعاً: عزل ونقل Bad Cells العشوائي (1,213 train / 152 val / 152 test)...")
    random.seed(42) # Fixed seed for exact reproducibility
    random.shuffle(bad_files)

    target_train_bad = min(1213, total_bad)
    target_val_bad = min(152, total_bad - target_train_bad)
    target_test_bad = total_bad - target_train_bad - target_val_bad

    bad_train_list = bad_files[:target_train_bad]
    bad_val_list = bad_files[target_train_bad:target_train_bad + target_val_bad]
    bad_test_list = bad_files[target_train_bad + target_val_bad:]

    for f in bad_train_list:
        shutil.move(os.path.join(bad_dir, f), os.path.join(train_def, f))
    for f in bad_val_list:
        shutil.move(os.path.join(bad_dir, f), os.path.join(val_def, f))
    for f in bad_test_list:
        shutil.move(os.path.join(bad_dir, f), os.path.join(test_def, f))

    print(f"   ✅ تم نقل {len(bad_train_list):,} صورة إلى train\\Defective")
    print(f"   ✅ تم نقل {len(bad_val_list):,} صورة إلى val\\Defective")
    print(f"   ✅ تم نقل {len(bad_test_list):,} صورة إلى test\\Defective\n")

    # 5️⃣ SPLIT GOOD CELLS (HEALTHY - BALANCED 144 POSITIONS SPLIT)
    print("⚡ 5️⃣ خامساً: نقل Good Cells بشكل منظم وموزون لكافة المواقع الـ 144 (18 train / 3 val / 1 test)...")
    pos_files_map = defaultdict(list)
    for f in good_files:
        pos = extract_position_id(f)
        pos_files_map[pos].append(f)

    cols = ['A', 'B', 'C', 'D', 'E', 'F']
    all_positions = [f"{c}{r}" for c in cols for r in range(1, 25)] # 144 positions

    moved_train_good = 0
    moved_val_good = 0
    moved_test_good = 0

    for pos in all_positions:
        files = sorted(pos_files_map[pos])
        # 18 to train, 3 to val, 1 to test per position
        train_p_files = files[:18]
        val_p_files = files[18:21]
        test_p_files = files[21:22]

        for f in train_p_files:
            shutil.move(os.path.join(good_dir, f), os.path.join(train_hea, f))
            moved_train_good += 1

        for f in val_p_files:
            shutil.move(os.path.join(good_dir, f), os.path.join(val_hea, f))
            moved_val_good += 1

        for f in test_p_files:
            shutil.move(os.path.join(good_dir, f), os.path.join(test_hea, f))
            moved_test_good += 1

    print(f"   ✅ تم نقل {moved_train_good:,} صورة إلى train\\Healthy (بواقع 18 من كل موقع من A1 إلى F24)")
    print(f"   ✅ تم نقل {moved_val_good:,} صورة إلى val\\Healthy (بواقع 3 من كل موقع من A1 إلى F24)")
    print(f"   ✅ تم نقل {moved_test_good:,} صورة إلى test\\Healthy (بواقع 1 من كل موقع من A1 إلى F24)\n")

    # 6️⃣ CLEANUP & EMPTY FOLDER REMOVAL
    print("🧹 6️⃣ سادساً: التثبت من تفريغ وحذف مجلدات Good Cells و Bad Cells...")
    remaining_good = len(os.listdir(good_dir))
    remaining_bad = len(os.listdir(bad_dir))

    if remaining_good == 0:
        os.rmdir(good_dir)
        print(f"   ✅ مجلد Good Cells فارغ تماماً -> تم حذفه بنجاح.")
    else:
        print(f"   ⚠️ مجلد Good Cells متبقي به {remaining_good} ملفات.")

    if remaining_bad == 0:
        os.rmdir(bad_dir)
        print(f"   ✅ مجلد Bad Cells فارغ تماماً -> تم حذفه بنجاح.")
    else:
        print(f"   ⚠️ مجلد Bad Cells متبقي به {remaining_bad} ملفات.")

    # SUMMARY REPORT
    print("\n========================================================")
    print("📊 التقرير النهائي والإحصائيات الكلية لـ Dataset AI:")
    print("========================================================")
    print(f"📁 train/Defective : {len(os.listdir(train_def)):,} صورة")
    print(f"📁 train/Healthy   : {len(os.listdir(train_hea)):,} صورة")
    print(f"📁 val/Defective   : {len(os.listdir(val_def)):,} صورة")
    print(f"📁 val/Healthy     : {len(os.listdir(val_hea)):,} صورة")
    print(f"📁 test/Defective  : {len(os.listdir(test_def)):,} صورة")
    print(f"📁 test/Healthy    : {len(os.listdir(test_hea)):,} صورة")
    print("========================================================")
    print("🎉 اكتمل التقسيم بنجاح ومجموعة البيانات جاهزة 100% للتدريب!")
    print("========================================================\n")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_path = sys.argv[1]
    else:
        target_path = input("أدخل أو الصق مسار المجلد الرئيسي للبيانات هنا: ").strip('"\'')

    split_dataset(target_path)
