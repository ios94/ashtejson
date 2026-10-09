import sys
import os
import json
import requests
import random
import re
import urllib.parse
from bs4 import BeautifulSoup
from datetime import datetime, timezone

# بەشی دووەم: کاتێک ڕۆبۆتەکە لە ڕیزدایە تەنها بۆ نوێکردنەوەی سۆرسەکە
if len(sys.argv) > 1 and sys.argv[1] == "update_json":
    if not os.path.exists("temp_app.json"):
        exit(0)
        
    with open("temp_app.json", "r", encoding="utf-8") as f:
        new_app = json.load(f)
        
    json_file = "ashtemobile94.json"
    backup_file = "backup_memory.json"
    
    if os.path.exists(json_file):
        with open(json_file, "r", encoding="utf-8") as f:
            try:
                source_data = json.load(f)
                if "apps" not in source_data:
                    source_data["apps"] = []
            except:
                source_data = {"apps": []}
    else:
        source_data = {"apps": []}

    for i, existing_app in enumerate(source_data.get("apps", [])):
        if existing_app.get("name") == new_app["name"]:
            new_app["id"] = existing_app.get("id", new_app["id"])
            source_data["apps"].pop(i)
            break

    # خستنە ڕیزی یەکەم
    source_data["apps"].insert(0, new_app)

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(source_data, f, ensure_ascii=False, indent=4)
    with open(backup_file, "w", encoding="utf-8") as f:
        json.dump(source_data, f, ensure_ascii=False, indent=4)
        
    print("زانیارییەکان بە خێرایی و بە سەرکەوتوویی خرانە ناو سۆرسەکەت.")
    exit(0)


# بەشی یەکەم: هێنانی زانیارییەکان و داگرتنی فایلەکان
app_type = os.environ.get("APP_TYPE", "games").strip()
app_input = os.environ.get("APP_NAME", "").strip()
ipa_link = os.environ.get("IPA_LINK", "").strip()

if not app_input or not ipa_link:
    print("کێشە: پێویستە خانەکان پڕ بکرێنەوە!")
    exit(1)

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
target_app = None

def find_app_by_name(data, target_name):
    if isinstance(data, dict):
        name = data.get('name', '')
        if isinstance(name, str) and target_name.lower() in name.lower():
            if 'version' in data and 'size' in data: return data
        for value in data.values():
            res = find_app_by_name(value, target_name)
            if res: return res
    elif isinstance(data, list):
        for item in data:
            res = find_app_by_name(item, target_name)
            if res: return res
    return None

def find_main_app_in_page(data):
    if isinstance(data, dict):
        if 'name' in data and 'version' in data and 'size' in data and 'uuid' in data: return data
        for value in data.values():
            res = find_main_app_in_page(value)
            if res: return res
    elif isinstance(data, list):
        for item in data:
            res = find_main_app_in_page(item)
            if res: return res
    return None

if app_input.startswith("http"):
    print("لینک دۆزرایەوە! خەریکی هێنانی زانیارییەکانم...")
    try:
        res = requests.get(app_input, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        app_div = soup.find('div', id='app')
        if app_div and app_div.has_attr('data-page'):
            page_data = json.loads(app_div['data-page'])
            target_app = find_main_app_in_page(page_data)
    except Exception as e:
        print(f"کێشە لە کردنەوەی لینکەکە: {e}")
else:
    print(f"خەریکی گەڕانم بەدوای '{app_input}'...")
    search_params = [
        f"?filter[search]={urllib.parse.quote(app_input)}",
        f"?search={urllib.parse.quote(app_input)}"
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
                    target_app = find_app_by_name(page_data, app_input)
                    if target_app: break
        except: pass
    
    if not target_app:
        for page in range(1, 10):
            url = f"https://check0ver.net/en/iapps?page={page}"
            try:
                res = requests.get(url, headers=headers, timeout=10)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, 'html.parser')
                    app_div = soup.find('div', id='app')
                    if app_div and app_div.has_attr('data-page'):
                        page_data = json.loads(app_div['data-page'])
                        target_app = find_app_by_name(page_data, app_input)
                        if target_app: break
            except: continue

if not target_app:
    print("کێشە: نەمتوانی زانیاری یارییەکە بدۆزمەوە.")
    exit(1)

app_name_final = target_app.get('name', 'Unknown')
print(f"سەرکەوتوو بوو! دۆزرایەوە: {app_name_final} | بەشی: {app_type}")

slug = "".join(e for e in app_name_final if e.isalnum()).lower()
if not slug: slug = f"app{random.randint(1000, 9999)}"

app_icon_url = target_app.get('image', target_app.get('icon', target_app.get('iconURL', '')))
os.makedirs("img", exist_ok=True)
ext = ".jpg" if not ".png" in app_icon_url.lower() else ".png"
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
        pass

icon_relative = f"img/{downloaded_icon_name}"
icon_full_url = f"https://raw.githubusercontent.com/ios94/ashtejson/main/img/{downloaded_icon_name}"

os.makedirs("ipas", exist_ok=True)
ipa_filename = f"ipas/{slug}.ipa"
print("خەریکی داگرتنی یارییەکە...")
try:
    r = requests.get(ipa_link, stream=True)
    if r.status_code == 200:
        with open(ipa_filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
except Exception as e:
    print("کێشە لە داگرتنی یارییەکە هەیە!")
    exit(1)

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
    "name": app_name_final,
    "version": target_app.get('version', '1.0'),
    "size": str(app_size_str),
    "icon": icon_relative,
    "badge": "",
    "type": app_type,
    "install_url": github_release_url,
    "download_url": github_release_url,
    "bundleIdentifier": target_app.get('bundle', target_app.get('bundleIdentifier', f"com.ashtemobile.{slug}")),
    "marketplaceID": "",
    "developerName": "AshteMobile",
    "subtitle": "Awesome App",
    "localizedDescription": target_app.get('description', "Downloaded from AshteMobile Source."),
    "iconURL": icon_full_url,
    "tintColor": "#04ecfc",
    "category": app_type,
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

with open("temp_app.json", "w", encoding="utf-8") as f:
    json.dump(new_app, f, ensure_ascii=False, indent=4)
    
print("هەموو فایلەکان ئامادەن، ئێستا دەچێتە ڕیزەوە بۆ ئەوەی بخرێتە ناو سۆرسەکەت بێ کێشە.")
