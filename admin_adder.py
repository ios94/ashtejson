import os
import json
import requests
import random
import re
from datetime import datetime, timezone

app_name = os.environ.get("APP_NAME")
app_version = os.environ.get("APP_VERSION")
app_size_str = os.environ.get("APP_SIZE")
app_icon_input = os.environ.get("APP_ICON").strip()
ipa_link = os.environ.get("IPA_LINK").strip()

slug = "".join(e for e in app_name if e.isalnum()).lower()
app_id = random.randint(1111111111, 1999999999)

try:
    size_in_mb = float(re.sub(r'[^\d.]', '', app_size_str))
    size_in_bytes = int(size_in_mb * 1024 * 1024)
except:
    size_in_bytes = 150000000

os.makedirs("img", exist_ok=True)

if app_icon_input.startswith("http://") or app_icon_input.startswith("https://"):
    print("دەستم کرد بە داگرتنی وێنەکە لە لینکەکەوە...")
    ext = ".jpg"
    if ".png" in app_icon_input.lower():
        ext = ".png"
    elif ".jpeg" in app_icon_input.lower():
        ext = ".jpeg"
        
    downloaded_icon_name = f"{slug}{ext}"
    icon_path = os.path.join("img", downloaded_icon_name)
    
    try:
        ir = requests.get(app_icon_input, stream=True)
        if ir.status_code == 200:
            with open(icon_path, "wb") as f:
                for chunk in ir.iter_content(1024):
                    f.write(chunk)
            print(f"وێنەکە داگیرا: {downloaded_icon_name}")
    except Exception as e:
        print(f"ئیرۆر لە وێنە: {e}")

    icon_relative = f"img/{downloaded_icon_name}"
    icon_full_url = f"https://raw.githubusercontent.com/ios94/ashtejson/main/img/{downloaded_icon_name}"
else:
    print("تەنها ناوی وێنەکە بەکاردەهێنم.")
    icon_relative = f"img/{app_icon_input}"
    icon_full_url = f"https://raw.githubusercontent.com/ios94/ashtejson/main/img/{app_icon_input}"

os.makedirs("ipas", exist_ok=True)
ipa_filename = f"ipas/{slug}.ipa"

print(f"خەریکی داگرتنی یاری {app_name} ...")

try:
    r = requests.get(ipa_link, stream=True)
    if r.status_code == 200:
        with open(ipa_filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        print("داگرتنی یارییەکە سەرکەوتوو بوو.")
    else:
        print("کێشە لە داگرتنی IPA هەیە!")
        exit(1)
except Exception as e:
    print(f"Error: {e}")
    exit(1)

json_file = "ashtemobile94.json"
backup_file = "backup_memory.json"

if os.path.exists(json_file):
    with open(json_file, "r", encoding="utf-8") as f:
        source_data = json.load(f)
elif os.path.exists(backup_file):
    with open(backup_file, "r", encoding="utf-8") as f:
        source_data = json.load(f)
else:
    source_data = {
        "name": "Ashtemobile",
        "subtitle": "A source for all of my apps & games",
        "description": "Welcome to my source! Here you'll find all of my apps.",
        "iconURL": "https://ashtemobile.site/logo.png",
        "website": "https://ashtemobile.site/",
        "patreonURL": "https://ashtemobile.site/Ashtemobile.json",
        "tintColor": "#ff007f",
        "featuredApps": [],
        "headerURL": "https://ashtemobile.site/logo.png",
        "apps": [],
        "news": []
    }

github_release_url = f"https://github.com/ios94/ashtejson/releases/download/V1/{slug}.ipa"
current_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")

new_app = {
    "id": app_id,
    "name": app_name,
    "version": app_version,
    "size": app_size_str,
    "icon": icon_relative,
    "badge": "",
    "type": "apps",
    "install_url": github_release_url,
    "download_url": github_release_url,
    "bundleIdentifier": f"com.ashtemobile.app{app_id}",
    "marketplaceID": "",
    "developerName": "AshteMobile",
    "subtitle": "Awesome App",
    "localizedDescription": "Downloaded from AshteMobile Source.",
    "iconURL": icon_full_url,
    "tintColor": "#04ecfc",
    "category": "apps",
    "screenshots": [],
    "versions": [
        {
            "version": app_version,
            "date": current_date,
            "localizedDescription": None,
            "downloadURL": github_release_url,
            "size": size_in_bytes,
            "buildVersion": None,
            "minOSVersion": "14.0"
        }
    ],
    "appPermissions": {
        "entitlements": [],
        "privacy": {
            "NSUserTrackingUsageDescription": "Your data will be used to deliver personalized ads to you."
        }
    },
    "patreon": {}
}

existing_idx = next((i for i, a in enumerate(source_data["apps"]) if a.get("name") == new_app["name"]), None)
if existing_idx is not None:
    source_data["apps"][existing_idx] = new_app
else:
    source_data["apps"].append(new_app)

with open(json_file, "w", encoding="utf-8") as f:
    json.dump(source_data, f, ensure_ascii=False, indent=4)
    
with open(backup_file, "w", encoding="utf-8") as f:
    json.dump(source_data, f, ensure_ascii=False, indent=4)

print("بە سەرکەوتوویی یارییەکە و وێنەکەی سەیڤ کران!")
