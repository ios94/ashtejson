import sys
import os
import zipfile
import shutil
import glob
from macholib.MachO import MachO
from macholib.mach_o import dylib_command, LC_LOAD_DYLIB

def inject():
    ipa_list = glob.glob("ipas/*.ipa")
    if not ipa_list:
        print("هیچ فایلێکی IPA نەدۆزرایەوە!")
        return

    target_ipa = ipa_list[0]
    dylib_file = "AlertAshte.dylib"

    if not os.path.exists(dylib_file):
        print("فایلی AlertAshte.dylib نەدۆزرایەوە، هەنگاوەکە تێپەڕێنرا.")
        return

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
        print("فۆڵدەری .app نەدۆزرایەوە!")
        return

    app_dir = os.path.join(payload_dir, app_folders[0])
    app_name = os.path.splitext(app_folders[0])[0]
    main_exec = os.path.join(app_dir, app_name)

    frameworks_dir = os.path.join(app_dir, "Frameworks")
    os.makedirs(frameworks_dir, exist_ok=True)
    target_dylib = os.path.join(frameworks_dir, "AlertAshte.dylib")
    shutil.copy2(dylib_file, target_dylib)
    os.chmod(target_dylib, 0o755)

    dylib_path = b"@executable_path/Frameworks/AlertAshte.dylib"
    try:
        m = MachO(main_exec)
        for header in m.headers:
            cmd = dylib_command()
            cmd.name = len(dylib_command)
            cmd.timestamp = 0
            cmd.current_version = 0
            cmd.compatibility_version = 0
            header.commands.append((LC_LOAD_DYLIB, cmd, dylib_path + b'\x00' * ((4 - len(dylib_path) % 4) % 4)))

        with open(main_exec, 'rb+') as f:
            m.write(f)
        print("فایلی AlertAshte.dylib بە سەرکەوتوویی خرایە ناو باینەری ئەپەکە.")
    except Exception as e:
        print(f"تێبینی لە کاتی دانان: {e}")

    os.remove(target_ipa)
    shutil.make_archive("repacked", 'zip', work_dir)
    shutil.move("repacked.zip", target_ipa)
    shutil.rmtree(work_dir)
    print("هەموو شتێک تەواو بوو! IPA نوێیەکە ئامادەیە.")

if __name__ == "__main__":
    inject()
