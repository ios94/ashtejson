import os
import json
import requests
import random
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime, timezone

website_url = "https://ashtemobile.tututweak.com/o.html"
print(f"خەریکی خوێندنەوەی تەواوی ماڵپەڕەکەم: {website_url}")

headers = {"User-Agent": "Mozilla/5.0"}
try:
    response = requests.get(website_url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
except Exception as e:
    print(f"نەمتوانی ماڵپەڕەکە بکەمەوە: {e}")
    exit(1)

# دروستکردنەوەی قاڵبی سەرەکی سۆرسەکە لە سفرەوە
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

os.makedirs("ipas", exist_ok=True)
current_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")

apps_count = 0

# گەڕان بەدوای هەموو دوگمەکانی دابەزاندن
for a_tag in soup.find_all('a'):
    btn_text = a_tag.get_text(strip=True)
    if "دابەزاندن" in btn_text or "داگرتن" in btn_text:
        card = a_tag.parent
        # دۆزینەوەی تەواوی چوارچێوەی یارییەکە
        while card and card.name != 'body':
            if card.find('img'):
                break
            card = card.parent
        
        if not card or card.name == 'body':
            continue
            
        card_text = card.get_text(separator=' ', strip=True)
        
        # دەرهێنانی ناو
        heading = card.find(['h1', 'h2', 'h3', 'h4', 'strong', 'p', 'span'])
        app_name = heading.get_text(strip=True) if heading else "Unknown App"
        
        if not app_name or app_name == "Unknown App":
            continue
            
        ipa_link = urljoin(website_url, a_tag.get('href'))
        
        # دەرهێنانی لۆگۆ
        img_tag = card.find('img')
        icon_url = urljoin(website_url, img_tag.get('src')) if img_tag and img_tag.get('src') else "https://ashtemobile.site/logo.png"
        
        # دەرهێنانی ڤێرژن و قەبارە
        v_match = re.search(r'V\s*([\d\.]+)', card_text, re.IGNORECASE)
        version = v_match.group(1) if v_match else "1.0"
        
        s_match = re.search(r'MB\s*([\d\.]+)', card_text, re.IGNORECASE)
        size_str = f"{s_match.group(1)} MB" if s_match else "100 MB"
        
        print(f"یاری دۆزرایەوە: {app_name} | {version} | {size_str}")
        
        try:
            size_in_mb = float(re.sub(r'[^\d.]', '', size_str))
            size_in_bytes = int(size_in_mb * 1024 * 1024)
        except:
            size_in_bytes = 150000000

        slug = "".join(e for e in app_name if e.isalnum()).lower()
        app_id = random.randint(1111111111, 1999999999)
        ipa_filename = f"ipas/{slug}.ipa"
        
        print(f"   --> خەریکی داگرتنی {app_name} ...")
        try:
            r = requests.get(ipa_link, stream=True, headers=headers)
            if r.status_code == 200:
                with open(ipa_filename, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            else:
                print(f"   --> کێشە لە لینکی {app_name} هەیە، تێپەڕێنرا.")
                continue
        except Exception as e:
            print(f"   --> هەڵە لە داگرتنی {app_name}: {e}")
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
                "privacy": {"NSUserTrackingUsageDescription": "Your data will be used to deliver personalized ads to you."}
            },
            "patreon": {}
        }
        source_data["apps"].append(new_app)
        apps_count += 1

# سەیڤکردنی کۆتایی لە هەردوو فایلەکەدا
with open("ashtemobile94.json", "w", encoding="utf-8") as f:
    json.dump(source_data, f, ensure_ascii=False, indent=4)
    
with open("backup_memory.json", "w", encoding="utf-8") as f:
    json.dump(source_data, f, ensure_ascii=False, indent=4)

print(f"\nسەرکەوتوو بوو! کۆی گشتی {apps_count} یاری بە ئۆتۆماتیکی داگیران و خرانە ناو سۆرسەکەتەوە.")
