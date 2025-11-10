import os
from dotenv import load_dotenv
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from source import models

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

client_config = {
    "web": {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://127.0.0.1:8000/auth/callback"],
    }
}

# FIXED: Use explicit scope URLs and ensure Gmail scope is included
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',  # MUST be first
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/userinfo.email',
    'openid',
]

REDIRECT_URI = "http://127.0.0.1:8000/auth/callback"

def create_oauth_flow():
    """
    Creates an OAuth2 flow for Google authentication.
    """
    flow = Flow.from_client_config(
        client_config=client_config,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    
    return flow

def get_google_user_info(credentials):
    """
    Uses the provided credentials to fetch users profile information.
    """
    user_info_service = build('oauth2', 'v2', credentials=credentials)
    user_info = user_info_service.userinfo().get().execute()
    return user_info

def rebuild_credentials(user_token: models.UserToken) -> Credentials:
    """
    Rebuilds a Google Credentials object from the token data stored in our database.
    """
    return Credentials(
        token=user_token.access_token,
        refresh_token=user_token.refresh_token,
        token_uri=client_config['web']['token_uri'],
        client_id=client_config['web']['client_id'],
        client_secret=client_config['web']['client_secret'],
        scopes=SCOPES  # Use the same scopes
    )