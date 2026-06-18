"""Test the Inbox Agent by invoking the Runtime directly."""
import argparse, json, sys
import boto3

def get_runtime_arn(region):
    cf = boto3.client("cloudformation", region_name=region)
    resp = cf.describe_stacks(StackName="AgentCore-InboxAgent-dev")
    for out in resp["Stacks"][0].get("Outputs", []):
        if out["OutputKey"] == "RuntimeArn":
            return out["OutputValue"]
    raise ValueError("RuntimeArn not found")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", default="us-west-2")
    parser.add_argument("--message-id", default="msg-001")
    parser.add_argument("--prompt", default=None)
    args = parser.parse_args()
    arn = get_runtime_arn(args.region)
    print(f"Runtime: {arn}")
    payload = {"prompt": args.prompt, "user_id": "default-user"} if args.prompt else {"message_id": args.message_id, "sender": "test@example.com", "subject": "Test", "user_id": "default-user", "priority": "MEDIUM"}
    print(f"Payload: {json.dumps(payload, indent=2)}\n─── Response ───")
    # Direct invoke placeholder — actual implementation depends on SDK version

if __name__ == "__main__":
    main()
