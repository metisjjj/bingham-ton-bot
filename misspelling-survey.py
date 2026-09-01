"""Read-only survey of r/all for the 'Binghampton' misspelling.

Logs each sighting (subreddit, permalink, timestamp, short context snippet)
to a sqlite file for later analysis. Never replies to anything.

Usage:
    python misspelling-survey.py            # run the collector
    python misspelling-survey.py --report   # print counts by subreddit
"""
import argparse
import logging
import re
import sqlite3
import time

import prawcore
import praw

SITE_NAME = "bot1"
STATE_DB = "misspelling-sightings.sqlite3"
MISSPELLING_PATTERN = re.compile(r"\bbinghampton\b", re.IGNORECASE)
CONTEXT_CHARS = 40
RECONNECT_DELAY_SECONDS = 30

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("misspelling-survey")


def init_db(path):
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sightings (
            comment_id TEXT PRIMARY KEY,
            subreddit TEXT NOT NULL,
            created_utc REAL NOT NULL,
            permalink TEXT NOT NULL,
            snippet TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def already_logged(conn, comment_id):
    row = conn.execute(
        "SELECT 1 FROM sightings WHERE comment_id = ?", (comment_id,)
    ).fetchone()
    return row is not None


def extract_snippet(body, match):
    start = max(0, match.start() - CONTEXT_CHARS)
    end = min(len(body), match.end() + CONTEXT_CHARS)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(body) else ""
    return prefix + body[start:end].replace("\n", " ") + suffix


def log_sighting(conn, comment, match):
    conn.execute(
        "INSERT OR IGNORE INTO sightings (comment_id, subreddit, created_utc, permalink, snippet) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            comment.id,
            str(comment.subreddit),
            comment.created_utc,
            "https://reddit.com" + comment.permalink,
            extract_snippet(comment.body, match),
        ),
    )
    conn.commit()


def handle_comment(conn, comment):
    if already_logged(conn, comment.id):
        return
    match = MISSPELLING_PATTERN.search(comment.body)
    if not match:
        return
    log_sighting(conn, comment, match)
    log.info("Sighting in r/%s: %s", comment.subreddit, comment.permalink)


def run():
    reddit = praw.Reddit(SITE_NAME)
    subreddit = reddit.subreddit("all")
    conn = init_db(STATE_DB)

    log.info("Surveying r/all for misspellings of Binghamton (logging only, no replies)")
    while True:
        try:
            for comment in subreddit.stream.comments(skip_existing=True):
                handle_comment(conn, comment)
        except (prawcore.exceptions.RequestException, prawcore.exceptions.ServerError) as e:
            log.warning("Lost connection to Reddit (%s); reconnecting in %ss", e, RECONNECT_DELAY_SECONDS)
            time.sleep(RECONNECT_DELAY_SECONDS)
        except KeyboardInterrupt:
            log.info("Shutting down")
            break


def report():
    conn = init_db(STATE_DB)
    total = conn.execute("SELECT COUNT(*) FROM sightings").fetchone()[0]
    print(f"Total sightings: {total}\n")
    print(f"{'count':>6}  subreddit")
    for count, subreddit in conn.execute(
        "SELECT COUNT(*), subreddit FROM sightings GROUP BY subreddit ORDER BY COUNT(*) DESC"
    ):
        print(f"{count:>6}  r/{subreddit}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="store_true", help="print counts by subreddit and exit")
    args = parser.parse_args()

    if args.report:
        report()
    else:
        run()
