import os
import json
import base64
import urllib.parse

def _d(s):
    return base64.b64decode(s).decode('utf-8')

app_to_delete = os.environ.get("DELETE_APP_NAME", "").strip()

if not app_to_delete:
    print("⚠️ تکایە ناوی یارییەکە بنووسە بۆ سڕینەوە.")
    exit(1)

json_file = _d('YXNodGVtb2JpbGU5NC5qc29u')
backup_file = "backup_memory.json"

if not os.path.exists(json_file):
    print("⚠️ فایلی جەیسۆن نەدۆزرایەوە.")
    exit(1)

with open(json_file, "r", encoding="utf-8") as f:
    data = json.load(f)

apps = data.get("apps", [])
found = False
files_to_delete = []
ipa_name_for_release = ""

for i, app in enumerate(apps):
    # بەراوردکردنی ناوەکان بە بێ گوێدانە پیتی گەورە و بچووک
    if app.get("name", "").lower().strip() == app_to_delete.lower().strip():
        
        # دۆزینەوەی وێنەی ئایکۆن
        icon_path = app.get("icon", "")
        if icon_path:
            files_to_delete.append(icon_path)
        
        # دۆزینەوەی سکرینشۆتەکان
        for screen in app.get("screenshots", []):
            screen_name = screen.split("/")[-1]
            files_to_delete.append(os.path.join("imgg", screen_name))

        # دۆزینەوەی ناوی فایلی IPA بۆ سڕینەوەی لە ڕیلیز
        install_url = app.get("install_url", "")
        if install_url:
            ipa_name_for_release = urllib.parse.unquote(install_url.split("/")[-1])

        # سڕینەوەی یارییەکە لە جەیسۆن
        apps.pop(i)
        found = True
        break

if not found:
    print(f"⚠️ یاری '{app_to_delete}' نەدۆزرایەوە لەناو جەیسۆنەکەدا.")
    exit(1)

# سەیڤکردنەوەی فایلی جەیسۆن بە بێ ئەو یارییە
with open(json_file, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)
with open(backup_file, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

# سڕینەوەی وێنەکان لە گیتهاپ
for file_path in files_to_delete:
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"🗑️ سڕییەوە: {file_path}")
    else:
        print(f"⚠️ وێنەکە نەدۆزرایەوە بۆ سڕینەوە: {file_path}")

# ناردنی ناوی IPA بۆ GitHub Actions تا لەوێ بیسڕێتەوە
env_file = os.getenv('GITHUB_ENV')
if env_file and ipa_name_for_release:
    with open(env_file, "a") as f:
        f.write(f"IPA_TO_DELETE={ipa_name_for_release}\n")

print(f"✅ یاری '{app_to_delete}' بە تەواوی سڕایەوە و پاک کرایەوە!")
