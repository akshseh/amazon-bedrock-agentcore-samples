# Personal Inbox Automation Agent

> **Sample for educational/demonstration purposes.** Showcases AgentCore Runtime, Memory, Gateway, Policy Engine, and Online Evaluation.

An AI agent that processes your Gmail inbox: triaging messages, drafting replies (saved to Drafts folder — never sent), extracting to-do items, and unsubscribing from junk.

## Quick Facts

| | |
|---|---|
| **Deploy time** | ~8 min |
| **Teardown** | `agentcore destroy --target dev --yes` |
| **Gmail integration** | Optional — works with seed data or real Gmail |

## What You'll Learn

| Capability | Demonstration |
|---|---|
| Runtime | CodeZip Python agent with streaming |
| Memory | SUMMARIZATION for sender preferences |
| Gateway | 5 Lambda tools via MCP (AWS_IAM auth) |
| Policy Engine | Cedar blocks mass-unsubscribe |
| Online Eval | Correctness + Helpfulness + ToolSelection |
| Gmail Polling | EventBridge schedule → OAuth → S3 |

## Quick Start

```bash
cp .env.example .env   # edit with your account ID
./scripts/deploy.sh

# Test with seed data
python3 scripts/test_invoke.py --region us-west-2

# Connect real Gmail (optional)
# See docs/gmail-setup.md
```

## Project Structure

```
personal-inbox-automation/
├── app/inboxagent/           # Agent runtime (main.py, config, model, memory, mcp_client)
├── agentcore/                # agentcore.json + CDK
├── lambdas/tools/            # 5 Gateway Lambda targets
├── lambdas/poller/           # Gmail API polling (Docker image)
├── lambdas/trigger/          # S3 → Runtime invocation
├── tool-schemas/             # MCP tool definitions
├── seed-data/emails/         # 5 sample emails
├── scripts/                  # deploy, seed, test, gmail_auth, lint
└── docs/                     # ARCHITECTURE.md, gmail-setup.md
```

## License

MIT-0
