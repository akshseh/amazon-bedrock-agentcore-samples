"""Personal Inbox Automation Agent — AgentCore Runtime entrypoint."""
import json
import logging
import uuid
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from config import LOG_LEVEL
from memory.session import get_memory_session_manager
from model.load import load_model
from mcp_client.client import get_mcp_client

app = BedrockAgentCoreApp()
log = app.logger
logging.getLogger().setLevel(LOG_LEVEL)

SYSTEM_PROMPT = """You are a Personal Inbox Assistant that processes incoming emails.

Your job:
1. READ the email using the get-email tool (pass the message_id).
2. TRIAGE — classify: IMPORTANT, REPLY_NEEDED, TODO, or JUNK.
3. ACT based on classification:
   - IMPORTANT: Summarize key points. Extract action items with save-task.
   - REPLY_NEEDED: Draft a professional reply using draft-reply.
   - TODO: Extract each action item with save-task.
   - JUNK: Use unsubscribe to suppress future emails from this sender.
4. RESPOND with a structured summary of what you did.

Rules:
- Always read the email first before deciding.
- Be conservative with JUNK — only classify clearly marketing/spam.
- When drafting replies, match the tone of the original sender.
- Extract concrete, actionable tasks — skip vague items.
"""


def _build_prompt(payload: dict) -> str:
    if "prompt" in payload and "message_id" not in payload:
        return payload["prompt"]
    message_id = payload.get("message_id", "")
    sender = payload.get("sender", "unknown")
    subject = payload.get("subject", "(no subject)")
    return f"New email arrived.\nMessage ID: {message_id}\nFrom: {sender}\nSubject: {subject}\n\nPlease triage this email and take appropriate action."


@app.entrypoint
async def invoke(payload, context):
    log.info("Inbox Agent invoked")
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            payload = {"prompt": payload}
    if "prompt" in payload and "message_id" not in payload:
        prompt_value = payload["prompt"]
        if isinstance(prompt_value, str):
            try:
                parsed = json.loads(prompt_value)
                if isinstance(parsed, dict) and "message_id" in parsed:
                    payload = parsed
            except (json.JSONDecodeError, TypeError):
                pass

    user_id = payload.get("user_id", "default-user")
    message_id = payload.get("message_id", uuid.uuid4().hex[:8])
    priority = payload.get("priority", "MEDIUM")
    session_id = f"inbox-{user_id}-{message_id}"
    prompt = _build_prompt(payload)

    session_manager = None
    try:
        session_manager = get_memory_session_manager(session_id, user_id)
    except Exception as exc:
        log.warning("Memory unavailable: %s", exc)

    mcp_client = get_mcp_client()
    tools = [mcp_client] if mcp_client else []

    try:
        agent = Agent(model=load_model(priority), session_manager=session_manager, system_prompt=SYSTEM_PROMPT, tools=tools)
    except Exception as exc:
        log.error("Agent init failed: %s", exc)
        yield json.dumps({"error": str(exc)})
        return

    try:
        stream = agent.stream_async(prompt)
        async for event in stream:
            if "data" in event and isinstance(event["data"], str):
                yield event["data"]
    except Exception as exc:
        log.exception("Agent execution failed")
        yield json.dumps({"error": str(exc)})


if __name__ == "__main__":
    app.run()
