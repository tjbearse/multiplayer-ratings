import typing
from trueskill import Rating, quality, rate
from functools import reduce

import trueskill

# TODO rewrite with openskill, glick, etc?

PlayerID = str
PlayerRatings = dict[PlayerID, Rating]
GameResult = list[tuple[PlayerID, int]] # zero indexed ranks

def qualityFFA(players: PlayerRatings):
	return quality([{p:r} for p,r in players.items()])

# ordered by success
def rateFFA(players: PlayerRatings, result:GameResult)-> PlayerRatings:
	groups = [
		{ player: getOrFactory(players, player, Rating)} for player, _ in result ]
	ranks = [ rank for _, rank in result ]
	ratings = rate(groups, ranks=ranks)
	return reduce(lambda a,b: a | b, ratings, players)

MU = trueskill.MU

T = typing.TypeVar('T')
U = typing.TypeVar('U')
def getOrFactory(d:dict[T,U], k:T, factory:typing.Callable[[],U]) -> U:
	v = d.get(k)
	if v is not None:
		return v
	else:
		return factory()