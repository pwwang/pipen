import sys, re
from os import path, makedirs, symlink, remove
# just in case that package not installed in sys.path
sys.path.insert(0, path.join(
	path.dirname(path.dirname(path.dirname(path.realpath(__file__)))),
	'PyPPL'
))

import tempfile, inspect, shutil
from hashlib import md5
from box import Box
from simpleconf import config
from pyppl.logger import logger

from contextlib import contextmanager
from six import StringIO, with_metaclass, assertRaisesRegex as sixAssertRaisesRegex

fn = path.basename(inspect.getframeinfo(inspect.getouterframes(inspect.currentframe())[1][0])[0])

def writeFile(f, contents = ''):
	if isinstance(contents, list):
		contents = '\n'.join(contents) + '\n'
	with open(f, 'w') as fin:
		fin.write(str(contents))

def readFile(f, transform = None):
	with open(f, 'r') as fin:
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

@contextmanager
def log2str(levels = 'normal', theme = True, logfile = None, lvldiff = None):
	new_out, new_err = StringIO(), StringIO()
	old_out, old_err = sys.stdout, sys.stderr
	profile = config._protected['profile']
	try:
		sys.stdout, sys.stderr = new_out, new_err
		#yield sys.stdout.getvalue(), sys.stderr.getvalue()
		config._log.update(levels = levels, theme = theme, file = logfile, leveldiffs = lvldiff)
		logger.init()
		yield sys.stdout, sys.stderr
	finally:
		config._use(profile)
		sys.stdout, sys.stderr = old_out, old_err

assertTextEqual = lambda t, first, second, msg = None: t.assertListEqual(
	first if isinstance(first, list) else first.split('\n'), 
	second if isinstance(second, list) else second.split('\n'), msg)

def assertInFile(t, text, file, msg = None):
	t.longMessage = True
	text = text if isinstance(text, (tuple, list)) else text.split('\n')
	msg  = msg or '\n"{text}" is not in file "{file}"\n'.format(
		text = '\n'.join(text), file = file
	)
	with open(file) as f:
		t.assertSeqContains(text, [
			line.rstrip('\n') for line in f
		], msg)
		
def assertInSvgFile(t, text, file, starts = None, msg = None):
	t.longMessage = True
	text = text if isinstance(text, (tuple, list)) else text.split('\n')
	if starts:
		text = [line for line in text if line.startswith(starts)]
	msg  = msg or '\n"{text}" is not in SVG file "{file}"\n'.format(
		text = '\n'.join(text), file = file
	)
	with open(file) as f:
		t.assertSeqContains(text, [
			line.rstrip('\n') 
			for line in f 
			if not starts or line.startswith(starts)
		], msg)

from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
#from loky import ProcessPoolExecutor

class Parallel(object):
	"""
	A parallel runner
	"""

	def __init__(self, nthread = 1, backend = 'process', raiseExc = True):
		"""
		Constructor
		@params:
			`nthread` : Number of jobs to run simultaneously. Default: `1`
			`backend` : The backend, either `process` (default) or `thread`
			`raiseExc`: Whether raise exception or not. Default: `True`
		"""
		PoolExecutor   = ProcessPoolExecutor if backend.lower() in 'multiprocessing' else ThreadPoolExecutor
		self.executor  = PoolExecutor(max_workers = nthread)
		self.raiseExc  = raiseExc

	def run(self, func, args):
		"""
		Run parallel jobs
		@params:
			`func`    : The function to run
			`args`    : The arguments for the function, should be a `list` with `tuple`s
			`nthread` : Number of jobs to run simultaneously. Default: `1`
			`backend` : The backend, either `process` (default) or `thread`
			`raiseExc`: Whether raise exception or not. Default: `True`
		@returns:
			The merged results from each job.
		"""
		_func = lambda arg: func(*arg)

		submits   = []
		results   = []
		with self.executor:
			for arg in args:
				submits.append(self.executor.submit(_func, arg))

			for submit in as_completed(submits):
				if submit.exception() is not None:
					if self.raiseExc:
						raise submit.exception()
				else:
					results.append(submit.result())

		return results

# shortcuts
def parallel(func, args, nthread = 1, backend = 'process', raiseExc = True):
	"""
	A shortcut of `Parallel.run`
	@params:
		`func`    : The function to run
		`args`    : The arguments for the function, should be a `list` with `tuple`s
		`nthread` : Number of jobs to run simultaneously. Default: `1`
		`backend` : The backend, either `process` (default) or `thread`
		`raiseExc`: Whether raise exception or not. Default: `True`
	@returns:
		The merged results from each job.
	"""
	return Parallel(nthread, backend, raiseExc).run(func, args)
