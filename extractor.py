import json
import requests

url = "https://ng-api.builds.io/api/v1/applications/?page=1&page_size=100"

headers = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Accept": "application/json"
}

response = requests.get(url, headers=headers)
apps_data = []

if response.status_code == 200:
    data = response.json()
    if "data" in data:
        for app in data["data"]:
            apps_data.append({
                "name": app.get("name"),
                "slug": app.get("slug"),
                "icon": app.get("icon"),
                "last_modified": app.get("last_modified_at"),
                "ipa_link": f"https://builds.io/{app.get('slug')}"
            })

output_file = "ashtemobile94.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(apps_data, f, ensure_ascii=False, indent=4)

print(f"Successfully extracted {len(apps_data)} apps into {output_file}")
