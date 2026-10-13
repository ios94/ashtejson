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
        
    print(f"Data successfully updated! Added {len(new_apps)} apps.")
    exit(0)

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def process_app_data(app_info, app_type):
    ex_name = app_info.get('name', '')
    ex_desc = app_info.get('description', '')
    ex_version = app_info.get('version', '')
    ex_icon = app_info.get('image', '')
    ex_bundle = app_info.get('bundle', app_info.get('uniqueBundle', ''))
    uuid_val = app_info.get('uuid', '')

    if not ex_name:
        return None

    # لینکی داگرتنی ڕاستەوخۆی IPA لە سایتەکە
    found_ipa_link = f"https://check0ver.net/api/iapps/{uuid_val}/download"

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
    final_desc = ex_desc or as_desc or app_desc or "Awesome App! Downloaded from AshteMobile."
    slug = "".join(e for e in final_name if e.isalnum()).lower()
    if not slug: slug = f"app{random.randint(1000, 9999)}"
    final_bundle = ex_bundle or as_bundle or f"com.ashtemobile.{slug}"
    final_version = ex_version if ex_version else (as_version or "1.0")

    # =========================================================================
    # مەرجی دابەزاندن و پشکنینی قەبارە (< 1.10 GB)
    # =========================================================================
    os.makedirs("ipas", exist_ok=True)
    ipa_filename = f"ipas/{slug}.ipa"
    print(f"⬇️ پشکنین و دابەزاندنی: {final_name} ...")
    
    limit_bytes = 1.10 * 1024 * 1024 * 1024 # 1.10 GB
    downloaded_bytes = 0
    is_too_large = False
    file_size_bytes = 0

    try:
        r = requests.get(found_ipa_link, stream=True, timeout=30)
        if r.status_code == 200:
            with open(ipa_filename, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    downloaded_bytes += len(chunk)
                    if downloaded_bytes > limit_bytes:
                        is_too_large = True
                        break
                    f.write(chunk)
            
            if is_too_large:
                f.close()
                if os.path.exists(ipa_filename):
                    os.remove(ipa_filename)
                print(f"⚠️ تێپەڕێنرا: قەبارەی '{final_name}' لە 1.10 GB گەورەترە!")
                return None
                
            if zipfile.is_zipfile(ipa_filename):
                file_size_bytes = os.path.getsize(ipa_filename)
            else:
                file_size_bytes = downloaded_bytes
        else:
            print(f"⚠️ سێرڤەر کۆدی هەڵەی دا: {r.status_code}")
            return None
    except Exception as e:
        print(f"⚠️ هەڵە لە دابەزاندن: {e}")
        return None

    # دابەزاندنی وێنە و ئایکۆنەکان
    os.makedirs("img", exist_ok=True)
    os.makedirs("imgg", exist_ok=True)
    base_github_raw = _d('aHR0cHM6Ly9yYXcuZ2l0aHVidXNlcmNvbnRlbnQuY29tL2lvczk0L2FzaHRlanNvbi9tYWluL2ltZy8=')
    base_github_raw_imgg = _d('aHR0cHM6Ly9yYXcuZ2l0aHVidXNlcmNvbnRlbnQuY29tL2lvczk0L2FzaHRlanNvbi9tYWluL2ltZ2cv')

    icon_to_download = ex_icon or as_icon
    ext = ".png" if not icon_to_download or ".png" in icon_to_download.lower() else ".jpg"
    downloaded_icon_name = f"{slug}{ext}"
    icon_path = os.path.join("img", downloaded_icon_name)

    if icon_to_download and icon_to_download.startswith("http"):
        try:
            ir = requests.get(icon_to_download, stream=True, headers=headers)
            if ir.status_code == 200:
                with open(icon_path, "wb") as f:
                    for chunk in ir.iter_content(1024): f.write(chunk)
        except: pass

    icon_relative = f"img/{downloaded_icon_name}"
    icon_full_url = f"{base_github_raw}{downloaded_icon_name}"

    final_screenshot_urls = []
    if app_store_screenshots:
        custom_headers = {"User-Agent": "Mozilla/5.0"}
        for idx, s_url in enumerate(app_store_screenshots[:4]):
            ext_s = ".png" if ".png" in s_url.lower() else ".jpg"
            screen_filename = f"{slug}_screen_{idx+1}{ext_s}"
            screen_path = os.path.join("imgg", screen_filename)
            try:
                sr = requests.get(s_url.split('?')[0], stream=True, headers=custom_headers, timeout=15)
                if sr.status_code == 200:
                    with open(screen_path, "wb") as f:
                        for chunk in sr.iter_content(8192): f.write(chunk)
                    final_screenshot_urls.append(f"{base_github_raw_imgg}{screen_filename}")
            except: pass

    size_mb = file_size_bytes / (1024 * 1024)
    if size_mb >= 1024:
        size_gb = size_mb / 1024
        final_size_str = f"{size_gb:.2f} GB"
    else:
        final_size_str = f"{size_mb:.2f} MB"

    github_release_url = f"{_d('aHR0cHM6Ly9naXRodWIuY29tL2lvczk0L2FzaHRlanNvbi9yZWxlYXNlcy9kb3dubG9hZC9WMS8=')}{slug}.ipa"
    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    
    print(f"✅ یاری '{final_name}' سەرکەوتوو بوو. قەبارە: {final_size_str}")

    return {
        "id": random.randint(1111111111, 1999999999),
        "name": final_name,
        "version": final_version,
        "size": final_size_str,
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
            "size": file_size_bytes,
            "version": final_version,
            "date": current_date,
            "localizedDescription": None,
            "downloadURL": github_release_url,
            "buildVersion": None,
            "minOSVersion": "14.0",
            "screenshots": final_screenshot_urls 
        }]
    }

# =========================================================================
# دەستپێکردنی کارکردن لەسەر پەیجەکان
# =========================================================================
app_type = os.environ.get("APP_TYPE", "games").strip()
app_input = os.environ.get("APP_NAME", "").strip()
ipa_input = os.environ.get("IPA_LINK", "").strip()

if not app_input:
    print("Error: Missing required input fields.")
    exit(1)

generated_apps = []

if ipa_input.lower() == "bulk" or "page=" in app_input or "filter" in app_input:
    print("📦 سیستەمی خوێندنەوەی ڕاستەوخۆی Inertia (JSON) بۆ هەموو پەڕەکان چالاک کرا...")
    
    base_url = re.sub(r'([?&])page=\d+', r'\g<1>page=', app_input)
    if "page=" not in base_url:
        base_url += "&page=" if "?" in base_url else "?page="

    page_num = 1
    all_apps_data = []

    while True:
        current_url = re.sub(r'page=\d*', f'page={page_num}', base_url)
        print(f"\n📄 پشکنینی داتای پەڕەی {page_num}...")
        try:
            res = requests.get(current_url, headers=headers, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            app_div = soup.find('div', id='app')
            if not app_div or not app_div.has_attr('data-page'):
                print("🏁 هیچ داتایەک نەدۆزرایەوە، گەڕان کۆتایی هات.")
                break
                
            page_json = json.loads(app_div['data-page'])
            paginator_data = page_json.get('props', {}).get('paginator', {})
            items = paginator_data.get('data', [])
            
            if not items:
                print("🏁 پەڕەکە خاڵییە، گەڕان کۆتایی هات.")
                break
                
            all_apps_data.extend(items)
            print(f"✅ {len(items)} یاری لە پەڕەی {page_num} دۆزرایەوە (کۆی گشتی: {len(all_apps_data)}).")
            
            # پشکنین ئایا پەڕەی تر هەیە یان نەخێر
            last_page = paginator_data.get('meta', {}).get('last_page', 1)
            if page_num >= last_page:
                print("🏁 گەیشتە کۆتا پەڕەی سایتەکە.")
                break
                
            page_num += 1
            time.sleep(1)
            
        except Exception as e:
            print(f"Error reading page {page_num}: {e}")
            break

    print(f"\n🔍 کۆی گشتی {len(all_apps_data)} یاری هێنران. دەست دەکەین بە دابەزاندن...")
    
    for i, app_info in enumerate(all_apps_data):
        print(f"\n⏳ یاری {i+1} لە کۆی {len(all_apps_data)}")
        result = process_app_data(app_info, app_type)
        if result:
            generated_apps.append(result)
        time.sleep(2)

else:
    # ئەگەر تەنها لینکێکی دیاریکراو بوو
    try:
        res = requests.get(app_input, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        app_div = soup.find('div', id='app')
        if app_div and app_div.has_attr('data-page'):
            page_json = json.loads(app_div['data-page'])
            # گەڕان بەدوای زانیاری یارییەکە
            def find_dict(d):
                if isinstance(d, dict):
                    if 'uuid' in d and 'name' in d and 'bundle' in d: return d
                    for v in d.values():
                        r = find_dict(v)
                        if r: return r
                elif isinstance(d, list):
                    for item in d:
                        r = find_dict(item)
                        if r: return r
                return None
            target = find_dict(page_json)
            if target:
                result = process_app_data(target, app_type)
                if result: generated_apps.append(result)
    except Exception as e:
        print(f"Error: {e}")

if generated_apps:
    with open("temp_app.json", "w", encoding="utf-8") as f:
        json.dump(generated_apps, f, ensure_ascii=False, indent=4)
    print(f"\n✅ {len(generated_apps)} یاری بە سەرکەوتوویی زیاد کران!")
else:
    print("\n⚠️ هیچ یارییەکی گونجاو نەدۆزرایەوە.")
    exit(1)
