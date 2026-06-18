"""Lambda handler: get-email — Retrieve email content from S3 inbox bucket."""
import json, logging, os
import boto3

logger = logging.getLogger()
logger.setLevel("INFO")
INBOX_BUCKET = os.environ.get("INBOX_BUCKET", "")
_s3 = boto3.client("s3") if INBOX_BUCKET else None


def handler(event, context):
    logger.info("get-email invoked: %s", json.dumps(event, default=str))
    message_id = event.get("message_id", "").strip()
    if not message_id:
        return {"error": "message_id is required"}
    if not _s3 or not INBOX_BUCKET:
        return {"error": "INBOX_BUCKET not configured"}
    key = f"inbox/{message_id}.json"
    try:
        resp = _s3.get_object(Bucket=INBOX_BUCKET, Key=key)
        return json.loads(resp["Body"].read().decode("utf-8"))
    except _s3.exceptions.NoSuchKey:
        return {"error": f"Email not found: {message_id}"}
    except Exception as exc:
        logger.exception("S3 read failed")
        return {"error": f"Failed to read email: {type(exc).__name__}"}
