"""Lambda handler: save-task — Persist a to-do item."""
import json, logging, os, uuid
from datetime import datetime, timezone
import boto3

logger = logging.getLogger()
logger.setLevel("INFO")
TASKS_TABLE = os.environ.get("TASKS_TABLE", "")
_ddb = boto3.resource("dynamodb").Table(TASKS_TABLE) if TASKS_TABLE else None


def handler(event, context):
    logger.info("save-task invoked: %s", json.dumps(event, default=str))
    title = event.get("title", "").strip()
    if not title:
        return {"error": "title is required"}
    if len(title) > 500:
        return {"error": "title too long (max 500)"}
    user_id = event.get("user_id", "default-user").strip()
    due_date = event.get("due_date", "")
    source_email = event.get("source_email", "")
    priority = event.get("priority", "MEDIUM").upper()
    if priority not in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
        return {"error": f"Invalid priority: {priority}"}
    if not _ddb or not TASKS_TABLE:
        return {"error": "TASKS_TABLE not configured"}
    task_id = f"TASK-{uuid.uuid4().hex[:8].upper()}"
    item = {"task_id": task_id, "user_id": user_id, "title": title, "status": "pending",
            "priority": priority, "source_email": source_email, "created_at": datetime.now(timezone.utc).isoformat()}
    if due_date:
        item["due_date"] = due_date
    try:
        _ddb.put_item(Item=item)
        return {"task_id": task_id, "title": title, "status": "pending", "priority": priority}
    except Exception as exc:
        logger.exception("DDB put failed")
        return {"error": f"Failed to save task: {type(exc).__name__}"}
