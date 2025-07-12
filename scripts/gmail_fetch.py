import os
import base64
import datetime
import re
import json
from email import message_from_bytes
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Gmail API 사용 범위
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# 키워드 목록
KEYWORDS = ["Singularity", "Longevity", "Transhumanism", "AI"]

# Gmail 인증 및 서비스 객체 생성
def gmail_authenticate():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    service = build("gmail", "v1", credentials=creds)
    return service

# 이메일 본문에서 텍스트 추출
def extract_body(payload):
    if "data" in payload['body']:
        data = payload['body']['data']
        return base64.urlsafe_b64decode(data.encode("UTF-8")).decode("utf-8")
    elif "parts" in payload:
        for part in payload['parts']:
            text = extract_body(part)
            if text:
                return text
    return ""

# 저장 함수 (Markdown)
def save_to_markdown(subject, sender, date, body):
    today = datetime.date.today()
    year = today.strftime("%Y")
    month = today.strftime("%m")
    date_str = today.strftime("%Y-%m-%d")

    safe_subject = "_".join(subject.strip().split())[:50].replace("/", "-")
    dir_path = os.path.join("docs", "articles", year, month)
    os.makedirs(dir_path, exist_ok=True)
    filename = f"{date_str}_{safe_subject}.md"
    filepath = os.path.join(dir_path, filename)

    content = f"""# {subject}

**보낸 사람:** {sender}  
**받은 날짜:** {date}  

## 본문 요약
{body[:500]}...

"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

# 본문 내 키워드 검색 후 저장
def search_emails(service):
    result = service.users().messages().list(userId='me', q='newer_than:1d').execute()
    messages = result.get("messages", [])

    for msg in messages:
        msg_data = service.users().messages().get(userId="me", id=msg["id"]).execute()
        headers = msg_data["payload"]["headers"]
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
        sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown")
        date = next((h["value"] for h in headers if h["name"] == "Date"), "")

        body = extract_body(msg_data["payload"])

        if any(keyword.lower() in subject.lower() or keyword.lower() in body.lower() for keyword in KEYWORDS):
            print(f"✅ 저장됨: {subject}")
            save_to_markdown(subject, sender, date, body)
        else:
            print(f"⏭️ 필터 제외: {subject}")

if __name__ == "__main__":
    service = gmail_authenticate()
    search_emails(service)
