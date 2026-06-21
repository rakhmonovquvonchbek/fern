from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from fern.config import CREDENTIALS_PATH, SCOPES, TOKEN_PATH


def get_gmail_service():
    """Authenticate and return a Gmail API service client."""
    if not CREDENTIALS_PATH.exists():
        raise FileNotFoundError(
            f"Missing credentials at {CREDENTIALS_PATH}. Download OAuth credentials "
            "from Google Cloud Console and save as ~/.fern/credentials.json"
        )

    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_PATH), SCOPES
            )
            print(
                "Opening browser for Google sign-in. "
                "If it does not open, copy the URL printed below into your browser.",
                flush=True,
            )
            creds = flow.run_local_server(port=8080, open_browser=True, prompt="consent")
            print("Google sign-in complete.", flush=True)
        TOKEN_PATH.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds)
