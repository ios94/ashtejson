"""
ashte_sync.py - یارییەکان لە ماڵپەڕی ashtemobile.tututweak.com دەهێنێت و دەیانخاتە ناو سۆرسەکە
بە هەمان شێوازی admin_adder.py (ریلیز + ashtemobile94.json).

بەکارهێنان:
  python ashte_sync.py prepare          -> دەبینێتەوە + ashte_queue.json دروست دەکات
  python ashte_sync.py batch <ژمارە>    -> ١٠ یاری لە queue وەردەگرێت و admin_adder.py ی لەسەر دەکات
"""
import base64
import json
import os
import re
import subprocess
import hashlib
import unicodedata
import sys
import time
import urllib.parse

import requests

SITE_URL = os.environ.get("SITE_URL", "https://ashtemobile.tututweak.com/index.html").strip()
DATA_URL = os.environ.get("DATA_URL", "").strip()
LIMIT = int(os.environ.get("LIMIT", "0") or 0)  # 0 = هەموو یارییەکان
BATCH_SIZE = 10  # admin_adder.py تەنها ١٠ یاری پێکەوە وەردەگرێت

JSON_FILE = base64.b64decode("YXNodGVtb2JpbGU5NC5qc29u").decode()
QUEUE_FILE = "ashte_queue.json"
FAILED_FILE = "ashte_failed.txt"  # ئەو یارییانەی IPA ـیان دانەبەزی، جارێکی تر هەوڵیان بۆ نادرێت

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

NAME_KEYS = ("name", "title", "app_name", "appName")
IPA_KEYS = ("downloadURL", "download_url", "install_url", "ipa", "ipa_url", "ipaUrl",
            "ipaURL", "url", "link", "download", "file")
DESC_KEYS = ("localizedDescription", "description", "desc", "features", "mods", "mod")
LIST_KEYS = ("apps", "games", "data", "items", "results", "list")


# ----------------------------------------------------------------- دۆزینەوەی فیدەکە
def candidates_from_site(site_url):
    """لە index.html و فایلە JS ـەکانی ئەو لینکانە دەدۆزێتەوە کە داتاکەی لێ دەهێنرێت"""
    found = []
    html = requests.get(site_url, headers=HEADERS, timeout=20).text
    blobs = [html]
    for src in re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html, re.I):
        try:
            blobs.append(requests.get(urllib.parse.urljoin(site_url, src), headers=HEADERS, timeout=20).text)
        except Exception:
            pass
    for blob in blobs:
        for m in re.findall(r'fetch\(\s*[\'"`]([^\'"`]+)[\'"`]', blob):
            found.append(m)
        for m in re.findall(r'[\'"`]([^\'"`\s]+\.json(?:\?[^\'"`\s]*)?)[\'"`]', blob):
            found.append(m)
    found = [urllib.parse.urljoin(site_url, u) for u in found if "${" not in u]
    # فایلە باوەکان وەک پاشەکشە
    for guess in ("apps.json", "games.json", "data.json", "ashtemobile.json", "source.json", "list.json"):
        found.append(urllib.parse.urljoin(site_url, guess))
    seen, out = set(), []
    for u in found:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def find_item_list(node):
    """گەورەترین لیستی dict ـەکان لە ناو JSON دەدۆزێتەوە"""
    if isinstance(node, list):
        if node and all(isinstance(x, dict) for x in node):
            return node
        return None
    if isinstance(node, dict):
        for k in LIST_KEYS:
            if isinstance(node.get(k), list) and node[k] and isinstance(node[k][0], dict):
                return node[k]
        best = None
        for v in node.values():
            r = find_item_list(v)
            if r and (best is None or len(r) > len(best)):
                best = r
        return best
    return None


MAX_PAGES = 400  # 400 پەڕە x 100 = 40,000 یاری، زیاتر لە پێویست


def fetch_items(url):
    r = requests.get(url, headers=HEADERS, timeout=60)
    if r.status_code != 200:
        return None
    items = find_item_list(r.json())
    if items and any(k in items[0] for k in NAME_KEYS):
        return items
    return None


def load_paged(url_template):
    """ئەگەر لینکەکە page= ی تێدا بوو، هەموو پەڕەکان (1، 2، 3 ...) دەهێنێت تا بەتاڵ دەبێت"""
    all_items, seen = [], set()
    for page in range(1, MAX_PAGES + 1):
        url = re.sub(r"page=[^&]*", f"page={page}", url_template, count=1)
        items = None
        for attempt in range(3):  # ئەگەر سێرڤەر کێشەی هەبوو سێ جار هەوڵ دەدات
            try:
                items = fetch_items(url)
                break
            except Exception as e:
                print(f"⚠️ page {page} attempt {attempt + 1} failed: {e}")
                time.sleep(3)
        if not items and all_items:
            # ڕەنگە کێشەی کاتی سێرڤەر بێت: چەند جار دووبارە هەوڵ دەدات پێش ئەوەی بڵێت پەڕەی کۆتاییە
            for retry in range(2):
                time.sleep(5)
                try:
                    items = fetch_items(url)
                except Exception:
                    items = None
                if items:
                    break
        if not items:
            print(f"📄 page {page}: empty -> end of feed (total {len(all_items)})")
            break  # پەڕەی کۆتایی (بەتاڵ) یان کێشە
        new = 0
        for it in items:
            key = pick(it, NAME_KEYS).lower() + "|" + pick_ipa(it)
            if key not in seen:
                seen.add(key)
                all_items.append(it)
                new += 1
        if page <= 3 or page % 10 == 0 or new == 0:
            print(f"📄 page {page}: {len(items)} items, +{new} new, total {len(all_items)}")
        if new == 0:  # سێرڤەر page ی پشتگوێ خستووە و هەمان لیست دەداتەوە
            break
    return all_items


def load_feed():
    if DATA_URL and "page=" in DATA_URL:
        items = load_paged(DATA_URL)
        if items:
            print(f"✅ Feed found (paged): {len(items)} items total")
            return items
        print("⚠️ Paged feed returned nothing, trying the normal way...")
    urls = [DATA_URL] if DATA_URL else candidates_from_site(SITE_URL)
    for u in urls:
        try:
            r = requests.get(u, headers=HEADERS, timeout=60)
            if r.status_code != 200:
                continue
            items = find_item_list(r.json())
            if items and any(k in items[0] for k in NAME_KEYS):
                print(f"✅ Feed found: {u}  ({len(items)} items)")
                return items
        except Exception:
            continue
    print("❌ Could not find the games feed. Pass the JSON link in the 'data_url' input.")
    sys.exit(1)


# ----------------------------------------------------------------- ڕێکخستنی یارییەکان
def pick(d, keys):
    for k in keys:
        v = d.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def pick_ipa(d):
    for k in IPA_KEYS:
        v = d.get(k)
        if isinstance(v, str) and v.lower().startswith("http") and ".ipa" in v.lower():
            return v.strip()
    vs = d.get("versions")
    if isinstance(vs, list) and vs and isinstance(vs[0], dict):
        v = pick(vs[0], ("downloadURL", "download_url", "url"))
        if v.lower().startswith("http"):
            return v
    for k in IPA_KEYS:  # دوا هەوڵ: هەر لینکێک
        v = d.get(k)
        if isinstance(v, str) and v.lower().startswith("http"):
            return v.strip()
    return ""


def normalize(items):
    games = []
    for it in items:
        name, ipa = pick(it, NAME_KEYS), pick_ipa(it)
        if name and ipa:
            games.append({"name": name, "ipa": ipa, "desc": pick(it, DESC_KEYS)})
    return games


def existing_names():
    try:
        with open(JSON_FILE, encoding="utf-8") as f:
            return {a.get("name", "").lower().strip() for a in json.load(f).get("apps", [])}
    except Exception:
        return set()


def failed_names():
    try:
        with open(FAILED_FILE, encoding="utf-8") as f:
            return {l.strip().lower() for l in f if l.strip()}
    except Exception:
        return set()


def prepare():
    games = normalize(load_feed())
    skip = existing_names() | failed_names()
    queue, seen = [], set()
    for g in games:
        key = g["name"].lower().strip()
        if key in skip or key in seen:
            continue
        seen.add(key)
        queue.append(g)
    if LIMIT:
        queue = queue[:LIMIT]
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)
    n = (len(queue) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"📋 {len(queue)} new games queued in {n} batch(es).")
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a") as f:
            f.write(f"batches={n}\ncount={len(queue)}\n")


def slug_of(name):
    """هەمان make_slug ی admin_adder.py ـە: تەنها ئینگلیزی/ژمارە، ئەگەر نەبوو hash"""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = "".join(c for c in ascii_name if c.isalnum()).lower()
    if not s:
        s = "app" + hashlib.md5(name.strip().encode("utf-8")).hexdigest()[:10]
    return s


def batch(i):
    with open(QUEUE_FILE, encoding="utf-8") as f:
        queue = json.load(f)
    chunk = queue[i * BATCH_SIZE:(i + 1) * BATCH_SIZE]
    if not chunk:
        sys.exit(1)
    env = os.environ.copy()
    for n in range(1, BATCH_SIZE + 1):
        env[f"APP{n}_NAME"] = chunk[n - 1]["name"] if n <= len(chunk) else ""
        env[f"APP{n}_IPA"] = chunk[n - 1]["ipa"] if n <= len(chunk) else ""
    if os.path.exists("temp_app.json"):
        os.remove("temp_app.json")
    rc = subprocess.run([sys.executable, "admin_adder.py"], env=env).returncode
    if rc != 0:  # نموونە: هەموو یارییەکانی ئەم پارچەیە گەورەتر بوون لە 2GB
        print("⚠️ Nothing usable in this batch (all skipped or failed).")
        sys.exit(1)

    with open("temp_app.json", encoding="utf-8") as f:
        apps = json.load(f)
    kept = []
    by_name = {c["name"].strip(): c for c in chunk}
    for app in apps:
        src = by_name.get(app["name"].strip(), {"desc": ""})
        path = f"ipas/{slug_of(app['name'])}.ipa"
        if not os.path.exists(path):
            print(f"⚠️ IPA download failed, skipped: {app['name']}")
            with open(FAILED_FILE, "a", encoding="utf-8") as ff:
                ff.write(app["name"] + "\n")
            continue
        if src["desc"]:  # وەسفی ڕاستەقینەی ماڵپەڕەکە (مۆدەکان) بپارێزە
            app["localizedDescription"] = src["desc"]
        kept.append(app)
    if not kept:
        print("⚠️ Nothing usable in this batch.")
        sys.exit(1)
    with open("temp_app.json", "w", encoding="utf-8") as f:
        json.dump(kept, f, ensure_ascii=False, indent=4)
    print(f"✅ Batch {i}: {len(kept)}/{len(chunk)} games ready.")


MAX_IPA_BYTES = 2147483648 - 1024 * 1024


def filter_size():
    """دوای inject: ئەو IPA ـانەی لە 2GB گەورەترن دەسڕێتەوە و لە temp_app.json ـیش لایاندەبات"""
    with open("temp_app.json", encoding="utf-8") as f:
        apps = json.load(f)
    kept = []
    for app in apps:
        path = f"ipas/{slug_of(app['name'])}.ipa"
        if not os.path.exists(path):
            continue
        size = os.path.getsize(path)
        if size >= MAX_IPA_BYTES:
            print(f"⛔ {app['name']} is {size / 1024**3:.2f} GB (> 2GB), skipped.")
            os.remove(path)
            with open(FAILED_FILE, "a", encoding="utf-8") as ff:
                ff.write(app["name"] + "\n")
            continue
        kept.append(app)
    if not kept:
        print("⚠️ Nothing left to upload in this batch.")
        sys.exit(1)
    with open("temp_app.json", "w", encoding="utf-8") as f:
        json.dump(kept, f, ensure_ascii=False, indent=4)
    print(f"✅ {len(kept)} file(s) ready to upload.")


def prune():
    """ئەو یارییانەی IPA ـەکەیان بەرز نەکرایەوە (فایلەکە سڕاوەتەوە) لە temp_app.json لادەبات"""
    with open("temp_app.json", encoding="utf-8") as f:
        apps = json.load(f)
    kept = [a for a in apps if os.path.exists(f"ipas/{slug_of(a['name'])}.ipa")]
    for a in apps:
        if a not in kept:
            print(f"⚠️ Upload failed, not added to the source: {a['name']}")
    if not kept:
        sys.exit(1)
    with open("temp_app.json", "w", encoding="utf-8") as f:
        json.dump(kept, f, ensure_ascii=False, indent=4)
    print(f"✅ {len(kept)}/{len(apps)} uploaded.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "prepare":
        prepare()
    elif len(sys.argv) > 1 and sys.argv[1] == "prune":
        prune()
    elif len(sys.argv) > 1 and sys.argv[1] == "filter":
        filter_size()
    elif len(sys.argv) > 2 and sys.argv[1] == "batch":
        batch(int(sys.argv[2]))
    else:
        print(__doc__)
