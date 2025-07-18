# common_utils.py
import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"


def strip_html_tags(text):
    return re.sub(r"<.*?>", "", text or "")


def clean_google_url(url):
    if "google.com/url" in url:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        if "url" in query:
            return query["url"][0]
    return url


def translate_text(text):
    if not text.strip():
        return ""
    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
    }
    prompt = (
        "Please translate the following text into Korean. "
        "Return only the translation, with no explanation, no greetings, and no formatting.\n"
        f"Text to translate:\n{text}"
    )
    data = {
        "model": "claude-3-sonnet-20240229",
        "max_tokens": 1024,
        "temperature": 0.7,
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        res = requests.post(CLAUDE_API_URL, headers=headers, json=data)
        res.raise_for_status()
        result = res.json()
        return result["content"][0]["text"].strip()
    except Exception as e:
        print("⚠️ 번역 실패:", e)
        return ""


def fetch_article_body(url, max_length=1000):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        article = soup.find("article")
        if article:
            text = article.get_text()
        else:
            paragraphs = soup.find_all("p")
            text = "\n".join(p.get_text().strip() for p in paragraphs)
        return text[:max_length]
    except Exception as e:
        print(f"⚠️ 본문 크롤 실패: {e}")
        return ""

def is_duplicate_md(filepath, original_title):
    if not os.path.exists(filepath):
        return False
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            return original_title in content
    except:
        return False

def safe_filename(text, max_length=80):
    text = re.sub(r"[\\/:*?\"<>|]", "", text)
    return text.strip()[:max_length]
