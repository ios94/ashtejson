import sys
import os
import zipfile
import shutil
import glob
import struct
import plistlib

def inject_macho_slice(data, offset=0):
    magic = struct.unpack_from(">I", data, offset)[0]
    
    # پشکنینی معمارەیی 64-bit Mach-O (Little Endian یان Big Endian)
    is_64 = magic in (0xfeedfacf, 0xcffaedfe)
    if not is_64:
        return data, False

    endian = "<" if magic == 0xfeedfacf else ">"
    
    # خوێندنەوەی هێدەری سەرەکی
    cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags, reserved = struct.unpack_from(
        f"{endian}7I", data, offset + 4
    )

    dylib_path = b"@executable_path/AlertAshte.dylib\x00"
    path_len = len(dylib_path)
    # دروستکردنی درێژی دێڕ بە ستانداردی 8-بایت
    pad_len = (8 - (path_len % 8)) % 8
    padded_path = dylib_path + (b"\x00" * pad_len)
    
    cmd_size = 24 + len(padded_path)
    lc_load_dylib = 0x0C

    # پشکنین بۆ ئەوەی بزانین پێشتر تێیدایە یان نا
    cmd_offset = offset + 32
    for _ in range(ncmds):
        cmd, csize = struct.unpack_from(f"{endian}2I", data, cmd_offset)
        if cmd == lc_load_dylib:
            str_offset = struct.unpack_from(f"{endian}I", data, cmd_offset + 8)[0]
            existing_path = data[cmd_offset + str_offset : cmd_offset + csize].split(b"\x00")[0]
            if b"AlertAshte.dylib" in existing_path:
                print("دیلایب پێشتر لە باینەرییەکەدا بوونی هەیە.")
                return data, True
        cmd_offset += csize

    # پشکنینی شوێنی بەتاڵ بۆ دانانی فەرمانە نوێیەکە
    new_cmd_offset = offset + 32 + sizeofcmds
    space_check = data[new_cmd_offset : new_cmd_offset + cmd_size]
    if space_check != b"\x00" * len(space_check):
        print("بۆشایی بەتاڵ لە هێدەرەکە نەدۆزرایەوە بۆ ئینجێکتکردن.")
        return data, False

    # دروستکردنی کەرستەی LC_LOAD_DYLIB
    # cmd, cmdsize, offset_to_path, timestamp, current_version, compatibility_version
    dylib_cmd = struct.pack(f"{endian}6I", lc_load_dylib, cmd_size, 24, 0, 0, 0) + padded_path

    data_bytearray = bytearray(data)
    # زیادکردنی ژمارەی فەرمانەکان و قەبارەی گشتی
    struct.pack_into(f"{endian}I", data_bytearray, offset + 16, ncmds + 1)
    struct.pack_into(f"{endian}I", data_bytearray, offset + 20, sizeofcmds + cmd_size)
    # نووسینی فەرمانەکە
    data_bytearray[new_cmd_offset : new_cmd_offset + cmd_size] = dylib_cmd

    return bytes(data_bytearray), True

def inject_binary(file_path):
    with open(file_path, "rb") as f:
        data = f.read()

    if len(data) < 32:
        return False

    magic = struct.unpack_from(">I", data, 0)[0]
    success = False

    # پشکنینی Universal/Fat Binary
    if magic in (0xcafebabe, 0xbebafeca):
        endian = ">" if magic == 0xcafebabe else "<"
        nfat_arch = struct.unpack_from(f"{endian}I", data, 4)[0]
        arch_offset = 8
        for _ in range(nfat_arch):
            cputype, cpusubtype, arch_off, arch_size = struct.unpack_from(f"{endian}4I", data, arch_offset)
            data, ok = inject_macho_slice(data, arch_off)
            if ok: success = True
            arch_offset += 20
    else:
        data, ok = inject_macho_slice(data, 0)
        if ok: success = True

    if success:
        with open(file_path, "wb") as f:
            f.write(data)
        print("فەرمانی لۆدکردن بە سەرکەوتوویی لە باینەری سەرەکی تۆمار کرا!")
    return success

def inject():
    ipa_list = glob.glob("ipas/*.ipa")
    if not ipa_list:
        print("هیچ IPAیەک نەدۆزرایەوە!")
        return

    target_ipa = ipa_list[0]
    dylib_file = "AlertAshte.dylib"

    if not os.path.exists(dylib_file):
        print("فایلی AlertAshte.dylib نەدۆزرایەوە!")
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
    
    # دۆزینەوەی ناوی باینەری ڕاستەقینە لە ناو Info.plist
    plist_path = os.path.join(app_dir, "Info.plist")
    exec_name = None
    if os.path.exists(plist_path):
        try:
            with open(plist_path, "rb") as fp:
                pl = plistlib.load(fp)
                exec_name = pl.get("CFBundleExecutable")
        except Exception as e:
            print(f"نەتوانرا پڵست بخوێندرێتەوە: {e}")

    if not exec_name:
        exec_name = os.path.splitext(app_folders[0])[0]

    main_exec = os.path.join(app_dir, exec_name)
    print(f"باینەری سەرەکی دەستنیشانکرا: {main_exec}")

    # ١. لەبەرگرتنەوەی فایلی dylib بۆ ناو .app
    target_dylib = os.path.join(app_dir, "AlertAshte.dylib")
    shutil.copy2(dylib_file, target_dylib)
    os.chmod(target_dylib, 0o755)

    # ٢. ئینجێکتکردنی ڕاستەوخۆ بە پایتۆن لە ناو هێدەری باینەری
    if os.path.exists(main_exec):
        inject_binary(main_exec)
    else:
        print("باینەری سەرەکی نەدۆزرایەوە!")

    # ٣. دووبارە بەستنەوەی فایلی IPA
    os.remove(target_ipa)
    shutil.make_archive("repacked", 'zip', work_dir)
    shutil.move("repacked.zip", target_ipa)
    shutil.rmtree(work_dir)
    print("هەموو کارەکان تەواو بوون، فایلی IPA نوێ ئامادەیە!")

if __name__ == "__main__":
    inject()
