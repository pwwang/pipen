import sys, re
from os import path, makedirs, symlink, remove
# just in case that package not installed in sys.path
sys.path.insert(0, path.join(
	path.dirname(path.dirname(path.dirname(path.realpath(__file__)))),
	'PyPPL'
))

import tempfile, inspect, unittest, shutil
from hashlib import md5
from pyppl import logger, Box

from contextlib import contextmanager
from six import StringIO, with_metaclass, assertRaisesRegex as sixAssertRaisesRegex

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
	try:
		sys.stdout, sys.stderr = new_out, new_err
		#yield sys.stdout.getvalue(), sys.stderr.getvalue()
		logger.getLogger(levels = levels, theme = theme, logfile = logfile, lvldiff = lvldiff)
		yield sys.stdout, sys.stderr
	finally:
		sys.stdout, sys.stderr = old_out, old_err

# make sure the order is like:
# testA
# testA_1
# testA_2
# testAB
# testAB_1
# instead of:
# testA
# testAB
# testAB_1
# testA_1
# testA_2
def testingOrder (_, x, y):
	if not re.search(r'_\d+$', x):
		x += '_0'
	if not re.search(r'_\d+$', y):
		y += '_0'
	return -1 if x<y else 1 if x>y else 0

unittest.TestLoader.sortTestMethodsUsing = testingOrder
class DataProviderSupport(type):
	def __new__(meta, classname, bases, classDict):
		# method for creating our test methods
		def create_test_method(testFunc, args):
			return lambda self: testFunc(self, *args)

		def create_setupteardown_method(stfunc):
			def stFunc(self):
				if not re.search(r'_\d+$', self._testMethodName):
					stfunc(self)
			return stFunc

		parentDir = path.join(tempfile.gettempdir(), 'PyPPL_unittest', classname)
		if path.isdir(parentDir):
			shutil.rmtree(parentDir)
		# look for data provider functions
		
		for attrName in list(classDict.keys()):

			attr = classDict[attrName]
			if attrName == 'setUp':
				classDict['setUp'] = create_setupteardown_method(attr)
				continue
			if attrName == 'tearDown':
				classDict['tearDown'] = create_setupteardown_method(attr)
				continue

			if not attrName.startswith("dataProvider_"):
				continue

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
			data    = attr(Box(classDict), testdir) if lenargs == 2 else attr(Box(classDict)) if lenargs == 1 else attr()
			if data:
				for i, arg in enumerate(data):
					key = testName if i == 0 else testName + '_' + str(i)
					classDict[key] = create_test_method(testFunc, arg)

		# create the type
		return type.__new__(meta, classname, bases, classDict)


class TestCase(with_metaclass(DataProviderSupport, unittest.TestCase)):

	def assertItemEqual(self, first, second, msg = None):
		first          = [repr(x) for x in first]
		second         = [repr(x) for x in second]
		first          = str(sorted(first))
		second         = str(sorted(second))
		assertion_func = self._getAssertEqualityFunc(first, second)
		assertion_func(first, second, msg=msg)

	def assertDictIn(self, first, second, msg = 'Not all k-v pairs in 1st element are in the second.'):
		assert isinstance(first, dict)
		assert isinstance(second, dict)
		notInkeys = [k for k in first.keys() if k not in second.keys()]
		if notInkeys:
			self.fail(msg = 'Keys of first dict not in second: %s' % notInkeys)
		else:
			seconds2 = {k:second[k] for k in first.keys()}
			for k in first.keys():
				v1   = first[k]
				v2   = second[k]
				self.assertSequenceEqual(v1, v2)

	def assertDictNotIn(self, first, second, msg = 'all k-v pairs in 1st element are in the second.'):
		assert isinstance(first, dict)
		assert isinstance(second, dict)
		ret = False
		for k in first.keys():
			if k in second:
				if first[k] != second[k]:
					ret = True
			else:
				ret = True
		if not ret:
			self.fail(msg)

	def assertTextEqual(self, first, second, msg = None):
		first  = first.split('\n')
		second = second.split('\n')
		self.assertListEqual(first, second, msg)

	def assertRaisesStr(self, exc, s, callable, *args, **kwds):
		sixAssertRaisesRegex(self, exc, s, callable, *args, **kwds)

	def assertItemSubset(self, s, t, msg = 'The first list is not a subset of the second.'):
		assert isinstance(s, list)
		assert isinstance(t, list)
		self.assertTrue(set(s) < set(t), msg = msg)

	def assertInFile(self, s, f):
		sf = readFile(f, str)
		self.assertIn(s, sf)

