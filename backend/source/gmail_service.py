import base64
from email import message_from_bytes
from sqlite3 import DateFromTicks
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from datetime import datetime

def get_gmail_service(credentials:Credentials):
    """
        Create and returns a Gmail API service object.
    """
    return build('gmail', 'v1', credentials=credentials)

def fetch_email_list(service, max_results=20):
    """
    Fetches a list of email message IDs from the users inbox
    """
    results = service.users().messages().list(userId='me', maxResults=max_results).execute()
    messages = results.get('messages', [])
    return messages

def fetch_email_details(service, message_id:str):
    """Fetches the full details of a single email message"""
    return service.users().messages().get(userId='me', id=message_id, format='raw').execute()

def parse_email(raw_email:dict)->dict|None:
    """
    Parses the raw email data to extract key information like sender, subject, date, and body.
    """
    if 'raw' not in raw_email:
        return None
    
    msg_str = base64.urlsafe_b64decode(raw_email['raw'].encode('ASCII'))
    mime_msg = message_from_bytes(msg_str)

    subject = mime_msg['subject']
    sender = mime_msg['from']

    date_str = mime_msg['date']
    try:
        received__at = datetime.strptime(date_str, '%a, %d, %b, %Y, %H:%M:%S %z (%Z)')
    except ValueError:
        try:
            received__at = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z')
        except ValueError:
            received__at = None
    
    body = ""
    if mime_msg.is_multipart():
        for part in mime_msg.walk():
            ctype = part.get_content_type()
            cdispo = str(part.get('Content-Disposition'))
            if ctype == 'text/plain' and 'attachment' not in cdispo:
                body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                break
    else:
        body = mime_msg.get_payload(decode=True).decode('utf-8', errors='ignore')
    
    return {
        "message_id" : raw_email['id'],
        "subject" : subject,
        "sender" : sender,
        "body" : body,
        "received_at" : received__at
    }