from collections import defaultdict
import dataclasses
from pathlib import Path
from trueskill import Rating
import argparse
import csv
import sys
import os
from typing import Iterable, TypeVar, Iterator

from iohelp import debug, openOrDefault
from freeForAll import rateFFA, Rating, PlayerRatings, GameResult, MU


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
history add -i [history] [game...] -> [history]

File format

HISTORY
Player, GameID, Rank, NewRatingMu, NewRatingSigma

GAME -- separate games by file or blank line (no header)
Rank,Player
"""
def addToHistory(args):
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
def processHistory(f, fn=lambda r: None) -> tuple[PlayerRatings, int]:
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

"""
history compact [history] -> [ratings]
"""
def compactHistory(args):
	inFile = args.history

	with open(inFile, 'r') as fi:
		ratings, nextGameId = processHistory(fi)
	
	writer = csv.DictWriter(sys.stdout, fieldnames=['rank','player','mu','sigma'])
	writer.writeheader()
	for rank, kv in rankAndSortBy(ratings.items(), pred=lambda x: x[1], reverse=True):
		player, rating = kv
		writer.writerow(dict(
			rank=rank,
			player=player,
			mu=rating.mu,
			sigma=rating.sigma
		))

T = TypeVar('T')
def rankAndSortBy(items: Iterable[T], pred, reverse=False) -> Iterable[tuple[int,T]]:
	ordered = sorted(items, key=pred, reverse=reverse)
	if not ordered:
		return []

	place = 1
	lastValue = pred(ordered[0])
	res = list()
	for item in ordered:
		if pred(item) != lastValue:
			place += 1
		res.append((place, item))
	return res

# TODO Make matches: PlayerRankings + TableParams -> Partition of Players
# TableParams, number of tables, bounds on players per table

"""
history deltas [history] [player...]
prints a summary of how each game effected a player's rating
"""
def deltas(args):
	muMap = defaultdict(lambda : MU)
	if args.player is not None:
		playerSelect = lambda p : p in args.player
	else:
		playerSelect = lambda p: True

	with open(args.history, 'r') as f:
		reader = csv.DictReader(f)
		for row in reader:
			h = HistoryRow.fromDict(row)
			if not playerSelect(h.player):
				continue
			new = h.newRatingMu
			old = muMap[h.player]
			diff = new - old
			print(f'{h.player.ljust(10, " ")} game {h.gameId} #{h.rank} => {diff:+10.4f}')
			muMap[h.player] = new
	
def addUpdateHistoryArgs(parser:argparse.ArgumentParser):
	parser.set_defaults(command=lambda _: parser.print_help())
	sub = parser.add_subparsers()

	p = sub.add_parser('add')
	p.add_argument('history', type=Path)
	p.add_argument('-i', '--in-place', default=False, dest='inPlace', action='store_true')
	p.add_argument('game', nargs='+', type=Path)
	p.set_defaults(command=addToHistory)

	p = sub.add_parser('ranking')
	p.add_argument('history', type=Path)
	p.set_defaults(command=compactHistory)

	p = sub.add_parser('deltas')
	p.add_argument('history', type=Path)
	p.add_argument('player', nargs='*')
	p.set_defaults(command=deltas)