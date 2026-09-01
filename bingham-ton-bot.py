import logging
import re
import sqlite3
import time

import prawcore
import praw

SITE_NAME = "bot1"
SUBREDDIT_NAME = "hikingcny"
STATE_DB = "responded-to-posts.sqlite3"
MISSPELLING_PATTERN = re.compile(r"\bbinghampton\b", re.IGNORECASE)
REPLY_TEXT = (
    'Hi there! Binghamton, New York was [named for William Bingham]'
    '(https://en.wikipedia.org/wiki/Binghamton,_New_York#Early_settlement), '
    'a wealthy land investor. The name of the city is often misspelled to '
    'include a "p", likely because of confusion with other place names - '
    'particularly on New York\'s Long Island - that include the English '
    'place name "Hampton".  \n  \n^I ^am ^a ^bot.'
)
RECONNECT_DELAY_SECONDS = 30

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("bingham-ton-bot")


def init_state_db(path):
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS responded_comments (comment_id TEXT PRIMARY KEY)"
    )
    conn.commit()
    return conn


def already_responded(conn, comment_id):
    row = conn.execute(
        "SELECT 1 FROM responded_comments WHERE comment_id = ?", (comment_id,)
    ).fetchone()
    return row is not None


def mark_responded(conn, comment_id):
    conn.execute(
        "INSERT OR IGNORE INTO responded_comments (comment_id) VALUES (?)",
        (comment_id,),
    )
    conn.commit()


def handle_comment(conn, comment):
    if already_responded(conn, comment.id):
        return
    if not MISSPELLING_PATTERN.search(comment.body):
        return
    try:
        comment.reply(REPLY_TEXT)
        log.info("Replied to comment %s", comment.id)
    except praw.exceptions.RedditAPIException as e:
        log.warning("Reddit API rejected reply to %s: %s", comment.id, e)
    except prawcore.exceptions.Forbidden:
        log.warning("Forbidden to reply to comment %s (banned/removed?)", comment.id)
        return
    except (prawcore.exceptions.RequestException, prawcore.exceptions.ServerError) as e:
        log.warning("Transient error replying to %s: %s", comment.id, e)
        return
    mark_responded(conn, comment.id)


def run():
    reddit = praw.Reddit(SITE_NAME)
    subreddit = reddit.subreddit(SUBREDDIT_NAME)
    conn = init_state_db(STATE_DB)

    log.info("Watching r/%s for misspellings of Binghamton", SUBREDDIT_NAME)
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


if __name__ == "__main__":
    run()
