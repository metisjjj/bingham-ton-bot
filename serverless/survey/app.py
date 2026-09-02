"""Lambda handler: polls r/all for the 'Binghampton' misspelling.

Triggered on a schedule (see ../template.yaml). Each run pages back through
Reddit's site-wide "new comments" listing until it reaches the last comment
seen on the previous run (tracked in DynamoDB), so it picks up everything
new since last time rather than just a fixed top-100 snapshot. Never
replies to anything - read-only, logging only.
"""
import logging
import os
import re
import time
from decimal import Decimal

import boto3
import praw

TABLE_NAME = os.environ["TABLE_NAME"]
MISSPELLING_PATTERN = re.compile(r"\bbinghampton\b", re.IGNORECASE)
CONTEXT_CHARS = 40
MAX_ITEMS_PER_RUN = 1000  # safety cap: ~10 API calls at 100 items/page

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

table = boto3.resource("dynamodb").Table(TABLE_NAME)


def reddit_client():
    return praw.Reddit(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        user_agent=os.environ.get("REDDIT_USER_AGENT", "misspelling-survey-lambda/1.0"),
    )


def get_cursor():
    item = table.get_item(Key={"pk": "state"}).get("Item")
    return item["last_seen_fullname"] if item else None


def set_cursor(fullname):
    table.put_item(Item={"pk": "state", "last_seen_fullname": fullname, "last_run": int(time.time())})


def extract_snippet(body, match):
    start = max(0, match.start() - CONTEXT_CHARS)
    end = min(len(body), match.end() + CONTEXT_CHARS)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(body) else ""
    return prefix + body[start:end].replace("\n", " ") + suffix


def log_sighting(comment, match):
    table.put_item(
        Item={
            "pk": f"sighting#{comment.id}",
            "comment_id": comment.id,
            "subreddit": str(comment.subreddit),
            "created_utc": Decimal(str(comment.created_utc)),
            "permalink": "https://reddit.com" + comment.permalink,
            "snippet": extract_snippet(comment.body, match),
        }
    )


def handler(event, context):
    reddit = reddit_client()
    last_seen = get_cursor()

    newest_fullname = None
    scanned = 0
    hits = 0

    for comment in reddit.subreddit("all").comments(limit=MAX_ITEMS_PER_RUN):
        if newest_fullname is None:
            newest_fullname = comment.fullname
        if last_seen and comment.fullname == last_seen:
            break
        scanned += 1
        match = MISSPELLING_PATTERN.search(comment.body)
        if match:
            log_sighting(comment, match)
            hits += 1

    if newest_fullname:
        set_cursor(newest_fullname)

    log.info("Scanned %d new comments, logged %d sightings", scanned, hits)
    return {"scanned": scanned, "hits": hits}
