"""
update_check.py - ئابدەیتی یاری و ئەپەکان بە شێوەی خۆکار

  python update_check.py prepare   -> وەشانی هەر یارییەک لە سەرچاوە دەپشکنێت و لیستی ئابدەیتەکان دروست دەکات
  python update_check.py batch <i> -> IPA ی نوێ دادەبەزێنێت (١٠ دانە) بە هەمان admin_adder.py
  python update_check.py merge     -> زانیاری وەشانی نوێ دەخاتە ناو ashtemobile94.json (باقی زانیارییەکان وەک خۆیان)

چۆن وەشان دەپشکنێت: تەنها Info.plist ی ناو IPA ی سەرچاوە دەخوێنێتەوە (Range request، چەند سەد KB)،
بەراوردی دەکات لەگەڵ وەشانی ناو JSON. تەنها ئەگەر نوێتر بوو ئابدەیت دەکرێت.
ئەگەر سێرڤەری سەرچاوە Range پشتگیری نەکات، ئەوا size/ETag/Last-Modified بەراورد دەکرێت (update_state.json).
"""
import base64
import json
import os
import plistlib
import re
import subprocess
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

import ashte_sync as sync
from fix_types import HTTPRangeFile

JSON_FILE = base64.b64decode("YXNodGVtb2JpbGU5NC5qc29u").decode()
BACKUP_FILE = "backup_memory.json"
QUEUE_FILE = "update_queue.json"
STATE_FILE = "update_state.json"
TAG_FILE = "batch_tag.txt"
BATCH_SIZE = sync.BATCH_SIZE

DATA_URLS = [u for u in re.split(r"[,\s]+", os.environ.get("DATA_URLS", "").strip()) if u]
MAX_UPDATES = int(os.environ.get("MAX_UPDATES", "60") or 60)
DRY_RUN = os.environ.get("DRY_RUN", "No").strip().lower() in ("yes", "true", "1")
WORKERS = 8
HEADERS = sync.HEADERS


# ------------------------------------------------------------------ وەشان
def version_tuple(v):
    t = [int(x) for x in re.findall(r"\d+", v or "")]
    while t and t[-1] == 0:
        t.pop()
    return tuple(t)


def is_newer(new, old):
    new, old = (new or "").strip(), (old or "").strip()
    if not new or new == old:
        return False
    a, b = version_tuple(new), version_tuple(old)
    if a and b:
        return a > b
    return True  # وەشانەکان ژمارە نین، جیاوازیان هەیە


def remote_version(url):
    """وەشانی IPA ی دوور بەبێ دابەزاندنی تەواوی (CFBundleShortVersionString یان CFBundleVersion)"""
    with zipfile.ZipFile(HTTPRangeFile(url)) as zf:
        pname = next((n for n in zf.namelist() if re.match(r"^Payload/[^/]+\.app/Info\.plist$", n)), None)
        if not pname:
            raise RuntimeError("Info.plist not found")
        pl = plistlib.loads(zf.read(pname))
        return str(pl.get("CFBundleShortVersionString") or pl.get("CFBundleVersion") or "").strip()


def signature(url):
    r = requests.get(url, headers=HEADERS, stream=True, timeout=60)
    try:
        h = r.headers
        return f"{h.get('Content-Length', '')}|{h.get('ETag', '')}|{h.get('Last-Modified', '')}"
    finally:
        r.close()


def release_tag_of(app):
    m = re.search(r"/releases/download/([^/]+)/", app.get("download_url") or app.get("install_url") or "")
    return m.group(1) if m else ""


def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def check_one(game, app, state):
    """(نووسراوەی ئەنجام، وەشانی نوێ، sig)"""
    url = game["ipa"]
    if not url.lower().startswith("http"):
        return "skip (not a direct link)", None, None
    try:
        new_v = remote_version(url)
        return "range", new_v, None
    except RuntimeError as e:
        msg = str(e)
        if "does not support Range (HTTP 200)" not in msg:
            return f"error: {msg}", None, None
    except Exception as e:
        return f"error: {e}", None, None
    # سێرڤەرەکە Range ی نیە: بەراوردی sig
    try:
        sig = signature(url)
    except Exception as e:
        return f"error: {e}", None, None
    key = app["name"].strip().lower()
    if key not in state:
        return "baseline", None, sig  # یەکەم جار: تەنها تۆمار دەکرێت
    if state[key] != sig:
        return "sig-changed", "?", sig
    return "unchanged", None, sig


# ------------------------------------------------------------------ prepare
def gather_feed():
    items, seen = [], set()
    for url in (DATA_URLS or [sync.DATA_URL]):
        sync.DATA_URL = url
        try:
            got = sync.normalize(sync.load_feed())
        except SystemExit:
            print(f"⚠️ feed not available: {url}")
            continue
        except Exception as e:
            print(f"⚠️ feed error ({url}): {e}")
            continue
        for g in got:
            k = g["name"].lower().strip()
            if k not in seen:
                seen.add(k)
                items.append(g)
    return items


def prepare():
    with open(JSON_FILE, encoding="utf-8") as f:
        data = json.load(f)
    by_name = {a["name"].strip().lower(): a for a in data.get("apps", []) if a.get("name")}
    games = [g for g in gather_feed() if g["name"].lower().strip() in by_name]
    print(f"🔎 {len(games)} games of your JSON were found in the source. Checking versions...")

    state = load_state()
    found, stats, done = [], {}, 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(check_one, g, by_name[g["name"].lower().strip()], state): g for g in games}
        for fut in as_completed(futs):
            g = futs[fut]
            app = by_name[g["name"].lower().strip()]
            how, new_v, sig = fut.result()
            stats[how.split(":")[0]] = stats.get(how.split(":")[0], 0) + 1
            if sig:
                if how in ("baseline", "unchanged"):
                    state[app["name"].strip().lower()] = sig
            old_v = app.get("version", "")
            if how == "sig-changed" or (new_v and is_newer(new_v, old_v)):
                tag = release_tag_of(app)
                if not tag:
                    print(f"⚠️ no release tag for {app['name']}, skipped")
                else:
                    found.append({"name": app["name"], "ipa": g["ipa"], "desc": g.get("desc", ""),
                                  "old_version": old_v, "new_version": new_v, "tag": tag, "sig": sig})
                    print(f"🆕 {app['name']}: {old_v} -> {new_v}  [{tag}]")
            elif how.startswith("error"):
                print(f"⚠️ {app['name']}: {how}")
            done += 1
            if done % 100 == 0:
                print(f"   {done}/{len(games)} checked")
    print(f"📊 {stats}")

    found = found[:MAX_UPDATES]
    batches = []
    for tag in sorted({f["tag"] for f in found}):  # هەر batch تەنها یەک ڕیلیزی هەیە
        items = [f for f in found if f["tag"] == tag]
        for i in range(0, len(items), BATCH_SIZE):
            batches.append({"tag": tag, "items": items[i:i + BATCH_SIZE]})

    if DRY_RUN:
        print(f"\n(DRY RUN) {len(found)} update(s) would be installed. Nothing changed.")
        batches = []
    else:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=1)
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(batches, f, ensure_ascii=False, indent=2)
    print(f"📋 {sum(len(b['items']) for b in batches)} update(s) in {len(batches)} batch(es).")
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a") as f:
            f.write(f"batches={len(batches)}\ncount={sum(len(b['items']) for b in batches)}\n")


# ------------------------------------------------------------------ batch
def batch(i):
    with open(QUEUE_FILE, encoding="utf-8") as f:
        b = json.load(f)[i]
    items, tag = b["items"], b["tag"]
    env = os.environ.copy()
    env["RELEASE_TAG"] = tag
    for n in range(1, BATCH_SIZE + 1):
        env[f"APP{n}_NAME"] = items[n - 1]["name"] if n <= len(items) else ""
        env[f"APP{n}_IPA"] = items[n - 1]["ipa"] if n <= len(items) else ""
    if os.path.exists("temp_app.json"):
        os.remove("temp_app.json")
    rc = subprocess.run([sys.executable, "admin_adder.py"], env=env).returncode
    if rc != 0:
        print("⚠️ Nothing usable in this batch.")
        sys.exit(1)
    with open("temp_app.json", encoding="utf-8") as f:
        apps = json.load(f)
    kept = [a for a in apps if os.path.exists(f"ipas/{sync.slug_of(a['name'])}.ipa")]
    if not kept:
        print("⚠️ No IPA was downloaded in this batch.")
        sys.exit(1)
    with open("temp_app.json", "w", encoding="utf-8") as f:
        json.dump(kept, f, ensure_ascii=False, indent=4)
    with open(TAG_FILE, "w") as f:
        f.write(tag)
    print(f"✅ Batch {i}: {len(kept)}/{len(items)} update(s) ready → release {tag}")


# ------------------------------------------------------------------ merge
def merge():
    """تەنها بەشی وەشان دەگۆڕێت: version, size, لینکی داونلۆد، versions. باقی (وەسف، وێنە، جۆر ...) وەک خۆی."""
    if not os.path.exists("temp_app.json"):
        print("nothing to merge")
        return
    with open("temp_app.json", encoding="utf-8") as f:
        new_apps = json.load(f)
    with open(JSON_FILE, encoding="utf-8") as f:
        data = json.load(f)
    try:
        with open(QUEUE_FILE, encoding="utf-8") as f:
            sigs = {it["name"]: it.get("sig") for b in json.load(f) for it in b["items"]}
    except Exception:
        sigs = {}
    state, merged = load_state(), 0

    for new in new_apps:
        apps = data.get("apps", [])
        idx = next((i for i, a in enumerate(apps) if a.get("name") == new["name"]), None)
        if idx is None:
            continue
        old = apps[idx]
        if not is_newer(new.get("version", ""), old.get("version", "")):
            print(f"⏭️ {new['name']}: version {new.get('version')} is not newer than {old.get('version')}, JSON not changed")
        else:
            for k in ("version", "size", "install_url", "download_url", "versions"):
                if k in new:
                    old[k] = new[k]
            apps.pop(idx)
            apps.insert(0, old)  # ئابدەیتکراو دەچێتە سەرەوە
            merged += 1
            print(f"🔄 {new['name']} -> {old['version']}")
        if sigs.get(new["name"]):
            state[new["name"].strip().lower()] = sigs[new["name"]]

    for path in (JSON_FILE, BACKUP_FILE):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)
    print(f"✅ {merged} update(s) written to {JSON_FILE}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "prepare":
        prepare()
    elif cmd == "batch" and len(sys.argv) > 2:
        batch(int(sys.argv[2]))
    elif cmd == "merge":
        merge()
    else:
        print(__doc__)
        sys.exit(1)
