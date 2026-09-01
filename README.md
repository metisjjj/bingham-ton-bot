# bingham-ton-bot

A Reddit bot that watches r/hikingcny's comment stream and gently corrects
people who misspell "Binghamton" as "Binghampton".

## Setup

1. Create a Reddit "script" app at https://www.reddit.com/prefs/apps to get a
   client ID and secret.
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `praw.ini` file in the project root (it's gitignored, never
   commit it) with a `[bot1]` section:
   ```ini
   [bot1]
   client_id=YOUR_CLIENT_ID
   client_secret=YOUR_CLIENT_SECRET
   username=YOUR_BOT_USERNAME
   password=YOUR_BOT_PASSWORD
   user_agent=bingham-ton-bot by u/YOUR_USERNAME
   ```

## Running

```
python bingham-ton-bot.py
```

The bot keeps a small `responded-to-posts.sqlite3` file (gitignored) so it
won't reply twice to the same comment across restarts. On first run (or
after being down for a while) it skips the stream's backlog instead of
replying to old comments all at once.

If the connection to Reddit drops, it logs a warning and retries after a
short delay rather than exiting. To run it unattended, use a process
supervisor (systemd, supervisord, a Docker restart policy, etc.) as a
second layer of restart protection.

## Misspelling survey (read-only)

`misspelling-survey.py` uses the same `praw.ini` credentials to watch
r/all for the same misspelling, purely for measurement — it never
replies. Each sighting (subreddit, permalink, timestamp, a short text
snippet around the match) is logged to `misspelling-sightings.sqlite3`
(gitignored).

```
python misspelling-survey.py            # run the collector
python misspelling-survey.py --report   # print counts by subreddit
```

Let it run for a while, then use `--report` to see which subreddits the
misspelling shows up in most.
