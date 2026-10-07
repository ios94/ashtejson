import json
import os

# نموونەی ئەو داتایانەی کە لە پەیجەکە یان کەتەلۆگەکە دەرهێنراون
# دەتوانیت لێرەدا پەرە بە سکریپتەکە بدەیت بۆ ئەوەی بە API یان Web Scraping داتاکان وەربگرێت
apps_data = [
    {
        "name": "BuildStore",
        "bundle_id": "com.builds.store",
        "version": "1.0",
        "size": "45 MB",
        "icon": "https://builds.io/icon1.png",
        "ipa_link": "https://builds.io/downloads/buildstore.ipa"
    },
    {
        "name": "iPoGo - Pokemon GO++",
        "bundle_id": "com.nianticlabs.pokemongo.ipogo",
        "version": "3.5.0",
        "size": "120 MB",
        "icon": "https://builds.io/icon2.png",
        "ipa_link": "https://builds.io/downloads/ipogo.ipa"
    },
    {
        "name": "Coin Master Hack",
        "bundle_id": "com.moonactive.coinmaster.hack",
        "version": "3.5.2731",
        "size": "107.88 MB",
        "icon": "https://builds.io/icon3.png",
        "ipa_link": "https://builds.io/downloads/coinmaster.ipa"
    }
]

# پاشەکەوتکردنی داتاکان بۆ ناو فایلی JSON
output_file = "ashtemobile94.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(apps_data, f, ensure_ascii=False, indent=4)

print(f"Successfully generated {output_file}")
