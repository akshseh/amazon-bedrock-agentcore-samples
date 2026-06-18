# Gmail Integration Setup Guide

## Overview

This guide connects the Inbox Agent to your personal Gmail. The agent polls for unread emails every 5 minutes via OAuth 2.0, and can create draft replies in your Gmail Drafts folder. It **never sends** emails.

## Prerequisites

- Google account (personal Gmail works)
- AWS CLI configured
- Python 3.12+ installed locally (for one-time auth script)

## Step 1: Create a Google Cloud Project

1. Go to https://console.cloud.google.com/
2. Click project dropdown → **New Project**
3. Name: `Inbox Automation Agent` → Create

## Step 2: Enable the Gmail API

1. Go to **APIs & Services → Library**: https://console.cloud.google.com/apis/library
2. Search "Gmail API" → Click **Enable**

## Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services → OAuth consent screen**
2. Select **External** → Create
3. App name: `Inbox Agent`, support email: yours
4. Click **Save and Continue**
5. Scopes → Add:
   - `https://www.googleapis.com/auth/gmail.readonly`
   - `https://www.googleapis.com/auth/gmail.compose`
6. Click **Update** → Save and Continue
7. Test users → Add your Gmail address → Save

## Step 4: Create OAuth Credentials

1. Go to **APIs & Services → Credentials**
2. **Create Credentials → OAuth client ID**
3. Type: **Desktop app**, Name: `Inbox Agent CLI`
4. Download JSON → save as `credentials.json` in project root

## Step 5: Generate Refresh Token

```bash
pip install google-auth-oauthlib google-api-python-client
python3 scripts/gmail_auth.py
```

A browser opens for OAuth consent. After approving, `gmail_token.json` is saved.

## Step 6: Store in Secrets Manager

```bash
aws secretsmanager create-secret \
  --name inbox-agent/gmail-credentials \
  --secret-string file://gmail_token.json \
  --region us-west-2
```

Add the ARN to `.env`:
```
GMAIL_SECRETS_ARN=arn:aws:secretsmanager:us-west-2:123456789012:secret:inbox-agent/gmail-credentials-XyZ
```

## Step 7: Configure Labels (Optional)

Find label IDs:
```bash
python3 -c "
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
creds = Credentials.from_authorized_user_file('gmail_token.json')
service = build('gmail', 'v1', credentials=creds)
for l in service.users().labels().list(userId='me').execute().get('labels', []):
    print(f'{l[\"name\"]:<30} {l[\"id\"]}')
"
```

Set in `.env`: `GMAIL_LABEL_IDS=Label_123,IMPORTANT`

If empty → processes all unread in INBOX.

## Scopes

| Scope | What it does | What it CANNOT do |
|---|---|---|
| `gmail.readonly` | Read messages, list labels | Modify or delete |
| `gmail.compose` | Create drafts | **Send emails** (needs gmail.send) |

## Security

- `credentials.json` and `gmail_token.json` are gitignored
- Refresh token is encrypted at rest in Secrets Manager
- Agent can only read + create drafts — cannot send
- Revoke anytime: https://myaccount.google.com/permissions

## Troubleshooting

| Error | Fix |
|---|---|
| "Access blocked" | Add yourself as test user in OAuth consent screen |
| "Token expired" | Re-run `scripts/gmail_auth.py`, update secret |
| "Insufficient permissions" | Check scopes match, re-auth |
| "redirect_uri_mismatch" | Use Desktop app type, not Web application |
