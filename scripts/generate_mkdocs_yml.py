import os
import yaml
import re

def shorten_title(title, max_length=60):
    """긴 제목을 자르고, 개행·특수문자 제거"""
    title = title.strip().replace('\n', ' ').replace('\r', '')
    title = re.sub(r'\s+', ' ', title)
    title = re.sub(r'[\"\'`]', '', title)
    if len(title) > max_length:
        title = title[:max_length].rstrip() + "..."
    return title  # 더 이상 따옴표 감싸지 않음

def collect_markdown_files(base_dir):
    sections = {}
    for section in ['articles', 'topics', 'papers']:
        section_path = os.path.join("docs", section)
        if not os.path.exists(section_path):
            continue

        if section == 'articles':
            entries = {}
            for root, _, files in os.walk(section_path):
                for file in sorted(files):
                    if file.endswith(".md"):
                        rel_path = os.path.relpath(os.path.join(root, file), "docs")
                        date = rel_path.split("/")[1]
                        title = shorten_title(os.path.splitext(file)[0])
                        entries.setdefault(date, []).append({title: rel_path})
            nav_section = [{date: entries[date]} for date in sorted(entries.keys())]
            sections[section] = nav_section

        else:  # topics, papers
            entries = {}
            for keyword in sorted(os.listdir(section_path)):
                keyword_path = os.path.join(section_path, keyword)
                if not os.path.isdir(keyword_path):
                    continue
                date_entries = {}
                for date in sorted(os.listdir(keyword_path)):
                    date_path = os.path.join(keyword_path, date)
                    if not os.path.isdir(date_path):
                        continue
                    md_files = []
                    for f in sorted(os.listdir(date_path)):
                        if f.endswith(".md"):
                            title = shorten_title(os.path.splitext(f)[0])
                            rel_path = os.path.relpath(os.path.join(date_path, f), "docs")
                            md_files.append({title: rel_path})
                    if md_files:
                        date_entries[date] = md_files
                if date_entries:
                    keyword_nav = [{date: date_entries[date]} for date in date_entries]
                    entries[keyword] = keyword_nav
            nav_section = [{keyword: entries[keyword]} for keyword in entries]
            sections[section] = nav_section
    return sections

def write_mkdocs_yml(sections):
    config = {
        "site_name": "Singularity Daily",
        "site_url": "https://leejunyoung920.github.io/singularity-daily-site/",
        "repo_url": "https://github.com/leejunyoung920/singularity-daily-site/",
        "theme": {
            "name": "material",
            "language": "ko",
            "features": [
                "navigation.sections",
                "navigation.expand",
                "navigation.top",
                "content.code.copy",
                "toc.integrate"
            ]
        },
        "use_directory_urls": False,
        "markdown_extensions": [
            "admonition",
            {
                "toc": {
                    "permalink": True
                }
            },
            "footnotes",
            "meta"
        ],
        "extra_css": [
            "stylesheets/extra.css"
        ],
        "plugins": [
            "search",
            "awesome-pages"
        ],
        "nav": []
    }

    for section in ['articles', 'topics', 'papers']:
        if section in sections:
            config["nav"].append({section: sections[section]})

    with open("mkdocs.generated.yml", "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, sort_keys=False, width=1000)

    print("✅ mkdocs.generated.yml 생성 완료")

if __name__ == "__main__":
    sections = collect_markdown_files("docs")
    write_mkdocs_yml(sections)
