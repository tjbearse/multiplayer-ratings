import dataclasses
from pathlib import Path
from trueskill import Rating
import argparse
import csv
import fileinput
import io
import sys
import os
from typing import Iterator

from iohelp import debug, openOrDefault
from freeForAll import PlayerRatings, GameResult, rateFFA

def ratingsFromCSV(f) -> PlayerRatings:
	return {
		row['Player']: Rating(row['Mu'], row['Sigma'])
		for row in csv.DictReader(f)
	}
def ratingsToCSV(f, ratings:PlayerRatings):
	writer = csv.DictWriter(f, fieldnames=['Player', 'Mu', 'Sigma'])
	writer.writeheader()
	writer.writerows((
		{ 'Player': p, 'Mu': r.mu, 'Sigma': r.sigma }
		for p,r in ratings.items()
	))

def resultFromCSV(f) -> GameResult:
	return [
		(str(row['Player']), int(row['Rank']))
		for row in csv.DictReader(f)
	]

"""
Rankings:
Player, Mu, Sigma

Result:
Rank, Player
"""
# TODO restructure args to allow in place modification as in https://docs.python.org/3/library/fileinput.html
def update(args):
	with openOrDefault(args.ratingsIn, 'r', io.StringIO(), dashed=sys.stdin) as f:
		ratings = ratingsFromCSV(f)
	debug(f'loaded ratings for {len(ratings)} players')

	for resFile in args.results:
		res = resultFromCSV(resFile)
		debug(f'loaded a game played by {len(res)} players')
		newRatings = rateFFA(ratings, res)
		# TODO summarize the rankings changes
		ratings = newRatings

	debug(f'writing ratings for {len(ratings)} players')
	ratingsToCSV(sys.stdout, ratings)

def addUpdateArgs(parser:argparse.ArgumentParser):
	parser.add_argument('ratingsIn', nargs='?', default=None, type=Path)
	parser.add_argument('results', nargs='+', type=argparse.FileType('r'))
	parser.set_defaults(command=update)