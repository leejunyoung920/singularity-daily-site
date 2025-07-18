# scripts/collect_articles.py
import os
import datetime
import feedparser
import requests
from bs4 import BeautifulSoup
import base64
import re
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from common_utils import translate_text, fetch_article_body, safe_filename, is_duplicate_md

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
GMAIL_QUERY = 'subject:(Google 알리미)'
CREDENTIALS_FILE = 'gmail_credentials.json'
TOKEN_FILE = 'token.json'

RSS_FEEDS = [
    "https://www.technologyreview.com/feed/",
    "https://singularityhub.com/feed/",
    "https://longevity.technology/feed/",
    "https://www.kurzweilai.net/news/feed",
    "https://spectrum.ieee.org/rss/robotics",
    "https://www.fightaging.org/rss.xml",
    "https://www.futuretimeline.net/blog/rss.xml",
    "https://nautil.us/feed/",
    "https://www.neurotechreports.com/rss.xml",
    "https://a16z.com/feed/",
    "https://the-decoder.com/feed/"
]

def summarize_article(title, url, content):
    prompt = f"""
    다음은 기술 관련 기사입니다. 제목과 내용을 **한국어로 읽고**, 다음 2가지를 작성해주세요:

    1. 원제목을 한국어로 번역한 제목 (1문장, 너무 직역하지 말고 자연스럽게)
    2. 기사 내용의 핵심 요약 (5줄 이내)

    다음 형식으로 출력하세요:

    번역 제목: ...
    요약:
    ...

    제목: {title}
    내용: {content[:3000]}
    """
    try:
        headers = {
            "x-api-key": os.getenv("CLAUDE_API_KEY"),
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        data = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 400,
            "messages": [{"role": "user", "content": prompt}]
        }
        response = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        full_text = result["content"][0]["text"].strip()

        translated_title = ""
        summary = ""
        for line in full_text.splitlines():
            if line.lower().startswith("번역 제목"):
                translated_title = line.split(":", 1)[1].strip()
            elif line.lower().startswith("요약"):
                summary_index = full_text.index(line) + len("요약:")
                summary = full_text[summary_index:].strip()
                break

        return translated_title or title, summary or "요약 실패"

    except Exception as e:
        print(f"⚠️ 요약 실패: {e}")
        return title, "요약 실패"

def save_to_markdown(title, url, summary, original_title=None):
    date_str = datetime.date.today().strftime("%Y-%m-%d")
    dir_path = os.path.join("docs", "articles", date_str)
    os.makedirs(dir_path, exist_ok=True)

    safe_title = safe_filename(title)
    filepath = os.path.join(dir_path, f"{safe_title}.md")

    content = f"""# {title}

**영문 원제목:** {original_title or title}  
**출처:** {url}

## 요약
{summary}

## 원문 링크
[{url}]({url})
"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ 저장 완료: {filepath}")

def fetch_alert_links():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    else:
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)
    result = service.users().messages().list(userId='me', q=GMAIL_QUERY).execute()
    messages = result.get('messages', [])

    urls = []
    for msg in messages[:5]:
        msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        for part in msg_data['payload'].get('parts', []):
            if part['mimeType'] == 'text/html':
                data = part['body']['data']
                html = base64.urlsafe_b64decode(data).decode('utf-8')
                found_urls = re.findall(r'https?://[^\s"]+', html)
                urls.extend(found_urls)

    return list(set(urls))

def run():
    today = datetime.date.today()
    date_str = today.strftime("%Y-%m-%d")

    for feed_url in RSS_FEEDS:
        print(f"📡 RSS 수집: {feed_url}")
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:10]:
                title = entry.get("title", "").strip()
                url = entry.get("link", "").strip()
                content = fetch_article_body(url)
                if not content or len(content.strip()) < 300:
                    print(f"🚫 본문 짧음: {title}")
                    continue

                safe_title = safe_filename(title)
                dir_path = os.path.join("docs", "articles", date_str)
                filepath = os.path.join(dir_path, f"{safe_title}.md")
                if is_duplicate_md(filepath, title):
                    print(f"🚫 중복 기사: {title}")
                    continue

                translated_title, summary = summarize_article(title, url, content)
                save_to_markdown(translated_title, url, summary, original_title=title)
        except Exception as e:
            print(f"❌ 수집 실패 ({feed_url}): {e}")

    alert_urls = fetch_alert_links()
    for url in alert_urls:
        title = url.split("/")[-1].replace("-", " ").replace("_", " ").strip()
        content = fetch_article_body(url)
        if not content or len(content.strip()) < 500:
            print(f"🚫 본문 짧음: {title}")
            continue

        safe_title = safe_filename(title)
        dir_path = os.path.join("docs", "articles", date_str)
        filepath = os.path.join(dir_path, f"{safe_title}.md")
        if is_duplicate_md(filepath, title):
            print(f"🚫 중복 기사: {title}")
            continue

        translated_title, summary = summarize_article(title, url, content)
        save_to_markdown(translated_title, url, summary, original_title=title)

if __name__ == "__main__":
    run()


