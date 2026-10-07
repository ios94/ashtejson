import json
import os
import requests

# دروستکردنی فۆڵدەرێک بۆ ئەوەی فایلە دابەزێنراوەکانی IPAی تێدا کۆبکرێتەوە
os.makedirs("ipas", exist_ok=True)

url = "https://ng-api.builds.io/api/v1/applications/?page=1&page_size=20" # دەتوانیت ژمارەکە بگۆڕیت

headers = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
    "Accept": "application/json"
}

response = requests.get(url, headers=headers)
apps_list = []

if response.status_code == 200:
    data = response.json()
    if "data" in data:
        for app in data["data"]:
            name = app.get("name")
            slug = app.get("slug")
            icon = app.get("icon")
            last_modified = app.get("last_modified_at")
            versions = app.get("versions", [])
            
            version_str = "1.0"
            size_str = "45 MB"
            
            if versions and len(versions) > 0:
                current_ver = versions[0]
                version_str = current_ver.get("version", "1.0")
                byte_size = current_ver.get("ipa_size", 0)
                if byte_size:
                    size_str = f"{round(byte_size / (1024 * 1024), 2)} MB"

            # ---------------------------------------------------------
            # بەشی داگرتنی ئۆتۆماتیکی فایلی ipa بۆ ناو سێرڤەری گیتهاپ
            # ---------------------------------------------------------
            api_download_url = f"https://ng-api.builds.io/api/v1/applications/{slug}/download"
            ipa_filename = f"ipas/{slug}.ipa"
            print(f"Downloading {name}...")
            
            try:
                # تێبینی: ئەگەر ماڵپەڕەکە پێویستی بە هەژمار (Cookie) هەبوو بۆ داگرتن، دەبێت لێرەدا Cookie بۆ Header زیاد بکەیت
                r = requests.get(api_download_url, headers=headers, stream=True)
                if r.status_code == 200 and "application/json" not in r.headers.get("Content-Type", ""):
                    with open(ipa_filename, "wb") as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                else:
                    print(f"Skipping {name}, direct download not available without login.")
            except Exception as e:
                print(f"Error downloading {name}: {e}")

            # لینکی فایلی ipa کە دەچێتە ناو JSON (دەبەسترێتەوە بە ڕێلیزی V1)
            github_release_url = f"https://github.com/ios94/ashtejson/releases/download/V1/{slug}.ipa"

            if name and slug:
                apps_list.append({
                    "name": name,
                    "bundleIdentifier": f"com.builds.{slug}",
                    "version": version_str,
                    "size": size_str,
                    "versionDate": last_modified,
                    "downloadURL": github_release_url,
                    "iconURL": icon,
                    "localizedDescription": name
                })

altstore_source = {
    "name": "AshteMobile Store",
    "identifier": "com.ashtemobile.source",
    "apps": apps_list
}

# پاشەکەوتکردنی JSON بە شێوەی ئاسایی
output_file = "ashtemobile94.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(altstore_source, f, ensure_ascii=False, indent=4)

print(f"Successfully processed {len(apps_list)} apps.")
