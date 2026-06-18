"""Lambda handler: unsubscribe — Suppress future emails from a sender."""
import json, logging, os
from datetime import datetime, timezone
import boto3

logger = logging.getLogger()
logger.setLevel("INFO")
SUPPRESSIONS_TABLE = os.environ.get("SUPPRESSIONS_TABLE", "")
_ddb = boto3.resource("dynamodb").Table(SUPPRESSIONS_TABLE) if SUPPRESSIONS_TABLE else None


def handler(event, context):
    logger.info("unsubscribe invoked: %s", json.dumps(event, default=str))
    sender_address = event.get("sender_address", "").strip().lower()
    if not sender_address:
        return {"error": "sender_address is required"}
    if "@" not in sender_address:
        return {"error": f"Invalid email address: {sender_address}"}
    user_id = event.get("user_id", "default-user").strip()
    reason = event.get("reason", "junk").strip()
    if not _ddb or not SUPPRESSIONS_TABLE:
        return {"error": "SUPPRESSIONS_TABLE not configured"}
    try:
        _ddb.put_item(Item={"user_id": user_id, "sender_address": sender_address, "reason": reason, "suppressed_at": datetime.now(timezone.utc).isoformat()})
        return {"sender_address": sender_address, "action": "unsubscribed", "reason": reason}
    except Exception as exc:
        logger.exception("DDB put failed")
        return {"error": f"Failed to unsubscribe: {type(exc).__name__}"}
