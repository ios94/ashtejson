import os
import json
import requests
from datetime import datetime

# وەرگرتنی زانیارییەکان لە فۆڕمەکەی گیتهاپەوە
app_name = os.environ.get("APP_NAME")
app_version = os.environ.get("APP_VERSION")
app_size = os.environ.get("APP_SIZE")
app_icon_input = os.environ.get("APP_ICON")
ipa_link = os.environ.get("IPA_LINK")

# دروستکردنی ناوی کورت (slug) بەبێ بۆشایی و هێما
slug = "".join(e for e in app_name if e.isalnum()).lower()

# ڕێکخستنی وێنەکە بۆ ئەوەی ڕاستەوخۆ لە فۆڵدەری img بیخوێنێتەوە
if app_icon_input.startswith("http"):
    final_icon_url = app_icon_input
else:
    # لێرەدا خۆکارانە دەچێتە سەر فۆڵدەری img لەناو گیتهاپەکەت
    final_icon_url = f"https://raw.githubusercontent.com/ios94/ashtejson/main/img/{app_icon_input}"

# دروستکردنی فۆڵدەر بۆ داگرتنی فایلی IPA
os.makedirs("ipas", exist_ok=True)
ipa_filename = f"ipas/{slug}.ipa"

print(f"Admin is downloading {app_name}...")

try:
    r = requests.get(ipa_link, stream=True)
    if r.status_code == 200:
        with open(ipa_filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        print("Download successful.")
    else:
        print(f"Failed to download the IPA link! Status: {r.status_code}")
        exit(1)
except Exception as e:
    print(f"Error downloading {app_name}: {e}")
    exit(1)

# نوێکردنەوەی فایلی ashtemobile94.json
json_file = "ashtemobile94.json"
if os.path.exists(json_file):
    with open(json_file, "r", encoding="utf-8") as f:
        source_data = json.load(f)
else:
    source_data = {
        "name": "AshteMobile Store",
        "identifier": "com.ashtemobile.source",
        "apps": []
    }

# بەستنەوەی لینکی IPA بە ڕێلیزی V1 ەوە
github_release_url = f"https://github.com/ios94/ashtejson/releases/download/V1/{slug}.ipa"

new_app = {
    "name": app_name,
    "bundleIdentifier": f"com.ashtemobile.{slug}",
    "version": app_version,
    "size": app_size,
    "versionDate": datetime.now().strftime("%Y-%m-%d"),
    "downloadURL": github_release_url,
    "iconURL": final_icon_url,
    "localizedDescription": "Uploaded by Admin AshteMobile"
}

# دانانی یارییەکە یان نوێکردنەوەی ئەگەر پێشتر هەبوو
existing_idx = next((i for i, a in enumerate(source_data["apps"]) if a["bundleIdentifier"] == new_app["bundleIdentifier"]), None)
if existing_idx is not None:
    source_data["apps"][existing_idx] = new_app
else:
    source_data["apps"].append(new_app)

with open(json_file, "w", encoding="utf-8") as f:
    json.dump(source_data, f, ensure_ascii=False, indent=4)

print(f"Successfully added {app_name} to the store source with icon {final_icon_url}!")
