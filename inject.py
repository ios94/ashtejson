import sys
import os
import zipfile
import shutil
import glob
import subprocess

def setup_insert_dylib():
    """ئامادەکردنی ئامرازی insert_dylib لەسەر سیستەم بۆ ئەوەی باینەرییەکە کراش نەکات"""
    if not os.path.exists("insert_dylib"):
        print("خەریکی داگرتن و ئامادەکردنی ئامرازی سەقامگیری باینەریم...")
        subprocess.run(["git", "clone", "--depth=1", "https://github.com/tyilo/insert_dylib.git"], check=False)
        if os.path.exists("insert_dylib/Makefile"):
            subprocess.run(["make", "-C", "insert_dylib"], check=False)
            if os.path.exists("insert_dylib/insert_dylib"):
                shutil.copy2("insert_dylib/insert_dylib", "./insert_dylib_tool")
                os.chmod("./insert_dylib_tool", 0o755)

def inject():
    ipa_list = glob.glob("ipas/*.ipa")
    if not ipa_list:
        print("هیچ فایلێکی IPA نەدۆزرایەوە لەناو ipas!")
        return

    target_ipa = ipa_list[0]
    dylib_file = "AlertAshte.dylib"

    if not os.path.exists(dylib_file):
        print("فایلی AlertAshte.dylib نەدۆزرایەوە لە پەڕەی سەرەکی!")
        return

    setup_insert_dylib()

    print(f"خەریکی کارکردنم لەسەر: {target_ipa}")
    work_dir = "extracted_ipa"
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)
    os.makedirs(work_dir, exist_ok=True)

    with zipfile.ZipFile(target_ipa, 'r') as zip_ref:
        zip_ref.extractall(work_dir)

    payload_dir = os.path.join(work_dir, "Payload")
    app_folders = [f for f in os.listdir(payload_dir) if f.endswith(".app")]
    if not app_folders:
        print("فۆڵدەری .app نەدۆزرایەوە لەناو Payload!")
        return

    app_dir = os.path.join(payload_dir, app_folders[0])
    app_name = os.path.splitext(app_folders[0])[0]
    main_exec = os.path.join(app_dir, app_name)

    # ١. خستنە ناو سەرەکی فایلی ئەپەکە ڕێک هاوشێوەی وێنەکە
    target_dylib = os.path.join(app_dir, "AlertAshte.dylib")
    shutil.copy2(dylib_file, target_dylib)
    os.chmod(target_dylib, 0o755)

    # ٢. بەستنەوە بە شێوازی سەقامگیر تا کێشەی کراش دروست نەبێت
    dylib_load_path = "@executable_path/AlertAshte.dylib"
    tool_binary = "./insert_dylib_tool"

    if os.path.exists(tool_binary):
        cmd = [tool_binary, "--inplace", "--overwrite", dylib_load_path, main_exec]
        res = subprocess.run(cmd, capture_output=True, text=True)
        print("ئەنجامی ئینجێکت بە ئامرازی فەرمی:")
        print(res.stdout)
    else:
        print("ئاگاداری: ئامرازی insert_dylib ساز نەکرا، پشکنین بکە.")

    # ٣. دووبارە کۆکردنەوەی IPA
    os.remove(target_ipa)
    shutil.make_archive("repacked", 'zip', work_dir)
    shutil.move("repacked.zip", target_ipa)
    shutil.rmtree(work_dir)
    print("هەموو شتێک ڕێک هاوشێوەی وێنەکە تەواو کرا.")

if __name__ == "__main__":
    inject()
