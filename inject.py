import sys
import os
import zipfile
import shutil
import glob
import plistlib
import lief
import traceback

# Improved inject.py: validate IPA before extracting, print diagnostics on failure,
# and avoid swallowing exceptions silently.

def diagnose_file(path):
    exists = os.path.exists(path)
    size = None
    try:
        size = os.path.getsize(path) if exists else None
    except Exception:
        size = None
    print(f"DIAG: path={path} exists={exists} size={size}")
    if exists:
        try:
            with open(path, "rb") as f:
                head = f.read(512)
            try:
                # Print a utf-8-safe preview
                print("DIAG: first bytes (utf-8 safe):", head[:200].decode('utf-8', errors='replace'))
            except Exception:
                print("DIAG: first bytes (hex):", head[:64].hex())
        except Exception as e:
            print("DIAG: could not read file head:", e)

def inject():
    ipa_list = glob.glob("ipas/*.ipa")
    if not ipa_list:
        print("هیچ فایلێکی IPA نەدۆزرایەوە!")
        sys.exit(1)

    target_ipa = ipa_list[0]
    print(f"دەستپێکردنی کار لەسەر: {target_ipa}")

    # Validate the IPA file before attempting to open it as a zip
    if not zipfile.is_zipfile(target_ipa):
        print("ERROR: target file is not a valid zip/ipa:", target_ipa)
        diagnose_file(target_ipa)
        sys.exit(2)

    dylib_file = "AlertAshte.dylib"
    if not os.path.exists(dylib_file):
        print(f"{dylib_file} لە پەڕەی سەرەکی نەدۆزرایەوە!")
        sys.exit(3)

    work_dir = "extracted_ipa"
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)
    os.makedirs(work_dir, exist_ok=True)

    try:
        with zipfile.ZipFile(target_ipa, 'r') as zip_ref:
            zip_ref.extractall(work_dir)
    except zipfile.BadZipFile as e:
        print("ERROR: BadZipFile when extracting:", e)
        diagnose_file(target_ipa)
        traceback.print_exc()
        sys.exit(4)
    except Exception as e:
        print("ERROR: Exception during extract:", e)
        traceback.print_exc()
        sys.exit(5)

    payload_dir = os.path.join(work_dir, "Payload")
    if not os.path.exists(payload_dir):
        print("ERROR: Payload directory not found inside IPA")
        sys.exit(6)

    app_folders = [f for f in os.listdir(payload_dir) if f.endswith(".app")]
    if not app_folders:
        print("فۆڵدەری .app نەدۆزرایەوە!")
        sys.exit(7)

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
            if not base_name:
                base_name = "App"

            clean_name = str(base_name).replace("✨", "").replace("🌟", "").strip()
            suffix = " - ashtemobile"

            if not clean_name.endswith(suffix.strip()) and not clean_name.endswith(suffix):
                new_name = f"{clean_name}{suffix}"
                pl["CFBundleDisplayName"] = new_name
                pl["CFBundleName"] = new_name

                with open(plist_path, "wb") as fp:
                    plistlib.dump(pl, fp)

            for strings_file in glob.glob(os.path.join(app_dir, "**", "InfoPlist.strings"), recursive=True):
                try:
                    os.remove(strings_file)
                except Exception as e:
                    print(f"WARN: could not remove {strings_file}: {e}")

        except Exception as e:
            print("WARN: failed to parse or modify Info.plist:", e)
            traceback.print_exc()

    if not exec_name:
        exec_name = os.path.splitext(app_folders[0])[0]

    # Copy the dylib into the app bundle with a fake system-like name
    fake_official_name = "libswiftCoreGraphics.dylib"
    target_dylib = os.path.join(app_dir, fake_official_name)
    try:
        shutil.copy2(dylib_file, target_dylib)
        os.chmod(target_dylib, 0o755)
    except Exception as e:
        print("ERROR: failed to copy dylib into app bundle:", e)
        traceback.print_exc()
        sys.exit(8)

    dylib_load_path = f"@executable_path/{fake_official_name}"

    def inject_to_binary(binary_path):
        if not os.path.exists(binary_path):
            print(f"WARN: binary not found: {binary_path}")
            return
        try:
            parsed = lief.MachO.parse(binary_path)
            if parsed:
                injected = False
                for arch in parsed:
                    existing = [lib.name for lib in arch.libraries]
                    if dylib_load_path not in existing:
                        arch.add_library(dylib_load_path)
                        injected = True
                if injected:
                    parsed.write(binary_path)
                    os.chmod(binary_path, 0o755)
        except Exception as e:
            print(f"WARN: failed to inject into binary {binary_path}: {e}")
            traceback.print_exc()

    main_exec = os.path.join(app_dir, exec_name)
    inject_to_binary(main_exec)

    frameworks_dir = os.path.join(app_dir, "Frameworks")
    if os.path.exists(frameworks_dir):
        for fw in os.listdir(frameworks_dir):
            if fw.endswith(".framework") or fw.endswith(".dylib"):
                fw_name = os.path.splitext(fw)[0]
                fw_exec_path = os.path.join(frameworks_dir, fw, fw_name) if fw.endswith(".framework") else os.path.join(frameworks_dir, fw)
                inject_to_binary(fw_exec_path)

    # Repack IPA safely
    try:
        try:
            os.remove(target_ipa)
        except Exception:
            pass
        shutil.make_archive("repacked", 'zip', work_dir)
        shutil.move("repacked.zip", target_ipa)
    except Exception as e:
        print("ERROR: failed to repack ipa:", e)
        traceback.print_exc()
        sys.exit(9)

    # cleanup
    try:
        shutil.rmtree(work_dir)
    except Exception as e:
        print("WARN: failed to remove work_dir:", e)

    print("پڕۆسەی بەستنەوەی فرە-لایەنە بە سەرکەوتوویی کۆتایی هات!")

if __name__ == "__main__":
    inject()
