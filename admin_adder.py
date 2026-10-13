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

# === بەشی سەرەکی و هێنانی زانیارییەکان ===
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def find_main_app_in_page(data):
    if isinstance(data, dict):
        if 'name' in data and 'version' in data and 'uuid' in data: return data
        for value in data.values():
            res = find_main_app_in_page(value)
            if res: return res
    elif isinstance(data, list):
        for item in data:
            res = find_main_app_in_page(item)
            if res: return res
    return None

def process_single_app(target_url, provided_ipa, app_type):
    ex_name, ex_desc, ex_icon, ex_version, ex_bundle = "", "", "", "", ""
    found_ipa_link = provided_ipa

    if target_url.startswith("http"):
        try:
            res = requests.get(target_url, headers=headers, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')

            app_div = soup.find('div', id='app')
            if app_div and app_div.has_attr('data-page'):
                page_data = json.loads(app_div['data-page'])
                target_app = find_main_app_in_page(page_data)
                if target_app:
                    ex_name = target_app.get('name', '')
                    ex_desc = target_app.get('description', '')
                    ex_version = target_app.get('version', '')
                    ex_icon = target_app.get('image', target_app.get('icon', ''))
                    ex_bundle = target_app.get('bundle', target_app.get('bundleIdentifier', ''))
                    
                    if found_ipa_link.lower() == "bulk" or not found_ipa_link:
                        if 'downloadUrl' in target_app: found_ipa_link = target_app['downloadUrl']
                        elif 'ipa' in target_app: found_ipa_link = target_app['ipa']
                        else:
                            for a in soup.find_all('a', href=True):
                                if '.ipa' in a['href'] or '/download/' in a['href']:
                                    found_ipa_link = a['href']
                                    if found_ipa_link.startswith('/'): 
                                        found_ipa_link = "https://check0ver.net" + found_ipa_link
                                    break
        except Exception as e:
            pass

        if not ex_name:
            og_title = soup.find('meta', property='og:title')
            if og_title and og_title.get('content'):
                ex_name = og_title.get('content')
            elif soup.title:
                ex_name = soup.title.string
            if ex_name:
                ex_name = ex_name.split('|')[0].split('-')[0].strip()

    if not ex_name:
        ex_name = "Unknown App"
        
    if found_ipa_link.lower() == "bulk" or not found_ipa_link:
        print(f"⚠️ نەتوانرا لینکی IPA بدۆزرێتەوە بۆ {ex_name}. تێپەڕێنرا.")
        return None

    clean_search_name = re.split(r'[\+\-\(\)\[\]\|]', ex_name)[0].strip()
    words_to_remove = ['Premium', 'Hack', 'Mod', 'Pro', 'IPA', 'Download', 'Free', 'Cheats', 'Unlocked']
    for w in words_to_remove:
        clean_search_name = re.sub(rf'\b{re.escape(w)}\b', '', clean_search_name, flags=re.IGNORECASE).strip()
    if not clean_search_name: clean_search_name = ex_name

    as_name, as_desc, as_icon, as_bundle, as_version, as_track_id = None, None, None, None, None, None
    app_store_screenshots = []
    try:
        itunes_url = f"https://itunes.apple.com/search?term={urllib.parse.quote(clean_search_name)}&entity=software&limit=1"
        itunes_res = requests.get(itunes_url, timeout=10)
        if itunes_res.status_code == 200:
            itunes_data = itunes_res.json()
            if itunes_data.get('resultCount', 0) > 0:
                app_info = itunes_data['results'][0]
                as_name = app_info.get('trackName')
                app_store_screenshots = app_info.get('screenshotUrls', [])
                as_icon = app_info.get('artworkUrl512')
                as_desc = app_info.get('description')
                as_bundle = app_info.get('bundleId')
                as_version = app_info.get('version')
                as_track_id = app_info.get('trackId')
    except Exception:
        pass

    final_name = ex_name if len(ex_name) < 40 else (as_name or "Unknown App")
    final_desc = ex_desc or as_desc or "Awesome App! Downloaded from AshteMobile."
    slug = "".join(e for e in final_name if e.isalnum()).lower()
    if not slug: slug = f"app{random.randint(1000, 9999)}"
    final_bundle = ex_bundle or as_bundle or f"com.ashtemobile.{slug}"
    final_version = ex_version if ex_version else (as_version or "1.0")

    # =========================================================================
    # دابەزاندنی فایلەکە لەگەڵ مەرجی < 1.10 GB
    # =========================================================================
    os.makedirs("ipas", exist_ok=True)
    ipa_filename = f"ipas/{slug}.ipa"
    print(f"⬇️ دابەزاندنی یاری: {final_name} ...")
    
    limit_bytes = 1.10 * 1024 * 1024 * 1024 # ڕێک 1.10 گێگابایت
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
                        break # ئەگەر لە 1.10GB زیاتر بوو، دەوەستێت
                    f.write(chunk)
            
            if is_too_large:
                f.close()
                os.remove(ipa_filename) # فایلە نیوەکە دەسڕێتەوە
                print(f"⚠️ تێپەڕێنرا: قەبارەی '{final_name}' لە 1.10 GB گەورەتر بوو!")
                return None
                
            if zipfile.is_zipfile(ipa_filename):
                file_size_bytes = os.path.getsize(ipa_filename)
            else:
                file_size_bytes = downloaded_bytes
        else:
            print(f"⚠️ کێشە لە دابەزاندن: سێرڤەر کۆدی {r.status_code} ی دا.")
            return None
    except Exception as e:
        print(f"⚠️ هەڵە لە دابەزاندن: {e}")
        return None

    # دابەزاندنی وێنە و ئایکۆن بە شێوازی جیا (img و imgg)
    os.makedirs("img", exist_ok=True)
    os.makedirs("imgg", exist_ok=True)
    base_github_raw = _d('aHR0cHM6Ly9yYXcuZ2l0aHVidXNlcmNvbnRlbnQuY29tL2lvczk0L2FzaHRlanNvbi9tYWluL2ltZy8=')
    base_github_raw_imgg = _d('aHR0cHM6Ly9yYXcuZ2l0aHVidXNlcmNvbnRlbnQuY29tL2lvczk0L2FzaHRlanNvbi9tYWluL2ltZ2cv')

    icon_to_download = as_icon or ex_icon
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
        custom_headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)"}
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
    app_id = random.randint(1111111111, 1999999999)

    print(f"✅ یاری '{final_name}' سەرکەوتوو بوو. قەبارە: {final_size_str}")

    return {
        "id": app_id,
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
        "versions": [
            {
                "size": final_size_bytes,
                "version": final_version,
                "date": current_date,
                "localizedDescription": None,
                "downloadURL": github_release_url,
                "buildVersion": None,
                "minOSVersion": "14.0",
                "screenshots": final_screenshot_urls 
            }
        ]
    }

# =========================================================================
# بەشی دەستپێکردن
# =========================================================================
app_type = os.environ.get("APP_TYPE", "games").strip()
app_input = os.environ.get("APP_NAME", "").strip()
ipa_input = os.environ.get("IPA_LINK", "").strip()

if not app_input:
    print("Error: Missing required input fields.")
    exit(1)

generated_apps = []

# ئەگەر داوای خستنەناوی بە کۆمەڵی کرد (Bulk)
if ipa_input.lower() == "bulk" or "page=" in app_input or "filter" in app_input:
    print("📦 سیستەمی ڕۆبۆتی بەکۆمەڵ (BULK) چالاک کرا...")
    
    # ڕێکخستنی لینکی سەرەکی بۆ ئەوەی پەڕە بە پەڕە بڕوات
    base_url = re.sub(r'([?&])page=\d+', r'\g<1>page=', app_input)
    if "page=" not in base_url:
        base_url += "&page=" if "?" in base_url else "?page="

    page_num = 1
    all_app_links = []
    
    # گەڕان بەناو پەڕەکاندا
    while True:
        current_url = re.sub(r'page=\d*', f'page={page_num}', base_url)
        print(f"\n📄 دەگەڕێت لە پەڕەی {page_num}...")
        try:
            res = requests.get(current_url, headers=headers, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            page_links = []
            
            for a in soup.find_all('a', href=True):
                if '/iapps/' in a['href'] and '?' not in a['href']:
                    full_link = urllib.parse.urljoin("https://check0ver.net", a['href'])
                    if full_link not in page_links and full_link not in all_app_links:
                        page_links.append(full_link)
            
            if not page_links:
                print("🏁 هیچ یارییەکی تر نەما، گەڕان کۆتایی هات.")
                break
                
            all_app_links.extend(page_links)
            print(f"✅ {len(page_links)} یاری لەم پەڕەیەدا دۆزرایەوە.")
            page_num += 1
            
            # دانانی ڕێگر بۆ ئەوەی لە ١٠٠ پەڕە زیاتر نەڕوات لە یەک کاتدا بۆ پاراستنی گیتهاپ
            if page_num > 100:
                print("🛑 گەیشتە سنووری ١٠٠ پەڕە.")
                break
                
        except Exception as e:
            print(f"Error scraping page {page_num}: {e}")
            break

    print(f"\n🔍 کۆی گشتی {len(all_app_links)} یاری دۆزرایەوە. دەست دەکەین بە دابەزاندن...")
    
    for i, link in enumerate(all_app_links):
        print(f"\n⏳ یاری {i+1} لە کۆی {len(all_app_links)}")
        result = process_single_app(link, "bulk", app_type)
        if result:
            generated_apps.append(result)
        time.sleep(2) # پشوویەک بۆ ئەوەی سایتەکە بلۆکمان نەکات

else:
    # ئەگەر تەنها یەک یاری بوو وەکو پێشوو کار دەکات
    result = process_single_app(app_input, ipa_input, app_type)
    if result:
        generated_apps.append(result)

# هەڵگرتنی ئەنجامەکە
if generated_apps:
    with open("temp_app.json", "w", encoding="utf-8") as f:
        json.dump(generated_apps, f, ensure_ascii=False, indent=4)
    print(f"\n✅ {len(generated_apps)} یاری بە سەرکەوتوویی ئامادەکران.")
else:
    print("\n⚠️ هیچ یارییەکی گونجاو نەدۆزرایەوە (یان هەموویان قەبارەیان گەورە بوو).")
    exit(1)
