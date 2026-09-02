"""Print sighting counts by subreddit from the deployed DynamoDB table.

Run locally with AWS credentials configured (same account the stack was
deployed to):

    python report.py --table <TableName from `sam deploy` output>
"""
import argparse
import collections

import boto3


def report(table_name):
    table = boto3.resource("dynamodb").Table(table_name)
    counts = collections.Counter()
    total = 0

    scan_kwargs = {}
    while True:
        resp = table.scan(**scan_kwargs)
        for item in resp["Items"]:
            if not item["pk"].startswith("sighting#"):
                continue
            counts[item["subreddit"]] += 1
            total += 1
        if "LastEvaluatedKey" not in resp:
            break
        scan_kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]

    print(f"Total sightings: {total}\n")
    print(f"{'count':>6}  subreddit")
    for subreddit, count in counts.most_common():
        print(f"{count:>6}  r/{subreddit}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table", required=True, help="DynamoDB table name from the stack output")
    args = parser.parse_args()
    report(args.table)
