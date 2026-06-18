"""Lambda trigger: S3 email upload → AgentCore Runtime invocation (SigV4)."""
import json, logging, os
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import urllib.request

logger = logging.getLogger()
logger.setLevel("INFO")
RUNTIME_ARN = os.environ.get("RUNTIME_ARN", "")
REGION = os.environ.get("AWS_REGION", "us-west-2")
_s3 = boto3.client("s3")
_session = boto3.Session()


def _get_runtime_url():
    parts = RUNTIME_ARN.split(":")
    region = parts[3]
    runtime_id = parts[5].split("/")[1]
    return f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{runtime_id}/invoke"


def _invoke_runtime(payload):
    url = _get_runtime_url()
    body = json.dumps(payload).encode("utf-8")
    request = AWSRequest(method="POST", url=url, data=body, headers={"Content-Type": "application/json"})
    credentials = _session.get_credentials().get_frozen_credentials()
    SigV4Auth(credentials, "bedrock-agentcore", REGION).add_auth(request)
    req = urllib.request.Request(url, data=body, headers=dict(request.headers), method="POST")
    with urllib.request.urlopen(req) as resp:  # nosec B310
        return json.loads(resp.read())


def handler(event, context):
    logger.info("Trigger invoked: %s", json.dumps(event, default=str))
    if not RUNTIME_ARN:
        return {"error": "RUNTIME_ARN not set"}
    detail = event.get("detail", {})
    bucket = detail.get("bucket", {}).get("name", "")
    key = detail.get("object", {}).get("key", "")
    if not bucket or not key:
        return {"error": "Invalid event"}
    message_id = key.replace("inbox/", "").replace(".json", "")
    try:
        resp = _s3.get_object(Bucket=bucket, Key=key)
        email_data = json.loads(resp["Body"].read().decode("utf-8"))
    except Exception as exc:
        logger.exception("S3 read failed")
        return {"error": f"S3 read failed: {type(exc).__name__}"}
    runtime_payload = {"message_id": message_id, "sender": email_data.get("from", "unknown"),
                       "subject": email_data.get("subject", ""), "user_id": email_data.get("user_id", "default-user"), "priority": "MEDIUM"}
    try:
        _invoke_runtime(runtime_payload)
        return {"status": "processed", "message_id": message_id}
    except Exception as exc:
        logger.exception("Runtime invoke failed")
        return {"error": f"Runtime invoke failed: {exc}"}
