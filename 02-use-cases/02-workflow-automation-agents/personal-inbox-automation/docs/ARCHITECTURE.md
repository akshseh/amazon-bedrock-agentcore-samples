# Architecture — Personal Inbox Automation Agent

## Data Flow (5-Step Pattern)

```
① TRIGGER: Email → S3 (via Gmail Poller or manual upload)
② ENRICH: Agent calls get-email to read full content + Memory retrieves sender history
③ REASON: LLM classifies → IMPORTANT | REPLY_NEEDED | TODO | JUNK
④ ACT: save-task / draft-reply (DDB + Gmail Drafts) / unsubscribe
⑤ EMIT: Streams structured summary back to caller; Memory persists session
```

## Auth: AWS_IAM (SigV4) — Zero Cognito

```
Trigger Lambda ──SigV4──→ Runtime ──SigV4──→ Gateway ──IAM──→ Lambda Tools
```

## Gmail Polling (Conditional)

When `GMAIL_SECRETS_ARN` is set:
- EventBridge schedule fires every 5 min
- GmailPoller Lambda reads refresh token from Secrets Manager
- Calls Gmail API to fetch unread messages (filtered by label if configured)
- Converts to JSON and uploads to S3 inbox/ prefix
- Existing EventBridge rule fires → Agent processes

## DynamoDB Schema

- **InboxAgent-Tasks**: PK=task_id, GSI=user-status-index (user_id + status)
- **InboxAgent-Drafts**: PK=draft_id
- **InboxAgent-Suppressions**: PK=user_id, SK=sender_address
