import argparse

from history import addUpdateHistoryArgs
from rating import addUpdateArgs

def makeParser():
	parser = argparse.ArgumentParser(prog='trueskill')
	parser.set_defaults(command=lambda a : parser.print_help())

	sub = parser.add_subparsers()

	parser_update = sub.add_parser('update')
	addUpdateArgs(parser_update)

	parser_updateHistory = sub.add_parser('history')
	addUpdateHistoryArgs(parser_updateHistory)

	return parser


def main(args):
	args.command(args)

if __name__ == '__main__':
	args = makeParser().parse_args()
	main(args)