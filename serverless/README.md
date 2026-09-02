# Serverless survey (AWS)

Same purpose as `../misspelling-survey.py` - logging sightings of the
"Binghampton" misspelling across r/all, never replying - but built to run
on AWS Lambda + DynamoDB instead of a machine you keep on. No server to
manage, and it should cost effectively $0/month at hobby volume.

## Why this looks different from the local script

A Lambda function can't hold the always-on connection PRAW's
`stream.comments()` uses. Instead, `survey/app.py` runs on a schedule
(default: every minute) and each run pages backwards through Reddit's
site-wide "new comments" listing until it reaches the last comment it saw
on the previous run (tracked in DynamoDB), so it's not just glancing at a
fixed top-100 snapshot. Under a sudden traffic spike it could still fall
behind within a single run - there's a safety cap of ~1000 comments
(~10 API calls) per invocation - but it should keep up under normal load.

It authenticates read-only (`client_id` + `client_secret` only, no
account username/password needed), since it never posts anything.

## Cost

- **Lambda**: 1M requests + 400,000 GB-seconds/month always free - a
  1-minute schedule is ~43,200 invocations/month, far under that.
- **DynamoDB**: the table is provisioned at 2 RCU / 2 WCU, well inside the
  25 RCU / 25 WCU / 25GB storage that's *always* free (not just a
  12-month intro offer) - as long as this is the only table using that
  allowance on the account.
- **EventBridge**: scheduled rules aren't billed separately; you only pay
  for the Lambda invocations they trigger, which are covered above.

"Effectively free" assumes a personal AWS account with headroom in those
free tiers - it's not a contractual guarantee from AWS.

## Deploy

Requires the [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
and AWS credentials configured locally. This creates real resources in
your AWS account - review the `sam deploy --guided` prompts before
confirming.

1. Create a Reddit app at https://www.reddit.com/prefs/apps (type
   "script" works fine even for read-only use) to get a client ID and
   secret.
2. From this directory:
   ```
   sam build
   sam deploy --guided
   ```
   When prompted, supply `RedditClientId` and `RedditClientSecret` as
   stack parameters (SAM stores them, not this repo).
3. Note the `TableName` and `FunctionName` from the deploy output.

## Checking results

```
python report.py --table <TableName>
```

## Tearing down

```
sam delete
```
removes the Lambda function, DynamoDB table (and its data), and the
EventBridge schedule.
