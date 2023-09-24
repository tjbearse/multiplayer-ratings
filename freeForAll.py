import typing
from trueskill import Rating, quality, rate
from functools import reduce

# TODO rewrite with openskill?

# Process Game: PlayerRatings + GameResult -> PlayerRatings
PlayerID = str
PlayerRatings = dict[PlayerID, Rating]
GameResult = list[tuple[PlayerID, int]] # zero indexed ranks

# Make matches: PlayerRankings + TableParams -> Partition of Players
# TableParams, number of tables, bounds on players per table

def qualityFFA(players: PlayerRatings):
	return quality([{p:r} for p,r in players.items()])

# ordered by success
def rateFFA(players: PlayerRatings, result:GameResult)-> PlayerRatings:
	groups = [
		{ player: getOrFactory(players, player, Rating)} for player, _ in result ]
	ranks = [ rank for _, rank in result ]
	ratings = rate(groups, ranks=ranks)
	return reduce(lambda a,b: a | b, ratings, players)

T = typing.TypeVar('T')
U = typing.TypeVar('U')
def getOrFactory(d:dict[T,U], k:T, factory:typing.Callable[[],U]) -> U:
	v = d.get(k)
	if v is not None:
		return v
	else:
		return factory()

"""
players = dict(p1=Rating(), p2=Rating(), p3=Rating(), p4=Rating())

print('quality', qualityFFA(players))

players2 = rateFFA(players, [('p1', 0), ('p2', 2), ('p3', 0), ('p5', 5)])
print('rating', players2)

print('quality2', qualityFFA(players2))
"""