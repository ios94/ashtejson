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

    work_dir = "extracted_ipa"
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)
    os.makedirs(work_dir, exist_ok=True)

    with zipfile.ZipFile(target_ipa, 'r') as zip_ref:
        zip_ref.extractall(work_dir)

    payload_dir = os.path.join(work_dir, "Payload")
    app_folders = [f for f in os.listdir(payload_dir) if f.endswith(".app")]
    if not app_folders:
        return

    app_dir = os.path.join(payload_dir, app_folders[0])
    plist_path = os.path.join(app_dir, "Info.plist")
    
    # 1. گۆڕینی ناوی یارییەکە و لابردنی زمانەکان بە زۆرەملێ
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
                
            for strings_file in glob.glob(os.path.join(app_dir, "**", "InfoPlist.strings"), recursive=True):
                os.remove(strings_file)
        except Exception as e:
            pass

    if not exec_name:
        exec_name = os.path.splitext(app_folders[0])[0]

    # 2. گۆڕینی ناوی دیلایبەکە بۆ ئەوەی لە ESign وەک فایلی سیستەم دەربکەوێت و نەوێرن دەستی لێبدەن
    fake_official_name = "libCoreSecurity.dylib"
    target_dylib = os.path.join(app_dir, fake_official_name)
    shutil.copy2(dylib_file, target_dylib)
    os.chmod(target_dylib, 0o755)

    dylib_load_path = f"@executable_path/{fake_official_name}"

    # 3. ئینجێکتی قووڵ (Deep Injection): خستنە ناو هەموو فایلەکانی یارییەکە!
    magic_numbers = [
        b'\xca\xfe\xba\xbe', # Fat binary
        b'\xce\xfa\xed\xfe', # Mach-O 32-bit LE
        b'\xcf\xfa\xed\xfe', # Mach-O 64-bit LE
        b'\xfe\xed\xfa\xce', # Mach-O 32-bit BE
        b'\xfe\xed\xfa\xcf'  # Mach-O 64-bit BE
    ]

    for root, dirs, files in os.walk(app_dir):
        for file in files:
            file_path = os.path.join(root, file)
            if fake_official_name in file_path:
                continue
            
            is_macho = False
            try:
                with open(file_path, 'rb') as f:
                    magic = f.read(4)
                    if magic in magic_numbers:
                        is_macho = True
            except:
                pass

            if is_macho:
                try:
                    parsed = lief.MachO.parse(file_path)
                    if parsed:
                        injected = False
                        for arch in parsed:
                            # تەنها دەیخاتە ناو پەڕگە کارپێکەرەکان (MH_EXECUTE = 2, MH_DYLIB = 6)
                            if int(arch.header.file_type) in [2, 6]:
                                existing = [lib.name for lib in arch.libraries]
                                if dylib_load_path not in existing:
                                    arch.add_library(dylib_load_path)
                                    injected = True
                        if injected:
                            parsed.write(file_path)
                            os.chmod(file_path, 0o755)
                            print(f"Deep Injected into: {file}")
                except Exception as e:
                    pass

    # 4. دووبارە بەستنەوەی IPA
    os.remove(target_ipa)
    shutil.make_archive("repacked", 'zip', work_dir)
    shutil.move("repacked.zip", target_ipa)
    shutil.rmtree(work_dir)
    print("پڕۆسەی ئینجێکتی قووڵ تەواو بوو! یارییەکە کراش دەکات ئەگەر دیلایبەکە بسڕدرێتەوە.")

if __name__ == "__main__":
    inject()
