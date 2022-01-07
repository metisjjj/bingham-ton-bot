import praw
import re
import os
import json

r = praw.Reddit('bot1')

historyFile = 'ids-of-responded-to-posts.txt'

f = open(historyFile, 'a') # Create file if it doesn't already exist

f = open(historyFile, 'r+') # Open in read/write mode

IDs = f.readlines()

mdGentleReminder = 'Hi there! Binghamton, New York was [named for William Bingham](https://en.wikipedia.org/wiki/Binghamton,_New_York#Early_settlement), a wealthy land investor. The name of the city is often misspelled to include a "p", likely because of confusion with other place names - particularly on New York\'s Long Island - that include the English place name "Hampton".  \n  \n^I ^am ^a ^bot.'

subreddit = r.subreddit("hikingcny")

for comment in subreddit.stream.comments():
	if str(comment.id) + '\n' not in IDs:
		if re.search("binghampton", comment.body, re.IGNORECASE):
			comment.reply(mdGentleReminder)
			print("Bot replying to: ", comment.body)
		else:
			print("Bot NOT replying to: ", comment.id)
		f.write(comment.id + '\n')

f.close()
