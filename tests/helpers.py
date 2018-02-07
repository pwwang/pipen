import sys
from os import path, makedirs, symlink, remove
# just in case that package not installed in sys.path
sys.path.insert(0, path.join(
	path.dirname(path.dirname(path.dirname(path.realpath(__file__)))),
	'PyPPL'
))

import tempfile, inspect, unittest, shutil
from hashlib import md5
from pyppl import logger

from contextlib import contextmanager
from six import StringIO, with_metaclass

fn = path.basename(inspect.getframeinfo(inspect.getouterframes(inspect.currentframe())[1][0])[0])

def writeFile(f, contents = ''):
	with open(f, 'w') as fin:
		fin.write(str(contents))

def readFile(f, transform = None):
	from io import open
	with open(f, 'r', encoding = "ISO-8859-1") as fin:
		r = fin.read()
	return transform(r) if callable(transform) else r

def createDeadlink(f):
	tmpfile = path.join(tempfile.gettempdir(), md5(f).hexdigest())
	writeFile(tmpfile)
	symlink(tmpfile, f)
	remove(tmpfile)


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

class DataProviderSupport(type):
	def __new__(meta, classname, bases, classDict):
		# method for creating our test methods
		def create_test_method(testFunc, args):
			return lambda self: testFunc(self, *args)

		parentDir = path.join(tempfile.gettempdir(), 'PyPPL_unittest', classname)
		if path.isdir(parentDir):
			shutil.rmtree(parentDir)
		# look for data provider functions
		
		for attrName in list(classDict.keys()):
			if not attrName.startswith("dataProvider_"):
				continue

			attr = classDict[attrName]
			# find out the corresponding test method
			testName = attrName[13:]
			testFunc = classDict[testName]
			testdir  = path.join(parentDir, testName)
			if not path.isdir(testdir):
				makedirs(testdir)

			# the test method is no longer needed
			#del classDict[testName]
			# in case if there is no data provided
			classDict[testName] = lambda self: None

			# generate test method variants based on
			# data from the data porovider function
			lenargs = len(inspect.getargspec(attr).args)
			data    = attr(None, testdir) if lenargs == 2 else attr(None) if lenargs == 1 else attr()
			for i, arg in enumerate(data):
				key = testName if i == 0 else testName + '_' + str(i)
				classDict[key] = create_test_method(testFunc, arg)

		# create the type
		return type.__new__(meta, classname, bases, classDict)


class TestCase(with_metaclass(DataProviderSupport, unittest.TestCase)):

	def assertItemEqual(self, first, second, msg = None):
		first          = str(sorted(first))
		second         = str(sorted(second))
		assertion_func = self._getAssertEqualityFunc(first, second)
		assertion_func(first, second, msg=msg)

	'''
	def assertEvalEqual(self, expr, value, msg = None):
		first = literal_eval(expr)
		assertion_func = self._getAssertEqualityFunc(first, value)
		assertion_func(expr, value, msg=msg)
	'''
