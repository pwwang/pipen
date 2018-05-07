import helpers, unittest

import traceback
from copy import deepcopy
from os import path, symlink, remove, rename, makedirs, utime, X_OK, access
from pyppl import utils
from pyppl.utils import Box
from time import time, sleep
from shutil import copyfile, rmtree
from subprocess import Popen

class TestUtils (helpers.TestCase):

	def dataProvider_testBox(self):
		box = Box()
		yield box, {}
		box1 = Box()
		box1.a = Box()
		yield box1, dict(a = {})
		box2 = Box()
		box2.a = Box()
		box2.a.b = 1
		yield box2, dict(a = dict(b = 1))

	def testBox(self, box, out):
		self.assertDictEqual(box, out)

	def dataProvider_testFlushFile(self, testdir):
		file1 = path.join(testdir, 'testFlushFile1.txt')
		file2 = path.join(testdir, 'testFlushFile2.txt')
		file3 = path.join(testdir, 'testFlushFile3.txt')
		file4 = path.join(testdir, 'testFlushFile4.txt')

		yield (
			file1, [
				('', [], '', False), # string append to the file, lines flushed, and remaining string
				('abcde', [], 'abcde', False),
				('ccc\ne1', ['abcdeccc\n', 'e1\n'], '', True),
			]
		)
		yield (
			file2, [
				('a\nb', ['a\n'], 'b', False), # string append to the file, lines flushed, and remaining string
				('c', [], 'bc', False),
				('d\n', ['bcd\n'], '', True),
			]
		)
		yield (
			file3, [
				('\n', ['\n'], '', False), # string append to the file, lines flushed, and remaining string, end
				('\n', ['\n'], '', False),
				('\na', ['\n', 'a\n'], '', True),
			]
		)
		yield (
			file4, [
				('123', [], '123', False),
				('', ['123\n'], '', True)
			]
		)

	def testFlushFile(self, fn, appends):
		fa = open(fn, 'a')
		fr = open(fn, 'r')
		lastmsg = ''
		for app in appends:
			a, l, r, e = app
			fa.write(a)
			fa.flush()
			lines, lastmsg = utils.flushFile(fr, lastmsg, e)
			self.assertEqual(l, lines)
			self.assertEqual(r, lastmsg)
		fa.close()
		fr.close()

	def dataProvider_testParallel(self):
		yield ([(1,2), (3,4), (5,6), (7,8)], 4, 'thread')
		yield ([(1,2), (3,4), (5,6), (7,8)], 4, 'process')

	def testParallel(self, data, nthread, method):
		globalVars = []
		interval   = .1
		def func(a, b):
			sleep(interval)
			globalVars.append(a)
			globalVars.append(b)

		t0 = time()
		utils.Parallel(nthread, method).run(func, data)
		t = time() - t0
		if method == 'thread':
			self.assertItemEqual(utils.reduce(lambda x, y: list(x) + list(y), data), globalVars)
		else: # globalVars not shared between processes
			self.assertListEqual([], globalVars)
		self.assertLess(t, interval * nthread)

	def dataProvider_testVarname():
		class Klass(object):
			def __init__(self, default='', d2=''):
				self.id = utils.varname()

			def copy(self, *arg):
				return utils.varname()

		def func():
			return utils.varname()

		h = Klass()
		h2 = Klass()
		h3 = Klass(
			default = 'a',
			d2 = 'c'
		)
		h4 = [Klass()]
		v1 = h.copy()
		v2 = h2.copy(
			2,
			3,
			4
		)
		v3 = [h3.copy(
			1, 2,
			4
		)]
		f = func()
		f2 = [func()]

		yield (h.id, 'h')
		yield (h2.id, 'h2')
		yield (h3.id, 'h3')
		yield (h4[0].id, 'var_0')
		yield (v1, 'v1')
		yield (v2, 'v2')
		yield (v3[0], 'var_1')
		yield (f, 'f')
		yield (f2[0], 'var_2')

	def testVarname(self, idExpr, idVal):
		self.assertEqual(idExpr, idVal)

	def dataProvider_testMap():
		yield ([1, 0, False, '', '0', 2], str, ['1', '0', 'False', '', '0', '2'])
		yield ([1, 0, False, '', '0', 2], bool, [True, False, False, False, True, True])
		yield ([1, 0, False, '1', '0', 2], int, [1, 0, 0, 1, 0, 2])

	def testMap(self, l, func, ret):
		self.assertEqual(utils.map(func, l), ret)

	def dataProvider_testReduce():
		yield ([1, 0, False, '1', '0', 2], lambda x, y: str(x) + str(y), '10False102')
		yield ([1, 0, False, '1', '0', 2], lambda x, y: int(x) + int(y), 4)
		yield ([1, 0, False, '1', '0', 2], lambda x, y: bool(x) and bool(y), False)

	def testReduce(self, l, func, ret):
		self.assertEqual(utils.reduce(func, l), ret)

	def dataProvider_testFilter():
		yield ([1, 0, False, '1', '0', 2], lambda x: isinstance(x, int), [1, 0, False, 2])
		yield ([1, 0, False, '1', '0', 2], None, [1, '1', '0', 2])
		yield ([1, 0, False, '1', '0', 2], lambda x: not bool(x), [0, False])

	def testFilter(self, l, func, ret):
		self.assertEqual(utils.filter(func, l), ret)

	def dataProvider_testSplit(self):
		yield ("a|b|c", "|", ["a", "b", "c"])
		yield ('a|b\|c', "|", ["a", "b\\|c"])
		yield ('a|b\|c|(|)', "|", ["a", "b\\|c", "(|)"])
		yield ('a|b\|c|(\)|)', "|", ["a", "b\\|c", "(\\)|)"])
		yield ('a|b\|c|(\)\\\'|)', "|", ["a", "b\\|c", "(\\)\\'|)"])
		yield ('outdir:dir:{{in.pattern | lambda x: __import__("glob").glob(x)[0] | fn }}_etc', ':', ["outdir", "dir", "{{in.pattern | lambda x: __import__(\"glob\").glob(x)[0] | fn }}_etc"])

	def testSplit (self, s, d, a):
		self.assertEqual(utils.split(s, d), a)

	def dataProvider_testDictUpdate(self):
		yield (
			{"a":1, "b":{"c": 3, "d": 9}},       # original dict
			{"b":{"c": 4}, "c":8},               # replacement
			{"a":1, "b":{"c":4, "d":9}, "c":8},  # result of utils.update
			{"a":1, "b":{"c": 4}, "c":8},        # result of naive update
		)
		b = {'args': {'inopts': {'ftype': 'head'}}}
		def ud (d):
			d['args']['inopts']['ftype'] = 'hello'
		yield (
			b,
			{'args': {'inopts': {'ftype': 'nometa'}}},
			{'args': {'inopts': {'ftype': 'nometa'}}},
			{'args': {'inopts': {'ftype': 'nometa'}}},
			ud
		)
		yield (
			{},
			{"b":{"c": 4}, "c":8},
			{"b":{"c": 4}, "c":8},
			{"b":{"c": 4}, "c":8},
		)
		yield (
			{'a':1,'b':2,'c':[3,4],'d':{'a':0}},
			{'a':1,'b':2,'c':[1,4],'d':{'a':1}},
			{'a':1,'b':2,'c':[1,4],'d':{'a':1}},
			{'a':1,'b':2,'c':[1,4],'d':{'a':1}},
		)

	def testDictUpdate (self, odict, rdict, ndict, naive, cb = None):
		odict1 = deepcopy(odict)
		rdict1 = deepcopy(rdict)
		#print rdict
		#if callable(cb): cb(odict1)
		utils.dictUpdate(odict, rdict)
		odict1.update(rdict)
		#print rdict
		self.assertEqual(odict1, naive)
		self.assertEqual(rdict1, rdict)

	def dataProvider_testFuncSig(self):
		def func1():
			pass
		func2 = lambda x: x
		func3 = ""
		func4 = "A"
		yield (func1, "def func1():\n\t\t\tpass")
		yield (func2, "func2 = lambda x: x")
		yield (func3, "None")
		yield (func4, "None")

	def testFuncSig (self, func, src):
		self.assertEqual (utils.funcsig(func).strip(), src)

	def dataProvider_testUid(self):
		yield ('a', 'O4JnVAW7')
		yield ('', '6SFsQFoW')

	def testUid(self, s, uid):
		self.assertEqual(utils.uid(s), uid)

	def testUidUnique (self):
		import random, string

		def randomword(length):
		   return ''.join(random.choice(list('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890')) for i in range(length)).encode('utf-8')

		uids = {}
		for _ in range (10000):
			s = randomword (10)
			uid = utils.uid (s)
			self.assertEqual(uid, utils.uid(s))
			uids[uid] = 1
		self.assertEqual (len (uids.keys()), 10000)

	def dataProvider_testFormatsecs(self):
		yield (1, "00:00:01.000")
		yield (1.001, "00:00:01.001")
		yield (100, "00:01:40.000")
		yield (7211, "02:00:11.000")

	def testFormatsecs(self, sec, secstr):
		self.assertEqual (utils.formatSecs(sec), secstr)

	def dataProvider_testRange(self):
		yield (utils.range(3), [0,1,2])
		yield (utils.range(1), [0])
		yield (utils.range(0), [])

	def testRange(self, r1, r2):
		self.assertEqual (type(r1), type(r2))
		self.assertEqual (r1, r2)

	def dataProvider_testAlwayslist(self):
		yield ("a, b,c", ['a', 'b', 'c'])
		yield (["a, b,c"], ['a', 'b', 'c'])
		yield (["a, b,c", 'd'], ['a', 'b', 'c', 'd'])
		yield ("a,b, c, 'd,e'", ['a', 'b', 'c', "'d,e'"])
		yield (
			["o1:var:{{c1}}", "o2:var:{{c2 | __import__('math').pow(float(_), 2.0)}}", "o3:file:{{c3.fn}}2{{c3.ext}}"],
			["o1:var:{{c1}}", "o2:var:{{c2 | __import__('math').pow(float(_), 2.0)}}", "o3:file:{{c3.fn}}2{{c3.ext}}"]
		)
		yield (
			["o1:var:{{c1}}", "o2:var:c2 | __import__('math').pow float(_), 2.0)}}", "o3:file:{{c3.fn}}2{{c3.ext}}"],
			#                                                             ^ comma is not quoted
			["o1:var:{{c1}}", "o2:var:c2 | __import__('math').pow float(_)", "2.0)}}", "o3:file:{{c3.fn}}2{{c3.ext}}"]
		)

	def testAlwayslist(self, albefore, alafter):
		self.assertSequenceEqual (utils.alwaysList (albefore), alafter)

	def dataProvider_testAlwayslistException(self):
		yield ({'a': 1}, )
		yield (None, )
		yield ((1,2), )

	def testAlwayslistException(self, albefore):
		self.assertRaises(ValueError, utils.alwaysList, albefore)

	def dataProvider_test_lockfile(self, testdir):
		file1 = path.join(testdir, 'test_lockfile1.txt')
		file2 = path.join(testdir, 'test_lockfile2.txt')
		file3 = path.join(testdir, 'test_lockfile3.txt')
		helpers.writeFile(file1)
		helpers.writeFile(file2)
		symlink(file1, file3)
		yield testdir, file1, utils.uid(file1, 16) + '.lock'
		yield testdir, file2, utils.uid(file2, 16) + '.lock'
		yield testdir, file3, utils.uid(file1, 16) + '.lock'
		# if file not exists
		file4 = path.join(testdir, 'test_lockfile4.txt')
		file5 = path.join(testdir, 'test_lockfile5.txt')
		helpers.writeFile(file4)
		symlink(file4, file5)
		yield testdir, file4, utils.uid(file4, 16) + '.lock'
		yield testdir, file5, utils.uid(file4, 16) + '.lock'
		file6 = path.join(testdir, 'test_lockfile6.txt')
		# file6 not exists
		yield testdir, file6, utils.uid(file6, 16) + '.lock', False

	def test_lockfile(self, testdir, origfile, lockfile, real = True):
		self.assertEqual(utils._lockfile(origfile, tmpdir = testdir), path.join(testdir, lockfile))

	def dataProvider_test_rm(self, testdir):
		file1 = path.join(testdir, 'test_rm1.txt')
		file2 = path.join(testdir, 'test_rm2.dir')
		helpers.writeFile(file1)
		makedirs(file2)
		yield file1,
		yield file2,

	def test_rm(self, f):
		utils._rm(f)
		self.assertFalse(path.exists(f))

	def dataProvider_test_cp(self, testdir):
		file1    = path.join(testdir, 'test_cp1.txt')
		file1_cp = path.join(testdir, 'test_cp1_cp.txt')
		file2    = path.join(testdir, 'test_cp2.dir')
		file2_cp = path.join(testdir, 'test_cp2_cp.dir')
		helpers.writeFile(file1)
		makedirs(file2)
		yield file1, file1_cp
		yield file2, file2_cp

	def test_cp(self, f1, f2):
		utils._cp(f1, f2)
		self.assertTrue(path.exists(f1))
		self.assertTrue(path.exists(f2))

	def dataProvider_test_link(self, testdir):
		file1      = path.join(testdir, 'test_link1.txt')
		file1_link = path.join(testdir, 'test_link1_link.txt')
		file2      = path.join(testdir, 'test_link2.dir')
		file2_link = path.join(testdir, 'test_link2_link.dir')
		helpers.writeFile(file1)
		makedirs(file2)
		yield file1, file1_link
		yield file2, file2_link

	def test_link(self, f1, f2):
		utils._link(f1, f2)
		self.assertTrue(path.exists(f1))
		self.assertTrue(path.exists(f2))
		self.assertTrue(path.islink(f2))

	def dataProvider_test1FS(self, testdir):

		def _int(s):
			return 0 if not s else int(s)

		def _write(r, f):
			if not r:
				helpers.writeFile(f, 1)
			else:
				i = helpers.readFile(f, _int)
				helpers.writeFile(f, i+1)

		def _delayRemove(f):
			sleep(.1)
			remove(f)

		"""
		Simple file exists: 0-2
		"""
		file01 = path.join(testdir, 'testFileExists01.txt')
		file02 = path.join(testdir, 'testFileExists02.txt')
		file03 = path.join(testdir, 'testFileExists03.dir')
		flag01 = path.join(testdir, 'testFileExists01-flag.txt')
		flag02 = path.join(testdir, 'testFileExists02-flag.txt')
		flag03 = path.join(testdir, 'testFileExists03-flag.txt')
		helpers.writeFile(file01)
		makedirs(file03)
		def func01(f):
			if utils.fileExists(f, tmpdir = testdir):
				helpers.writeFile(flag01)
		def func02(f):
			if utils.fileExists(f, tmpdir = testdir):
				helpers.writeFile(flag02)
		def func03(f):
			if utils.fileExists(f, tmpdir = testdir):
				helpers.writeFile(flag03)
		yield (func01, file01, 2,  lambda: path.exists(flag01))
		yield (func02, file02, 2,  lambda: not path.exists(flag02))
		yield (func03, file03, 2,  lambda: path.exists(flag03))

		"""
		Thread-safe file exists, increment the number in a file: 3
		"""
		file1 = path.join(testdir, 'testFileExists1.txt')
		# thread-safe, so number accumulates
		def func1(f):
			utils.fileExists(f, _write, tmpdir = testdir)
		yield (func1,  file1,  20, lambda: helpers.readFile(file1, _int) == 20)

		"""
		Thread-unsafe file exists, number will not accumulated to max: 4
		"""
		file2 = path.join(testdir, 'testFileExists2.txt')
		# non-thread-safe, so number may be lost
		def func2(f):
			_write(path.exists(f), f)
		yield (func2,  file2,  20, lambda: helpers.readFile(file2, _int) < 20)

		"""
		Thread-safe file exists, remove a file in multiple thread, no error: 5
		"""
		file3 = path.join(testdir, 'testFileExists3.txt')
		flag3 = path.join(testdir, 'testFileExists3-flag.txt')
		helpers.writeFile(file3)
		# thread-safe, so no flag file generated
		def func3(f):
			try:
				utils.fileExists(f, lambda r, f: _delayRemove(f) if r else None, tmpdir = testdir)
			except OSError:
				helpers.writeFile(flag3)
		yield (func3,  file3,  10, lambda: not path.exists(flag3))

		"""
		Thread-unsafe file exists, remove a file in multiple thread, error happens
		"""
		file4 = path.join(testdir, 'testFileExists4.txt')
		flag4 = path.join(testdir, 'testFileExists4-flag.txt')
		helpers.writeFile(file4)
		# thread-safe, so no flag file generated
		def func4(f):
			try:
				if path.exists(f):
					_delayRemove(f)
			except OSError:
				helpers.writeFile(flag4)
		yield (func4,  file4,  10, lambda: path.exists(flag4))

		"""
		Thread-safe file remove, remove file in multiple thread, no error
		"""
		file5 = path.join(testdir, 'testFileRemove1.txt')
		flag5 = path.join(testdir, 'testFileRemove1-flag.txt')
		helpers.writeFile(file5)
		def func5(f):
			try:
				utils.safeRemove(f, tmpdir = testdir, callback = lambda r, fn: helpers.writeFile(fn) if r else None)
			except OSError:
				helpers.writeFile(flag5)
		yield (func5,  file5,  10, lambda: not path.exists(flag5))

		"""
		Thread-safe file remove, remove directory in multiple thread, no error
		"""
		file51 = path.join(testdir, 'testFileRemove1.dir')
		flag51 = path.join(testdir, 'testFileRemove1dir-flag.txt')
		makedirs(file51)
		def func51(f):
			try:
				utils.safeRemove(f, tmpdir = testdir)
			except OSError as ex:
				helpers.writeFile(flag51, ex)
		yield (func51, file51, 10, lambda: not path.exists(file51) and not path.exists(flag51))

		"""
		Thread-unsafe file remove, remove file in multiple thread, error happens
		"""
		file6 = path.join(testdir, 'testFileRemove2.txt')
		flag6 = path.join(testdir, 'testFileRemove2-flag.txt')
		helpers.writeFile(file6)
		def func6(f):
			try:
				_delayRemove(f)
			except OSError:
				helpers.writeFile(flag6)
		yield (func6,  file6,  10, lambda: path.exists(flag6))

	def test1FS(self, func, f, length, state):
		utils.Parallel(length, 'thread').run(func, [(f, ) for _ in range(length)])
		self.assertTrue(state())

	def dataProvider_test2FS(self, testdir):

		def _int(s):
			return 0 if not s else int(s)

		def _write(r, f1, f2):
			if not r:
				helpers.writeFile(f1, 1)
			else:
				i = helpers.readFile(f1, _int)
				helpers.writeFile(f1, i+1)

		def _delayRemove(f):
			sleep(.1)
			remove(f)

		"""
		#0,1 Simple samefile
		"""
		file01 = path.join(testdir, 'testSamefile01.txt')
		file02 = path.join(testdir, 'testSamefile02.txt')
		flag0  = path.join(testdir, 'testSamefileFlag0.txt')
		helpers.writeFile(file01)
		symlink(file01, file02)
		def func0(f1, f2):
			if not utils.samefile(f1, f2, tmpdir = testdir):
				helpers.writeFile(flag0)
		yield (func0, file01, file02, 10, lambda: not path.exists(flag0))

		file11 = path.join(testdir, 'testSamefile11.txt')
		file12 = path.join(testdir, 'testSamefile12.txt')
		flag1  = path.join(testdir, 'testSamefileFlag1.txt')
		def func1(f1, f2):
			if not utils.samefile(f1, f2, tmpdir = testdir):
				helpers.writeFile(flag1)
		yield (func1, file11, file12, 10, lambda: path.exists(flag1))

		"""
		#2 Thread-safe samefile, increment the number in a file
		"""
		file21 = path.join(testdir, 'testSamefile21.txt')
		file22 = path.join(testdir, 'testSamefile22.txt')
		helpers.writeFile(file21)
		symlink(file21, file22)
		# thread-safe, so number accumulates
		def func2(f1, f2):
			utils.samefile(f1, f2, _write, tmpdir = testdir)
		yield (func2, file21, file22, 20, lambda: helpers.readFile(file21, _int) == 20)

		"""
		#3 Thread-unsafe samefile, number will not accumulated to max
		"""
		file31 = path.join(testdir, 'testSamefile31.txt')
		file32 = path.join(testdir, 'testSamefile32.txt')
		helpers.writeFile(file31)
		symlink(file31, file32)
		# non-thread-safe, so number may be lost
		def func3(f1, f2):
			_write(path.samefile(f1, f2), f1, f2)
		yield (func3, file31, file32, 20, lambda: helpers.readFile(file31, _int) < 20)

		"""
		#4 Thread-safe samefile, remove a file in multiple thread, no error
		"""
		file41 = path.join(testdir, 'testSamefile41.txt')
		file42 = path.join(testdir, 'testSamefile42.txt')
		flag4  = path.join(testdir, 'testSamefile4-flag.txt')
		helpers.writeFile(file41)
		symlink(file41, file42)
		# thread-safe, so no flag file generated
		def func4(f1, f2):
			try:
				utils.samefile(f1, f2, lambda r, f1, f2: _delayRemove(f2) if r else None, tmpdir = testdir)
			except OSError as ex:
				helpers.writeFile(flag4, ex)
		yield (func4, file41, file42, 10, lambda: not path.exists(flag4))


		"""
		#5 Thread-safe samefile, remove a file in multiple thread, error happens
		"""
		file51 = path.join(testdir, 'testSamefile51.txt')
		file52 = path.join(testdir, 'testSamefile52.txt')
		flag5  = path.join(testdir, 'testSamefile5-flag.txt')
		helpers.writeFile(file51)
		symlink(file51, file52)
		# thread-safe, so no flag file generated
		def func5(f1, f2):
			try:
				if path.samefile(f1, f2):
					_delayRemove(f2)
			except OSError as ex:
				helpers.writeFile(flag5, ex)
		yield (func5, file51, file52, 10, lambda: path.exists(flag5))

		"""
		#6 Thread-safe move, move one file in multiple thread, no error
		"""
		file61 = path.join(testdir, 'testMove1.txt')
		file62 = path.join(testdir, 'testMove2.txt')
		flag6  = path.join(testdir, 'testMove1-flag.txt')
		helpers.writeFile(file61)

		def func6(f1, f2):
			try:
				utils.safeMove(f1, f2, tmpdir = testdir)
			except OSError as ex:
				helpers.writeFile(flag6, ex)
		yield (func6, file61, file62, 10, lambda: not path.exists(flag6) and path.exists(file62) and not  path.exists(file61))

		"""
		#7 Thread-safe move, move the same file, nothing happens
		"""
		file63 = path.join(testdir, 'testMove63.txt')
		file64 = path.join(testdir, 'testMove64.txt')
		helpers.writeFile(file63)
		symlink(file63, file64)
		def func63(f1, f2):
			utils.safeMove(f1, f2, tmpdir = testdir)
		yield (func63, file63, file64, 1, lambda: path.isfile(file63) and path.islink(file64), '#7: File 1 is not a file or file 2 is not a link.')

		"""
		#8 Thread-safe move, move the file, without overwrite
		"""
		file65 = path.join(testdir, 'testMove5.txt')
		file66 = path.join(testdir, 'testMove6.txt')
		helpers.writeFile(file65, 65)
		helpers.writeFile(file66, 66)
		def func65(f1, f2):
			utils.safeMove(f1, f2, overwrite = False, tmpdir = testdir)
		yield (func65, file65, file66, 1, lambda: helpers.readFile(file66, int) == 66)

		"""
		#9 Thread-safe move, move the file, with overwrite
		"""
		file67 = path.join(testdir, 'testMove7.txt')
		file68 = path.join(testdir, 'testMove8.txt')
		helpers.writeFile(file67, 67)
		helpers.writeFile(file68, 68)
		def func67(f1, f2):
			utils.safeMove(f1, f2, overwrite = True, tmpdir = testdir)
		yield (func67, file67, file68, 1, lambda: helpers.readFile(file68, int) == 67)

		"""
		#10 Thread-unsafe move, move one file in multiple thread, error happens
		"""
		file71 = path.join(testdir, 'testMove3.txt')
		file72 = path.join(testdir, 'testMove4.txt')
		flag7  = path.join(testdir, 'testMove3-flag.txt')
		helpers.writeFile(file71)

		def func7(f1, f2):
			try:
				rename(f1, f2)
			except OSError as ex:
				helpers.writeFile(flag7, ex)
		yield (func7, file71, file72, 10, lambda: path.exists(flag7) and path.exists(file72) and not  path.exists(file71))

		"""
		#11 Thread-safe safeMoveWithLink
		"""
		file81 = path.join(testdir, 'testMoveWithLink81.txt')
		file82 = path.join(testdir, 'testMoveWithLink82.txt')
		flag8  = path.join(testdir, 'testMoveWithLink8-flag.txt')
		helpers.writeFile(file81)
		def func8(f1, f2):
			try:
				utils.safeMoveWithLink(f1, f2, tmpdir = testdir)
			except OSError as ex:
				helpers.writeFile(flag8, ex)
		yield (func8, file81, file82, 2, lambda: not path.exists(flag8) and path.exists(file81) and  path.islink(file81) and path.exists(file82) and not path.islink(file82))

		"""
		#12 Thread-unsafe safeMoveWithLink
		"""
		file91 = path.join(testdir, 'testMoveWithLink21.txt')
		file92 = path.join(testdir, 'testMoveWithLink22.txt')
		flag9  = path.join(testdir, 'testMoveWithLink2-flag.txt')
		helpers.writeFile(file91)
		def func9(f1, f2):
			try:
				rename(f1, f2)
				symlink(f2, f1)
			except OSError as ex:
				helpers.writeFile(flag9, ex)
		yield (func9, file91, file92, 20, lambda: path.exists(flag9))

		"""
		#13 Thread-safe copy
		"""
		file101 = path.join(testdir, 'testSafeCopy11.txt')
		file102 = path.join(testdir, 'testSafeCopy12.txt')
		flag10  = path.join(testdir, 'testSafeCopy10-flag.txt')
		helpers.writeFile(file101)
		def func10(f1, f2):
			try:
				utils.safeCopy(f1, f2, lambda r, f1, f2: remove(f1) if r else None, tmpdir = testdir)
			except OSError as ex:
				helpers.writeFile(flag10, ex)
		yield (func10, file101, file102, 10, lambda: not path.exists(flag10) and not path.isfile(file101) and path.isfile(file102))

		"""
		#14 Thread-unsafe copy
		"""
		file111 = path.join(testdir, 'testSafeCopy21.txt')
		file112 = path.join(testdir, 'testSafeCopy22.txt')
		flag11  = path.join(testdir, 'testSafeCopy11-flag.txt')
		helpers.writeFile(file111)
		def func11(f1, f2):
			try:
				copyfile(f1, f2)
				remove(f1)
			except (OSError, IOError) as ex:
				helpers.writeFile(flag11, ex)
		yield (func11, file111, file112, 10, lambda: path.exists(flag11) and not path.isfile(file111) and  path.isfile(file112))

		"""
		#15 Thread-safe link
		"""
		file121 = path.join(testdir, 'testSafeLink11.txt')
		file122 = path.join(testdir, 'testSafeLink12.txt')
		flag12  = path.join(testdir, 'testSafeLink1-flag.txt')
		helpers.writeFile(file121)
		def func12(f1, f2):
			try:
				utils.safeLink(file121, file122, lambda r, f1, f2: remove(f1) if r else None, tmpdir = testdir)
			except OSError as ex:
				helpers.writeFile(flag12, ex)
		yield (func12, file121, file122, 10, lambda: not path.exists(flag12) and not path.isfile(file121) and path.islink(file122))

		"""
		#16 Thread-unsafe link
		"""
		file131 = path.join(testdir, 'testSafeLink21.txt')
		file132 = path.join(testdir, 'testSafeLink22.txt')
		flag13  = path.join(testdir, 'testSafeLink2-flag.txt')
		helpers.writeFile(file131)
		def func13(f1, f2):
			try:
				symlink(f1, f2)
				remove(f1)
			except OSError as ex:
				helpers.writeFile(flag13, ex)
		yield (func13, file131, file132, 10, lambda: path.exists(flag13) and not path.isfile(file131) and  path.islink(file132))

		"""
		#17 Thread-safe file exists, dead link removed
		"""
		file141 = path.join(testdir, 'testFileExists141.txt')
		file142 = path.join(testdir, 'testFileExists142.txt')
		flag141 = path.join(testdir, 'testFileExists141-flag.txt')
		helpers.writeFile(file141)
		symlink(file141, file142)
		remove(file141)
		flag142 = not path.exists(file141) and not path.exists(file142) and path.islink(file142)
		# now file21 is a dead link
		def func14(f1, f2):
			r = utils.fileExists(f2, tmpdir = testdir)
			if r or path.exists(f1) or path.exists(f2) or path.islink(f2):
				helpers.writeFile(flag141)
		yield (func14, file141, file142, 1, lambda: flag142 and not path.exists(flag141))

		"""
		#18 Thread-unsafe file exists, dead link not removed
		"""
		file151 = path.join(testdir, 'testFileExists151.txt')
		file152 = path.join(testdir, 'testFileExists152.txt')
		flag151 = path.join(testdir, 'testFileExists151-flag.txt')
		helpers.writeFile(file151)
		symlink(file151, file152)
		remove(file151)
		flag152 = not path.exists(file151) and not path.exists(file152) and path.islink(file152)
		# now file21 is a dead link
		def func15(f1, f2):
			r = path.exists(f2)
			if r or path.exists(f1) or path.exists(f2) or path.islink(f2):
				helpers.writeFile(flag151)
		yield (func15, file151, file152, 1, lambda: flag152 and path.exists(flag151))

		"""
		#19 Targz: source is not a dir
		"""
		filetgz1 = path.join(testdir, 'testTgz1.txt')
		filetgz2 = path.join(testdir, 'testTgz2.tgz')
		filetgzflag1 = path.join(testdir, 'testTgz1-flag.txt')
		def functgz1(f1, f2):
			if utils.targz(f1, f2, tmpdir = testdir):
				helpers.writeFile(filetgzflag1)
		yield (functgz1, filetgz1, filetgz2, 2, lambda: not path.exists(filetgzflag1))

		"""
		#20 Targz: overwrite target
		"""
		filetgz3 = path.join(testdir, 'testTgz3.dir')
		filetgz4 = path.join(testdir, 'testTgz3.tgz')
		makedirs(filetgz3)
		helpers.writeFile(filetgz4, '1')
		def functgz3(f1, f2):
			utils.targz(f1, f2, tmpdir = testdir)
		yield (functgz3, filetgz3, filetgz4, 2, lambda: helpers.readFile(filetgz4) != '1')

		"""
		#21 Targz and untargz
		"""
		filetgz5 = path.join(testdir, 'testTgz5.dir')
		filetgz6 = path.join(testdir, 'testTgz6.tgz')
		filetgz7 = path.join(filetgz5, 'testTgz7.txt')
		filetgz8 = path.join(filetgz5, 'testTgz8.dir')
		filetgz9 = path.join(filetgz8, 'testTgz7.txt')
		makedirs(filetgz5)
		helpers.writeFile(filetgz7, 'Hello')
		def functgz5(f1, f2):
			utils.targz(f1, f2)
			utils.untargz(f2, filetgz8)
		yield (functgz5, filetgz5, filetgz6, 2, lambda: helpers.readFile(filetgz9) == 'Hello')

		"""
		#22 Gz: source is not a file
		"""
		filegz1 = path.join(testdir, 'testGz1.txt')
		filegz2 = path.join(testdir, 'testGz2.gz')
		filegzflag1 = path.join(testdir, 'testGz1-flag.txt')
		def funcgz1(f1, f2):
			if utils.gz(f1, f2, tmpdir = testdir):
				helpers.writeFile(filegzflag1)
		yield (funcgz1, filegz1, filegz2, 2, lambda: not path.exists(filegzflag1))

		"""
		#23 Gz: overwrite target
		"""
		filegz3 = path.join(testdir, 'testGz3.txt')
		filegz4 = path.join(testdir, 'testGz3.gz')
		helpers.writeFile(filegz3, '2')
		helpers.writeFile(filegz4, '1')
		def funcgz3(f1, f2):
			utils.gz(f1, f2, tmpdir = testdir)
		yield (funcgz3, filegz3, filegz4, 2, lambda: helpers.readFile(filegz4) != '1')

		"""
		#24 Gz and ungz
		"""
		filegz5 = path.join(testdir, 'testGz5.txt')
		filegz6 = path.join(testdir, 'testGz6.tgz')
		filegz7 = path.join(testdir, 'testGz7.txt')
		helpers.writeFile(filegz5, 'HelloWorld')
		def funcgz5(f1, f2):
			utils.gz(f1, f2)
			utils.ungz(f2, filegz7)
		yield (funcgz5, filegz5, filegz6, 2, lambda: helpers.readFile(filegz7) == 'HelloWorld')

		"""
		#25 Thread-safe move, move one directory in multiple thread, no error
		"""
		file251 = path.join(testdir, 'testMove251.dir')
		file252 = path.join(testdir, 'testMove252.dir')
		flag25  = path.join(testdir, 'testMove25-flag.txt')
		makedirs(file251)
		makedirs(file252)

		def func25(f1, f2):
			try:
				utils.safeMove(f1, f2, overwrite = True, tmpdir = testdir)
			except OSError as ex:
				helpers.writeFile(flag25, ex)
		yield (func25, file251, file252, 10, lambda: not path.exists(flag25) and path.exists(file252) and not  path.exists(file251))

		"""
		#26 Thread-safe safeMoveWithLink, f1, f2 is the same file, f2 is a link
		"""
		file261 = path.join(testdir, 'testMoveWithLink261.txt')
		file262 = path.join(testdir, 'testMoveWithLink262.txt')
		flag26  = path.join(testdir, 'testMoveWithLink26-flag.txt')
		helpers.writeFile(file261)
		symlink(file261, file262)
		def func26(f1, f2):
			try:
				utils.safeMoveWithLink(f1, f2, tmpdir = testdir, callback = lambda r, f1, f2: None)
			except OSError:
				helpers.writeFile(flag26, traceback.format_exc())
		yield (func26, file261, file262, 100, lambda: not path.exists(flag26) and path.exists(file261) and  path.islink(file261) and path.exists(file262) and not path.islink(file262))

		"""
		#27 Thread-safe safeMoveWithLink, f1 is link and to be removed
		"""
		file271 = path.join(testdir, 'testMoveWithLink271.txt')
		file272 = path.join(testdir, 'testMoveWithLink272.txt')
		flag27  = path.join(testdir, 'testMoveWithLink27-flag.txt')
		helpers.writeFile(file272)
		helpers.createDeadlink(file271)
		def func27(f1, f2):
			try:
				utils.safeMoveWithLink(f1, f2, overwrite = False, tmpdir = testdir)
			except OSError:
				helpers.writeFile(flag27, traceback.format_exc())
		yield (func27, file271, file272, 10, lambda: not path.exists(flag27) and not path.exists(file271) and path.islink(file271) and path.exists(file272) and not path.islink(file272))

		"""
		#28 Thread-safe copy
		"""
		file281 = path.join(testdir, 'testSafeCopy281.dir')
		file282 = path.join(testdir, 'testSafeCopy282.dir')
		flag28  = path.join(testdir, 'testSafeCopy28-flag.txt')
		makedirs(file281)
		symlink(file281, file282)
		def func28(f1, f2):
			try:
				utils.safeCopy(f1, f2, overwrite = False, tmpdir = testdir)
			except OSError:
				helpers.writeFile(flag28, traceback.format_exc())
		yield (func28, file281, file282, 10, lambda: not path.exists(flag28) and path.isdir(file281) and path.isdir(file282))

		"""
		#29 Thread-safe copy
		"""
		file291 = path.join(testdir, 'testSafeCopy291.dir')
		file292 = path.join(testdir, 'testSafeCopy292.dir')
		flag29  = path.join(testdir, 'testSafeCopy29-flag.txt')
		makedirs(file291)
		makedirs(file292)
		def func29(f1, f2):
			try:
				utils.safeCopy(f1, f2, overwrite = True, tmpdir = testdir)
			except OSError:
				helpers.writeFile(flag29, traceback.format_exc())
		yield (func29, file291, file292, 10, lambda: not path.exists(flag29) and path.isdir(file291) and path.isdir(file292))

		"""
		#30 Thread-safe copy
		"""
		file301 = path.join(testdir, 'testSafeCopy301.dir')
		file302 = path.join(testdir, 'testSafeCopy302.dir')
		flag30  = path.join(testdir, 'testSafeCopy30-flag.txt')
		makedirs(file301)
		helpers.writeFile(file302)
		def func30(f1, f2):
			try:
				utils.safeCopy(f1, f2, overwrite = True, tmpdir = testdir)
			except OSError:
				helpers.writeFile(flag30, traceback.format_exc())
		yield (func30, file301, file302, 10, lambda: not path.exists(flag30) and path.isdir(file301) and path.isdir(file302))

		"""
		#31 Thread-safe link, samefile
		"""
		file311 = path.join(testdir, 'testSafeLink311.txt')
		file312 = path.join(testdir, 'testSafeLink312.txt')
		flag31  = path.join(testdir, 'testSafeLink31-flag.txt')
		helpers.writeFile(file311)
		symlink(file311, file312)
		def func31(f1, f2):
			try:
				utils.safeLink(file311, file312, overwrite = True, tmpdir = testdir)
			except OSError as ex:
				helpers.writeFile(flag31, ex)
		yield (func31, file311, file312, 10, lambda: not path.exists(flag31) and path.isfile(file311) and path.islink(file312))

		"""
		#32 Thread-safe link, not the samefile, f1 is dir
		"""
		file321 = path.join(testdir, 'testSafeLink321.dir')
		file322 = path.join(testdir, 'testSafeLink322.txt')
		flag32  = path.join(testdir, 'testSafeLink32-flag.txt')
		makedirs(file321)
		helpers.writeFile(file322)
		def func32(f1, f2):
			try:
				utils.safeLink(file321, file322, overwrite = True, tmpdir = testdir)
			except OSError as ex:
				helpers.writeFile(flag32, ex)
		yield (func32, file321, file322, 10, lambda: not path.exists(flag32) and path.isdir(file321) and path.islink(file322))

		"""
		#33 samefile f1 == f2 with callback
		"""
		file331 = path.join(testdir, 'testSamefile331.txt')
		file332 = path.join(testdir, 'testSamefile331.txt')
		flag33  = path.join(testdir, 'testSamefile33-flag.txt')
		helpers.writeFile(file331)
		def func33(f1, f2):
			utils.samefile(f1, f2, callback = lambda r, f1, f2: helpers.writeFile(flag33) if not r else None, tmpdir = testdir)
		yield func33, file331, file332, 1, lambda: not path.exists(flag33)

		"""
		#34 move f1 == f2 with callback
		"""
		file341 = path.join(testdir, 'testSamefile341.txt')
		file342 = path.join(testdir, 'testSamefile341.txt')
		flag34  = path.join(testdir, 'testSamefile34-flag.txt')
		helpers.writeFile(file341)
		def func34(f1, f2):
			utils.safeMove(f1, f2, callback = lambda r, f1, f2: helpers.writeFile(flag34) if r else None, tmpdir = testdir)
		yield func34, file341, file342, 1, lambda: not path.exists(flag34)

		"""
		#35 move f2 is a deak link with callback
		"""
		file351 = path.join(testdir, 'testSamefile351.txt')
		file352 = path.join(testdir, 'testSamefile352.txt')
		flag35  = path.join(testdir, 'testSamefile35-flag.txt')
		helpers.writeFile(file351)
		helpers.createDeadlink(file352)

		def func35(f1, f2):
			utils.safeMove(f1, f2, callback = lambda r, f1, f2: helpers.writeFile(flag35) if not r else None, tmpdir = testdir)
		yield func35, file351, file352, 1, lambda: not path.exists(flag35)

		"""
		#36 safeMoveWithLink samefile with callback
		"""
		file361 = path.join(testdir, 'testSamefile361.txt')
		file362 = path.join(testdir, 'testSamefile361.txt')
		flag36  = path.join(testdir, 'testSamefile36-flag.txt')
		def func36(f1, f2):
			utils.safeMoveWithLink(f1, f2, callback = lambda r, f1, f2: helpers.writeFile(flag36) if r else None, tmpdir = testdir)
		yield func36, file361, file362, 1, lambda: not path.exists(flag36)

		"""
		#37 safeMoveWithLink, overwrite
		"""
		file371 = path.join(testdir, 'testMoveWithLink371.txt')
		file372 = path.join(testdir, 'testMoveWithLink372.txt')
		flag37  = path.join(testdir, 'testMoveWithLink37-flag.txt')
		helpers.writeFile(file371)
		helpers.writeFile(file372)
		def func37(f1, f2):
			try:
				utils.safeMoveWithLink(f1, f2, tmpdir = testdir, overwrite = True)
			except OSError as ex:
				helpers.writeFile(flag37, ex)
		yield (func37, file371, file372, 10, lambda: not path.exists(flag37) and path.exists(file371) and  path.islink(file371) and path.exists(file372) and not path.islink(file372))

		"""
		#38 safeMoveWithLink, no overwrite
		"""
		file381 = path.join(testdir, 'testMoveWithLink381.txt')
		file382 = path.join(testdir, 'testMoveWithLink382.txt')
		flag38  = path.join(testdir, 'testMoveWithLink38-flag.txt')
		helpers.writeFile(file381)
		helpers.writeFile(file382)
		def func38(f1, f2):
			try:
				utils.safeMoveWithLink(f1, f2, tmpdir = testdir, overwrite = False)
			except OSError as ex:
				helpers.writeFile(flag38, ex)
		yield (func38, file381, file382, 10, lambda: not path.exists(flag38) and path.exists(file381) and not path.islink(file381) and path.exists(file382) and not path.islink(file382))

		"""
		#39 safeMoveWithLink, f2 is a deadlink
		"""
		file391 = path.join(testdir, 'testMoveWithLink391.txt')
		file392 = path.join(testdir, 'testMoveWithLink392.txt')
		flag39  = path.join(testdir, 'testMoveWithLink39-flag.txt')
		helpers.writeFile(file391)
		helpers.createDeadlink(file392)
		def func39(f1, f2):
			try:
				utils.safeMoveWithLink(f1, f2, tmpdir = testdir, overwrite = False)
			except OSError as ex:
				helpers.writeFile(flag39, ex)
		yield (func39, file391, file392, 10, lambda: not path.exists(flag39) and path.exists(file391) and path.islink(file391) and path.exists(file392) and not path.islink(file392))

		"""
		#40 Thread-safe copy samefile with callback
		"""
		file401 = path.join(testdir, 'testSafeCopy401.txt')
		file402 = path.join(testdir, 'testSafeCopy401.txt')
		flag40  = path.join(testdir, 'testSafeCopy40-flag.txt')
		helpers.writeFile(file401)
		def func40(f1, f2):
			utils.safeCopy(f1, f2, lambda r, f1, f2: helpers.writeFile(flag40) if r else None, tmpdir = testdir)
		yield (func40, file401, file402, 1, lambda: not path.exists(flag40))

		"""
		#41 Thread-safe copy no overwrite
		"""
		file411 = path.join(testdir, 'testSafeCopy411.txt')
		file412 = path.join(testdir, 'testSafeCopy412.txt')
		helpers.writeFile(file411, 1)
		helpers.writeFile(file412, 2)
		def func41(f1, f2):
			utils.safeCopy(f1, f2, overwrite = False, tmpdir = testdir)
		yield (func41, file411, file412, 1, lambda: helpers.readFile(file411, int) == 1 and helpers.readFile(file412, int) == 2)

		"""
		#42 Thread-safe copy deadlink
		"""
		file421 = path.join(testdir, 'testSafeCopy421.txt')
		file422 = path.join(testdir, 'testSafeCopy422.txt')
		helpers.writeFile(file421, 1)
		helpers.createDeadlink(file422)
		def func42(f1, f2):
			utils.safeCopy(f1, f2, tmpdir = testdir)
		yield (func42, file421, file422, 1, lambda: helpers.readFile(file422, int) == 1 and helpers.readFile(file422, int) == 1)

		"""
		#43 Thread-safe link samefile
		"""
		file431 = path.join(testdir, 'testSafeLink431.txt')
		file432 = path.join(testdir, 'testSafeLink431.txt')
		flag43  = path.join(testdir, 'testSafeLink43-flag.txt')
		def func43(f1, f2):
			utils.safeLink(file431, file432, lambda r, f1, f2: helpers.writeFile(flag43) if r else None, tmpdir = testdir)
		yield (func43, file431, file432, 1, lambda: not path.exists(flag43))

		"""
		#44 Thread-safe samefile and f2 is a file, f1 is a link
		"""
		file441 = path.join(testdir, 'testSafeLink441.txt')
		file442 = path.join(testdir, 'testSafeLink442.txt')
		helpers.writeFile(file442)
		symlink(file442, file441)
		def func44(f1, f2):
			utils.safeLink(file441, file442, tmpdir = testdir)
		yield (func44, file441, file442, 1, lambda: path.islink(file442) and path.isfile(file441) and not path.islink(file441))

		"""
		#45 untargz, not a file
		"""
		filetgz451 = path.join(testdir, 'testTgz451.dir')
		filetgz452 = path.join(testdir, 'testTgz452')
		flagtgz45  = path.join(testdir, 'testTgz45-flag.txt')
		makedirs(filetgz451)
		def functgz45(f1, f2):
			if utils.untargz(f1, f2):
				helpers.writeFile(flagtgz45)
		yield (functgz45, filetgz451, filetgz452, 1, lambda: not path.exists(flagtgz45))

		"""
		#46 Gz and ungz
		"""
		filegz461 = path.join(testdir, 'testGz461.dir')
		filegz462 = path.join(testdir, 'testGz462')
		flaggz46  = path.join(testdir, 'testGz46.txt')
		makedirs(filegz461)
		def funcgz46(f1, f2):
			if utils.ungz(f1, f2):
				helpers.writeFile(flaggz46)
		yield (funcgz46, filegz461, filegz462, 1, lambda: not path.exists(flaggz46))

		"""
		#47 Thread-safe link no overwrite
		"""
		file431 = path.join(testdir, 'testSafeLink431.txt')
		file432 = path.join(testdir, 'testSafeLink431.txt')
		flag43  = path.join(testdir, 'testSafeLink43-flag.txt')
		def func43(f1, f2):
			utils.safeLink(file431, file432, lambda r, f1, f2: helpers.writeFile(flag43) if r else None, tmpdir = testdir)
		yield (func43, file431, file432, 1, lambda: not path.exists(flag43))

		"""
		#48 Thread-safe link no overwrite
		"""
		file481 = path.join(testdir, 'testSafeLink481.txt')
		file482 = path.join(testdir, 'testSafeLink482.txt')
		helpers.writeFile(file481, 1)
		helpers.writeFile(file482, 2)
		def func48(f1, f2):
			utils.safeLink(f1, f2, overwrite = False, tmpdir = testdir)
		yield (func48, file481, file482, 1, lambda: helpers.readFile(file481, int) == 1 and helpers.readFile(file482, int) == 2)


	def test2FS(self, func, f1, f2, length, state, msg = None):
		utils.Parallel(length, 'thread').run(func, [(f1, f2) for _ in range(length)])
		self.assertTrue(state(), msg)

	def dataProvider_testDirmtime(self, testdir):

		"""
		#0 Empty directory
		"""
		file0 = path.join(testdir, 'testDirmtime0.dir')
		makedirs(file0)
		m0    = path.getmtime(file0)
		yield file0, m0

		"""
		#1 A newer file created
		"""
		dir1  = path.join(testdir, 'testDirmtime1.dir')
		file1 = path.join(dir1, 'mtime1.txt')
		makedirs(dir1)
		helpers.writeFile(file1)
		t     = time()
		utime(file1, (t+2, t+2))
		yield dir1, t+2

		"""
		#2 dir touched
		"""
		dir2  = path.join(testdir, 'testDirmtime2.dir')
		file2 = path.join(dir2, 'mtime2.dir')
		makedirs(file2)
		t = time()
		utime(file2, (t+10, t+10))
		yield dir2, t+10

	def testDirmtime(self, d, mt):
		self.assertEqual(int(utils.dirmtime(d)), int(mt))

	def dataProvider_testFilesig(self, testdir):
		"""
		#0: Empty string
		"""
		yield '', ['', 0]

		"""
		#1: Path not exists
		"""
		yield '/a/b/pathnotexists', False

		"""
		#2: A file
		"""
		filesig1 = path.join(testdir, 'testFilesig1.txt')
		helpers.writeFile(filesig1)
		sig1     = [filesig1, int(path.getmtime(filesig1))]
		yield filesig1, sig1

		"""
		#3: A Link to file
		"""
		filesig2 = path.join(testdir, 'testFilesig2.txt')
		symlink(filesig1, filesig2)
		sig2 = [filesig2, sig1[1]]
		yield filesig2, sig2

		"""
		#4: A link to directory
		"""
		filesig3 = path.join(testdir, 'testFilesig3.dir')
		filesig4 = path.join(testdir, 'testFilesig4.dir')
		makedirs(filesig3)
		symlink(filesig3, filesig4)
		t = int(time())
		utime(filesig3, (t - 10, t - 10))
		sig3 = [filesig4, t - 10]
		yield filesig4, sig3

		"""
		#5: A newer file created
		"""
		filesig5 = path.join(testdir, 'testFilesig5.dir')
		filesig6 = path.join(filesig5, 'testFilesig6.txt')
		makedirs(filesig5)
		helpers.writeFile(filesig6)
		t = int(path.getmtime(filesig6))
		utime(filesig6, (t + 10, t + 10))
		sig5 = [filesig5, t+10]
		yield filesig5, sig5

		"""
		#6: Don't go into the dir
		"""
		yield filesig5, [filesig5, t], False

	def testFilesig(self, f, sig, dirsig = True):
		self.assertEqual(utils.filesig(f, dirsig), sig)

	def dataProvider_testChmodX(self, testdir):
		"""
		#0: plain file, can be made as executable
		"""
		fileChmodx1 = path.join(testdir, 'testChmodX1.txt')
		helpers.writeFile(fileChmodx1)
		yield fileChmodx1, [fileChmodx1], True

		"""
		#1:  plain file, cannot be made as executable
		"""
		fileChmodx2 = '/usr/bin/ldd'
		if path.exists(fileChmodx2):
			yield fileChmodx2, ['/bin/bash', fileChmodx2], True

	def testChmodX(self, f, ret, x):
		self.assertListEqual(utils.chmodX(f), ret)
		self.assertTrue(path.isfile(ret[-1]) and access(ret[-1], X_OK))

	def dataProvider_testChmodXException(self):
		file1 = '/bin/ls'
		if path.exists(file1):
			yield file1,

	def testChmodXException(self, f):
		self.assertRaises(Exception, utils.chmodX, f)

	def dataProvider_testDumbPopen(self):
		yield 'ls', True, 0, False
		yield 'bash -c "exit 1"', True, 1, True
		yield 'ls2', True, 127, True
		yield 'ls2', False, 0, False

	def testDumbPopen(self, cmd, isPopen, rc = 0, shell = False):
		with helpers.captured_output() as (out, err):
			p = utils.dumbPopen(cmd, shell = shell)
			r = p.wait() if isPopen else 0

		self.assertTrue(isinstance(p, Popen) or not isPopen)
		self.assertEqual(out.getvalue(), '')
		self.assertEqual(err.getvalue(), '')
		self.assertEqual(r, rc)

	def dataProvider_testBriefList():
		yield ([0, 1, 2, 3, 4, 5, 6, 7], "0-7")
		yield ([1, 3, 5, 7, 9], "1, 3, 5, 7, 9")
		yield ([1, 3, 5, 7, 9, 4, 8, 12, 13], "1, 3-5, 7-9, 12, 13")
		yield ([13, 9, 5, 7, 4, 3, 8, 1, 12], "1, 3-5, 7-9, 12, 13")

	def testBriefList(self, list2Brief, collapsedStr):
		self.assertEqual(utils.briefList(list2Brief), collapsedStr)

if __name__ == '__main__':
	unittest.main(verbosity=2)
