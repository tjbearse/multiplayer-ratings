import dataclasses
from pathlib import Path
from trueskill import Rating
import argparse
import csv
import sys
import os
from typing import Iterator

from iohelp import debug, openOrDefault
from freeForAll import rateFFA, Rating, PlayerRatings, GameResult


@dataclasses.dataclass
class HistoryRow:
	player: str
	gameId: int
	rank: int
	newRatingMu: float
	newRatingSigma: float

	@staticmethod
	def fromDict(d:dict) -> 'HistoryRow':
		return HistoryRow(
			d['player'],
			int(d['gameId']),
			int(d['rank']),
			float(d['newRatingMu']),
			float(d['newRatingSigma']),
		)

HistoryRow_fields = [f.name for f in dataclasses.fields(HistoryRow)]
"""
File format

HISTORY
Player, GameID, Rank, NewRatingMu, NewRatingSigma

GAME -- separate by file or blank line
Rank,Player
"""
def updateHistory(args):
	debug(args)
	outFile = None
	inFile = args.history

	if args.inPlace:
		newInFile = inFile.with_suffix(inFile.suffix + '.bak')
		os.rename(inFile, newInFile)
		outFile, inFile = inFile, newInFile

	with openOrDefault(outFile, 'w', sys.stdout) as fo:
		writer = csv.DictWriter(fo, fieldnames=HistoryRow_fields)
		writer.writeheader()
		with open(inFile, 'r') as fi:
			ranks, nextGameId = processHistory(fi, lambda r: writer.writerow(r))

		for fp in args.game:
			with open(fp, 'r') as f:
				for game in readGames(f):
					newRatings = rateFFA(ranks, game)
					rows = [
						dataclasses.asdict(
							HistoryRow(player, nextGameId, rank, newRatings[player].mu, newRatings[player].sigma)
						)
						for player, rank in game
					]
					nextGameId += 1
					writer.writerows(rows)

# accumulate current ranks and the highest gameId used so far
def processHistory(f, fn=lambda x: None) -> tuple[PlayerRatings, int]:
	ratings = dict()
	nextGameId = 0

	reader = csv.DictReader(f)
	for row in reader:
		h = HistoryRow.fromDict(row)
		r = Rating(h.newRatingMu, h.newRatingSigma)
		ratings[h.player] = r
		nextGameId = max(nextGameId, h.gameId)
		fn(row)
	
	nextGameId += 1
	return ratings, nextGameId
		

# detect new file or non-monotomic change
def readGames(f) -> Iterator[GameResult]:
	game = []
	for line in f:
		line = line.strip()
		if line == '':
			# new game
			if game:
				yield game
				game = []
			continue

		rank,player = line.split(',')
		player = player.strip()
		rank = int(rank)
		game.append((player, rank))
		
	if game:
		yield game


def addUpdateHistoryArgs(parser:argparse.ArgumentParser):
	parser.add_argument('history', type=Path)
	parser.add_argument('-i', '--in-place', default=False, dest='inPlace', action='store_true')
	parser.add_argument('game', nargs='+', type=Path)
	parser.set_defaults(command=updateHistory)
