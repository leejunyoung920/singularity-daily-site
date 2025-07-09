# scripts/update_nav.py
import os
import datetime
import yaml

# mkdocs.yml 경로
MKDOCS_YML_PATH = "mkdocs.yml"
ARTICLES_DIR = "docs/articles"

def generate_nav_entries():
    entries = []
    for filename in sorted(os.listdir(ARTICLES_DIR), reverse=True):
        if filename.endswith(".md"):
            title = filename.replace(".md", "").split("_", 1)[-1].replace("-", " ").replace("_", " ")
            entries.append({title.title(): f"articles/{filename}"})
    return entries

def update_mkdocs_yml():
    with open(MKDOCS_YML_PATH, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    nav = config.get("nav", [])
    new_nav = []
    found_articles = False

    for item in nav:
        if isinstance(item, dict) and "기사 모음" in item:
            new_nav.append({"기사 모음": generate_nav_entries()})
            found_articles = True
        else:
            new_nav.append(item)

    if not found_articles:
        new_nav.append({"기사 모음": generate_nav_entries()})

    config["nav"] = new_nav

    with open(MKDOCS_YML_PATH, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True)

    print("✅ mkdocs.yml 메뉴 자동 업데이트 완료")

if __name__ == "__main__":
    update_mkdocs_yml()
