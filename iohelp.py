from contextlib import contextmanager
from pathlib import Path
import sys

@contextmanager
def openOrDefault(path:Path|None, mode, default, dashed=None):
	if path is None:
		yield default
	elif dashed is not None and path.match('-'):
		yield dashed
	else:
		with open(path, mode) as f:
			yield f

def debug(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)
