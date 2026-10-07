import os
import json
import requests
import random
import re
from datetime import datetime, timezone

bulk_data = os.environ.get("BULK_DATA", "").strip()

json_file = "ashtemobile94.json"
backup_file = "backup_memory.json"

# کردنەوەی فایلە سەرەکییەکان
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

os.makedirs("img", exist_ok=True)
os.makedirs("ipas", exist_ok=True)
current_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")

added_count = 0
lines = bulk_data.split('\n')

for line in lines:
    line = line.strip()
    if not line or "|" not in line:
        continue
        
    parts = [p.strip() for p in line.split("|")]
    if len(parts) < 5:
        print(f"زانیاری کەمە لەم دێڕەدا: {line}")
        continue
        
    app_name, app_version, app_size_str, app_icon_input, ipa_link = parts[0], parts[1], parts[2], parts[3], parts[4]
    
    slug = "".join(e for e in app_name if e.isalnum()).lower()
    app_id = random.randint(1111111111, 1999999999)

    try:
        size_in_mb = float(re.sub(r'[^\d.]', '', app_size_str))
        size_in_bytes = int(size_in_mb * 1024 * 1024)
    except:
        size_in_bytes = 150000000

    # ڕێکخستن و داگرتنی وێنەکە
    if app_icon_input.startswith("http://") or app_icon_input.startswith("https://"):
        print(f"داگرتنی وێنە بۆ {app_name}...")
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
        except Exception as e:
            print(f"کێشە لە وێنەی {app_name}: {e}")

        icon_relative = f"img/{downloaded_icon_name}"
        icon_full_url = f"https://raw.githubusercontent.com/ios94/ashtejson/main/img/{downloaded_icon_name}"
    else:
        icon_relative = f"img/{app_icon_input}"
        icon_full_url = f"https://raw.githubusercontent.com/ios94/ashtejson/main/img/{app_icon_input}"

    # داگرتنی یارییەکە
    ipa_filename = f"ipas/{slug}.ipa"
    print(f"خەریکی داگرتنی یاری {app_name} ...")
    
    try:
        r = requests.get(ipa_link, stream=True)
        if r.status_code == 200:
            with open(ipa_filename, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"داگرتنی {app_name} سەرکەوتوو بوو.")
        else:
            print(f"کێشە لە لینکی {app_name} هەیە، تێپەڕێنرا.")
            continue
    except Exception as e:
        print(f"ئیرۆری داگرتن بۆ {app_name}: {e}")
        continue

    github_release_url = f"https://github.com/ios94/ashtejson/releases/download/V1/{slug}.ipa"

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

    # سڕینەوەی یارییە کۆنەکە ئەگەر بە هەمان ناو هەبوو، بۆ ئەوەی دووبارە نەبێتەوە
    source_data["apps"] = [a for a in source_data["apps"] if a.get("name") != app_name]
    source_data["apps"].append(new_app)
    added_count += 1

# پاشەکەوتکردن لە هەردوو فایلەکەدا
with open(json_file, "w", encoding="utf-8") as f:
    json.dump(source_data, f, ensure_ascii=False, indent=4)
    
with open(backup_file, "w", encoding="utf-8") as f:
    json.dump(source_data, f, ensure_ascii=False, indent=4)

print(f"\nکۆتایی هات! {added_count} یاری بە سەرکەوتوویی زیاد کران.")
