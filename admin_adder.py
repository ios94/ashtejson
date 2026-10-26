import sys
import os
import json
import requests
import random
import re
import urllib.parse
import base64
import zipfile
import shutil
import subprocess
import struct
import zlib
import plistlib
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
        
    print("Data successfully updated in the source file.")
    exit(0)


# =========================================================================
# بەشی نوێ: کارکردن لەگەڵ فایلی IPA (ناو، وەشان، بەندڵ، ئایکۆن لە ناو خۆی IPA)
# =========================================================================
UPLOADS_DIR = "uploads"
CONSUMED_FILE = "uploads_consumed.txt"

def resolve_local_ipa(value):
    """ئەگەر بەهاکە لینک نەبوو و فایلێکی IPA بوو (لە repo یان uploads/) ڕێڕەوەکەی دەگەڕێنێتەوە"""
    if not value or value.lower().startswith("http"):
        return None
    v = value.strip().lstrip("./")
    candidates = [v, os.path.join(UPLOADS_DIR, v)]
    if not v.lower().endswith(".ipa"):
        candidates += [v + ".ipa", os.path.join(UPLOADS_DIR, v + ".ipa")]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None

def fetch_chunked_ipa(value, dest):
    """IPA ی پارچەپارچەکراو لە لقی کاتی (upload:BRANCH) کە upload.html دروستی کردووە، دەیانگەڕێنێتەوە بۆ یەک فایل"""
    branch = value.split(":", 1)[1].strip()
    print(f"📦 Chunked upload detected on branch: {branch}")
    subprocess.run(["git", "fetch", "--depth=1", "origin", f"refs/heads/{branch}"], check=True)
    names = subprocess.run(["git", "ls-tree", "-r", "--name-only", "FETCH_HEAD"],
                           capture_output=True, text=True, check=True).stdout.split("\n")
    parts = sorted(n for n in names if n.startswith("chunks/"))
    if not parts:
        raise RuntimeError("no chunks found on branch " + branch)
    with open(dest, "wb") as out:
        for n in parts:
            out.write(subprocess.run(["git", "show", f"FETCH_HEAD:{n}"], capture_output=True, check=True).stdout)
    with open("uploads_consumed_branches.txt", "a", encoding="utf-8") as bf:
        bf.write(branch + "\n")

def decgbi(data):
    """ئایکۆنی IPA بە فۆرماتی CgBI ی ئەپڵە — دەیگۆڕێت بۆ PNG ی ئاسایی"""
    sig = b"\x89PNG\r\n\x1a\n"
    if not data.startswith(sig):
        return data
    pos, chunks = 8, []
    while pos + 8 <= len(data):
        ln = struct.unpack(">I", data[pos:pos+4])[0]
        typ = data[pos+4:pos+8]
        chunks.append((typ, data[pos+8:pos+8+ln]))
        pos += 12 + ln
    if not any(t == b"CgBI" for t, _ in chunks):
        return data  # PNG ی ئاساییە
    ihdr = next(d for t, d in chunks if t == b"IHDR")
    w, h, bitdepth, ctype = struct.unpack(">IIBB", ihdr[:10])
    if bitdepth != 8 or ctype != 6:
        return data
    raw = zlib.decompress(b"".join(d for t, d in chunks if t == b"IDAT"), -zlib.MAX_WBITS)
    bpp, stride = 4, w * 4
    out, prev = bytearray(), bytearray(stride)
    i = 0
    for _ in range(h):
        ft = raw[i]; i += 1
        line = bytearray(raw[i:i+stride]); i += stride
        if ft == 1:
            for x in range(bpp, stride): line[x] = (line[x] + line[x-bpp]) & 255
        elif ft == 2:
            for x in range(stride): line[x] = (line[x] + prev[x]) & 255
        elif ft == 3:
            for x in range(stride):
                a = line[x-bpp] if x >= bpp else 0
                line[x] = (line[x] + ((a + prev[x]) >> 1)) & 255
        elif ft == 4:
            for x in range(stride):
                a = line[x-bpp] if x >= bpp else 0
                b = prev[x]
                c = prev[x-bpp] if x >= bpp else 0
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2*c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[x] = (line[x] + pr) & 255
        prev = line
        row = bytearray(stride)
        for x in range(0, stride, 4):
            bch, g, r, a = line[x], line[x+1], line[x+2], line[x+3]
            if 0 < a < 255:
                r = min(255, (r * 255 + a // 2) // a)
                g = min(255, (g * 255 + a // 2) // a)
                bch = min(255, (bch * 255 + a // 2) // a)
            row[x], row[x+1], row[x+2], row[x+3] = r, g, bch, a
        out += b"\x00" + row
    def mk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    return sig + mk(b"IHDR", ihdr) + mk(b"IDAT", zlib.compress(bytes(out), 9)) + mk(b"IEND", b"")

def read_ipa_meta(ipa_path):
    """زانیاری ڕاستەقینەی ئەپەکە لە ناو IPA دەردەهێنێت"""
    meta = {"name": "", "version": "", "bundle": "", "minos": "", "icon": None}
    try:
        with zipfile.ZipFile(ipa_path) as zf:
            plist_name = next((n for n in zf.namelist() if re.match(r"^Payload/[^/]+\.app/Info\.plist$", n)), None)
            if not plist_name:
                return meta
            pl = plistlib.loads(zf.read(plist_name))
            meta["name"] = str(pl.get("CFBundleDisplayName") or pl.get("CFBundleName") or "").replace(" - ashtemobile", "").strip()
            meta["version"] = str(pl.get("CFBundleShortVersionString") or pl.get("CFBundleVersion") or "").strip()
            meta["bundle"] = str(pl.get("CFBundleIdentifier") or "").strip()
            meta["minos"] = str(pl.get("MinimumOSVersion") or "").strip()

            app_dir = plist_name.rsplit("/", 1)[0] + "/"
            prefixes = set()
            for key in ("CFBundleIcons", "CFBundleIcons~ipad"):
                prim = (pl.get(key) or {}).get("CFBundlePrimaryIcon") or {}
                if isinstance(prim, dict):
                    prefixes.update(prim.get("CFBundleIconFiles", []) or [])
                    if prim.get("CFBundleIconName"): prefixes.add(prim["CFBundleIconName"])
                elif isinstance(prim, str):
                    prefixes.add(prim)
            prefixes.update(pl.get("CFBundleIconFiles", []) or [])
            prefixes = {os.path.splitext(p)[0] for p in prefixes if p}
            pngs = [i for i in zf.infolist() if i.filename.startswith(app_dir)
                    and "/" not in i.filename[len(app_dir):] and i.filename.lower().endswith(".png")]
            cands = [i for i in pngs if any(os.path.basename(i.filename).startswith(p) for p in prefixes)] if prefixes else []
            if not cands:
                cands = [i for i in pngs if re.match(r"(appicon|icon)", os.path.basename(i.filename), re.I)]
            if cands:
                best = max(cands, key=lambda i: i.file_size)
                meta["icon"] = decgbi(zf.read(best.filename))
    except Exception as e:
        print("IPA metadata read failed:", e)
    return meta

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

def process_single_app(app_input, ipa_link, app_type):
    ex_name, ex_desc, ex_icon, ex_version, ex_bundle = "", "", "", "", ""

    # ---- هەنگاوی ١: وەرگرتنی IPA (فایلی ناوخۆیی یان لینک) ----
    os.makedirs("ipas", exist_ok=True)
    tmp_ipa = f"ipas/_tmp_{random.randint(100000, 999999)}.ipa"
    local_src = resolve_local_ipa(ipa_link)
    if ipa_link.startswith("upload:"):
        try:
            fetch_chunked_ipa(ipa_link, tmp_ipa)
        except Exception as e:
            print("Chunked upload read failed:", e)
    elif local_src:
        print(f"📦 IPA file detected in repo: {local_src}")
        shutil.copy2(local_src, tmp_ipa)
        with open(CONSUMED_FILE, "a", encoding="utf-8") as cf:
            cf.write(local_src + "\n")
    else:
        print("Downloading primary package (IPA)...")
        # فایلی کاتی کە لە upload.html بۆ تاگی "uploads" بەرزکراوەتەوە — دوای کار دەسڕدرێتەوە
        if "/releases/download/uploads/" in ipa_link:
            with open("uploads_consumed_assets.txt", "a", encoding="utf-8") as af:
                af.write(urllib.parse.unquote(ipa_link.split("/releases/download/uploads/")[1].split("?")[0]) + "\n")
        try:
            r = requests.get(ipa_link, stream=True)
            if r.status_code == 200:
                with open(tmp_ipa, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
        except Exception as e:
            print("Error downloading package:", e)

    ipa_ok = os.path.exists(tmp_ipa) and zipfile.is_zipfile(tmp_ipa)
    ipa_meta = read_ipa_meta(tmp_ipa) if ipa_ok else {"name": "", "version": "", "bundle": "", "minos": "", "icon": None}
    if ipa_ok:
        print(f"🔎 IPA info -> name: {ipa_meta['name']} | version: {ipa_meta['version']} | bundle: {ipa_meta['bundle']} | icon: {'yes' if ipa_meta['icon'] else 'no'}")

    if app_input.startswith("http"):
        print(f"🔗 Universal Link Detected. Scraping website: {app_input}")
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
                if ex_name and ("Just a moment" in ex_name or "Cloudflare" in ex_name or "Attention Required" in ex_name):
                    ex_name = ""
        except Exception as e:
            print(f"Website Scraping Error: {e}")
            
        if not ex_name and ipa_meta["name"]:
            ex_name = ipa_meta["name"]
        if not ex_name:
            url_parts = [p for p in app_input.split('/') if p and p.lower() not in ['download', 'app', 'game', 'ipa', 'file']]
            if url_parts:
                ex_name = urllib.parse.unquote(url_parts[-1].split('.')[0]).replace('-', ' ').title()
    elif app_input:
        ex_name = app_input
    else:
        ex_name = ipa_meta["name"]  # تەنها فایلی IPA درا -> ناو لە ناو خۆی IPA

    if not ex_name:
        ex_name = "Unknown App"
    
    print(f"📝 App Name Detected: {ex_name}")

    # =========================================================
    # بەشی زیرەک: بۆ ئەوەی وێنە و ناوی هەڵە نەهێنێت
    # =========================================================
    search_name = ex_name
    lower_name = ex_name.lower()
    popular_apps = ["tiktok", "youtube", "facebook", "instagram", "twitter", "whatsapp", "snapchat", "spotify", "twitch", "discord", "reddit", "telegram", "messenger", "capcut", "picsart", "pubg", "roblox", "minecraft", "clash"]
    
    for app in popular_apps:
        if app in lower_name:
            search_name = app
            break

    clean_search_name = re.split(r'[\+\-\(\)\[\]\|]', search_name)[0].strip()
    words_to_remove = ['Premium', 'Hack', 'Mod', 'Pro', 'IPA', 'Download', 'Free', 'Cheats', 'Unlocked', 'BH', 'Wolf', 'Glow', 'DL', 'Plus', 'Business', 'Lrd']

    for w in words_to_remove:
        clean_search_name = re.sub(rf'\b{re.escape(w)}\b', '', clean_search_name, flags=re.IGNORECASE).strip()

    if not clean_search_name:
        clean_search_name = ex_name

    print(f"🍏 Searching Apple App Store for '{clean_search_name}'...")
    as_bundle, as_version, as_icon = None, None, None
    app_store_screenshots = []

    try:
        itunes_url = f"https://itunes.apple.com/search?term={urllib.parse.quote(clean_search_name)}&entity=software&limit=1"
        itunes_res = requests.get(itunes_url, timeout=10)
        if itunes_res.status_code == 200:
            itunes_data = itunes_res.json()
            if itunes_data.get('resultCount', 0) > 0:
                app_info = itunes_data['results'][0]
                app_store_screenshots = app_info.get('screenshotUrls', [])
                as_icon = app_info.get('artworkUrl512')
                as_bundle = app_info.get('bundleId')
                as_version = app_info.get('version')
                print(f"✅ App Store Match Found for Screenshots.")
            else:
                print("⚠️ No exact match found on App Store.")
    except Exception as e:
        print("App Store search failed:", e)

    # لێرەدا ڕێگریمان کردووە ناوی ڕاستەقینە بڕوات
    final_name = ex_name
    final_desc = ex_desc or "Awesome App! Downloaded from AshteMobile."

    slug = "".join(e for e in final_name if e.isalnum()).lower()
    if not slug: slug = f"app{random.randint(1000, 9999)}"
    final_bundle = ipa_meta["bundle"] or ex_bundle or as_bundle or f"com.ashtemobile.{slug}"
    final_version = ipa_meta["version"] or ex_version or as_version or "1.0"
    
    # گرنگ: وێنە سەرەکییەکە تەنها ئەگەر هی خۆی نەبوو ئینجا هی ئەپستۆر بەکاردەهێنێت
    icon_to_download = ex_icon if ex_icon else (as_icon if as_icon else "")

    os.makedirs("img", exist_ok=True)
    os.makedirs("imgg", exist_ok=True)

    base_github_raw = _d('aHR0cHM6Ly9yYXcuZ2l0aHVidXNlcmNvbnRlbnQuY29tL2lvczk0L2FzaHRlanNvbi9tYWluL2ltZy8=')
    base_github_raw_imgg = _d('aHR0cHM6Ly9yYXcuZ2l0aHVidXNlcmNvbnRlbnQuY29tL2lvczk0L2FzaHRlanNvbi9tYWluL2ltZ2cv')

    use_ipa_icon = bool(ipa_meta["icon"]) and not ex_icon
    if use_ipa_icon:
        icon_to_download = ""
    ext = ".png" if use_ipa_icon or not icon_to_download or ".png" in icon_to_download.lower() else ".jpg"
    downloaded_icon_name = f"{slug}{ext}"
    icon_path = os.path.join("img", downloaded_icon_name)

    if use_ipa_icon:
        print("Using icon extracted from the IPA...")
        with open(icon_path, "wb") as f:
            f.write(ipa_meta["icon"])
    elif icon_to_download and icon_to_download.startswith("http"):
        print("Downloading App Icon...")
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
                        for chunk in sr.iter_content(8192): f.write(chunk)
                    final_screenshot_urls.append(f"{base_github_raw_imgg}{screen_filename}")
            except: pass

    # ئەگەر سکرینشۆت هەر نەبوو با ئایکۆنەکە دابنێت
    if not final_screenshot_urls and icon_full_url:
        final_screenshot_urls = [icon_full_url]

    ipa_filename = f"ipas/{slug}.ipa"
    file_size_bytes = 150000000
    if os.path.exists(tmp_ipa):
        if os.path.exists(ipa_filename):
            os.remove(ipa_filename)
        os.replace(tmp_ipa, ipa_filename)
        if ipa_ok:
            file_size_bytes = os.path.getsize(ipa_filename)

    final_size_bytes = int(file_size_bytes)
    release_tag = os.environ.get("RELEASE_TAG", "V1").strip() or "V1"
    release_base = _d('aHR0cHM6Ly9naXRodWIuY29tL2lvczk0L2FzaHRlanNvbi9yZWxlYXNlcy9kb3dubG9hZC8=')
    github_release_url = f"{release_base}{release_tag}/{slug}.ipa"
    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    app_id = random.randint(1111111111, 1999999999)

    return {
        "id": app_id,
        "name": final_name,
        "version": final_version,
        "size": final_size_bytes,
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
            "size": final_size_bytes,
            "buildVersion": None,
            "minOSVersion": ipa_meta["minos"] or "14.0",
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
    if ipa:  # ناو/لینکی پەڕە ئارەزوومەندانەیە — ئەگەر بەتاڵ بێت ناو لە ناو IPA وەردەگیرێت
        print(f"\n--- Processing App {idx} ---")
        res = process_single_app(url, ipa, app_type)
        if res:
            generated_apps.append(res)

if generated_apps:
    with open("temp_app.json", "w", encoding="utf-8") as f:
        json.dump(generated_apps, f, ensure_ascii=False, indent=4)
    print("✅ All apps processed successfully.")
else:
    print("Error: No apps processed.")
    exit(1)
