# scripts/collect_articles.py
import os
import datetime
import feedparser
import requests
from bs4 import BeautifulSoup
import json
import httpx

# 1. Claude API 키 설정 (Anthropic)
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"

# 2. RSS 피드 예시 (원하는 만큼 추가 가능)
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

# 3. 기사 요약 함수 (Claude 사용)
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

# 4. 기사 본문 추출 함수
def extract_article_content(url):
    try:
        res = requests.get(url, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        paragraphs = soup.find_all('p')
        return '\n'.join(p.get_text() for p in paragraphs)
    except:
        return ""

# 5. 마크다운 파일 저장 함수
def save_to_markdown(title, url, summary, original_title=None):
    today = datetime.date.today().strftime("%Y-%m-%d")
    safe_title = "_".join(title.strip().split())[:50].replace('/', '-')
    filename = f"docs/articles/{today}_{safe_title}.md"

    content = f"""# {title}

**영문 원제목:** {original_title or title}  
**출처:** {url}

## 요약
{summary}

## 원문 링크
[{url}]({url})
"""
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

def is_duplicate(title):
    today = datetime.date.today().strftime("%Y-%m-%d")
    safe_title = "_".join(title.strip().split())[:50].replace('/', '-')
    filename = f"{today}_{safe_title}.md"
    full_path = os.path.join("docs/articles", filename)
    return os.path.exists(full_path)


# 6. 전체 수집 실행
def run():
    for feed_url in RSS_FEEDS:
        print(f"📡 피드 수집 중: {feed_url}")
        try:
            feed = feedparser.parse(feed_url)
        except Exception as e:
            print(f"❌ 피드 수집 실패 ({feed_url}): {e}")
            continue

        for entry in feed.entries[:3]:
            title = entry.title
            url = entry.link

            if is_duplicate(title):
                print(f"🚫 중복: {title}")
                continue

            content = extract_article_content(url)
            if not content or len(content) < 300:
                continue

            translated_title, summary = summarize_article(title, url, content)
            save_to_markdown(translated_title, url, summary, original_title=title)



if __name__ == "__main__":
    run()
