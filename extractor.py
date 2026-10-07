import json
import os
import requests

# داواکردنی داتاکان لە APIـی ماڵپەڕەکە
url = "https://ng-api.builds.io/api/v1/applications/?page=1&page_size=100"

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
            download_url = f"https://github.com/ios94/ashtejson/releases/download/V1/{slug}.ipa"
            
            if versions and len(versions) > 0:
                current_ver = versions[0]
                version_str = current_ver.get("version", "1.0")
                byte_size = current_ver.get("ipa_size", 0)
                if byte_size:
                    # گۆڕینی قەبارە بۆ مێگابایت
                    size_str = f"{round(byte_size / (1024 * 1024), 2)} MB"

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

altstore_source = {
    "name": "AshteMobile Store",
    "identifier": "com.ashtemobile.source",
    "apps": apps_list
}

output_file = "ashtemobile94.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(altstore_source, f, ensure_ascii=False, indent=4)

print(f"Successfully generated source with {len(apps_list)} apps.")
