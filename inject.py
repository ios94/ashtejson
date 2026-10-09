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
    dylib_file = "AlertAshte.dylib"

    if not os.path.exists(dylib_file):
        print("AlertAshte.dylib لە پەڕەی سەرەکی نەدۆزرایەوە!")
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
    
    # ١. دەستکاریکردنی زۆرەملێی Info.plist و سڕینەوەی زمانەکان
    if os.path.exists(plist_path):
        try:
            with open(plist_path, "rb") as fp:
                pl = plistlib.load(fp)
                
            exec_name = pl.get("CFBundleExecutable")
            
            # هێنانی ناوە کۆنەکە (ئەگەر هەبێت) یان بەکارهێنانی ناوی باینەری
            orig_display = pl.get("CFBundleDisplayName")
            orig_name = pl.get("CFBundleName", exec_name)
            
            base_name = orig_display if orig_display else orig_name
            if not base_name:
                base_name = "App"
                
            # پاککردنەوەی ناوەکە لە هێمای ✨ و بۆشاییە زیادەکان
            clean_name = str(base_name).replace("✨", "").replace("🌟", "").strip()
            
            suffix = " - ashtemobile"
            
            # زۆرەملێ زیادکردنی ناوەکە بۆ ناو فایلی سەرەکی
            if not clean_name.endswith(suffix.strip()) and not clean_name.endswith(suffix):
                new_name = f"{clean_name}{suffix}"
                pl["CFBundleDisplayName"] = new_name
                pl["CFBundleName"] = new_name
                
                with open(plist_path, "wb") as fp:
                    plistlib.dump(pl, fp)
                print(f"ناوی یارییەکە بە زۆرەملێ گۆڕدرا بۆ: {new_name}")
                
            # سڕینەوەی فایلی InfoPlist.strings کە ڕێگرە لە گۆڕینی ناوەکە لەسەر شاشە
            for strings_file in glob.glob(os.path.join(app_dir, "**", "InfoPlist.strings"), recursive=True):
                os.remove(strings_file)
                print(f"فایلی زمانی {strings_file} سڕدرایەوە بۆ ئەوەی ناوە نوێیەکە بە زۆر دەربکەوێت.")
                
        except Exception as e:
            print(f"تێبینی لە خوێندنەوە یان گۆڕینی Info.plist: {e}")

    if not exec_name:
        exec_name = os.path.splitext(app_folders[0])[0]

    main_exec = os.path.join(app_dir, exec_name)
    print(f"باینەری سەرەکی دۆزرایەوە: {main_exec}")

    # ٢. لەبەرگرتنەوەی فایلی AlertAshte.dylib
    target_dylib = os.path.join(app_dir, "AlertAshte.dylib")
    shutil.copy2(dylib_file, target_dylib)
    os.chmod(target_dylib, 0o755)

    # ٣. بەستنەوەی فەرمی فایلی dylib بە بەکارهێنانی کتێبخانەی LIEF
    if os.path.exists(main_exec):
        try:
            parsed_binary = lief.MachO.parse(main_exec)
            dylib_path_str = "@executable_path/AlertAshte.dylib"

            if parsed_binary:
                for binary in parsed_binary:
                    existing_libraries = [lib.name for lib in binary.libraries]
                    if dylib_path_str not in existing_libraries:
                        binary.add_library(dylib_path_str)
                
                parsed_binary.write(main_exec)
                os.chmod(main_exec, 0o755)
                print("AlertAshte.dylib بە سەرکەوتوویی لە ناو هێدەری باینەری تۆمار کرا!")
            else:
                print("نەتوانرا پێکهاتەی باینەری شیبکرێتەوە!")
        except Exception as e:
            print(f"هەڵە لە کاتی بەستنەوە بە LIEF: {e}")
    else:
        print("باینەری سەرەکی نەدۆزرایەوە بۆ بەستنەوە!")

    # ٤. دووبارە دروستکردنەوەی فایلی IPA
    os.remove(target_ipa)
    shutil.make_archive("repacked", 'zip', work_dir)
    shutil.move("repacked.zip", target_ipa)
    shutil.rmtree(work_dir)
    print("پڕۆسەی ئینجێکت و گۆڕینی ناو بە سەرکەوتوویی کۆتایی هات!")

if __name__ == "__main__":
    inject()
