from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import imaplib
import email
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()  # load .env file for credentials

app = FastAPI(title="Personal Mail Filter")

# Keyword store (dynamic)
keywords: List[str] = ["B.Tech cse","B.Tech computer science","all B.Tech","2026 Batch","B.Tech"]

# Load email credentials from .env
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("APP_PASSWORD")
IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com")
IMAP_FOLDER = os.getenv("IMAP_FOLDER", "INBOX")
MAX_EMAILS = int(os.getenv("MAX_EMAILS", 50))

# Pydantic model for API requests
class KeywordRequest(BaseModel):
    keyword: str

def fetch_emails():
    """Fetch unseen emails from IMAP inbox."""
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL, PASSWORD)
    mail.select(IMAP_FOLDER)

    # Fetch unseen emails
    _, search_data = mail.search(None, "UNSEEN")
    mail_ids = search_data[0].split()
    messages = []

    # Limit to latest MAX_EMAILS
    for num in mail_ids[-MAX_EMAILS:]:
        _, data = mail.fetch(num, "(RFC822)")
        raw_email = data[0][1]
        msg = email.message_from_bytes(raw_email)

        subject = msg["subject"] or ""
        sender = msg["from"] or ""
        body = ""

        # Extract plain text body
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode(errors="ignore")
                    break
        else:
            body = msg.get_payload(decode=True).decode(errors="ignore")

        messages.append({
            "subject": subject,
            "from": sender,
            "body": body,
            "timestamp": datetime.utcnow().isoformat()  
        })

    mail.logout()
    return messages

def is_relevant(mail: dict) -> bool:
    """Check if email matches keywords."""
    if keywords:
        haystack = f"{mail['subject']}\n{mail['body']}".lower()
        return any(kw.lower() in haystack for kw in keywords)
    return True

# -------------------- API ENDPOINTS --------------------

@app.get("/emails")
def get_filtered_emails():
    """Fetch filtered unseen emails."""
    mails = fetch_emails()
    filtered = [m for m in mails if is_relevant(m)]
    return {"keywords": keywords, "emails": filtered}

# Keywords management
@app.get("/keywords")
def list_keywords():
    return {"keywords": keywords}

@app.post("/keywords")
def add_keyword(req: KeywordRequest):
    if req.keyword not in keywords:
        keywords.append(req.keyword)
    return {"keywords": keywords}

@app.delete("/keywords")
def remove_keyword(req: KeywordRequest):
    if req.keyword in keywords:
        keywords.remove(req.keyword)
    return {"keywords": keywords}
