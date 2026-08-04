import os
import sys
import random
import shutil
from typing import Dict, List

def find_target_folder(root_dir: str, possible_names: List[str]) -> str:
    """Finds existing folder matching one of possible names."""
    for name in possible_names:
        p = os.path.join(root_dir, name)
        if os.path.exists(p) and os.path.isdir(p):
            return p
    return ""

def empty_directory(dir_path: str):
    """Deletes all files inside dir_path without removing the directory itself."""
    if os.path.exists(dir_path):
        for f in os.listdir(dir_path):
            file_p = os.path.join(dir_path, f)
            if os.path.isfile(file_p) or os.path.islink(file_p):
                os.unlink(file_p)
            elif os.path.isdir(file_p):
                shutil.rmtree(file_p)

def run_stratified_bad_cells_split(root_dir: str):
    root_dir = root_dir.strip('"\'')
    if not os.path.exists(root_dir):
        print(f"❌ خطأ: المجلد الرئيسي غير موجود: {root_dir}")
        return

    print(f"\n========================================================")
    print(f"🚀 بدء السكربت لفرز وتقسيم الخلايا المعيبة (Stratified Bad Cells Split)")
    print(f"📁 المجلد الرئيسي: {root_dir}")
    print(f"========================================================\n")

    # 1. Target Defective Directories
    train_def = os.path.join(root_dir, "train", "Defective")
    val_def = os.path.join(root_dir, "val", "Defective")
    test_def = os.path.join(root_dir, "test", "Defective")

    os.makedirs(train_def, exist_ok=True)
    os.makedirs(val_def, exist_ok=True)
    os.makedirs(test_def, exist_ok=True)

    # 2. Step 2: Clear existing Defective files
    print("🧹 1️⃣ حذف وإفراغ محتويات مجلدات Defective الحالية...")
    empty_directory(train_def)
    empty_directory(val_def)
    empty_directory(test_def)
    print("   ✅ تم إفراغ train/Defective و val/Defective و test/Defective بنجاح.\n")

    # 3. Locate allbadcells directory
    allbad_dir = find_target_folder(root_dir, ["allbadcells", "all bad cells", "bad cells"])
    if not allbad_dir:
        print(f"❌ خطأ: لم يتم العثور على مجلد allbadcells داخل: {root_dir}")
        return

    print(f"📁 2️⃣ مجلد الخلايا المعيبة المكتشف: {allbad_dir}\n")

    # 4. Verify defect categories
    expected_categories = ['Cracks', 'Impurity', 'Misalignment', 'Missing', 'Ribbons']
    found_categories = [cat for cat in expected_categories if os.path.exists(os.path.join(allbad_dir, cat))]

    print(f"🔍 3️⃣ الفحص والتحقق من المجلدات الفرعية للخلايا المعيبة:")
    for cat in expected_categories:
        cat_p = os.path.join(allbad_dir, cat)
        if os.path.exists(cat_p):
            cnt = len([f for f in os.listdir(cat_p) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
            print(f"   ✅ مجلد [{cat:<12}]: موجود ويحتوي على {cnt:,} صورة")
        else:
            print(f"   ⚠️ مجلد [{cat:<12}]: غير موجود")

    print("\n========================================================")
    print("⚡ 4️⃣ بدء التقسيم الموزون (80% Train / 10% Val / 10% Test) لكل فئة عيب:")
    print("========================================================\n")

    random.seed(42) # Seed for exact reproducibility

    stats_per_category = {}
    total_moved_train = 0
    total_moved_val = 0
    total_moved_test = 0

    for cat in found_categories:
        cat_dir = os.path.join(allbad_dir, cat)
        files = [f for f in sorted(os.listdir(cat_dir)) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        
        # Shuffle deterministically
        random.shuffle(files)

        n = len(files)
        n_train = int(round(0.80 * n))
        n_val = int(round(0.10 * n))
        n_test = n - n_train - n_val

        train_files = files[:n_train]
        val_files = files[n_train:n_train + n_val]
        test_files = files[n_train + n_val:]

        for f in train_files:
            shutil.move(os.path.join(cat_dir, f), os.path.join(train_def, f))
        for f in val_files:
            shutil.move(os.path.join(cat_dir, f), os.path.join(val_def, f))
        for f in test_files:
            shutil.move(os.path.join(cat_dir, f), os.path.join(test_def, f))

        total_moved_train += len(train_files)
        total_moved_val += len(val_files)
        total_moved_test += len(test_files)

        stats_per_category[cat] = {
            "total": n,
            "train": len(train_files),
            "val": len(val_files),
            "test": len(test_files)
        }

        print(f"📌 فئة [{cat:<12}]: الإجمالي = {n:<4} ⬅️  Train = {len(train_files):<4} | Val = {len(val_files):<3} | Test = {len(test_files):<3}")

    # 5. Cleanup empty subfolders
    print("\n🧹 5️⃣ التثبت من تفريغ وحذف مجلدات allbadcells الفرعية...")
    for cat in found_categories:
        cat_dir = os.path.join(allbad_dir, cat)
        if os.path.exists(cat_dir) and len(os.listdir(cat_dir)) == 0:
            os.rmdir(cat_dir)
            print(f"   ✅ تم حذف مجلد [{cat}] بعد تفريغه بالكامل.")

    if os.path.exists(allbad_dir) and len(os.listdir(allbad_dir)) == 0:
        os.rmdir(allbad_dir)
        print(f"   ✅ تم حذف مجلد allbadcells الرئيسي بعد تفريغه بالكامل.")

    # 6. SUMMARY REPORT
    print("\n========================================================")
    print("📊 التقرير النهائي لتوزيع الخلايا المعيبة (Defective Dataset Split):")
    print("========================================================")
    print(f"📁 train/Defective : {len(os.listdir(train_def)):,} صورة (المستهدف ~1,213)")
    print(f"📁 val/Defective   : {len(os.listdir(val_def)):,} صورة (المستهدف ~152)")
    print(f"📁 test/Defective  : {len(os.listdir(test_def)):,} صورة (المستهدف ~152)")
    print("========================================================")
    print("🎉 اكتمل تقسيم الخلايا المعيبة بنجاح ومجموعة البيانات جاهزة 100%!")
    print("========================================================\n")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_path = sys.argv[1]
    else:
        target_path = input("أدخل أو الصق مسار المجلد الرئيسي للبيانات هنا: ").strip('"\'')

    run_stratified_bad_cells_split(target_path)
