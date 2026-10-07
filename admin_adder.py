import os
import json
import requests
import random
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime, timezone

app_name_input = os.environ.get("APP_NAME", "").strip()
website_url = os.environ.get("WEBSITE_URL", "https://ashtemobile.tututweak.com/o.html").strip()

if not app_name_input:
    print("کێشە: دەبێت ناوی یارییەکە بنووسیت!")
    exit(1)

print(f"خەریکی گەڕانم بەدوای '{app_name_input}' لەناو {website_url} ...")

headers = {"User-Agent": "Mozilla/5.0"}
try:
    response = requests.get(website_url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
except Exception as e:
    print(f"نەمتوانی ماڵپەڕەکە بکەمەوە: {e}")
    exit(1)

app_found = False
ipa_link = ""
icon_url = "https://ashtemobile.site/logo.png"
version = "1.0"
size_str = "100 MB"
app_name = app_name_input

# گەڕان بەناو هەموو یارییەکانی ماڵپەڕەکە
for a_tag in soup.find_all('a'):
    btn_text = a_tag.get_text(strip=True)
    if "دابەزاندن" in btn_text or "داگرتن" in btn_text:
        # ڕاستکردنەوەی گەڕانەکە بۆ دۆزینەوەی تەواوی قاڵبی یارییەکە نەک تەنها دوگمەکە
        card = a_tag.parent
        while card and card.name != 'body':
            if card.find('img'):
                break
            card = card.parent
        
        if not card or card.name == 'body':
            continue
        
        card_text = card.get_text(separator=' ', strip=True)
        
        if app_name_input.lower() in card_text.lower():
            app_found = True
            
            # وەرگرتنی ناوە دروستەکە
            heading = card.find(['h1', 'h2', 'h3', 'h4', 'strong', 'p', 'span'])
            if heading:
                app_name = heading.get_text(strip=True)
            else:
                app_name = app_name_input
                
            ipa_link = urljoin(website_url, a_tag.get('href'))
            
            img_tag = card.find('img')
            if img_tag and img_tag.get('src'):
                icon_url = urljoin(website_url, img_tag.get('src'))
                
            v_match = re.search(r'V\s*([\d\.]+)', card_text, re.IGNORECASE)
            if v_match:
                version = v_match.group(1)
                
            s_match = re.search(r'MB\s*([\d\.]+)', card_text, re.IGNORECASE)
            if s_match:
                size_str = f"{s_match.group(1)} MB"
            
            break

if not app_found:
    print(f"کێشە: نەمتوانی یارییەکی وا بە ناوی '{app_name_input}' لە ماڵپەڕەکەتدا بدۆزمەوە.")
    exit(1)

print(f"دۆزیمەوە! ناو: {app_name} | ڤێرژن: {version} | قەبارە: {size_str}")
print(f"لۆگۆ: {icon_url}")

try:
    size_in_mb = float(re.sub(r'[^\d.]', '', size_str))
    size_in_bytes = int(size_in_mb * 1024 * 1024)
except:
    size_in_bytes = 150000000

slug = "".join(e for e in app_name if e.isalnum()).lower()
app_id = random.randint(1111111111, 1999999999)

os.makedirs("ipas", exist_ok=True)
ipa_filename = f"ipas/{slug}.ipa"

print(f"خەریکی داگرتنی {app_name} ...")
try:
    r = requests.get(ipa_link, stream=True, headers=headers)
    if r.status_code == 200:
        with open(ipa_filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        print("داگرتنەکە سەرکەوتوو بوو.")
    else:
        print("کێشە هەیە لە لینکی یارییەکە!")
        exit(1)
except Exception as e:
    print(f"ئیرۆر لە کاتی داگرتن: {e}")
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
    "localizedDescription": "Downloaded magically from AshteMobile Website.",
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

existing_idx = next((i for i, a in enumerate(source_data["apps"]) if a.get("name") == new_app["name"]), None)
if existing_idx is not None:
    source_data["apps"][existing_idx] = new_app
else:
    source_data["apps"].append(new_app)

with open(json_file, "w", encoding="utf-8") as f:
    json.dump(source_data, f, ensure_ascii=False, indent=4)
    
with open(backup_file, "w", encoding="utf-8") as f:
    json.dump(source_data, f, ensure_ascii=False, indent=4)

print(f"سەرکەوتوو بوو! یاری {app_name} خرایە ناو سۆرسەکەتەوە.")
