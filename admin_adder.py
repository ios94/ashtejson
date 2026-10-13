import sys
import os
import json
import requests
import random
import re
import urllib.parse
import base64
from bs4 import BeautifulSoup
from datetime import datetime, timezone

def _d(s):
    return base64.b64decode(s).decode('utf-8')

# === بەشی نوێکردنەوەی جەیسۆن ===
if len(sys.argv) > 1 and sys.argv[1] == "update_json":
    if not os.path.exists("temp_app.json"):
        exit(0)
        
    with open("temp_app.json", "r", encoding="utf-8") as f:
        new_app = json.load(f)
        
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
        
    print("Data successfully updated in the source file.")
    exit(0)

# === بەشی هێنانی زانیارییەکان ===
app_type = os.environ.get("APP_TYPE", "games").strip()
app_input = os.environ.get("APP_NAME", "").strip()
ipa_link = os.environ.get("IPA_LINK", "").strip()

if not app_input or not ipa_link:
    print("Error: Missing required input fields.")
    exit(1)

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

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

ex_name, ex_desc, ex_icon, ex_version, ex_size, ex_bundle = "", "", "", "", "", ""

# =========================================================================
# 1. بەشی سکراپەری گەردوونی (بۆ هەموو وێبسایتەکان)
# =========================================================================
if app_input.startswith("http"):
    print("🔗 Universal Link Detected. Scraping website...")
    try:
        res = requests.get(app_input, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')

        app_div = soup.find('div', id='app')
        if app_div and app_div.has_attr('data-page'):
            print("Flekstore format detected.")
            page_data = json.loads(app_div['data-page'])
            target_app = find_main_app_in_page(page_data)
            if target_app:
                ex_name = target_app.get('name', '')
                ex_desc = target_app.get('description', '')
                ex_version = target_app.get('version', '')
                ex_size = target_app.get('size', '')
                ex_icon = target_app.get('image', target_app.get('icon', ''))
                ex_bundle = target_app.get('bundle', target_app.get('bundleIdentifier', ''))
        
        if not ex_name:
            print("Generic website detected. Extracting metadata...")
            
            og_title = soup.find('meta', property='og:title')
            if og_title and og_title.get('content'):
                ex_name = og_title.get('content')
            elif soup.title:
                ex_name = soup.title.string
            
            if ex_name:
                ex_name = ex_name.split('|')[0].split('-')[0].strip()
            
            # چارەسەری کێشەی سکیوێرتی Cloudflare
            if ex_name and ("Just a moment" in ex_name or "Cloudflare" in ex_name or "Attention Required" in ex_name):
                ex_name = ""

            og_desc = soup.find('meta', property='og:description')
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if og_desc and og_desc.get('content'):
                ex_desc = og_desc.get('content')
            elif meta_desc and meta_desc.get('content'):
                ex_desc = meta_desc.get('content')
            
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                ex_icon = og_image.get('content')
                
    except Exception as e:
        print(f"Website Scraping Error: {e}")
        
    # ئەگەر سایتەکە ڕێگری کرد یان نەیدۆزییەوە، ناوەکە بە زیرەکی لە لینکەکە دەردەهێنێت
    if not ex_name:
        url_parts = [p for p in app_input.split('/') if p and p.lower() not in ['download', 'app', 'game', 'ipa', 'file']]
        if url_parts:
            ex_name = urllib.parse.unquote(url_parts[-1].split('.')[0]).replace('-', ' ').title()
else:
    ex_name = app_input

if not ex_name:
    ex_name = "Unknown App"
    
print(f"📝 App Name Detected: {ex_name}")

# =========================================================================
# 2. خاوێنکردنەوەی ناوەکە بۆ ئەپ ستۆر
# =========================================================================
clean_search_name = re.split(r'[\+\-\(\)\[\]\|]', ex_name)[0].strip()
words_to_remove = ['Premium', 'Hack', 'Mod', 'Pro', 'IPA', 'Download', 'Free', 'Cheats', 'Unlocked']

for w in words_to_remove:
    clean_search_name = re.sub(rf'\b{re.escape(w)}\b', '', clean_search_name, flags=re.IGNORECASE).strip()

if not clean_search_name:
    clean_search_name = ex_name

# =========================================================================
# 3. گەڕان لەناو App Store
# =========================================================================
print(f"🍏 Searching Apple App Store for '{clean_search_name}'...")
as_name, as_desc, as_icon, as_bundle, as_version, as_size_bytes = None, None, None, None, None, None
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
            as_size_bytes = app_info.get('fileSizeBytes')
            print(f"✅ App Store Match Found: {as_name}")
        else:
            print("⚠️ No exact match found on App Store.")
except Exception as e:
    print("App Store search failed:", e)

# =========================================================================
# 4. تێکەڵکردنی زانیارییەکان
# =========================================================================
final_name = ex_name if len(ex_name) < 40 else (as_name or "Unknown App")
final_desc = ex_desc or as_desc or "Awesome App! Downloaded from AshteMobile."

slug = "".join(e for e in final_name if e.isalnum()).lower()
if not slug: slug = f"app{random.randint(1000, 9999)}"
final_bundle = ex_bundle or as_bundle or f"com.ashtemobile.{slug}"

final_version = ex_version if ex_version else (as_version or "1.0")

# --- ئێرە بە تەواوی گەڕایەوە بۆ کۆدەکەی خۆت تا Feather کێشەی نەبێت ---
if ex_size:
    final_size_str = ex_size
    try:
        size_mb = float(re.sub(r'[^\d.]', '', str(final_size_str)))
        final_size_bytes = int(size_mb * 1024 * 1024)
        final_size_str = f"{size_mb} MB"
    except:
        final_size_bytes = 150000000
        final_size_str = "150 MB"
elif as_size_bytes:
    final_size_bytes = int(as_size_bytes)
    size_mb = round(final_size_bytes / (1024 * 1024), 2)
    final_size_str = f"{size_mb} MB" # تەنها MB نەک GB!
else:
    final_size_str = "150 MB"
    final_size_bytes = 150000000

icon_to_download = as_icon or ex_icon

# =========================================================================
# 5. دابەزاندنی وێنە و ئایکۆن
# =========================================================================
os.makedirs("img", exist_ok=True)
os.makedirs("imgg", exist_ok=True) # فۆڵدەری وێنەکان جیاکراوەتەوە بە تەواوی

base_github_raw = _d('aHR0cHM6Ly9yYXcuZ2l0aHVidXNlcmNvbnRlbnQuY29tL2lvczk0L2FzaHRlanNvbi9tYWluL2ltZy8=')
base_github_raw_imgg = _d('aHR0cHM6Ly9yYXcuZ2l0aHVidXNlcmNvbnRlbnQuY29tL2lvczk0L2FzaHRlanNvbi9tYWluL2ltZ2cv')

ext = ".png" if not icon_to_download or ".png" in icon_to_download.lower() else ".jpg"
downloaded_icon_name = f"{slug}{ext}"
icon_path = os.path.join("img", downloaded_icon_name)

if icon_to_download and icon_to_download.startswith("http"):
    print("Downloading App Icon...")
    try:
        ir = requests.get(icon_to_download, stream=True, headers=headers)
        if ir.status_code == 200:
            with open(icon_path, "wb") as f:
                for chunk in ir.iter_content(1024):
                    f.write(chunk)
    except: pass

icon_relative = f"img/{downloaded_icon_name}"
icon_full_url = f"{base_github_raw}{downloaded_icon_name}"

final_screenshot_urls = []
if app_store_screenshots:
    print("Downloading screenshots from App Store...")
    custom_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    }
    for idx, s_url in enumerate(app_store_screenshots[:4]):
        ext_s = ".png" if ".png" in s_url.lower() else ".jpg"
        clean_url = s_url.split('?')[0]
        screen_filename = f"{slug}_screen_{idx+1}{ext_s}"
        screen_path = os.path.join("imgg", screen_filename)
        
        try:
            sr = requests.get(clean_url, stream=True, headers=custom_headers, timeout=15)
            if sr.status_code == 200:
                with open(screen_path, "wb") as f:
                    for chunk in sr.iter_content(8192):
                        f.write(chunk)
                final_screenshot_urls.append(f"{base_github_raw_imgg}{screen_filename}")
        except: pass

# =========================================================================
# 6. دابەزاندنی فایلە سەرەکییەکە (IPA)
# =========================================================================
os.makedirs("ipas", exist_ok=True)
ipa_filename = f"ipas/{slug}.ipa"
print("Downloading primary package (IPA)...")
try:
    r = requests.get(ipa_link, stream=True)
    if r.status_code == 200:
        with open(ipa_filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
except Exception as e:
    print("Error downloading package.")
    exit(1)

# =========================================================================
# 7. دروستکردنی JSON بە ڕێکخستنی ئەسڵی خۆت
# =========================================================================
github_release_url = f"{_d('aHR0cHM6Ly9naXRodWIuY29tL2lvczk0L2FzaHRlanNvbi9yZWxlYXNlcy9kb3dubG9hZC9WMS8=')}{slug}.ipa"
current_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
app_id = random.randint(1111111111, 1999999999)

new_app = {
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
            "version": final_version,
            "date": current_date,
            "localizedDescription": None,
            "downloadURL": github_release_url,
            "size": final_size_bytes,
            "buildVersion": None,
            "minOSVersion": "14.0",
            "screenshots": final_screenshot_urls 
        }
    ]
}

with open("temp_app.json", "w", encoding="utf-8") as f:
    json.dump(new_app, f, ensure_ascii=False, indent=4)
    
print("✅ Operations completed. Task queued for processing.")
