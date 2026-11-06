"""
fix_types.py - ئەو یاری و ئەپانەی پێشتر لە ashtemobile94.json دانراون پشکنین دەکات و
type / category ـەکەیان دەکات بە games یان apps (بەبێ دابەزاندنی تەواوی IPA).

ڕێگاکان بە ڕیز:
  1) App Store: lookup بە bundleIdentifier ـی ڕاستەقینە (١٠٠ دانە پێکەوە، خێرا)
  2) ئەگەر لە App Store نەبوو: تەنها بەشە پێویستەکانی IPA لە GitHub Release دەخوێنرێتەوە
     (Range request، چەند سەد KB نەک چەند GB):
       - LSApplicationCategoryType ناو Info.plist
       - Unity / Unreal / Cocos / Godot ناو IPA = games
  3) ئەگەر هیچیان نەبوو، وەک خۆی دەمێنێتەوە و لە لۆگدا دەنووسرێت

DRY_RUN=Yes  ->  تەنها پیشان دەدات، هیچ نانووسێتەوە.
"""
import base64
import io
import json
import os
import plistlib
import re
import sys
import time
import urllib.parse
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

JSON_FILE = base64.b64decode("YXNodGVtb2JpbGU5NC5qc29u").decode()
BACKUP_FILE = "backup_memory.json"
DRY_RUN = os.environ.get("DRY_RUN", "No").strip().lower() in ("yes", "true", "1")
WORKERS = 8
CHUNK = 512 * 1024

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
ENGINE_MARKERS = ("unityframework", "libil2cpp", "unity default resources", "ue4commandline",
                  "unrealengine", "libcocos", "cocos2d", "libgodot")


# ------------------------------------------------------------ App Store lookup
def itunes_lookup(bundles):
    """{bundleId(lowercase): [genres]} بۆ ئەوانەی لە App Store دۆزرانەوە"""
    out = {}
    for i in range(0, len(bundles), 100):
        part = bundles[i:i + 100]
        url = ("https://itunes.apple.com/lookup?country=us&entity=software&bundleId="
               + ",".join(urllib.parse.quote(b, safe="") for b in part))
        for attempt in range(4):
            try:
                r = requests.get(url, headers=HEADERS, timeout=60)
                if r.status_code == 200:
                    for res in r.json().get("results", []):
                        b = (res.get("bundleId") or "").lower()
                        if b:
                            out[b] = list(res.get("genres") or []) + [res.get("primaryGenreName") or ""]
                    break
                print(f"⚠️ iTunes HTTP {r.status_code}, retrying...")
            except Exception as e:
                print(f"⚠️ iTunes error: {e}")
            time.sleep(10 * (attempt + 1))
        time.sleep(3)  # ئەپڵ سنووری ڕیکوێست هەیە
        print(f"🍏 App Store lookup: {min(i + 100, len(bundles))}/{len(bundles)} (found {len(out)})")
    return out


# ------------------------------------------------------------ خوێندنەوەی IPA لە دوورەوە
class HTTPRangeFile(io.RawIOBase):
    """فایلێکی دوور وەک فایلێکی ناوخۆیی دەخوێنێتەوە، تەنها بەو بەشانەی داوا دەکرێن"""

    def __init__(self, url):
        self.url = url
        self.pos = 0
        self.cache = {}
        self.size = self._probe()

    def _probe(self):
        r = requests.get(self.url, headers={**HEADERS, "Range": "bytes=0-0"}, stream=True, timeout=60)
        try:
            if r.status_code == 206:
                return int(r.headers["Content-Range"].split("/")[1])
            raise RuntimeError(f"server does not support Range (HTTP {r.status_code})")
        finally:
            r.close()

    def _get_range(self, start, end):
        r = requests.get(self.url, headers={**HEADERS, "Range": f"bytes={start}-{end}"}, timeout=120)
        if r.status_code != 206:
            raise RuntimeError(f"range request failed (HTTP {r.status_code})")
        return r.content

    def _chunk(self, ci):
        if ci not in self.cache:
            if len(self.cache) > 16:
                self.cache.clear()
            start = ci * CHUNK
            end = min(start + CHUNK, self.size) - 1
            self.cache[ci] = self._get_range(start, end)
        return self.cache[ci]

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        if whence == 0:
            self.pos = offset
        elif whence == 1:
            self.pos += offset
        else:
            self.pos = self.size + offset
        self.pos = max(0, min(self.pos, self.size))
        return self.pos

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self.pos
        end = min(self.pos + n, self.size)
        out, p = bytearray(), self.pos
        while p < end:
            ci = p // CHUNK
            chunk = self._chunk(ci)
            off = p - ci * CHUNK
            take = min(end - p, len(chunk) - off)
            out += chunk[off:off + take]
            p += take
        self.pos = end
        return bytes(out)

    def readinto(self, b):
        data = self.read(len(b))
        b[:len(data)] = data
        return len(data)


def classify_from_ipa(url):
    """(type یان None، سەرچاوە)"""
    try:
        with zipfile.ZipFile(HTTPRangeFile(url)) as zf:
            names = zf.namelist()
            plist_name = next((n for n in names if re.match(r"^Payload/[^/]+\.app/Info\.plist$", n)), None)
            cat = ""
            if plist_name:
                pl = plistlib.loads(zf.read(plist_name))
                cat = str(pl.get("LSApplicationCategoryType") or "").strip().lower()
            if cat:
                return ("games" if "games" in cat else "apps"), "IPA category"
            low = [n.lower() for n in names]
            if any(k in n for n in low for k in ENGINE_MARKERS):
                return "games", "game engine"
            return None, "no signal in IPA"
    except Exception as e:
        return None, f"IPA error: {e}"


def ipa_url_of(app):
    for k in ("download_url", "install_url"):
        v = app.get(k)
        if isinstance(v, str) and v.startswith("http"):
            return v
    vs = app.get("versions")
    if isinstance(vs, list) and vs and isinstance(vs[0], dict):
        v = vs[0].get("downloadURL")
        if isinstance(v, str) and v.startswith("http"):
            return v
    return ""


# ------------------------------------------------------------ سەرەکی
def main():
    with open(JSON_FILE, encoding="utf-8") as f:
        data = json.load(f)
    apps = data.get("apps", [])
    print(f"📦 {len(apps)} apps/games in {JSON_FILE}" + ("  [DRY RUN]" if DRY_RUN else ""))

    bundles = sorted({(a.get("bundleIdentifier") or "").strip().lower()
                      for a in apps if a.get("bundleIdentifier")})
    genres = itunes_lookup(bundles)

    result, todo = {}, []
    for i, a in enumerate(apps):
        g = genres.get((a.get("bundleIdentifier") or "").strip().lower())
        if g:
            result[i] = ("games" if any("game" in x.lower() for x in g if x) else "apps"), "App Store"
        else:
            todo.append(i)
    print(f"✅ {len(result)} resolved by App Store, {len(todo)} need IPA check")

    if todo:
        done = 0
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            futs = {}
            for i in todo:
                url = ipa_url_of(apps[i])
                futs[ex.submit(classify_from_ipa, url) if url else ex.submit(lambda: (None, "no url"))] = i
            for fut in as_completed(futs):
                result[futs[fut]] = fut.result()
                done += 1
                if done % 50 == 0 or done == len(todo):
                    print(f"🔎 IPA check: {done}/{len(todo)}")

    changed, unknown = [], []
    for i, a in enumerate(apps):
        t, src = result.get(i, (None, "none"))
        if not t:
            unknown.append((a.get("name"), src))
            continue
        old = a.get("type")
        if old != t or a.get("category") != t:
            changed.append((a.get("name"), old, t, src))
        a["type"] = t
        a["category"] = t

    print("\n================ ئەنجام ================")
    print(f"گۆڕدرا: {len(changed)} | دیار نەبوو (وەک خۆی ماوە): {len(unknown)} | "
          f"games: {sum(1 for a in apps if a.get('type') == 'games')} | "
          f"apps: {sum(1 for a in apps if a.get('type') == 'apps')}")
    for name, old, new, src in changed[:300]:
        print(f"  {name}: {old} -> {new}  ({src})")
    if len(changed) > 300:
        print(f"  ... و {len(changed) - 300} ی تر")
    if unknown:
        print("\nدیار نەبوو:")
        for name, why in unknown[:100]:
            print(f"  {name}  [{why}]")

    if DRY_RUN:
        print("\n(DRY RUN: هیچ نەنووسرایەوە)")
        return
    for path in (JSON_FILE, BACKUP_FILE):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"\n💾 {JSON_FILE} و {BACKUP_FILE} نووسرانەوە.")


if __name__ == "__main__":
    main()
