# scripts/collect_articles.py
import os
import datetime
import feedparser
import requests
from bs4 import BeautifulSoup
import json
import httpx
import base64
import re
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# GitHub Actions 환경에서는 실행하지 않도록
if os.getenv("GITHUB_ACTIONS") == "true":
    print("Skipping article collection on GitHub Actions.")
    exit(0)

CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"

# Gmail API 설정
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
GMAIL_QUERY = 'subject:(Google 알리미)'
CREDENTIALS_FILE = 'gmail_credentials.json'
TOKEN_FILE = 'token.json'

# 기존 RSS 피드 유지
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
    "https://a16z.com/feed/"
    "https://the-decoder.com/feed/"
]

def summarize_article(title, url, content):
    prompt = f"""
    아래는 기술 관련 기사입니다. 제목과 내용을**한국어로 읽고**, 다음 2가지를 작성해주세요:

    1. 원제목을 한국어로 번역한 제목 (한 문장, 너무 직역하지 말고 자연스럽게)
    2. 기사 내용의 핵심 요약 (한국어로 5줄 이내)

    다음 형식으로 출력하세요:

    번역 제목: ...
    요약:
    ... 

    제목: {title}
    내용: {content[:3000]}
    """
    try:
        headers = {
            "x-api-key": CLAUDE_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        data = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 400,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        response = httpx.post(CLAUDE_API_URL, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        full_text = result["content"][0]["text"].strip()

        translated_title = ""
        summary = ""
        for line in full_text.splitlines():
            if line.lower().startswith("번역 제목:"):
                translated_title = line.split(":", 1)[1].strip()
            elif line.lower().startswith("요약:"):
                summary_index = full_text.index(line) + len("요약:")
                summary = full_text[summary_index:].strip()
                break

        return translated_title or title, summary or "요약 실패"

    except Exception as e:
        print(f"요약 실패: {e}")
        return "요약 실패"

def extract_article_content(url):
    try:
        res = requests.get(url, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        paragraphs = soup.find_all('p')
        return '\n'.join(p.get_text() for p in paragraphs)
    except:
        return ""

def save_to_markdown(title, url, summary, original_title=None):
    today = datetime.date.today()
    year = today.strftime("%Y")
    month = today.strftime("%m")
    date = today.strftime("%Y-%m-%d")

    safe_title = "_".join(title.strip().split())[:50].replace('/', '-')
    dir_path = os.path.join("docs", "articles", year, month)
    os.makedirs(dir_path, exist_ok=True)
    filename = f"{date}_{safe_title}.md"
    filepath = os.path.join(dir_path, filename)

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

def is_duplicate(title):
    today = datetime.date.today()
    year = today.strftime("%Y")
    month = today.strftime("%m")
    date = today.strftime("%Y-%m-%d")

    safe_title = "_".join(title.strip().split())[:50].replace('/', '-')
    filename = f"{date}_{safe_title}.md"
    path = os.path.join("docs", "articles", year, month, filename)
    return os.path.exists(path)

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
    all_urls = fetch_alert_links()

    for feed_url in RSS_FEEDS:
        print(f"📡 피드 수집 중: {feed_url}")
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:3]:
                all_urls.append(entry.link)
        except Exception as e:
            print(f"❌ 피드 수집 실패 ({feed_url}): {e}")

    for url in all_urls:
        content = extract_article_content(url)
        if not content or len(content) < 300:
            continue

        title = url.split('/')[-1].replace('-', ' ').replace('_', ' ')
        if is_duplicate(title):
            print(f"🚫 중복: {title}")
            continue

        translated_title, summary = summarize_article(title, url, content)
        save_to_markdown(translated_title, url, summary, original_title=title)

if __name__ == "__main__":
    run()
