from collections import defaultdict
import dataclasses
from pathlib import Path
from trueskill import Rating
import argparse
import csv
import sys
import os
import io
from typing import Iterable, TypeVar, Iterator

from iohelp import debug, openOrDefault, error
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
player, gameID, rank, newRatingMu, newRatingSigma

GAME -- separate games by file or blank line (no header)
Rank,Player
"""
def addToHistory(args):
	if args.inPlace and args.history is None:
		error('option -i / --in-place requires a history file')
		exit(1)

	outFile = None
	inFile = args.history
	if args.inPlace:
		newInFile = inFile.with_suffix(inFile.suffix + '.bak')
		os.rename(inFile, newInFile)
		outFile, inFile = inFile, newInFile

	with openOrDefault(outFile, 'w', sys.stdout) as fo:
		writer = csv.DictWriter(fo, fieldnames=HistoryRow_fields)
		writer.writeheader()

		if inFile is not None:
			with open(inFile, 'r') as fi:
				ranks, nextGameId = processHistory(fi, lambda r: writer.writerow(r))
		else:
			ranks = dict()
			nextGameId = 1

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
	#TODO also track ranking changes, e.g. +1/-1
	muMap = defaultdict(lambda : MU)
	if args.player:
		playerSelect = lambda p : p in args.player
		playerJustify = max(map(len, args.player))
	else:
		playerSelect = lambda p: True
		playerJustify = 15

	with open(args.history, 'r') as f:
		reader = csv.DictReader(f)
		for row in reader:
			h = HistoryRow.fromDict(row)
			if not playerSelect(h.player):
				continue
			new = h.newRatingMu
			old = muMap[h.player]
			diff = new - old
			# FIXME simplify to csv format?
			print(f'{h.player.ljust(playerJustify, " ")} game {h.gameId} #{h.rank} => {diff:+7.3f} = {new:6.3f}')
			muMap[h.player] = new
	
def addUpdateHistoryArgs(parser:argparse.ArgumentParser):
	parser.set_defaults(command=lambda _: parser.print_help())
	sub = parser.add_subparsers()

	historyFileHelp = 'a csv file detailing history of ratings. Has column headers: player, gameID, rank, newRatingMu, newRatingSigma'

	addHelp = 'Appends game data to a rating history file.'
	p = sub.add_parser('add', description=addHelp, help=addHelp)
	p.add_argument('history', nargs='?', type=Path, help=historyFileHelp)
	p.add_argument('-i', '--in-place', default=False, dest='inPlace', action='store_true', help='overwrite the history file rather than print to stdout. A backup of the original is made with .bak extension')
	p.add_argument('game', nargs='+', type=Path, help='a file detailing game results in the form "<rank>,<player>". Games can be separated by newlines or passed as separate files')
	p.set_defaults(command=addToHistory)

	rankingHelp='Print the resulting ranks from a history file.'
	rankingDesc='Print the resulting ranks from a history file. Output is a csv with header columns "rank,player,mu,sigma"'
	p = sub.add_parser('ranking', description=rankingDesc, help=rankingHelp)
	p.add_argument('history', type=Path, help=historyFileHelp)
	p.set_defaults(command=compactHistory)

	deltasHelp='Print the ratings changes over time'
	p = sub.add_parser('deltas', description=deltasHelp, help=deltasHelp)
	p.add_argument('history', type=Path, help=historyFileHelp)
	p.add_argument('player', nargs='*', help='The names of players to show deltas for. Defaults to all players.')
	p.set_defaults(command=deltas)