import json
import os
import requests

# دروستکردنی فۆڵدەر بۆ دابەزاندنی IPA
os.makedirs("ipas", exist_ok=True)

# خوێندنەوەی ئەو فایلەی کە تۆ زانیارییەکانت تێدا نووسیوە
with open("apps.json", "r", encoding="utf-8") as f:
    apps_input = json.load(f)

altstore_apps = []

for app in apps_input:
    name = app["name"]
    slug = app["slug"]
    ipa_url = app["ipa_link"]
    
    ipa_filename = f"ipas/{slug}.ipa"
    print(f"Downloading {name}...")
    
    try:
        # دابەزاندنی فایلی IPA
        r = requests.get(ipa_url, stream=True)
        if r.status_code == 200:
            with open(ipa_filename, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Downloaded {name} successfully.")
            
            # لینکی IPA لە ناو ڕێلیزی گیتهاب کە دەچێتە ناو سۆرسەکەوە
            github_release_url = f"https://github.com/ios94/ashtejson/releases/download/V1/{slug}.ipa"
            
            # ئامادەکردنی زانیارییەکان بۆ ناو فایلی سۆرس
            altstore_apps.append({
                "name": name,
                "bundleIdentifier": f"com.ashtemobile.{slug}",
                "version": app.get("version", "1.0"),
                "size": app.get("size", "0 MB"),
                "versionDate": "2026-10-07",
                "downloadURL": github_release_url,
                "iconURL": app.get("icon", ""),
                "localizedDescription": f"{name} - Uploaded by AshteMobile"
            })
        else:
            print(f"Failed to download {name} from {ipa_url}")
    except Exception as e:
        print(f"Error downloading {name}: {e}")

# دروستکردنی فایلی ashtemobile94.json بە شێوەی ئۆتۆماتیکی
altstore_source = {
    "name": "AshteMobile Store",
    "identifier": "com.ashtemobile.source",
    "apps": altstore_apps
}

with open("ashtemobile94.json", "w", encoding="utf-8") as f:
    json.dump(altstore_source, f, ensure_ascii=False, indent=4)

print("Source JSON generated successfully.")
