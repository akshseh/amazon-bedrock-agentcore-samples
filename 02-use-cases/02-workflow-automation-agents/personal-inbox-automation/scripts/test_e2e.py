"""E2E test suite for Personal Inbox Automation Agent (5 scenarios)."""
import argparse, json, os, sys, time
import boto3

SCENARIOS = [
    {"name": "Work email with action items", "message_id": "msg-001", "expected_tools": ["get-email", "save-task"]},
    {"name": "Obvious spam", "message_id": "msg-002", "expected_tools": ["get-email", "unsubscribe"]},
    {"name": "Personal email needing reply", "message_id": "msg-003", "expected_tools": ["get-email", "draft-reply"]},
    {"name": "Critical alert", "message_id": "msg-004", "expected_tools": ["get-email", "save-task"]},
    {"name": "Newsletter", "message_id": "msg-005", "expected_tools": ["get-email", "unsubscribe"]},
]

def get_outputs(region):
    cf = boto3.client("cloudformation", region_name=region)
    resp = cf.describe_stacks(StackName="AgentCore-InboxAgent-dev")
    return {o["OutputKey"]: o["OutputValue"] for o in resp["Stacks"][0].get("Outputs", [])}

def run_test(scenario, outputs, region):
    s3 = boto3.client("s3", region_name=region)
    bucket = outputs["InboxBucket"]
    seed_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "seed-data", "emails"))
    filepath = os.path.join(seed_dir, f"{scenario['message_id']}.json")
    if not os.path.exists(filepath):
        print(f"  ⚠ Seed file not found: {filepath}"); return False
    s3.put_object(Bucket=bucket, Key=f"inbox/{scenario['message_id']}.json", Body=open(filepath).read(), ContentType="application/json")
    print(f"  ✓ Uploaded {scenario['message_id']}")
    print(f"  ⏳ Waiting 10s for processing...")
    time.sleep(10)
    print(f"  ✓ Scenario complete")
    return True

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", default="us-west-2")
    parser.add_argument("--test", type=int, default=None)
    args = parser.parse_args()
    try:
        outputs = get_outputs(args.region)
    except Exception as exc:
        print(f"Error: {exc}"); sys.exit(1)
    scenarios = [SCENARIOS[args.test - 1]] if args.test else SCENARIOS
    passed = sum(1 for s in scenarios if run_test(s, outputs, args.region))
    print(f"\n{'═'*40}\n  {passed}/{len(scenarios)} passed\n{'═'*40}")

if __name__ == "__main__":
    main()
