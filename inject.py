import sys
import os
import zipfile
import shutil
import glob

def inject():
    ipa_list = glob.glob("ipas/*.ipa")
    if not ipa_list:
        print("هیچ فایلێکی IPA نەدۆزرایەوە!")
        return

    target_ipa = ipa_list[0]
    dylib_file = "AlertAshte.dylib"

    if not os.path.exists(dylib_file):
        print("AlertAshte.dylib لە ڕەگی سەرەکی نەدۆزرایەوە!")
        return

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
    
    # دۆزینەوەی باینەری سەرەکی لە ناو Info.plist
    app_name = os.path.splitext(app_folders[0])[0]
    main_exec = os.path.join(app_dir, app_name)

    # ١. لەبەرگرتنەوەی dylib بۆ ناو .app
    target_dylib = os.path.join(app_dir, "AlertAshte.dylib")
    shutil.copy2(dylib_file, target_dylib)
    os.chmod(target_dylib, 0o755)

    # ٢. بەستنەوەی ڕاستەوخۆ بە شێوازی macholib بێ کراش
    try:
        from macholib.MachO import MachO
        from macholib.mach_o import dylib_command, LC_LOAD_DYLIB

        dylib_load_path = b"@executable_path/AlertAshte.dylib"
        m = MachO(main_exec)
        
        # پشکنین بۆ ئەوەی پێشتر لۆد نەکرا بێت
        already_injected = False
        for header in m.headers:
            for idx, (load_cmd, cmd, data) in enumerate(header.commands):
                if load_cmd == LC_LOAD_DYLIB and b"AlertAshte.dylib" in data:
                    already_injected = True
                    break

        if not already_injected:
            for header in m.headers:
                cmd = dylib_command()
                cmd.name = len(dylib_command)
                cmd.timestamp = 0
                cmd.current_version = 0
                cmd.compatibility_version = 0
                
                # ڕێکخستنی درێژی دێڕەکە تا کراش نەکات
                pad_len = (8 - (len(dylib_load_path) % 8)) % 8
                padded_data = dylib_load_path + b'\x00' * pad_len
                header.commands.append((LC_LOAD_DYLIB, cmd, padded_data))

            with open(main_exec, 'rb+') as f:
                m.write(f)
            print("AlertAshte.dylib بە سەرکەوتوویی لەگەڵ باینەری سەرەکی بەستراوە!")
        else:
            print("dylib پێشتر بەستراوە.")
    except Exception as e:
        print(f"هەڵە لە بەستنەوەی باینەری: {e}")

    # ٣. دووبارە بەستنەوەی فایلی IPA
    os.remove(target_ipa)
    shutil.make_archive("repacked", 'zip', work_dir)
    shutil.move("repacked.zip", target_ipa)
    shutil.rmtree(work_dir)
    print("IPA نوێیەکە دروستکرایەوە بە سەرکەوتوویی.")

if __name__ == "__main__":
    inject()
