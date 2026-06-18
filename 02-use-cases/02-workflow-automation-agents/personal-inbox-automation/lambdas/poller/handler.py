"""Lambda: Gmail Poller — Fetch unread emails, upload to S3 as JSON."""
import base64, json, logging, os, re
from datetime import datetime, timezone
from email.utils import parseaddr
import boto3
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger()
logger.setLevel("INFO")
INBOX_BUCKET = os.environ.get("INBOX_BUCKET", "")
GMAIL_SECRETS_ARN = os.environ.get("GMAIL_SECRETS_ARN", "")
GMAIL_LABEL_IDS = os.environ.get("GMAIL_LABEL_IDS", "")
GMAIL_USER_EMAIL = os.environ.get("GMAIL_USER_EMAIL", "me")
MAX_MESSAGES = int(os.environ.get("MAX_MESSAGES_PER_POLL", "10"))
_s3 = boto3.client("s3")
_secrets = boto3.client("secretsmanager")


def _get_creds():
    resp = _secrets.get_secret_value(SecretId=GMAIL_SECRETS_ARN)
    td = json.loads(resp["SecretString"])
    return Credentials(token=td.get("token"), refresh_token=td["refresh_token"],
                       token_uri=td.get("token_uri", "https://oauth2.googleapis.com/token"),
                       client_id=td["client_id"], client_secret=td["client_secret"])


def _extract_body(payload):
    if payload.get("mimeType") == "text/plain" and "data" in payload.get("body", {}):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain" and "data" in part.get("body", {}):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
        if part.get("mimeType", "").startswith("multipart/"):
            r = _extract_body(part)
            if r:
                return r
    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/html" and "data" in part.get("body", {}):
            html = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
            return re.sub(r"<[^>]+>", "", html).strip()
    return "(no body)"


def _get_header(headers, name):
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def handler(event, context):
    logger.info("Gmail poller invoked")
    if not INBOX_BUCKET or not GMAIL_SECRETS_ARN:
        return {"error": "INBOX_BUCKET or GMAIL_SECRETS_ARN not configured"}
    try:
        service = build("gmail", "v1", credentials=_get_creds())
    except Exception as exc:
        return {"error": f"Gmail auth failed: {exc}"}
    label_ids = ["INBOX", "UNREAD"]
    if GMAIL_LABEL_IDS:
        label_ids.extend([lid.strip() for lid in GMAIL_LABEL_IDS.split(",") if lid.strip()])
    try:
        results = service.users().messages().list(userId=GMAIL_USER_EMAIL, labelIds=label_ids, maxResults=MAX_MESSAGES).execute()
    except Exception as exc:
        return {"error": f"Gmail list failed: {exc}"}
    messages = results.get("messages", [])
    if not messages:
        return {"processed": 0, "messages": []}
    user_id = GMAIL_USER_EMAIL if GMAIL_USER_EMAIL != "me" else "default-user"
    processed = []
    for msg_ref in messages:
        msg_id = msg_ref["id"]
        try:
            msg = service.users().messages().get(userId=GMAIL_USER_EMAIL, id=msg_id, format="full").execute()
            payload = msg.get("payload", {})
            headers = payload.get("headers", [])
            _, from_addr = parseaddr(_get_header(headers, "From"))
            body = _extract_body(payload)
            if len(body) > 15000:
                body = body[:15000] + "\n[truncated]"
            attachments = [p.get("filename") for p in payload.get("parts", []) if p.get("filename")]
            ts = datetime.fromtimestamp(int(msg.get("internalDate", "0")) / 1000, tz=timezone.utc).isoformat()
            email_json = {"message_id": msg_id, "from": from_addr or _get_header(headers, "From"),
                          "to": _get_header(headers, "To"), "subject": _get_header(headers, "Subject") or "(no subject)",
                          "body": body, "timestamp": ts, "user_id": user_id, "attachments": attachments,
                          "gmail_thread_id": msg.get("threadId", "")}
            _s3.put_object(Bucket=INBOX_BUCKET, Key=f"inbox/{msg_id}.json", Body=json.dumps(email_json), ContentType="application/json")
            processed.append({"message_id": msg_id, "subject": email_json["subject"][:80]})
        except Exception as exc:
            logger.warning("Failed to process %s: %s", msg_id, exc)
    return {"processed": len(processed), "messages": processed}
