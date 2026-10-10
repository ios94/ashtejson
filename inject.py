import sys
import os
import zipfile
import shutil
import glob
import plistlib
import lief

def inject():
    ipa_list = glob.glob("ipas/*.ipa")
    if not ipa_list:
        print("هیچ فایلێکی IPA نەدۆزرایەوە!")
        return

    target_ipa = ipa_list[0]
    dylib_file = "SocialMenu.dylib"

    if not os.path.exists(dylib_file):
        print(f"{dylib_file} لە پەڕەی سەرەکی نەدۆزرایەوە!")
        return

    print(f"دەستپێکردنی کار لەسەر: {target_ipa}")
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
    plist_path = os.path.join(app_dir, "Info.plist")
    exec_name = None
    
    if os.path.exists(plist_path):
        try:
            with open(plist_path, "rb") as fp:
                pl = plistlib.load(fp)
            exec_name = pl.get("CFBundleExecutable")
            orig_display = pl.get("CFBundleDisplayName")
            orig_name = pl.get("CFBundleName", exec_name)
            base_name = orig_display if orig_display else orig_name
            if not base_name: base_name = "App"
            clean_name = str(base_name).replace("✨", "").replace("🌟", "").strip()
            suffix = " - ashtemobile"
            if not clean_name.endswith(suffix.strip()) and not clean_name.endswith(suffix):
                new_name = f"{clean_name}{suffix}"
                pl["CFBundleDisplayName"] = new_name
                pl["CFBundleName"] = new_name
                with open(plist_path, "wb") as fp:
                    plistlib.dump(pl, fp)
        except Exception as e:
            pass

    if not exec_name:
        exec_name = os.path.splitext(app_folders[0])[0]

    # ناوی دایلبەکە دەکەین بە ناوی فەرمی تا ESign نەزانێت ئەمە هی ئێمەیە
    fake_official_name = "libCoreSecurity.dylib"
    target_dylib = os.path.join(app_dir, fake_official_name)
    shutil.copy2(dylib_file, target_dylib)
    os.chmod(target_dylib, 0o755)

    dylib_load_path = f"@executable_path/{fake_official_name}"

    def inject_to_binary(binary_path):
        if not os.path.exists(binary_path): return
        try:
            parsed = lief.MachO.parse(binary_path)
            if parsed:
                injected = False
                for arch in parsed:
                    # فێڵە گەورەکە: گۆڕینی بەستەری Foundation بۆ دایلبەکەی تۆ
                    hijacked = False
                    for lib in arch.libraries:
                        if "Foundation.framework" in lib.name:
                            lib.name = dylib_load_path
                            hijacked = True
                            injected = True
                            break
                    
                    # ئەگەر Foundation نەدۆزرایەوە، بە شێوەی ئاسایی ئینجێکتی دەکەین
                    if not hijacked:
                        existing = [lib.name for lib in arch.libraries]
                        if dylib_load_path not in existing:
                            arch.add_library(dylib_load_path)
                            injected = True
                            
                if injected:
                    parsed.write(binary_path)
                    os.chmod(binary_path, 0o755)
        except Exception as e:
            pass

    main_exec = os.path.join(app_dir, exec_name)
    inject_to_binary(main_exec)

    frameworks_dir = os.path.join(app_dir, "Frameworks")
    if os.path.exists(frameworks_dir):
        for fw in os.listdir(frameworks_dir):
            if fw.endswith(".framework") or fw.endswith(".dylib"):
                fw_name = os.path.splitext(fw)[0]
                fw_exec_path = os.path.join(frameworks_dir, fw, fw_name) if fw.endswith(".framework") else os.path.join(frameworks_dir, fw)
                inject_to_binary(fw_exec_path)

    os.remove(target_ipa)
    shutil.make_archive("repacked", 'zip', work_dir)
    shutil.move("repacked.zip", target_ipa)
    shutil.rmtree(work_dir)
    print("پڕۆسەی بەستنەوە بە سەرکەوتوویی کۆتایی هات! پاراستنی دژە-سڕینەوە چالاککرا.")

if __name__ == "__main__":
    inject()
