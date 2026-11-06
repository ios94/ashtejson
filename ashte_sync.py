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
import sys
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


def load_feed():
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
    return "".join(c for c in name if c.isalnum()).lower()


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
    subprocess.run([sys.executable, "admin_adder.py"], env=env, check=True)

    with open("temp_app.json", encoding="utf-8") as f:
        apps = json.load(f)
    kept = []
    for app, src in zip(apps, chunk):
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


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "prepare":
        prepare()
    elif len(sys.argv) > 2 and sys.argv[1] == "batch":
        batch(int(sys.argv[2]))
    else:
        print(__doc__)
