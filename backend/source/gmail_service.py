import base64
from email import message_from_bytes
from email.header import decode_header
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from datetime import datetime

def get_gmail_service(credentials: Credentials):
    """
    Creates and returns a Gmail API service object.
    """
    return build('gmail', 'v1', credentials=credentials)


def fetch_email_list(service, max_results=20):
    """
    Fetches a list of email message IDs from the user's inbox.
    """
    results = service.users().messages().list(userId='me', maxResults=max_results).execute()
    messages = results.get('messages', [])
    return messages


def fetch_email_details(service, message_id: str):
    """
    Fetches the full details of a single email message.
    """
    return service.users().messages().get(userId='me', id=message_id, format='raw').execute()


def decode_mime_words(s: str) -> str:
    """
    Decodes MIME encoded words (RFC 2047) safely.
    """
    if not s:
        return ""
    parts = decode_header(s)
    decoded = []
    for text, charset in parts:
        if isinstance(text, bytes):
            decoded.append(text.decode(charset or "utf-8", errors="ignore"))
        else:
            decoded.append(text)
    return " ".join(decoded).strip()


def parse_email(raw_email: dict) -> dict | None:
    """
    Parses the raw email data to extract key information like sender, subject, date, and body.
    """
    if "raw" not in raw_email:
        return None

    msg_str = base64.urlsafe_b64decode(raw_email["raw"].encode("ASCII"))
    mime_msg = message_from_bytes(msg_str)

    # Decode subject and sender
    subject = decode_mime_words(mime_msg["subject"]) or "No Subject"
    sender_raw = mime_msg["from"]
    sender = decode_mime_words(sender_raw.split("<")[0].strip()) if sender_raw else "Unknown Sender"

    # Parse date with fallback
    date_str = mime_msg["date"]
    received_at = None
    if date_str:
        for fmt in [
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S %z (%Z)",
            "%d %b %Y %H:%M:%S %z",
        ]:
            try:
                received_at = datetime.strptime(date_str[:len(fmt)], fmt)
                break
            except Exception:
                continue

    # Fallback to Gmail internalDate
    if not received_at and "internalDate" in raw_email:
        try:
            ts = int(raw_email["internalDate"]) // 1000
            received_at = datetime.utcfromtimestamp(ts)
        except Exception:
            pass

    # Extract body
    body = ""
    if mime_msg.is_multipart():
        for part in mime_msg.walk():
            ctype = part.get_content_type()
            cdispo = str(part.get("Content-Disposition"))
            if ctype == "text/plain" and "attachment" not in cdispo:
                body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                break
    else:
        try:
            body = mime_msg.get_payload(decode=True).decode("utf-8", errors="ignore")
        except Exception:
            body = ""

    return {
        "message_id": raw_email.get("id"),
        "subject": subject,
        "sender": sender,
        "body": body.strip(),
        "received_at": received_at,  # ✅ keep as datetime for DB
        "priority": 0,
        "action": "No Action Needed",
        "summary": "",
    }
