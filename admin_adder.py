import os
import json
import requests
import random
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime, timezone

# --- ڕێکخستنەکان ---
url = "https://ashtemobile.tututweak.com/o.html"
os.makedirs("ipas", exist_ok=True)

json_file = "ashtemobile94.json"
backup_file = "backup_memory.json"

# بەدەستهێنانی زانیارییەکان لە ماڵپەڕەکەتەوە
headers = {"User-Agent": "Mozilla/5.0"}
print("خەریکی خوێندنەوەی ماڵپەڕەکەم...")
try:
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
except Exception as e:
    print(f"کێشە هەیە لە کردنەوەی ماڵپەڕەکە: {e}")
    exit(1)

# ئامادەکردنی مێشکی بنچینەیی بۆ سۆرسەکە
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

current_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
apps_found = 0

# گەڕان بەدوای وشەی "دابەزاندن" لەناو ماڵپەڕەکەت
for a_tag in soup.find_all('a'):
    btn_text = a_tag.get_text(strip=True)
    if "دابەزاندن" in btn_text or "داگرتن" in btn_text:
        parent = a_tag.find_parent('div')
        if not parent:
            continue

        ipa_link = urljoin(url, a_tag.get('href'))
        
        # دەرهێنانی ناوی یارییەکە
        app_name = "Unknown App"
        heading = parent.find(['h1', 'h2', 'h3', 'h4', 'strong', 'p', 'span'])
        if heading:
            app_name = heading.get_text(strip=True)
        
        # دەرهێنانی لۆگۆی یارییەکە ڕاستەوخۆ لە ماڵپەڕەکەوە
        icon_url = "https://ashtemobile.site/logo.png"
        img_tag = parent.find('img')
        if img_tag and img_tag.get('src'):
            icon_url = urljoin(url, img_tag.get('src'))

        # دەرهێنانی ڤێرژن و قەبارە (MB)
        version = "1.0"
        size_str = "100 MB"
        
        full_text = parent.get_text(separator=' ', strip=True)
        
        v_match = re.search(r'V\s*([\d\.]+)', full_text, re.IGNORECASE)
        if v_match:
            version = v_match.group(1)
            
        s_match = re.search(r'MB\s*([\d\.]+)', full_text, re.IGNORECASE)
        if s_match:
            size_str = f"{s_match.group(1)} MB"

        try:
            size_in_mb = float(re.sub(r'[^\d.]', '', size_str))
            size_in_bytes = int(size_in_mb * 1024 * 1024)
        except:
            size_in_bytes = 150000000

        slug = "".join(e for e in app_name if e.isalnum()).lower()
        app_id = random.randint(1111111111, 1999999999)
        ipa_filename = f"ipas/{slug}.ipa"
        
        # --- داگرتنی یارییەکان یەک لە دوای یەک ---
        print(f"خەریکی داگرتنی یاری {app_name} ...")
        try:
            r = requests.get(ipa_link, stream=True, headers=headers)
            if r.status_code == 200:
                with open(ipa_filename, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"سەرکەوتوو بوو: {app_name}")
            else:
                print(f"کێشە لە داگرتنی {app_name} هەیە.")
                continue
        except Exception as e:
            print(f"هەڵە: {e}")
            continue

        github_release_url = f"https://github.com/ios94/ashtejson/releases/download/V1/{slug}.ipa"

        new_app = {
            "id": app_id,
            "name": app_name,
            "version": version,
            "size": size_str,
            "icon": icon_url, 
            "badge": "",
            "type": "apps",
            "install_url": github_release_url,
            "download_url": github_release_url,
            "bundleIdentifier": f"com.ashtemobile.app{app_id}",
            "marketplaceID": "",
            "developerName": "AshteMobile",
            "subtitle": "Awesome App",
            "localizedDescription": "Downloaded automatically from AshteMobile Website.",
            "iconURL": icon_url,
            "tintColor": "#04ecfc",
            "category": "apps",
            "screenshots": [],
            "versions": [
                {
                    "version": version,
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

        source_data["apps"].append(new_app)
        apps_found += 1

# پاشەکەوتکردن لە فایلی سەرەکی و بیرگەی شاراوە
with open(json_file, "w", encoding="utf-8") as f:
    json.dump(source_data, f, ensure_ascii=False, indent=4)
    
with open(backup_file, "w", encoding="utf-8") as f:
    json.dump(source_data, f, ensure_ascii=False, indent=4)

print(f"کۆتایی هات! کۆی گشتی یارییە زیادکراوەکان: {apps_found}")
