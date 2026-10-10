import glob
import os
import plistlib
import shutil
import sys
import zipfile
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

  # دەرهێنانی فایلی IPA
  with zipfile.ZipFile(target_ipa, "r") as zip_ref:
    zip_ref.extractall(work_dir)

  payload_dir = os.path.join(work_dir, "Payload")
  app_folders = [f for f in os.listdir(payload_dir) if f.endswith(".app")]
  if not app_folders:
    print("فۆڵدەری .app نەدۆزرایەوە!")
    return

  app_dir = os.path.join(payload_dir, app_folders[0])
  plist_path = os.path.join(app_dir, "Info.plist")
  exec_name = None

  # ١. دەستکاریکردنی Info.plist بۆ گۆڕینی ناوی بەرنامە
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

      if not clean_name.endswith(suffix.strip()) and not clean_name.endswith(
          suffix
      ):
        new_name = f"{clean_name}{suffix}"
        pl["CFBundleDisplayName"] = new_name
        pl["CFBundleName"] = new_name

        with open(plist_path, "wb") as fp:
          plistlib.dump(pl, fp)

      # سڕینەوەی زمانەکان تا ناوی گۆڕدراو جێگیر بێت
      for strings_file in glob.glob(
          os.path.join(app_dir, "**", "InfoPlist.strings"), recursive=True
      ):
        try:
          os.remove(strings_file)
        except OSError:
          pass

    except Exception as e:
      print(f"هەڵە لە دەستکاریکردنی Info.plist: {e}")

  if not exec_name:
    exec_name = os.path.splitext(app_folders[0])[0]

  # ٢. دانانی فایلی dylib بە ناوی libCoreSecurity
  fake_official_name = "libCoreSecurity.dylib"
  target_dylib = os.path.join(app_dir, fake_official_name)
  shutil.copy2(dylib_file, target_dylib)
  os.chmod(target_dylib, 0o755)

  dylib_load_path = f"@executable_path/{fake_official_name}"

  # ٣. فەنکشنی بەستنەوە بە بەکارهێنانی LIEF
  def inject_to_binary(binary_path):
    if not os.path.exists(binary_path) or os.path.islink(binary_path):
      return False
    try:
      parsed = lief.MachO.parse(binary_path)
      if not parsed:
        return False

      injected = False
      for arch in parsed:
        existing_libs = [lib.name for lib in arch.libraries]
        if dylib_load_path not in existing_libs:
          arch.add_library(dylib_load_path)
          injected = True

      if injected:
        parsed.write(binary_path)
        os.chmod(binary_path, 0o755)
        print(f"بەستنەوە سەرکەوتوو بوو لە: {os.path.basename(binary_path)}")
        return True
    except Exception as e:
      print(f"نەتوانرا ببەسترێتەوە بە {os.path.basename(binary_path)}: {e}")
      return False

  # ٤. بەستنەوە بە باینەری سەرەکی
  main_exec = os.path.join(app_dir, exec_name)
  inject_to_binary(main_exec)

  # ٥. بەستنەوە بە فرەیمۆرکە سەرەکییەکان (UnityFramework یان فایلی .dylib لە ناو Frameworks)
  frameworks_dir = os.path.join(app_dir, "Frameworks")
  if os.path.exists(frameworks_dir):
    for item in os.listdir(frameworks_dir):
      item_path = os.path.join(frameworks_dir, item)
      if item.endswith(".framework") and os.path.isdir(item_path):
        framework_bin_name = os.path.splitext(item)[0]
        fw_binary = os.path.join(item_path, framework_bin_name)
        if os.path.exists(fw_binary):
          inject_to_binary(fw_binary)
      elif item.endswith(".dylib") and os.path.isfile(item_path):
        inject_to_binary(item_path)

  # ٦. کۆکردنەوە و دروستکردنەوەی فایلی IPA
  if os.path.exists(target_ipa):
    os.remove(target_ipa)

  shutil.make_archive("repacked", "zip", work_dir)
  shutil.move("repacked.zip", target_ipa)
  shutil.rmtree(work_dir)
  print("پڕۆسەی بەستنەوە بە سەرکەوتوویی کۆتایی هات!")


if __name__ == "__main__":
  inject()
