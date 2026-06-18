"""Lambda handler: draft-reply — Save draft to DDB + Gmail Drafts folder."""
import base64, json, logging, os, uuid
from datetime import datetime, timezone
from email.mime.text import MIMEText
import boto3

logger = logging.getLogger()
logger.setLevel("INFO")
DRAFTS_TABLE = os.environ.get("DRAFTS_TABLE", "")
GMAIL_SECRETS_ARN = os.environ.get("GMAIL_SECRETS_ARN", "")
_ddb = boto3.resource("dynamodb").Table(DRAFTS_TABLE) if DRAFTS_TABLE else None
_secrets = boto3.client("secretsmanager") if GMAIL_SECRETS_ARN else None


def _create_gmail_draft(to_address, subject, body, in_reply_to):
    if not GMAIL_SECRETS_ARN or not _secrets:
        return {"gmail_draft_id": None}
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError:
        return {"gmail_draft_id": None}
    try:
        resp = _secrets.get_secret_value(SecretId=GMAIL_SECRETS_ARN)
        token_data = json.loads(resp["SecretString"])
        creds = Credentials(token=token_data.get("token"), refresh_token=token_data["refresh_token"],
                            token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
                            client_id=token_data["client_id"], client_secret=token_data["client_secret"])
        service = build("gmail", "v1", credentials=creds)
        message = MIMEText(body)
        message["to"] = to_address
        message["subject"] = subject
        if in_reply_to:
            message["In-Reply-To"] = in_reply_to
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
        draft = service.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
        return {"gmail_draft_id": draft.get("id", "")}
    except Exception as exc:
        logger.warning("Gmail draft failed (non-fatal): %s", exc)
        return {"gmail_draft_id": None}


def handler(event, context):
    logger.info("draft-reply invoked: %s", json.dumps(event, default=str))
    to_address = event.get("to_address", "").strip()
    if not to_address:
        return {"error": "to_address is required"}
    subject = event.get("subject", "").strip()
    if not subject:
        return {"error": "subject is required"}
    body = event.get("body", "").strip()
    if not body:
        return {"error": "body is required"}
    if len(body) > 10000:
        return {"error": "body too long (max 10000 chars)"}
    user_id = event.get("user_id", "default-user").strip()
    in_reply_to = event.get("in_reply_to", "")
    if not _ddb or not DRAFTS_TABLE:
        return {"error": "DRAFTS_TABLE not configured"}
    draft_id = f"DRAFT-{uuid.uuid4().hex[:8].upper()}"
    item = {"draft_id": draft_id, "user_id": user_id, "to_address": to_address, "subject": subject,
            "body": body, "in_reply_to": in_reply_to, "status": "draft", "created_at": datetime.now(timezone.utc).isoformat()}
    try:
        _ddb.put_item(Item=item)
    except Exception as exc:
        logger.exception("DDB put failed")
        return {"error": f"Failed to save draft: {type(exc).__name__}"}
    gmail_result = _create_gmail_draft(to_address, subject, body, in_reply_to)
    result = {"draft_id": draft_id, "to_address": to_address, "subject": subject, "status": "draft"}
    if gmail_result.get("gmail_draft_id"):
        result["gmail_draft_id"] = gmail_result["gmail_draft_id"]
        result["gmail_status"] = "created in Drafts folder"
    else:
        result["gmail_status"] = "DDB only (Gmail not configured)"
    return result
