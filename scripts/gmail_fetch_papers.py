# gmail_fetch_papers.py (중복 검사 및 요약 기준 필터링 개선)
import os
import base64
import json
import re
from datetime import datetime
from email.utils import parsedate_to_datetime, parseaddr
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from tqdm import tqdm
from google.auth.transport.requests import Request
from bs4 import BeautifulSoup
from time import sleep
from common_utils import translate_text, safe_filename, is_duplicate_md

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
SEEN_FILE = "seen_paper_messages.json"

def get_gmail_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("gmail_credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)

def list_messages(service, max_results=100):
    results = service.users().messages().list(userId="me", maxResults=max_results).execute()
    return results.get("messages", [])

def get_message(service, msg_id):
    return service.users().messages().get(userId="me", id=msg_id, format="full").execute()

def parse_headers(headers):
    return {h["name"]: h["value"] for h in headers}

def extract_date(date_str):
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return "unknown-date"

def decode_body(body_data):
    decoded_bytes = base64.urlsafe_b64decode(body_data + "===")
    return decoded_bytes.decode("utf-8")

def extract_scholar_block(html):
    soup = BeautifulSoup(html, "html.parser")
    articles = []
    for a_tag in soup.find_all("a", class_="gse_alrt_title"):
        title = a_tag.get_text(strip=True)
        url = a_tag["href"]
        summary_div = a_tag.find_next_sibling("div", class_="gse_alrt_sni")
        summary = summary_div.get_text(strip=True) if summary_div else ""
        if title:
            articles.append({"title": title, "summary": summary, "url": url})
    return articles

def save_article(article, keyword, date):
    folder = os.path.join("docs", "papers", keyword, date)
    os.makedirs(folder, exist_ok=True)
    title = article.get("translated_title") or article["title"]
    filename = f"{safe_filename(title)}.md"
    filepath = os.path.join(folder, filename)

    if is_duplicate_md(filepath, article['title']):
        print(f"\U0001f6ab 중복 논문: {article['title']}")
        return

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# {article['translated_title'] or article['title']}\n\n")
        f.write(f"**원제목:** {article['title']}\n\n")
        f.write(f"**요약:** {article['translated_summary']}\n\n")
        f.write(f"[원문 링크]({article['url']})\n")
    print(f"\u2705 저장 완료: {filepath}")

def load_seen_ids():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return json.load(f)
    return []

def save_seen_ids(ids):
    with open(SEEN_FILE, "w") as f:
        json.dump(ids, f)

def main():
    print("\U0001f680 Gmail 학술 알리미 인증 중...")
    service = get_gmail_service()
    print("\U0001f4ec 메일 목록 가져오는 중...")
    messages = list_messages(service, max_results=100)
    print(f"✅ 총 {len(messages)}개의 메일을 확인합니다.")

    seen = load_seen_ids()
    new_msgs = [m for m in messages if m["id"] not in seen]
    saved_titles = set()

    for msg in tqdm(new_msgs):
        msg_id = msg["id"]
        msg_detail = get_message(service, msg_id)
        headers = parse_headers(msg_detail["payload"].get("headers", []))
        subject = headers.get("Subject", "")
        sender = parseaddr(headers.get("From", ""))[1]

        if sender != "scholaralerts-noreply@google.com":
            continue

        payload = msg_detail["payload"]
        body_data = None
        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/html":
                body_data = part.get("body", {}).get("data")
                break
        if not body_data and payload.get("mimeType") == "text/html":
            body_data = payload.get("body", {}).get("data")
        if not body_data:
            continue

        html = decode_body(body_data)
        articles = extract_scholar_block(html)
        if not articles:
            continue

        date = extract_date(headers.get("Date"))
        match = re.search(r"(.+?)\s*-\s*새로운 결과", subject)
        keyword = match.group(1).strip() if match else "unknown"

        for article in articles:
            orig_title = article.get("title", "").strip()
            if not orig_title or orig_title in saved_titles:
                continue

            folder = os.path.join("docs", "papers", keyword, date)
            os.makedirs(folder, exist_ok=True)
            filepath = os.path.join(folder, f"{safe_filename(orig_title)}.md")
            if is_duplicate_md(filepath, orig_title):
                print(f"\U0001f6ab 중복 논문 (번역 안 함): {orig_title}")
                continue

            summary = article.get("summary") or orig_title
            if not summary.strip() or len(summary.strip()) < 50:
                print(f"⚠️ 요약 부족 — 저장하지 않음: {orig_title}")
                continue

            article["translated_title"] = translate_text(orig_title)
            article["translated_summary"] = translate_text(summary)
            save_article(article, keyword, date)
            saved_titles.add(orig_title)
            sleep(1.5)

        seen.append(msg_id)

    save_seen_ids(seen)

if __name__ == "__main__":
    main()
