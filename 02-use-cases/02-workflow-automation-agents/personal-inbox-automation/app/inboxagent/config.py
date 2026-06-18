"""Centralized configuration. ALL env var reads live here — nowhere else."""
import os

REGION = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION", "us-west-2")
AGENT_MODEL_ID = os.getenv("AGENT_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
FAST_MODEL_ID = os.getenv("FAST_MODEL_ID", "us.anthropic.claude-haiku-4-5-20251001-v1:0")
MEMORY_ID = os.getenv("MEMORY_ID") or os.getenv("MEMORY_INBOXAGENTMEMORY_ID", "")
GATEWAY_URL = os.getenv("AGENTCORE_GATEWAY_INBOXGATEWAY_URL") or os.getenv("GATEWAY_URL", "")
INBOX_BUCKET = os.getenv("INBOX_BUCKET", "")
TASKS_TABLE = os.getenv("TASKS_TABLE", "")
DRAFTS_TABLE = os.getenv("DRAFTS_TABLE", "")
SUPPRESSIONS_TABLE = os.getenv("SUPPRESSIONS_TABLE", "")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
