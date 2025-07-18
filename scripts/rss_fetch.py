# rss_fetch.py (개선된 중복 검사 + 본문 길이 기준 + 비용 방지)
import os
import feedparser
from datetime import datetime
from time import sleep
from common_utils import (
    clean_google_url,
    strip_html_tags,
    translate_text,
    fetch_article_body,
    safe_filename,
    is_duplicate_md
)

# Claude API 키는 common_utils.py 내부에서 처리됨

# RSS 피드 목록 
RSS_FEEDS = {
    "AGI": "https://www.google.co.kr/alerts/feeds/14276058857012603250/2707178187233880419",
    "AI drug discovery": "https://www.google.co.kr/alerts/feeds/14276058857012603250/2271409061188943971",
    "Anti-aging therapeutics": "https://www.google.co.kr/alerts/feeds/14276058857012603250/1502131717617198121",
    "Cellular reprograming": "https://www.google.co.kr/alerts/feeds/14276058857012603250/2481308844339361893",
    "Longevity research": "https://www.google.co.kr/alerts/feeds/14276058857012603250/9706346182581700369",
    "nanobot": "https://www.google.co.kr/alerts/feeds/14276058857012603250/2271409061188945116",
    "NMN": "https://www.google.co.kr/alerts/feeds/14276058857012603250/1502131717617199599",
    "Rapamycin": "https://www.google.co.kr/alerts/feeds/14276058857012603250/2707178187233881309",
    "Senolytics": "https://www.google.co.kr/alerts/feeds/14276058857012603250/1502131717617200498",
    "Telomere extension": "https://www.google.co.kr/alerts/feeds/14276058857012603250/9135595537824711247",
    "Humanoid Robot": "https://www.google.co.kr/alerts/feeds/14276058857012603250/1273794955109409208"
}

def save_markdown(keyword, date_str, title_ko, title_en, summary_ko, url):
    safe_title = safe_filename(title_ko)
    folder = os.path.join("docs", "topics", keyword, date_str)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{safe_title}.md")

    if is_duplicate_md(path, title_en):
        print(f"🚫 중복 기사: {title_en}")
        return

    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# {title_ko}\n\n")
        f.write(f"**원제목:** {title_en}\n\n")
        f.write(f"**요약:** {summary_ko}\n\n")
        f.write(f"[원문 링크]({url})\n")
    print(f"✅ 저장 완료: {path}")

def main():
    for keyword, feed_url in RSS_FEEDS.items():
        print(f"🌐 RSS 수집 시작: {keyword}")
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:20]:
            raw_title = entry.get("title", "")
            raw_link = entry.get("link", "")
            link = clean_google_url(raw_link)
            title_en = strip_html_tags(raw_title)
            pub_date = entry.get("published", "") or entry.get("updated", "")
            date_str = datetime(*entry.published_parsed[:3]).strftime("%Y-%m-%d") if entry.published_parsed else "unknown-date"

            # ✅ 본문 먼저 추출 후 필터
            body = fetch_article_body(link)
            if not body or len(body.strip()) < 300:
                print(f"⚠️ 본문 부족 — 저장하지 않음: {title_en}")
                continue

            # ✅ 저장 경로 기준 중복 확인 (비용 발생 전)
            safe_title = safe_filename(title_en)
            folder = os.path.join("docs", "topics", keyword, date_str)
            os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder, f"{safe_title}.md")
            if is_duplicate_md(path, title_en):
                print(f"🚫 중복 기사 (번역 안 함): {title_en}")
                continue

            # ✅ 번역 수행
            title_ko = translate_text(title_en)
            summary_ko = translate_text(body)

            save_markdown(keyword, date_str, title_ko, title_en, summary_ko, link)
            sleep(1.5)

if __name__ == "__main__":
    main()
