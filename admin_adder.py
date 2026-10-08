import os
import json
import requests
import random
import re
import copy
import urllib.parse
from bs4 import BeautifulSoup
from datetime import datetime, timezone

checkover_link = os.environ.get("CHECKOVER_LINK", "").strip()
app_name_input = os.environ.get("APP_NAME", "").strip()
ipa_link = os.environ.get("IPA_LINK", "").strip()

if not checkover_link or not app_name_input or not ipa_link:
    print("کێشە: پێویستە هەموو خانەکان پڕ بکرێنەوە!")
    exit(1)

slug = "".join(e for e in app_name_input if e.isalnum()).lower()
if not slug:
    slug = f"app{random.randint(1000, 9999)}"

print("خەریکی پشکنینی سایتەکەم بۆ دۆزینەوەی یارییەکە...")

# ١. هێنانی زانیارییەکان لە سایتەکەوە
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}
try:
    response = requests.get(checkover_link, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # دۆزینەوەی داتای JSON لەناو سایتەکە
    app_div = soup.find('div', id='app')
    if not app_div or not app_div.has_attr('data-page'):
        print("کێشە: نەمتوانی زانیارییەکان لە سایتەکە دەربهێنم.")
        exit(1)
        
    page_data = json.loads(app_div['data-page'])
    games_list = page_data.get('props', {}).get('paginator', {}).get('data', [])
    
    if not games_list:
        # هەوڵدان لە شوێنی تر ئەگەر لەناو paginator نەبوو
        games_list = page_data.get('props', {}).get('app', {}).get('apps', [])
        
except Exception as e:
    print(f"کێشە لە پەیوەندیکردن بە سایتەکە: {e}")
    exit(1)

# ٢. دۆزینەوەی یارییەکە
target_app = None
for game in games_list:
    name = game.get('name', '')
    if app_name_input.lower() in name.lower():
        target_app = game
        break

if not target_app:
    print(f"کێشە: نەمتوانی یاری '{app_name_input}' لەناو ئەو لینکەدا بدۆزمەوە.")
    exit(1)

print(f"سەرکەوتوو بوو! یارییە دۆزرایەوە:")
print(f"- ناو: {target_app.get('name')}")
print(f"- ڤێرژن: {target_app.get('version')}")
print(f"- قەبارە: {target_app.get('size')}")

# ٣. ڕێکخستنی وێنەکە
app_icon_url = target_app.get('image', target_app.get('icon', target_app.get('iconURL', '')))
os.makedirs("img", exist_ok=True)
ext = ".jpg"
if ".png" in app_icon_url.lower():
    ext = ".png"
downloaded_icon_name = f"{slug}{ext}"
icon_path = os.path.join("img", downloaded_icon_name)

if app_icon_url and app_icon_url.startswith("http"):
    print("خەریکی داگرتنی وێنەکە...")
    try:
        ir = requests.get(app_icon_url, stream=True, headers=headers)
        if ir.status_code == 200:
            with open(icon_path, "wb") as f:
                for chunk in ir.iter_content(1024):
                    f.write(chunk)
    except Exception as e:
        print(f"ئیرۆر لە داگرتنی وێنە: {e}")

icon_relative = f"img/{downloaded_icon_name}"
icon_full_url = f"https://raw.githubusercontent.com/ios94/ashtejson/main/img/{downloaded_icon_name}"

# ٤. داگرتنی یارییەکە (IPA)
os.makedirs("ipas", exist_ok=True)
ipa_filename = f"ipas/{slug}.ipa"
print("خەریکی داگرتنی یارییەکە لە لینکەکەتەوە...")
try:
    r = requests.get(ipa_link, stream=True)
    if r.status_code == 200:
        with open(ipa_filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        print("داگرتنی IPA سەرکەوتوو بوو.")
    else:
        print("کێشە لە داگرتنی یارییەکە هەیە!")
        exit(1)
except Exception as e:
    print(f"Error: {e}")
    exit(1)

# ٥. دروستکردنی فۆرمات بۆ سۆرسەکەت
github_release_url = f"https://github.com/ios94/ashtejson/releases/download/V1/{slug}.ipa"
current_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
app_id = random.randint(1111111111, 1999999999)

app_size_str = target_app.get('size', '100 MB')
try:
    size_in_mb = float(re.sub(r'[^\d.]', '', app_size_str))
    size_in_bytes = int(size_in_mb * 1024 * 1024)
except:
    size_in_bytes = 150000000

new_app = {
    "id": app_id,
    "name": target_app.get('name', app_name_input),
    "version": target_app.get('version', '1.0'),
    "size": app_size_str,
    "icon": icon_relative,
    "badge": "",
    "type": "games",
    "install_url": github_release_url,
    "download_url": github_release_url,
    "bundleIdentifier": target_app.get('bundle', target_app.get('bundleIdentifier', f"com.ashtemobile.{slug}")),
    "marketplaceID": "",
    "developerName": "AshteMobile",
    "subtitle": "Awesome App",
    "localizedDescription": target_app.get('description', "Downloaded from AshteMobile Source."),
    "iconURL": icon_full_url,
    "tintColor": "#04ecfc",
    "category": "games",
    "screenshots": [],
    "versions": [
        {
            "version": target_app.get('version', '1.0'),
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

# ٦. سەیڤکردن لەناو JSON
json_file = "ashtemobile94.json"
backup_file = "backup_memory.json"
source_data = None

if os.path.exists(json_file):
    with open(json_file, "r", encoding="utf-8") as f:
        source_data = json.load(f)
else:
    source_data = {"apps": []}

is_update = False
for i, existing_app in enumerate(source_data.get("apps", [])):
    if existing_app.get("name") == new_app["name"]:
        # گۆڕینی ئایدی بۆ ئەوەی کۆنەکە تێک نەچێت
        new_app["id"] = existing_app.get("id", app_id)
        source_data["apps"][i] = new_app
        is_update = True
        break

if is_update:
    print("\n===> ئەم یارییە پێشتر هەبوو، ئاپدەیت کرا بۆ ڤێرژنە نوێیەکە! <===\n")
else:
    source_data.setdefault("apps", []).append(new_app)
    print("\n===> یارییەکی نوێیە، بە سەرکەوتوویی زیاد کرا! <===\n")

with open(json_file, "w", encoding="utf-8") as f:
    json.dump(source_data, f, ensure_ascii=False, indent=4)
    
with open(backup_file, "w", encoding="utf-8") as f:
    json.dump(source_data, f, ensure_ascii=False, indent=4)

print("هەموو کارەکان بە سەرکەوتوویی کۆتایی هات.")
