import sys
import os
import zipfile
import shutil
import glob
import subprocess
import urllib.request

def get_optool():
    """داگرتنی ئامرازی فەرمی optool بۆ لینوکس بەبێ هەڵە"""
    tool_path = "./optool"
    if not os.path.exists(tool_path):
        print("خەریکی ئامادەکردنی ئامرازی فەرمی optool...")
        # لە ئەکشنەکان یان سەرچاوەی فەرمی بە خێرایی کۆمپایل دەکرێت
        subprocess.run(["git", "clone", "--depth=1", "--recurse-submodules", "https://github.com/alexzielenski/optool.git"], check=False)
        if os.path.exists("optool"):
            # ئەگەر لەسەر سیستم هەبێت یان بە clang کۆمپایل بکرێت
            compile_cmd = "clang -O3 -fmodules optool/optool/*.m -o optool_bin"
            subprocess.run(compile_cmd, shell=True, check=False)
            if os.path.exists("optool_bin"):
                shutil.copy2("optool_bin", tool_path)
                os.chmod(tool_path, 0o755)
    return os.path.exists(tool_path)

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
    
    # دۆزینەوەی باینەری سەرەکی لە ناو Info.plist
    app_name = os.path.splitext(app_folders[0])[0]
    main_exec = os.path.join(app_dir, app_name)

    # ١. کۆپیکردنی AlertAshte.dylib بۆ سەرەکی ناو ئەپەکە
    target_dylib = os.path.join(app_dir, "AlertAshte.dylib")
    shutil.copy2(dylib_file, target_dylib)
    os.chmod(target_dylib, 0o755)

    # ٢. بەستنەوەی سەقامگیر و دروست بە باینەری (ئینجێکت)
    # هێنانی ئامرازی insert_dylib تایبەت بە لینوکس
    subprocess.run("git clone https://github.com/tyilo/insert_dylib.git && cd insert_dylib && make && cp insert_dylib ../insert_dylib_bin && cd ..", shell=True, check=False)
    
    injected_successfully = False
    if os.path.exists("./insert_dylib_bin"):
        print("خەریکی بەستنەوەی فەرمی dylib بە باینەری سەرەکیم...")
        cmd = ["./insert_dylib_bin", "--inplace", "--overwrite", "@executable_path/AlertAshte.dylib", main_exec]
        res = subprocess.run(cmd, capture_output=True, text=True)
        print(res.stdout)
        if "Added" in res.stdout or res.returncode == 0:
            injected_successfully = True

    # ئەگەر بە ئامرازی یەکەم نەبوو، بە ڕێگەی پایتۆن بە هێدەری ستاندارد دەبەسترێت
    if not injected_successfully:
        print("بەکارهێنانی شێوازی دووەم بۆ بەستنەوەی هێدەر...")
        try:
            from macholib.MachO import MachO
            from macholib.mach_o import dylib_command, LC_LOAD_DYLIB

            dylib_path = b"@executable_path/AlertAshte.dylib"
            m = MachO(main_exec)
            for header in m.headers:
                cmd = dylib_command()
                cmd.name = 24
                cmd.timestamp = 0
                cmd.current_version = 0
                cmd.compatibility_version = 0
                pad = (8 - (len(dylib_path) % 8)) % 8
                header.commands.append((LC_LOAD_DYLIB, cmd, dylib_path + b'\x00' * pad))
            with open(main_exec, "rb+") as f:
                m.write(f)
            print("بە شێوازی پایتۆن بەستراوە.")
        except Exception as e:
            print(f"کێشە لە بەستنەوە: {e}")

    # ٣. دووبارە بەستنەوەی فایلی IPA
    os.remove(target_ipa)
    shutil.make_archive("repacked", 'zip', work_dir)
    shutil.move("repacked.zip", target_ipa)
    shutil.rmtree(work_dir)
    print("پڕۆسەکە کۆتایی هات! ئێستا دەبێت لە ناو لیستی لایبرەرییەکان دەربکەوێت.")

if __name__ == "__main__":
    inject()
