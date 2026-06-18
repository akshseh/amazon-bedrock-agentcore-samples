"""Lambda handler: list-tasks — List pending tasks for a user."""
import json, logging, os
import boto3
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel("INFO")
TASKS_TABLE = os.environ.get("TASKS_TABLE", "")
_ddb = boto3.resource("dynamodb").Table(TASKS_TABLE) if TASKS_TABLE else None


def handler(event, context):
    logger.info("list-tasks invoked: %s", json.dumps(event, default=str))
    user_id = event.get("user_id", "default-user").strip()
    if not user_id:
        return {"error": "user_id is required"}
    status_filter = event.get("status", "").strip().lower()
    limit = min(int(event.get("limit", 20)), 50)
    if not _ddb or not TASKS_TABLE:
        return {"error": "TASKS_TABLE not configured"}
    try:
        kwargs = {"IndexName": "user-status-index", "KeyConditionExpression": Key("user_id").eq(user_id), "Limit": limit, "ScanIndexForward": False}
        if status_filter:
            kwargs["KeyConditionExpression"] = Key("user_id").eq(user_id) & Key("status").eq(status_filter)
        resp = _ddb.query(**kwargs)
        tasks = resp.get("Items", [])
        return {"tasks": tasks, "count": len(tasks)}
    except Exception as exc:
        logger.exception("DDB query failed")
        return {"error": f"Failed to list tasks: {type(exc).__name__}"}
