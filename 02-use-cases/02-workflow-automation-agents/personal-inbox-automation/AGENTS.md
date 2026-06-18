# Personal Inbox Automation Agent — AI Coding Assistant Context

> **For humans:** see [README.md](./README.md).

Event-driven email inbox automation on Amazon Bedrock AgentCore. Single-agent, 5 Lambda tools via MCP Gateway (AWS_IAM). Polls Gmail via OAuth or accepts manual S3 uploads.

---

## Architecture

```
Gmail (optional) → GmailPoller Lambda (every 5 min, OAuth via Secrets Manager)
  → S3 inbox/<message_id>.json
  → EventBridge (Object Created)
    → Trigger Lambda → AgentCore Runtime
      → get-email | save-task | list-tasks | draft-reply | unsubscribe
      → Gateway (AWS_IAM, Cedar policy enforcement)
      → draft-reply also creates Gmail Drafts (never sends)
```

## Key Invariants

1. Lambda handlers return direct objects — no HTTP envelope
2. Agent controls triage classification and tool selection
3. Tool schemas in `tool-schemas/` match handler params exactly
4. Memory wraps in try/except — graceful degradation
5. AWS_IAM auth — no Cognito needed
6. Gmail integration is conditional on GMAIL_SECRETS_ARN

## Build, Test, Deploy

```bash
agentcore validate
find app/ lambdas/ scripts/ -name "*.py" -exec python3 -m py_compile {} \;
cd agentcore/cdk && npx tsc --noEmit
./scripts/deploy.sh
python3 scripts/test_e2e.py --region us-west-2
```
