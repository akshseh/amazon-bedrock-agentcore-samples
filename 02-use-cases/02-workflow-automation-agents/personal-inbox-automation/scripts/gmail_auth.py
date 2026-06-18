"""One-time OAuth flow to generate Gmail refresh token.
Usage: pip install google-auth-oauthlib google-api-python-client && python3 scripts/gmail_auth.py
"""
import json, os, sys
try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("Install: pip install google-auth-oauthlib google-api-python-client"); sys.exit(1)

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/gmail.compose"]
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_FILE = os.path.join(PROJECT_DIR, "credentials.json")
TOKEN_FILE = os.path.join(PROJECT_DIR, "gmail_token.json")

def main():
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"Error: {CREDENTIALS_FILE} not found.\nSee docs/gmail-setup.md"); sys.exit(1)
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    creds = flow.run_local_server(port=8090, open_browser=True)
    token_data = {"token": creds.token, "refresh_token": creds.refresh_token, "token_uri": creds.token_uri,
                  "client_id": creds.client_id, "client_secret": creds.client_secret, "scopes": list(creds.scopes or SCOPES)}
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)
    print(f"\n✓ Saved to {TOKEN_FILE}")
    print(f"\nNext: aws secretsmanager create-secret --name inbox-agent/gmail-credentials --secret-string file://{TOKEN_FILE} --region us-west-2")

if __name__ == "__main__":
    main()
