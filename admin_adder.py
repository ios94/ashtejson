import json
import os
import re
import sys
import time
import hashlib
import zipfile
from datetime import datetime, timezone
from urllib.parse import quote, urlparse, parse_qs, urlencode, urlunparse

import requests
from bs4 import BeautifulSoup

JSON_FILE = "ashtemobile94.json"
BACKUP_FILE = "backup_memory.json"
MAX_PER_RUN = int(os.getenv("LIMIT_PER_RUN", "10"))
MAX_IPA_BYTES = int(float(os.getenv("MAX_IPA_GB", "1.10")) * 1024**3)
SOURCE_BASE = "https://check0ver.net"
RAW_BASE = "https://raw.githubusercontent.com/ios94/ashtejson/main/"
RELEASE_BASE = "https://github.com/ios94/ashtejson/releases/download/V1/"

session = requests.Session()
session.headers.update({
    "User-Agent": "AshteMobileCatalogueBot/1.0 (authorized public catalogue fetch)",
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
})

def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default

def safe_slug(value):
    slug = "".join(c for c in value.lower() if c.isalnum())
    return slug[:100] or "app"

def get_page_data(url):
    response = session.get(url, timeout=25)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    root = soup.find("div", id="app")
    if not root or not root.get("data-page"):
        raise RuntimeError(
            f"No public Inertia data found at {url}. The site may require access "
            "or may have changed its page format; use an official/authorized API."
        )
    try:
        return json.loads(root["data-page"])
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Could not parse page data from {url}") from exc

def fetch_bytes(url, referer=None, max_bytes=None):
    headers = {}
    if referer:
        headers["Referer"] = referer
    with session.get(url, headers=headers, stream=True, timeout=(20, 90), allow_redirects=True) as r:
        r.raise_for_status()
        content_type = r.headers.get("Content-Type", "").lower()
        chunks = []
        size = 0
        for chunk in r.iter_content(1024 * 128):
            if not chunk:
                continue
            size += len(chunk)
            if max_bytes and size > max_bytes:
                raise RuntimeError(f"Download exceeded size limit ({max_bytes} bytes)")
            chunks.append(chunk)
        return b"".join(chunks), content_type

def save_image(url, path):
    if not url or not url.startswith(("https://", "http://")):
        return False
    try:
        data, content_type = fetch_bytes(url, max_bytes=20 * 1024 * 1024)
        if not data or not content_type.startswith("image/"):
            return False
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        return True
    except Exception as exc:
        print(f"Image skipped ({url}): {exc}")
        return False

def get_itunes_info(name):
    try:
        url = "https://itunes.apple.com/search?" + urlencode({
            "term": name, "entity": "software", "limit": 5
        })
        r = session.get(url, timeout=15)
        r.raise_for_status()
        results = r.json().get("results", [])
        target = re.sub(r"[^a-z0-9]", "", name.lower())
        for item in results:
            candidate = re.sub(r"[^a-z0-9]", "", item.get("trackName", "").lower())
            if target and (target in candidate or candidate in target):
                return item
        return results[0] if results else {}
    except Exception as exc:
        print(f"App Store metadata unavailable for {name}: {exc}")
        return {}

def validate_ipa(path):
    if not zipfile.is_zipfile(path):
        raise RuntimeError("Downloaded file is not a valid ZIP/IPA archive")
    with zipfile.ZipFile(path) as z:
        bad_member = z.testzip()
        if bad_member:
            raise RuntimeError(f"Corrupt archive member: {bad_member}")
        names = z.namelist()
        if not any(n.startswith("Payload/") and n.endswith(".app/Info.plist") for n in names):
            raise RuntimeError("Archive does not contain Payload/*.app/Info.plist")
    return os.path.getsize(path)

def get_existing_apps():
    data = load_json(JSON_FILE, {"apps": []})
    if not isinstance(data, dict):
        data = {"apps": []}
    if not isinstance(data.get("apps"), list):
        data["apps"] = []
    return data, data["apps"]

def already_current(existing, name, version):
    for app in existing:
        if app.get("name", "").strip().casefold() == name.strip().casefold():
            return str(app.get("version", "")) == str(version)
    return False

def process_app(app_info, app_type, direct_ipa_url=""):
    name = str(app_info.get("name") or "").strip()
    if not name:
        print("Skipping item without a name.")
        return None

    uuid = str(app_info.get("uuid") or app_info.get("id") or "").strip()
    page_url = f"{SOURCE_BASE}/en/iapps/{uuid}" if uuid else ""
    version = str(app_info.get("version") or "")
    description = str(app_info.get("description") or "")
    icon_url = str(app_info.get("image") or app_info.get("icon") or "")
    bundle = str(app_info.get("bundle") or app_info.get("uniqueBundle") or "")

    appstore = get_itunes_info(name)
    version = version or str(appstore.get("version") or "1.0")
    description = description or str(appstore.get("description") or "Available from AshteMobile.")
    icon_url = icon_url or str(appstore.get("artworkUrl512") or "")
    bundle = bundle or str(appstore.get("bundleId") or "")

    slug = safe_slug(name)
    os.makedirs("ipas", exist_ok=True)
    os.makedirs("img", exist_ok=True)
    os.makedirs("imgg", exist_ok=True)
    ipa_path = f"ipas/{slug}.ipa"

    if direct_ipa_url:
        ipa_url = direct_ipa_url
    else:
        if not uuid:
            print(f"Skipping {name}: no UUID and no direct IPA URL.")
            return None
        ipa_url = f"{SOURCE_BASE}/api/iapps/{quote(uuid, safe='')}/download"
        if page_url:
            try:
                detail = get_page_data(page_url)
                download_url = detail.get("props", {}).get("iapp", {}).get("downloadURL")
                if download_url and str(download_url).startswith(("https://", "http://")):
                    ipa_url = str(download_url)
            except Exception as exc:
                print(f"Could not read public detail page for {name}: {exc}")

    print(f"Downloading: {name} ({version})")
    try:
        data, content_type = fetch_bytes(ipa_url, referer=page_url or SOURCE_BASE, max_bytes=MAX_IPA_BYTES)
        with open(ipa_path, "wb") as f:
            f.write(data)
        size = validate_ipa(ipa_path)
    except Exception as exc:
        if os.path.exists(ipa_path):
            os.remove(ipa_path)
        print(f"Download/validation failed for {name}: {exc}")
        return None

    icon_ext = ".png" if ".png" in icon_url.lower() else ".jpg"
    icon_name = f"{slug}{icon_ext}"
    icon_path = os.path.join("img", icon_name)
    icon_saved = save_image(icon_url, icon_path)
    icon_rel = f"img/{icon_name}"
    icon_full = RAW_BASE + icon_rel if icon_saved else ""

    screenshot_urls = appstore.get("screenshotUrls", []) or []
    saved_screenshots = []
    for index, url in enumerate(screenshot_urls[:4], start=1):
        ext = ".png" if ".png" in url.lower() else ".jpg"
        filename = f"{slug}_screen_{index}{ext}"
        path = os.path.join("imgg", filename)
        if save_image(url.split("?")[0], path):
            saved_screenshots.append(RAW_BASE + "imgg/" + filename)

    release_url = RELEASE_BASE + slug + ".ipa"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    return {
        "id": int(hashlib.sha256((name.casefold() + "|" + version).encode()).hexdigest()[:8], 16),
        "name": name,
        "version": version,
        "size": size,
        "icon": icon_rel,
        "badge": "",
        "type": app_type,
        "install_url": release_url,
        "download_url": release_url,
        "bundleIdentifier": bundle or f"com.ashtemobile.{slug}",
        "marketplaceID": "",
        "developerName": "AshteMobile",
        "subtitle": "AshteMobile",
        "localizedDescription": description,
        "iconURL": icon_full,
        "tintColor": "#04ecfc",
        "category": app_type,
        "screenshotURLs": saved_screenshots,
        "screenshots": saved_screenshots,
        "versions": [{
            "size": size,
            "version": version,
            "date": now,
            "localizedDescription": None,
            "downloadURL": release_url,
            "buildVersion": None,
            "minOSVersion": "14.0",
            "screenshots": saved_screenshots
        }]
    }

def update_json():
    if not os.path.exists("temp_app.json"):
        print("No temp_app.json; nothing to update.")
        return
    new_apps = load_json("temp_app.json", [])
    if isinstance(new_apps, dict):
        new_apps = [new_apps]
    if not isinstance(new_apps, list):
        raise RuntimeError("temp_app.json must contain a list or app object")

    source_data, apps = get_existing_apps()
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(source_data, f, ensure_ascii=False, indent=2)
    with open(BACKUP_FILE, "w", encoding="utf-8") as f:
        json.dump(source_data, f, ensure_ascii=False, indent=2)

    for new_app in new_apps:
        if not isinstance(new_app, dict) or not new_app.get("name"):
            continue
        old = next((a for a in apps if a.get("name", "").casefold() == new_app["name"].casefold()), None)
        if old and old.get("id") is not None:
            new_app["id"] = old["id"]
        apps[:] = [a for a in apps if a.get("name", "").casefold() != new_app["name"].casefold()]
        apps.insert(0, new_app)

    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(source_data, f, ensure_ascii=False, indent=2)
    with open(BACKUP_FILE, "w", encoding="utf-8") as f:
        json.dump(source_data, f, ensure_ascii=False, indent=2)
    print(f"Updated catalogue with {len(new_apps)} app record(s).")

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "update_json":
        update_json()
        return

    app_type = os.getenv("APP_TYPE", "games").strip().lower()
    if app_type not in ("games", "apps"):
        raise RuntimeError("APP_TYPE must be games or apps")

    app_input = os.getenv("APP_NAME", "").strip()
    direct_ipa = os.getenv("IPA_LINK", "").strip()
    if not app_input:
        raise RuntimeError("APP_NAME is required")

    existing_data, existing_apps = get_existing_apps()
    generated = []

    # A direct IPA URL requires APP_NAME to be the app's name, not a listing URL.
    if direct_ipa:
        item = {"name": app_input, "version": os.getenv("APP_VERSION", "1.0")}
        result = process_app(item, app_type, direct_ipa_url=direct_ipa)
        if result:
            generated.append(result)
    else:
        if not app_input.startswith(("https://", "http://")):
            raise RuntimeError("APP_NAME must be a public listing URL or use IPA_LINK with an app name.")
        page_num = 1
        while len(generated) < MAX_PER_RUN:
            parsed = urlparse(app_input)
            query = parse_qs(parsed.query, keep_blank_values=True)
            query["page"] = [str(page_num)]
            current_url = urlunparse(parsed._replace(query=urlencode(query, doseq=True)))
            print(f"Checking listing page {page_num}: {current_url}")
            try:
                page_data = get_page_data(current_url)
            except Exception as exc:
                print(f"Stopping listing scan: {exc}")
                break

            props = page_data.get("props", {})
            paginator = props.get("paginator", {})
            items = paginator.get("data", [])
            if not items:
                print("No items on this page.")
                break

            for item in items:
                if len(generated) >= MAX_PER_RUN:
                    break
                name = str(item.get("name") or "").strip()
                version = str(item.get("version") or "")
                if not name or already_current(existing_apps, name, version):
                    continue
                print(f"New app or version found: {name} {version}")
                result = process_app(item, app_type)
                if result:
                    generated.append(result)
                    existing_apps.append(result)
                time.sleep(1)

            meta = paginator.get("meta", {})
            last_page = int(meta.get("last_page") or page_num)
            if page_num >= last_page:
                break
            page_num += 1

    if generated:
        with open("temp_app.json", "w", encoding="utf-8") as f:
            json.dump(generated, f, ensure_ascii=False, indent=2)
        print(f"Prepared {len(generated)} app record(s).")
    else:
        print("No new valid apps were prepared.")

if __name__ == "__main__":
    main()
