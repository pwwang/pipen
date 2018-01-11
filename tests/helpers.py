import sys
from os import path
sys.path.insert(0, path.join(
    path.dirname(path.dirname(path.dirname(path.realpath(__file__)))),
    'PyPPL'
))

import tempfile, inspect
from pyppl import logger

from contextlib import contextmanager
from six import StringIO

testdir = tempfile.gettempdir()
def _getTestdir():
	global testdir
	fn = inspect.getframeinfo(inspect.getouterframes(inspect.currentframe())[2][0])[0]
	fn = path.basename(fn).replace('.', '')
	testdir = path.join(tempfile.gettempdir(), 'pyppl-tests', fn)
_getTestdir()

@contextmanager
def captured_output():
	new_out, new_err = StringIO(), StringIO()
	old_out, old_err = sys.stdout, sys.stderr
	try:
		sys.stdout, sys.stderr = new_out, new_err
		yield sys.stdout, sys.stderr
	finally:
		sys.stdout, sys.stderr = old_out, old_err

def log2str (levels = 'all'):
	with captured_output() as (out, err):
		logger.getLogger(levels = levels)
	return (out, err)

def log2sys (levels = 'all'):
	logger.getLogger(levels = levels)

def assertListEqual(cls, x, y):
	cls.assertEqual(sorted(x), sorted(y))

def assertPathExists(cls, x):
	cls.assertTrue(path.exists(x))

def assertPathNotExists(cls, x):
	cls.assertFalse(path.exists(x))



