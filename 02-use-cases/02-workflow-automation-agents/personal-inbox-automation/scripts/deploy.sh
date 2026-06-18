#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Personal Inbox Automation Agent — Deploy ==="
if [ -f "$PROJECT_DIR/.env" ]; then set -a; source "$PROJECT_DIR/.env"; set +a; fi
: "${CDK_DEFAULT_ACCOUNT:?Set CDK_DEFAULT_ACCOUNT in .env}"
export AWS_REGION="${AWS_REGION:-us-west-2}"

echo "  Account: $CDK_DEFAULT_ACCOUNT | Region: $AWS_REGION"
TEMPLATE="$PROJECT_DIR/agentcore/aws-targets.json.template"
TARGET="$PROJECT_DIR/agentcore/aws-targets.json"
if [ -f "$TEMPLATE" ]; then envsubst < "$TEMPLATE" > "$TARGET"; fi
cd "$PROJECT_DIR/agentcore/cdk" && npm install --silent && cd "$PROJECT_DIR"
cd "$PROJECT_DIR/app/inboxagent" && uv sync && cd "$PROJECT_DIR"
agentcore validate
agentcore deploy -y --target dev
python3 "$SCRIPT_DIR/seed.py" --region "$AWS_REGION"
echo -e "\n✓ Done! Test: python3 scripts/test_invoke.py --region $AWS_REGION"
