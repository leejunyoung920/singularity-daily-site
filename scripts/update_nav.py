# scripts/update_nav.py
import os
import datetime
import yaml

# mkdocs.yml 경로
MKDOCS_YML_PATH = "mkdocs.yml"
ARTICLES_DIR = "docs/articles"

def generate_nav_entries():
    nav_entries = []
    years = sorted(os.listdir(ARTICLES_DIR), reverse=True)

    for year in years:
        year_path = os.path.join(ARTICLES_DIR, year)
        if not os.path.isdir(year_path):
            continue
        year_entry = {}
        months = sorted(os.listdir(year_path), reverse=True)
        month_entries = []
        for month in months:
            month_path = os.path.join(year_path, month)
            if not os.path.isdir(month_path):
                continue
            article_entries = []
            for filename in sorted(os.listdir(month_path), reverse=True):
                if filename.endswith(".md"):
                    title = filename.replace(".md", "").split("_", 1)[-1].replace("-", " ").replace("_", " ")
                    rel_path = f"articles/{year}/{month}/{filename}"
                    article_entries.append({title.title(): rel_path})
            if article_entries:
                month_entries.append({f"{month}월": article_entries})
        if month_entries:
            year_entry[f"{year}년"] = month_entries
            nav_entries.append(year_entry)
    return nav_entries

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
