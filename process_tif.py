import os
import sys
from PIL import Image

def process_single_image(img: Image.Image) -> Image.Image:
    """
    Processes a single PIL Image according to the process_tif.py rules:
    - Ensures height is even (if height is odd, subtracts 1).
    - Ensures width does not exceed target_max_width = new_height // 2 (crops to min(width, target_max_width)).
    """
    width, height = img.size

    new_height = height if height % 2 == 0 else height - 1
    target_max_width = new_height // 2
    new_width = min(width, target_max_width)

    if new_width != width or new_height != height:
        return img.crop((0, 0, new_width, new_height))
    return img

def process_tif_files(folder_path):
    if not os.path.exists(folder_path):
        print(f"❌ المجلد غير موجود: {folder_path}")
        return

    processed_count = 0
    modified_count = 0
    error_count = 0

    print(f"🔍 جاري البحث عن ملفات TIF داخل: {folder_path} ...\n")

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(('.tif', '.tiff')):
                file_path = os.path.join(root, file)
                processed_count += 1

                try:
                    with Image.open(file_path) as img:
                        cropped_img = process_single_image(img)
                        width, height = img.size
                        new_width, new_height = cropped_img.size

                        if new_width != width or new_height != height:
                            temp_path = file_path + ".tmp"
                            cropped_img.save(temp_path, format=img.format)
                            img.close()

                            os.replace(temp_path, file_path)
                            modified_count += 1
                            print(f"✅ [تم التعديل] {file_path}")
                            print(f"   القياس القديم: {width}x{height} ⬅️ القياس الجديد: {new_width}x{new_height}")
                        else:
                            print(f"ℹ️ [بدون تغيير] {file_path} (الأبعاد: {width}x{height})")

                except Exception as e:
                    error_count += 1
                    print(f"❌ [خطأ] تعذر معالجة الملف: {file_path}")
                    print(f"   السبب: {e}")

    print("\n==========================================")
    print(f"🏁 اكتملت المعالجة!")
    print(f"📁 إجمالي ملفات TIF: {processed_count}")
    print(f"✂️ المعدلة: {modified_count}")
    print(f"⚠️ الأخطاء: {error_count}")
    print("==========================================")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_folder = sys.argv[1]
    else:
        target_folder = input("أدخل مسار المجلد هنا: ").strip('"\'')
    
    process_tif_files(target_folder)