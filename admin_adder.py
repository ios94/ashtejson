import os
import json
import requests
import random
import re
import urllib.parse
from bs4 import BeautifulSoup
from datetime import datetime, timezone

app_name_input = os.environ.get("APP_NAME", "").strip()
ipa_link = os.environ.get("IPA_LINK", "").strip()

if not app_name_input or not ipa_link:
    print("کێشە: پێویستە ناوی یاری و لینک پڕ بکرێتەوە!")
    exit(1)

slug = "".join(e for e in app_name_input if e.isalnum()).lower()
if not slug:
    slug = f"app{random.randint(1000, 9999)}"

print(f"خەریکی گەڕانم بەدوای '{app_name_input}' لەناو سایتەکە بە ئۆتۆماتیکی...")

# فەنکشن بۆ دۆزینەوەی یاری لەناو داتای سایتەکە
def find_app_in_json(data, target_name):
    if isinstance(data, dict):
        name = data.get('name', '')
        if isinstance(name, str) and target_name.lower() in name.lower():
            if 'version' in data or 'size' in data or 'image' in data or 'iconURL' in data:
                return data
        for value in data.values():
            result = find_app_in_json(value, target_name)
            if result: return result
    elif isinstance(data, list):
        for item in data:
            result = find_app_in_json(item, target_name)
            if result: return result
    return None

# فەنکشن بۆ هێنانی داتا لە سایتەکەوە بەبێ پێویستی بە لینک
def fetch_checkover_data(app_name):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    # ١. سەرەتا با لە ڕێگەی گەڕانی سایتەکەوە تاقی بکەینەوە
    search_params = [
        f"?filter[search]={urllib.parse.quote(app_name)}",
        f"?search={urllib.parse.quote(app_name)}",
        f"?q={urllib.parse.quote(app_name)}"
    ]
    
    for param in search_params:
        url = f"https://check0ver.net/en/iapps{param}"
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                app_div = soup.find('div', id='app')
                if app_div and app_div.has_attr('data-page'):
                    page_data = json.loads(app_div['data-page'])
                    found = find_app_in_json(page_data, app_name)
                    if found: return found
        except:
            pass
            
    # ٢. ئەگەر بە گەڕان نەیدۆزییەوە، با بەناو ١٥ لاپەڕەی یەکەمدا بگەڕێت!
    print("خەریکە بەناو لاپەڕەکانی سایتەکەدا دەگەڕێم، تکایە کەمێک چاوەڕێ بە...")
    for page in range(1, 16):
        url = f"https://check0ver.net/en/iapps?page={page}"
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                app_div = soup.find('div', id='app')
                if app_div and app_div.has_attr('data-page'):
                    page_data = json.loads(app_div['data-page'])
                    found = find_app_in_json(page_data, app_name)
                    if found: 
                        print(f"(یارییەکە لە لاپەڕەی {page} دۆزرایەوە!)")
                        return found
        except:
            continue
            
    return None

target_app = fetch_checkover_data(app_name_input)

if not target_app:
    print(f"کێشە: نەمتوانی یاری '{app_name_input}' بدۆزمەوە.")
    print("تکایە دڵنیابە کە ناوی یارییەکەت ڕاست نووسیوە.")
    exit(1)

print(f"سەرکەوتوو بوو! یارییە دۆزرایەوە:")
print(f"- ناو: {target_app.get('name', app_name_input)}")
print(f"- ڤێرژن: {target_app.get('version', '1.0')}")
print(f"- قەبارە: {target_app.get('size', 'N/A')}")

# ڕێکخستن و داگرتنی وێنەکە
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
        ir = requests.get(app_icon_url, stream=True, headers={"User-Agent": "Mozilla/5.0"})
        if ir.status_code == 200:
            with open(icon_path, "wb") as f:
                for chunk in ir.iter_content(1024):
                    f.write(chunk)
    except Exception as e:
        print(f"ئیرۆر لە داگرتنی وێنە: {e}")

icon_relative = f"img/{downloaded_icon_name}"
icon_full_url = f"https://raw.githubusercontent.com/ios94/ashtejson/main/img/{downloaded_icon_name}"

# داگرتنی یارییەکە
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

# دروستکردنی فۆرمات
github_release_url = f"https://github.com/ios94/ashtejson/releases/download/V1/{slug}.ipa"
current_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
app_id = random.randint(1111111111, 1999999999)

app_size_str = target_app.get('size', '100 MB')
try:
    size_in_mb = float(re.sub(r'[^\d.]', '', str(app_size_str)))
    size_in_bytes = int(size_in_mb * 1024 * 1024)
except:
    size_in_bytes = 150000000

new_app = {
    "id": app_id,
    "name": target_app.get('name', app_name_input),
    "version": target_app.get('version', '1.0'),
    "size": str(app_size_str),
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
    ]
}

# سەیڤکردن لە JSON وە خستنە ڕیزی یەکەم
json_file = "ashtemobile94.json"
backup_file = "backup_memory.json"
source_data = None

if os.path.exists(json_file):
    with open(json_file, "r", encoding="utf-8") as f:
        source_data = json.load(f)
else:
    source_data = {"apps": []}

if "apps" not in source_data:
    source_data["apps"] = []

is_update = False
for i, existing_app in enumerate(source_data["apps"]):
    if existing_app.get("name") == new_app["name"]:
        new_app["id"] = existing_app.get("id", app_id)
        source_data["apps"].pop(i)  # دەرکردنی کۆنەکە
        is_update = True
        break

# خستنە ڕیزی یەکەم
source_data["apps"].insert(0, new_app)

if is_update:
    print("\n===> ئەم یارییە پێشتر هەبوو، ئاپدەیت کرا و هاتە ڕیزی یەکەم! <===\n")
else:
    print("\n===> یارییەکی نوێیە، بە سەرکەوتوویی چووە ڕیزی یەکەم! <===\n")

with open(json_file, "w", encoding="utf-8") as f:
    json.dump(source_data, f, ensure_ascii=False, indent=4)
    
with open(backup_file, "w", encoding="utf-8") as f:
    json.dump(source_data, f, ensure_ascii=False, indent=4)

print("هەموو کارەکان بە سەرکەوتوویی کۆتایی هات.")
