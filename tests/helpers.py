import sys, re
from os import path, makedirs, symlink, remove
# just in case that package not installed in sys.path
sys.path.insert(0, path.join(
	path.dirname(path.dirname(path.dirname(path.realpath(__file__)))),
	'PyPPL'
))

import tempfile, inspect, shutil
from hashlib import md5
from pyppl import logger, Box

from contextlib import contextmanager
from six import StringIO, with_metaclass, assertRaisesRegex as sixAssertRaisesRegex

fn = path.basename(inspect.getframeinfo(inspect.getouterframes(inspect.currentframe())[1][0])[0])

def writeFile(f, contents = ''):
	if isinstance(contents, list):
		contents = '\n'.join(contents) + '\n'
	with open(f, 'w') as fin:
		fin.write(str(contents))

def readFile(f, transform = None):
	from io import open
	with open(f, 'r', encoding = "ISO-8859-1") as fin:
		r = fin.read()
	return transform(r) if callable(transform) else r

def createDeadlink(f):
	tmpfile = path.join(tempfile.gettempdir(), md5(f.encode('utf-8')).hexdigest())
	writeFile(tmpfile)
	symlink(tmpfile, f)
	remove(tmpfile)

def moduleInstalled(mod):
	try:
		__import__(mod)
		return True
	except ImportError:
		return False

@contextmanager
def captured_output():
	new_out, new_err = StringIO(), StringIO()
	old_out, old_err = sys.stdout, sys.stderr
	try:
		sys.stdout, sys.stderr = new_out, new_err
		yield sys.stdout, sys.stderr
	finally:
		sys.stdout, sys.stderr = old_out, old_err

def log2sys(levels = 'normal', theme = True, logfile = None, lvldiff = None):
	logger.getLogger(levels = levels, theme = theme, logfile = logfile, lvldiff = lvldiff)

@contextmanager
def log2str(levels = 'normal', theme = True, logfile = None, lvldiff = None):
	new_out, new_err = StringIO(), StringIO()
	old_out, old_err = sys.stdout, sys.stderr
	try:
		sys.stdout, sys.stderr = new_out, new_err
		#yield sys.stdout.getvalue(), sys.stderr.getvalue()
		logger.getLogger(levels = levels, theme = theme, logfile = logfile, lvldiff = lvldiff)
		yield sys.stdout, sys.stderr
	finally:
		sys.stdout, sys.stderr = old_out, old_err

assertTextEqual = lambda t, first, second, msg = None: t.assertListEqual(
	first if isinstance(first, list) else first.split('\n'), 
	second if isinstance(second, list) else second.split('\n'), msg)

def assertInFile(t, text, file, msg = None):
	with open(file) as f:
		t.assertSeqContains(text if isinstance(text, (tuple, list)) else text.split('\n'), [line.rstrip('\n') for line in f], msg)