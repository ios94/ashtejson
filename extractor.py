import json
import requests

url = "https://ng-api.builds.io/api/v1/applications/?page=1&page_size=100"

headers = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Accept": "application/json"
}

response = requests.get(url, headers=headers)
apps_list = []

if response.status_code == 200:
    data = response.json()
    if "data" in data:
        for app in data["data"]:
            slug = app.get("slug")
            apps_list.append({
                "name": app.get("name"),
                "bundleIdentifier": f"com.builds.{slug}",
                "version": "1.0",
                "versionDate": app.get("last_modified_at"),
                "downloadURL": f"https://ng-api.builds.io/api/v1/applications/{slug}/download",
                "iconURL": app.get("icon"),
                "localizedDescription": app.get("name")
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
