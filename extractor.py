import json
import requests

url = "https://ng-api.builds.io/api/v1/applications/?page=1&page_size=100"

headers = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Accept": "application/json",
    "Referer": "https://builds.io/apps"
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
            
            # دەرهێنانی ڤێرژن و لینکی ڕاستەقینەی IPA ئەگەر بەردەست بێت
            version_str = "1.0"
            download_url = f"https://builds.io/apps/{slug}"
            
            if versions and len(versions) > 0:
                current_ver = versions[0]
                version_str = current_ver.get("version", "1.0")
                ver_id = current_ver.get("id")
                if ver_id:
                    download_url = f"https://ng-api.builds.io/api/v1/applications/{slug}/download?version_id={ver_id}"

            if name and slug:
                apps_list.append({
                    "name": name,
                    "bundleIdentifier": f"com.builds.{slug}",
                    "version": version_str,
                    "versionDate": last_modified,
                    "downloadURL": download_url,
                    "iconURL": icon,
                    "localizedDescription": name
                })

altstore_source = {
    "name": "AshteMobile Builds",
    "identifier": "com.ashtemobile.source",
    "apps": apps_list
}

output_file = "ashtemobile94.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(altstore_source, f, ensure_ascii=False, indent=4)

print(f"Successfully generated AltStore source with {len(apps_list)} apps.")
