import sys
import os
import json
import requests
import random
import re
import urllib.parse
import base64
import zipfile
import time
from bs4 import BeautifulSoup
from datetime import datetime, timezone

def _d(s):
    return base64.b64decode(s).decode('utf-8')

# === بەشی نوێکردنەوەی جەیسۆن ===
if len(sys.argv) > 1 and sys.argv[1] == "update_json":
    if not os.path.exists("temp_app.json"):
        exit(0)
        
    with open("temp_app.json", "r", encoding="utf-8") as f:
        new_apps = json.load(f)
        
    if not isinstance(new_apps, list):
        new_apps = [new_apps]
        
    json_file = _d('YXNodGVtb2JpbGU5NC5qc29u')
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

    for new_app in new_apps:
        for i, existing_app in enumerate(source_data.get("apps", [])):
            if existing_app.get("name") == new_app["name"]:
                new_app["id"] = existing_app.get("id", new_app["id"])
                source_data["apps"].pop(i)
                break
        source_data["apps"].insert(0, new_app)

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(source_data, f, ensure_ascii=False, indent=4)
    with open(backup_file, "w", encoding="utf-8") as f:
        json.dump(source_data, f, ensure_ascii=False, indent=4)
        
    print(f"✅ داتا نوێکرایەوە! {len(new_apps)} یاری زیادکرا.")
    exit(0)

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def process_single_app(app_url, direct_ipa_url, app_type):
    ex_name, ex_desc, ex_icon, ex_version, ex_bundle = "", "", "", "", ""
    
    if app_url.startswith("http"):
        try:
            res = requests.get(app_url, headers=headers, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            app_div = soup.find('div', id='app')
            if app_div and app_div.has_attr('data-page'):
                page_data = json.loads(app_div['data-page'])
                
                def find_main_app_in_page(data):
                    if isinstance(data, dict):
                        if 'name' in data and 'version' in data and 'uuid' in data: return data
                        for value in data.values():
                            r = find_main_app_in_page(value)
                            if r: return r
                    elif isinstance(data, list):
                        for item in data:
                            r = find_main_app_in_page(item)
                            if r: return r
                    return None
                    
                target_app = find_main_app_in_page(page_data)
                if target_app:
                    ex_name = target_app.get('name', '')
                    ex_desc = target_app.get('description', '')
                    ex_version = target_app.get('version', '')
                    ex_icon = target_app.get('image', target_app.get('icon', ''))
                    ex_bundle = target_app.get('bundle', target_app.get('bundleIdentifier', ''))
            
            if not ex_name:
                og_title = soup.find('meta', property='og:title')
                if og_title and og_title.get('content'):
                    ex_name = og_title.get('content').split('|')[0].split('-')[0].strip()
        except Exception as e:
            print(f"⚠️ هەڵە لە خوێندنەوەی پەڕە: {e}")
            
        if not ex_name:
            url_parts = [p for p in app_url.split('/') if p and p.lower() not in ['download', 'app', 'game', 'ipa', 'file']]
            if url_parts:
                ex_name = urllib.parse.unquote(url_parts[-1].split('.')[0]).replace('-', ' ').title()
    else:
        ex_name = app_url

    if not ex_name or "Just a moment" in ex_name or "Cloudflare" in ex_name:
        ex_name = f"App_{random.randint(100, 999)}"

    clean_search_name = re.split(r'[\+\-\(\)\[\]\|]', ex_name)[0].strip()
    words_to_remove = ['Premium', 'Hack', 'Mod', 'Pro', 'IPA', 'Download', 'Free', 'Cheats', 'Unlocked']
    for w in words_to_remove:
        clean_search_name = re.sub(rf'\b{re.escape(w)}\b', '', clean_search_name, flags=re.IGNORECASE).strip()
    if not clean_search_name: clean_search_name = ex_name

    as_name, as_desc, as_icon, as_bundle, as_version = None, None, None, None, None
    app_store_screenshots = []
    try:
        itunes_url = f"https://itunes.apple.com/search?term={urllib.parse.quote(clean_search_name)}&entity=software&limit=1"
        itunes_res = requests.get(itunes_url, timeout=10)
        if itunes_res.status_code == 200:
            data = itunes_res.json()
            if data.get('resultCount', 0) > 0:
                info = data['results'][0]
                as_name = info.get('trackName')
                app_store_screenshots = info.get('screenshotUrls', [])
                as_icon = info.get('artworkUrl512')
                as_desc = info.get('description')
                as_bundle = info.get('bundleId')
                as_version = info.get('version')
    except: pass

    final_name = ex_name if len(ex_name) < 40 else (as_name or "Unknown App")
    final_desc = ex_desc or as_desc or "Awesome App! Downloaded from AshteMobile."
    slug = "".join(e for e in final_name if e.isalnum()).lower()
    if not slug: slug = f"app{random.randint(1000, 9999)}"
    final_bundle = ex_bundle or as_bundle or f"com.ashtemobile.{slug}"
    final_version = ex_version if ex_version else (as_version or "1.0")

    os.makedirs("ipas", exist_ok=True)
    ipa_filename = f"ipas/{slug}.ipa"
    file_size_bytes = 150000000

    print(f"⬇️ دابەزاندنی: {final_name} ...")
    try:
        r = requests.get(direct_ipa_url, stream=True, headers=headers, timeout=60)
        if r.status_code == 200:
            with open(ipa_filename, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            if zipfile.is_zipfile(ipa_filename):
                file_size_bytes = os.path.getsize(ipa_filename)
                print(f"✅ فایل دابەزی: {file_size_bytes} بایت.")
            else:
                print("⚠️ فایلی دابەزێنراو تێکچووە.")
                if os.path.exists(ipa_filename): os.remove(ipa_filename)
                return None
        else:
            print(f"⚠️ کێشە لە دابەزاندن. کۆد: {r.status_code}")
            return None
    except Exception as e:
        print(f"⚠️ هەڵە: {e}")
        return None

    os.makedirs("img", exist_ok=True)
    os.makedirs("imgg", exist_ok=True)
    base_github_raw = _d('aHR0cHM6Ly9yYXcuZ2l0aHVidXNlcmNvbnRlbnQuY29tL2lvczk0L2FzaHRlanNvbi9tYWluL2ltZy8=')
    base_github_raw_imgg = _d('aHR0cHM6Ly9yYXcuZ2l0aHVidXNlcmNvbnRlbnQuY29tL2lvczk0L2FzaHRlanNvbi9tYWluL2ltZ2cv')

    icon_to_download = as_icon or ex_icon or ""
    ext = ".png" if not icon_to_download or ".png" in icon_to_download.lower() else ".jpg"
    downloaded_icon_name = f"{slug}{ext}"
    icon_path = os.path.join("img", downloaded_icon_name)

    if icon_to_download and icon_to_download.startswith("http"):
        try:
            ir = requests.get(icon_to_download, stream=True, headers=headers, timeout=10)
            if ir.status_code == 200:
                with open(icon_path, "wb") as f:
                    for chunk in ir.iter_content(1024): f.write(chunk)
        except: pass

    icon_relative = f"img/{downloaded_icon_name}"
    icon_full_url = f"{base_github_raw}{downloaded_icon_name}"

    final_screenshot_urls = []
    if app_store_screenshots:
        for idx, s_url in enumerate(app_store_screenshots[:4]):
            ext_s = ".png" if ".png" in s_url.lower() else ".jpg"
            screen_filename = f"{slug}_screen_{idx+1}{ext_s}"
            screen_path = os.path.join("imgg", screen_filename)
            try:
                sr = requests.get(s_url.split('?')[0], stream=True, headers=headers, timeout=15)
                if sr.status_code == 200:
                    with open(screen_path, "wb") as f:
                        for chunk in sr.iter_content(8192): f.write(chunk)
                    final_screenshot_urls.append(f"{base_github_raw_imgg}{screen_filename}")
            except: pass

    github_release_url = f"{_d('aHR0cHM6Ly9naXRodWIuY29tL2lvczk0L2FzaHRlanNvbi9yZWxlYXNlcy9kb3dubG9hZC9WMS8=')}{slug}.ipa"
    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    
    return {
        "id": random.randint(1111111111, 1999999999),
        "name": final_name,
        "version": final_version,
        "size": file_size_bytes,
        "icon": icon_relative,
        "badge": "",
        "type": app_type,
        "install_url": github_release_url,
        "download_url": github_release_url,
        "bundleIdentifier": final_bundle,
        "marketplaceID": "",
        "developerName": _d('QXNodGVNb2JpbGU='),
        "subtitle": "Awesome App",
        "localizedDescription": final_desc,
        "iconURL": icon_full_url,
        "tintColor": "#04ecfc",
        "category": app_type,
        "screenshotURLs": final_screenshot_urls,
        "screenshots": final_screenshot_urls,
        "versions": [{
            "version": final_version,
            "date": current_date,
            "localizedDescription": None,
            "downloadURL": github_release_url,
            "size": file_size_bytes,
            "buildVersion": None,
            "minOSVersion": "14.0",
            "screenshots": final_screenshot_urls 
        }]
    }

# =========================================================================
# بەشی سەرەکی - وەرگرتنی ٤ یاری پێکەوە
# =========================================================================
app_type = os.environ.get("APP_TYPE", "games").strip()

pairs = [
    (os.environ.get("APP1_NAME", "").strip(), os.environ.get("APP1_IPA", "").strip()),
    (os.environ.get("APP2_NAME", "").strip(), os.environ.get("APP2_IPA", "").strip()),
    (os.environ.get("APP3_NAME", "").strip(), os.environ.get("APP3_IPA", "").strip()),
    (os.environ.get("APP4_NAME", "").strip(), os.environ.get("APP4_IPA", "").strip())
]

generated_apps = []

for idx, (url, ipa) in enumerate(pairs, 1):
    if url and ipa:
        print(f"\n======================================")
        print(f"📦 دەستپێکردنی یاری ژمارە {idx}")
        print(f"======================================")
        result = process_single_app(url, ipa, app_type)
        if result:
            generated_apps.append(result)
            time.sleep(2) # پشوویەکی کورت لە نێوان یارییەکان

if generated_apps:
    with open("temp_app.json", "w", encoding="utf-8") as f:
        json.dump(generated_apps, f, ensure_ascii=False, indent=4)
    print(f"\n✅ {len(generated_apps)} یاری بە سەرکەوتوویی زیاد کران!")
else:
    print("\n⚠️ هیچ یارییەک دانەبەزی (یان خانەکان خاڵی بوون).")
    exit(1)
