import json
import os
import requests

url = "https://ng-api.builds.io/api/v1/applications/?page=1&page_size=30" # دەتوانیت ژمارەکە زیاد بکەیت

headers = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
    "Accept": "application/json"
}

response = requests.get(url, headers=headers)
apps_list = []

# دروستکردنی فۆڵدەرێک بۆ فایلە دابەزێنراوەکان ئەگەر نەبوو
os.makedirs("ipas", exist_ok=True)

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

            # لێرەدا لینکی ڕاستەقینەی داگرتنی فایلی IPA دەبەستینەوە بە ڕێلیزی گیتهابەکەتەوە
            download_url = f"https://github.com/ios94/ashtejson/releases/download/V1/{slug}.ipa"

            if name and slug:
                apps_list.append({
                    "name": name,
                    "bundleIdentifier": f"com.builds.{slug}",
                    "version": version_str,
                    "size": size_str,
                    "versionDate": last_modified,
                    "downloadURL": download_url,
                    "iconURL": icon,
                    "localizedDescription": name
                })
                
                # تێبینی: ئەگەر لینکی دابەزاندنی ڕاستەقینەی ipaت هەبێت، لێرەدا داونلۆدی دەکەیت و دەیخەیتە فۆڵدەری ipas/
                # نموونە:
                # ipa_download_link = app.get("ipa_file_url")
                # if ipa_download_link:
                #     r = requests.get(ipa_download_link)
                #     with open(f"ipas/{slug}.ipa", "wb") as f:
                #         f.write(r.content)

altstore_source = {
    "name": "AshteMobile Store",
    "identifier": "com.ashtemobile.source",
    "apps": apps_list
}

with open("ashtemobile94.json", "w", encoding="utf-8") as f:
    json.dump(altstore_source, f, ensure_ascii=False, indent=4)

print("Extractor finished successfully.")
