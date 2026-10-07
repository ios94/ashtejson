import json
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# دروستکردنی فۆڵدەرێک بۆ ئەوەی فایلە دابەزێنراوەکانی IPAی تێدا کۆبکرێتەوە
os.makedirs("ipas", exist_ok=True)

url = "https://ashtemobile.tututweak.com/ii.html"
headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"}

response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')

apps_list = []
processed_slugs = set()

# گەڕان بۆ هەموو ئەو لینکانەی وشەی 'داگرتن'یان تێدایە
for a_tag in soup.find_all('a'):
    text = a_tag.get_text(strip=True)
    href = a_tag.get('href')
    
    if href and "داگرتن" in text:
        download_link = urljoin(url, href)
        
        # دۆزینەوەی ناوی ئەپەکە لە توخمەکانی پێشتردا
        name = "Unknown_App"
        parent = a_tag.find_parent('div')
        if parent:
            title_tag = parent.find(['h2', 'h3', 'h4', 'strong', 'span'])
            if title_tag:
                name = title_tag.get_text(strip=True)
        
        # دروستکردنی کورتکراوە (slug) بۆ ناوەکە
        slug = "".join(e for e in name if e.isalnum()).lower()
        if not slug or slug in processed_slugs:
            continue
            
        processed_slugs.add(slug)
        ipa_filename = f"ipas/{slug}.ipa"
        
        print(f"Downloading {name} from {download_link} ...")
        try:
            # داگرتنی فایلی ipa لە ماڵپەڕەکەوە
            r = requests.get(download_link, headers=headers, stream=True)
            if r.status_code == 200:
                with open(ipa_filename, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                # بەستنەوەی لینکی فایلی ناو JSON بە ڕێلیزی V1 ی گیتهابەکەت
                github_release_url = f"https://github.com/ios94/ashtejson/releases/download/V1/{slug}.ipa"
                
                apps_list.append({
                    "name": name,
                    "bundleIdentifier": f"com.ashtemobile.{slug}",
                    "version": "1.0",
                    "size": "50 MB",
                    "versionDate": "2026-10-07",
                    "downloadURL": github_release_url,
                    "iconURL": "https://ashtemobile.tututweak.com/logo.png",
                    "localizedDescription": "Downloaded from AshteMobile Source"
                })
            else:
                print(f"Failed to download {name}, status: {r.status_code}")
        except Exception as e:
            print(f"Error downloading {name}: {e}")

altstore_source = {
    "name": "AshteMobile Store",
    "identifier": "com.ashtemobile.source",
    "apps": apps_list
}

# پاشەکەوتکردنی JSON بە شێوەی ئاسایی بۆ ناو فایلەکانی گیتهاپ
output_file = "ashtemobile94.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(altstore_source, f, ensure_ascii=False, indent=4)

print(f"Successfully processed and downloaded {len(apps_list)} apps.")
