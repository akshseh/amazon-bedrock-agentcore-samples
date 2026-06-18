"""Seed sample emails into the S3 inbox bucket."""
import json, os, sys
import boto3

def get_bucket(region):
    cf = boto3.client("cloudformation", region_name=region)
    try:
        resp = cf.describe_stacks(StackName="AgentCore-InboxAgent-dev")
        for out in resp["Stacks"][0].get("Outputs", []):
            if out["OutputKey"] == "InboxBucket":
                return out["OutputValue"]
    except Exception:
        pass
    account = boto3.client("sts", region_name=region).get_caller_identity()["Account"]
    return f"inbox-agent-{account}-{region}"

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", default="us-west-2")
    args = parser.parse_args()
    bucket = get_bucket(args.region)
    s3 = boto3.client("s3", region_name=args.region)
    seed_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "seed-data", "emails"))
    count = 0
    for f in sorted(os.listdir(seed_dir)):
        if not f.endswith(".json"):
            continue
        path = os.path.join(seed_dir, f)
        s3.put_object(Bucket=bucket, Key=f"inbox/{f}", Body=open(path).read(), ContentType="application/json")
        print(f"  ✓ {f} → s3://{bucket}/inbox/{f}")
        count += 1
    print(f"\nSeeded {count} emails.")

if __name__ == "__main__":
    main()
