import os
import json
import requests
import random
import re
from datetime import datetime, timezone

# وەرگرتنی زانیارییەکان لە فۆڕمەکەی گیتهاپەوە
app_name = os.environ.get("APP_NAME")
app_version = os.environ.get("APP_VERSION")
app_size_str = os.environ.get("APP_SIZE")
app_icon_input = os.environ.get("APP_ICON")
ipa_link = os.environ.get("IPA_LINK")

# دروستکردنی ناوی کورت (slug) و ئایدییەکی هەڕەمەکی وەک فۆرماتەکەت
slug = "".join(e for e in app_name if e.isalnum()).lower()
app_id = random.randint(1111111111, 1999999999)

# گۆڕینی قەبارە لە MB بۆ Bytes بە شێوەی ئۆتۆماتیکی بۆ بەشی versions
try:
    size_in_mb = float(re.sub(r'[^\d.]', '', app_size_str))
    size_in_bytes = int(size_in_mb * 1024 * 1024)
except:
    size_in_bytes = 150000000

# ڕێکخستنی لینکەکانی وێنە بۆ فۆرماتە تایبەتەکەت
icon_relative = f"img/{app_icon_input}"
icon_full_url = f"https://ashtemobile.site/img/{app_icon_input}"

# دروستکردنی فۆڵدەر و داگرتنی IPA بۆ ناو ڕێلیز
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

# خوێندنەوەی فایلی JSON یان دروستکردنی بنچینە تایبەتەکەی خۆت ئەگەر نەبوو
json_file = "ashtemobile94.json"
if os.path.exists(json_file):
    with open(json_file, "r", encoding="utf-8") as f:
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
        "news": [
            {
                "title": "Instagram",
                "identifier": "news_kwuwharinc",
                "caption": "Ashtemobile",
                "date": "2026-08-28T16:13:42+00:00",
                "tintColor": "#ff007f",
                "imageURL": "https://ashtemobile.site/logo.png",
                "notify": True,
                "url": "https://www.instagram.com/ashtemobile",
                "appID": None
            },
            {
                "title": "Telegram",
                "identifier": "news_l2keyetzkn",
                "caption": "Ashtemobile",
                "date": "2026-08-28T16:13:42+00:00",
                "tintColor": "#ff007f",
                "imageURL": "https://ashtemobile.site/logo.png",
                "notify": True,
                "url": "https://t.me/ashtemobile",
                "appID": None
            }
        ]
    }

github_release_url = f"https://github.com/ios94/ashtejson/releases/download/V1/{slug}.ipa"
current_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")

# فۆرماتە تایبەتەکەی یارییەکە ڕێک وەک نموونەکەت
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

# نوێکردنەوە یان زیادکردنی ئەپەکە
existing_idx = next((i for i, a in enumerate(source_data["apps"]) if a.get("name") == new_app["name"]), None)
if existing_idx is not None:
    source_data["apps"][existing_idx] = new_app
else:
    source_data["apps"].append(new_app)

with open(json_file, "w", encoding="utf-8") as f:
    json.dump(source_data, f, ensure_ascii=False, indent=4)

print(f"Successfully generated perfect JSON for {app_name}!")
