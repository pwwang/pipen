import path, unittest

import sys
import tempfile

from time import sleep, time
from os import path, remove, makedirs, symlink, fdopen
from subprocess import Popen, PIPE
from contextlib import contextmanager
from six import StringIO
from box import Box
from shutil import rmtree, move, copyfile, copytree
from pyppl import utils

@contextmanager
def captured_output():
	new_out, new_err = StringIO(), StringIO()
	old_out, old_err = sys.stdout, sys.stderr
	try:
		sys.stdout, sys.stderr = new_out, new_err
		yield sys.stdout, sys.stderr
	finally:
		sys.stdout, sys.stderr = old_out, old_err

class Proc(object):
	def __init__(self, default='', d2=''):
		self.id = utils.varname()
	def copy(self, *arg):
		return utils.varname()

class TestUtils (unittest.TestCase):
	
	def testVarname(self):
				
		h = Proc()
		h2 = Proc()
		h3 = Proc(
			default = 'a', 
			d2 = 'c'
		)
		h4 = [Proc()]
		self.assertEqual(h.id, 'h')
		self.assertEqual(h2.id, 'h2')
		self.assertEqual(h3.id, 'h3')
		self.assertEqual(h4[0].id, 'var_0')
		
		v1 = h.copy()
		v2 = h2.copy(
			2,
			3,
			4
		)
		v3 = [h3.copy(
			1,2,
			4
		)]
		self.assertEqual(v1, 'v1')
		self.assertEqual(v2, 'v2')
		self.assertEqual(v3[0], 'var_1')

		def func():
			return utils.varname()

		v = func()
		self.assertEqual(v, 'v')
	
	
	def testMapReduceFilter(self):
		vec = [1, 0, False, '', '0', 2]
		self.assertEqual(utils.map(str, vec), ['1', '0', 'False', '', '0', '2'])
		self.assertEqual(utils.filter(None, vec), [1, '0', 2])
		self.assertEqual(utils.reduce(lambda x,y: str(x) + str(y), vec), '10False02')
	
	def testSplit (self):
		data = [
			("a|b|c", ["a", "b", "c"]),
			('a|b\|c', ["a", "b\\|c"]),
			('a|b\|c|(|)', ["a", "b\\|c", "(|)"]),
			('a|b\|c|(\)|)', ["a", "b\\|c", "(\\)|)"]),
			('a|b\|c|(\)\\\'|)', ["a", "b\\|c", "(\\)\\'|)"]),
		]
		for d in data:
			#pass
			self.assertEqual (utils.split(d[0], "|"), d[1])
		self.assertEqual(utils.split('outdir:dir:{{in.pattern | lambda x: __import__("glob").glob(x)[0] | fn }}_etc', ':'), ["outdir", "dir", "{{in.pattern | lambda x: __import__(\"glob\").glob(x)[0] | fn }}_etc"])
			
	def testDictUpdate (self):
		ref1 = {"c": 3, "d": 9}
		ref2 = {"c": 4}
		orig = {"a":1, "b":ref1}
		newd = {"b":ref2, "c":8}
		utils.dictUpdate (orig, newd)
		self.assertEqual (orig, {"a":1, "b":{"c":4, "d":9}, "c":8})
		orig2 = {"a":1, "b":ref1}
		newd2 = {"b":ref2, "c":8}
		orig2.update(newd2)
		self.assertEqual (orig2, {"a":1, "b":ref2, "c":8})

		newd = {}
		ref3 = {'a':1,'b':2,'c':[3,4],'d':Box({'a':0})}
		utils.dictUpdate(newd, ref3)
		newd['c'][0] = 1
		newd['d'].a  = 1
		self.assertEqual(ref3['c'], [3,4])
		self.assertEqual(ref3['d'].to_dict(), {'a': 0})
		self.assertEqual(newd['c'], [1,4])
		self.assertEqual(newd['d'].to_dict(), {'a':1})
		
	def testFuncSig (self):
		def func1 ():
			pass
		
		func2 = lambda x: x
		func3 = ""
		self.assertEqual (utils.funcsig(func1).strip(), "def func1 ():\n\t\t\tpass")
		self.assertEqual (utils.funcsig(func2).strip(), "func2 = lambda x: x")
		self.assertEqual (utils.funcsig(func3), "None")


		
	def testUid (self):
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
		
		self.assertEqual(utils.uid('a'), 'O4JnVAW7')
		self.assertEqual(utils.uid(''), '6SFsQFoW')
		
	def testFormatsecs(self):
		data = [
			(1, "00:00:01.000"),
			(1.001, "00:00:01.001"),
			(100, "00:01:40.000"),
			(7211, "02:00:11.000"),
		]
		for d in data:
			self.assertEqual (utils.formatSecs(d[0]), d[1])
			
	def testRange(self):
		data = [
			(utils.range(3), [0,1,2]),
			(isinstance(utils.range(1), list), True),
			(utils.range(0), []),
		]
		for d in data:
			self.assertEqual (d[0], d[1])
			
	def testAlwayslist(self):
		string = "a,b, c, 'd,e'"
		l = utils.alwaysList (string)
		self.assertEqual (l, ['a', 'b', 'c', "'d,e'"])
		string = ["o1:var:{{c1}}", "o2:var:{{c2 | __import__('math').pow(float(_), 2.0)}}", "o3:file:{{c3.fn}}2{{c3.ext}}"]
		l = utils.alwaysList (string)
		self.assertEqual (l, string)
		string = {'a': 1}
		self.assertRaises(ValueError, utils.alwaysList, string)
		
	def testProcessEx(self):
	
		def raiseEx():
			return 1/0
		proc = utils.ProcessEx(target = raiseEx)
		proc.start()
		self.assertRaises(ZeroDivisionError, proc.join)
	
	def testFileexists(self):
		testf = path.join(tempfile.gettempdir(), 'testFileexists')
		open(testf, 'w').close()
		
		def target(f):
			if path.exists(f):
				sleep(0.5)
				remove(f)
		p1 = utils.ProcessEx(target = target, args = (testf, ))
		p2 = utils.ProcessEx(target = target, args = (testf, ))
		p1.start()
		p2.start()
		p1.join()
		self.assertRaises(OSError, p2.join)
		
		open(testf, 'w').close()
		def callback(e, f):
			if path.exists(f):
				remove(f)
				
		procs = []
		for _ in range(10):
			p = utils.ProcessEx(target = utils.fileExists, args = (testf, callback))
			procs.append(p)
			p.start()
		for p in procs:
			p.join()
	
	def testSamefile(self):
		f1 = path.join(tempfile.gettempdir(), 'samefile1')
		f2 = path.join(tempfile.gettempdir(), 'samefile2')
		
		def makesamefile(file1, file2):
			open(file1, 'w').close()
			if path.exists(file2):
				remove(file2)
			symlink(file1, file2)
		
		makesamefile(f1, f2)
		
		def samefile(file1, file2):
			if path.samefile(file1, file2):
				sleep(.1)
				remove(file2)
			
		thr1 = utils.ProcessEx(target = samefile, args=(f1, f2))
		thr2 = utils.ProcessEx(target = samefile, args=(f1, f2))
		thr1.start()
		thr2.start()
		with self.assertRaises(OSError):
			thr1.join()
			thr2.join()
		
		def callback(sf, file1, file2):
			if sf:
				remove(file2)
				open(file2, 'w').close()

		procs = []
		for i in range(10):
			thr = utils.ProcessEx(target = utils.samefile, args=(f1, f2, callback))
			procs.append(thr)
			thr.start()
		for thr in procs:
			thr.join()

	def testSamefileSamefile(self):
		f = path.join(tempfile.gettempdir(), 'samefile1')
		ret = utils.samefile(f, f)
		self.assertTrue(ret)

			
	def testSaferemove(self):
		f1 = path.join(tempfile.gettempdir(), 'testSaferemove1')
		f2 = path.join(tempfile.gettempdir(), 'testSaferemove2')
		if not path.exists(f1):
			open(f1, 'w').close()
		if not path.exists(f2):
			makedirs(f2)
		
		def target(f1, f2):
			remove(f1)
			rmtree(f2)
		
		procs = []
		for i in range(10):
			thr = utils.ProcessEx(target = target, args=(f1, f2))
			thr.start()
			procs.append(thr)
		
		with self.assertRaises(OSError):
			for p in procs:
				p.join()
				
		def target2(f1, f2):
			utils.safeRemove(f1)
			utils.safeRemove(f2)
				
		procs = []
		for i in range(10):
			thr = utils.ProcessEx(target = target2, args=(f1, f2))
			thr.start()
			procs.append(thr)
		
		for p in procs:
			p.join()
			
		self.assertFalse(path.exists(f1))
		self.assertFalse(path.exists(f2))
			
	def testSafemove(self):
		f1 = path.join(tempfile.gettempdir(), 'testSafemove1')
		f2 = path.join(tempfile.gettempdir(), 'testSafemove2')
		f3 = path.join(tempfile.gettempdir(), 'testSafemove3')
		f4 = path.join(tempfile.gettempdir(), 'testSafemove4')
		utils.safeRemove(f1)
		utils.safeRemove(f2)
		utils.safeRemove(f3)
		utils.safeRemove(f4)
		if not path.exists(f1):
			open(f1, 'w').close()
		if not path.exists(f2):
			makedirs(f2)
		if path.exists(f3):
			remove(f3)
		if not path.exists(f4):
			open(f4, 'w').close()
		
		def target(f1, f2, f3, f4):
			move(f1, f3)
			move(f2, f4)

		procs = []
		for i in range(10):
			thr = utils.ProcessEx(target = target, args=(f1, f2, f3, f4))
			thr.start()
			procs.append(thr)
		
		with self.assertRaises((OSError, IOError)):
			for p in procs:
				p.join()
			
		sleep (.5)
		
		if not path.exists(f1):
			open(f1, 'w').close()
		if not path.exists(f2):
			makedirs(f2)
		if path.exists(f3):
			remove(f3)
		if not path.exists(f4):
			open(f4, 'w').close()
		
		self.assertTrue(path.exists(f1))
		
		def target2(f1, f2, f3, f4):
			utils.safeMove(f1, f3)
			utils.safeMove(f2, f4)
				
		procs = []
		for i in range(10):
			thr = utils.ProcessEx(target = target2, args=(f1, f2, f3, f4))
			thr.start()
			procs.append(thr)
		
		for p in procs:
			p.join()
		
		self.assertFalse(path.exists(f1))
		self.assertFalse(path.exists(f2))
		self.assertTrue(path.exists(f3))
		self.assertTrue(path.exists(f4))

		# create dead link: f1
		utils.safeLink(f3, f1)
		utils.safeRemove(f3)
		ret = utils.safeMove(f4, f1)
		self.assertTrue(ret)


	def testSafeMoveNotExists(self):
		ret = utils.safeMove('/a/b/c/NotExist', 'x')
		self.assertFalse(ret)

		# overwrite file
		f1 = path.join(tempfile.gettempdir(), 'testSafeMoveNotExists1')
		f2 = path.join(tempfile.gettempdir(), 'testSafeMoveNotExists2')
		f3 = path.join(tempfile.gettempdir(), 'testSafeMoveNotExists3')
		utils.safeRemove(f1)
		utils.safeRemove(f2)
		utils.safeRemove(f3)
		open(f1, 'w').close()
		open(f2, 'w').close()
		ret = utils.safeMove(f1, f2)
		self.assertTrue(ret)

		# overwrite dir
		utils.safeRemove(f1)
		utils.safeRemove(f2)
		makedirs(f1)
		makedirs(f2)
		ret = utils.safeMove(f1, f2)
		self.assertTrue(ret)

		# remove dead link
		utils.safeRemove(f1)
		utils.safeRemove(f2)
		open(f1, 'w').close()
		symlink(f2, f3)
		utils.safeRemove(f3)
		ret = utils.safeMove(f1, f2)
		self.assertTrue(ret)

		
	def testSafemovewithlink(self):
		f1 = path.join(tempfile.gettempdir(), 'Safemovewithlink')
		f2 = path.join(tempfile.gettempdir(), 'Safemovewithlink2')
		f3 = path.join(tempfile.gettempdir(), 'Safemovewithlink3')
		f4 = path.join(tempfile.gettempdir(), 'Safemovewithlink4')
		utils.safeRemove(f1)
		utils.safeRemove(f2)
		utils.safeRemove(f3)
		utils.safeRemove(f4)
		open(f1, 'w').close()
		makedirs(f2)
		open(f4, 'w').close()
		
		def target(f1, f2, f3, f4):
			move(f1, f3)
			symlink(f3, f1)
			move(f2, f4)
			symlink(f4, f2)

		procs = []
		for i in range(10):
			thr = utils.ProcessEx(target = target, args=(f1, f2, f3, f4))
			thr.start()
			procs.append(thr)
		
		with self.assertRaises(OSError):
			for p in procs:
				p.join()
				
		sleep (.5)
		utils.safeRemove(f1)
		utils.safeRemove(f2)
		utils.safeRemove(f3)
		utils.safeRemove(f4)
		
		open(f1, 'w').close()
		makedirs(f2)
		open(f4, 'w').close()
		
		self.assertTrue(path.exists(f1))
		
		def target2(f1, f2, f3, f4):
			utils.safeMoveWithLink(f1, f3)
			utils.safeMoveWithLink(f2, f4)
				
		procs = []
		for i in range(10):
			thr = utils.ProcessEx(target = target2, args=(f1, f2, f3, f4))
			thr.start()
			procs.append(thr)
		
		for p in procs:
			p.join()
		
		self.assertTrue(path.islink(f1))
		self.assertTrue(path.islink(f2))
		self.assertTrue(path.exists(f3))
		self.assertTrue(path.exists(f4))

		# if src is a link, linked to dst
		utils.safeRemove(f1)
		utils.safeRemove(f2)
		utils.safeRemove(f3)
		utils.safeRemove(f4)
		with open(f1, 'w') as fout:
			fout.write('f1')
		utils.safeLink(f1, f2)
		self.assertFalse(utils.safeMoveWithLink(f2, f1))

		# if src is a link, not linked to dst
		open(f3, 'w').close()
		self.assertFalse(utils.safeMoveWithLink(f2, f3, overwrite = False))

		# overwrite
		self.assertTrue(utils.safeMoveWithLink(f2, f3))
		with open(f3) as fin3, open(f1) as fin1:
			self.assertEqual(fin3.read(), fin1.read())
		self.assertTrue(path.islink(f2))
		self.assertTrue(path.samefile(f2, f3))

		# if src is a link and dst not exists
		self.assertTrue(utils.safeMoveWithLink(f2, f4))
		with open(f3) as fin3, open(f4) as fin4:
			self.assertEqual(fin3.read(), fin4.read())
		self.assertTrue(path.samefile(f2, f4))

		ret = utils.safeMoveWithLink("/a/b/c/NotExists", 'x')
		self.assertFalse(ret)

		utils.safeRemove(f1)
		utils.safeRemove(f2)
		utils.safeRemove(f3)
		utils.safeRemove(f4)

		open(f1, 'w').close()
		utils.safeLink(f1, f2)
		ret = utils.safeMoveWithLink(f1, f2, overwrite = False)
		self.assertFalse(ret)

		utils.safeRemove(f1)
		open(f3, 'w').close()
		ret = utils.safeMoveWithLink(f3, f2, overwrite = True)
		self.assertTrue(ret)


			
	def testSafecopy(self):
		f1 = path.join(tempfile.gettempdir(), 'testSafecopy')
		f2 = path.join(tempfile.gettempdir(), 'testSafecopy2')
		f3 = path.join(tempfile.gettempdir(), 'testSafecopy3')
		f4 = path.join(tempfile.gettempdir(), 'testSafecopy4')
		utils.safeRemove(f1)
		utils.safeRemove(f2)
		utils.safeRemove(f3)
		utils.safeRemove(f4)
		if not path.exists(f1):
			open(f1, 'w').close()
		if not path.exists(f2):
			makedirs(f2)
		if path.exists(f3):
			remove(f3)
		if not path.exists(f4):
			open(f4, 'w').close()
		
		def target(f1, f2, f3, f4):
			copyfile(f1, f3)
			copytree(f4, f2)

		procs = []
		for i in range(10):
			thr = utils.ProcessEx(target = target, args=(f1, f2, f3, f4))
			thr.start()
			procs.append(thr)
		
		with self.assertRaises(OSError):
			for p in procs:
				p.join()
				
		sleep (.5)
		utils.safeRemove(f1)
		utils.safeRemove(f2)
		utils.safeRemove(f3)
		utils.safeRemove(f4)
		
		if not path.exists(f1):
			open(f1, 'w').close()
		if not path.exists(f2):
			makedirs(f2)
		if path.exists(f3):
			remove(f3)
		if not path.exists(f4):
			open(f4, 'w').close()
		
		self.assertTrue(path.exists(f1))
		
		def target2(f1, f2, f3, f4):
			utils.safeCopy(f1, f3)
			utils.safeCopy(f2, f4)
				
		procs = []
		for i in range(10):
			thr = utils.ProcessEx(target = target2, args=(f1, f2, f3, f4))
			thr.start()
			procs.append(thr)
		
		for p in procs:
			p.join()
		
		self.assertTrue(path.exists(f1))
		self.assertTrue(path.exists(f2))
		self.assertTrue(path.exists(f3))
		self.assertTrue(path.exists(f4))

		ret = utils.safeCopy("/a/b/c/NotExists", "x")
		self.assertFalse(ret)
		
		f1 = path.join(tempfile.gettempdir(), 'testSafecopyfile1')
		f2 = path.join(tempfile.gettempdir(), 'testSafecopyfile2')
		open(f1, 'w').close()
		open(f2, 'w').close()
		ret = utils.safeCopy(f1, f2)
		self.assertTrue(ret)

		d1 = path.join(tempfile.gettempdir(), 'testSafecopydir1')
		d2 = path.join(tempfile.gettempdir(), 'testSafecopydir2')
		utils.safeRemove(d1)
		utils.safeRemove(d2)
		makedirs(d1)
		makedirs(d2)
		ret = utils.safeCopy(d1, d2)
		self.assertTrue(ret)

		
	def testSafelink(self):
		f0 = path.join(tempfile.gettempdir(), 'testSafelink0')
		f1 = path.join(tempfile.gettempdir(), 'testSafelink')
		f2 = path.join(tempfile.gettempdir(), 'testSafelink2')
		f3 = path.join(tempfile.gettempdir(), 'testSafelink3')
		f4 = path.join(tempfile.gettempdir(), 'testSafelink4')
		utils.safeRemove(f0)
		utils.safeRemove(f1)
		utils.safeRemove(f2)
		utils.safeRemove(f3)
		utils.safeRemove(f4)
		open(f0, 'w').close()
		open(f1, 'w').close()
		makedirs(f2)
		open(f4, 'w').close()

		self.assertFalse(utils.safeLink(f1, f0, overwrite = False))
		
		def target(f1, f2, f3, f4):
			symlink(f1, f3)
			symlink(f4, f2)

		procs = []
		for i in range(10):
			thr = utils.ProcessEx(target = target, args=(f1, f2, f3, f4))
			thr.start()
			procs.append(thr)
		
		with self.assertRaises(OSError):
			for p in procs:
				p.join()
				
		sleep (.5)
		utils.safeRemove(f1)
		utils.safeRemove(f2)
		utils.safeRemove(f3)
		utils.safeRemove(f4)
		
		if not path.exists(f1):
			open(f1, 'w').close()
		if not path.exists(f2):
			makedirs(f2)
		if path.exists(f3):
			remove(f3)
		if not path.exists(f4):
			open(f4, 'w').close()
		
		self.assertTrue(path.exists(f1))
		
		def target2(f1, f2, f3, f4):
			utils.safeLink(f1, f3)
			utils.safeLink(f2, f4)
				
		procs = []
		for i in range(10):
			thr = utils.ProcessEx(target = target2, args=(f1, f2, f3, f4))
			thr.start()
			procs.append(thr)
		
		for p in procs:
			p.join()
		
		self.assertTrue(path.exists(f1))
		self.assertTrue(path.exists(f2))
		self.assertTrue(path.islink(f3))
		self.assertTrue(path.islink(f4))

		ret = utils.safeLink("/a/b/c/NotExist", "x")
		self.assertFalse(ret)

		d1 = path.join(tempfile.gettempdir(), 'testSafelinkdir1')
		d2 = path.join(tempfile.gettempdir(), 'testSafelinkdir2')
		utils.safeRemove(d1)
		utils.safeRemove(d2)
		makedirs(d1)
		makedirs(d2)
		ret = utils.safeLink(d1, d2)
		self.assertTrue(ret)
		
	def testTargz(self):
		f1 = path.join(tempfile.gettempdir(), 'testTargz')
		f2 = path.join(tempfile.gettempdir(), 'testTargz2')
		f3 = path.join(tempfile.gettempdir(), 'testTargz.tgz')
		f4 = path.join(tempfile.gettempdir(), 'testTargz2.tgz')
		f5 = path.join(f1, 'a.txt')
		utils.safeRemove(f1)
		utils.safeRemove(f2)
		utils.safeRemove(f3)
		utils.safeRemove(f4)
		
		makedirs(f1)
		open(f2, 'w').close()
		open(f3, 'w').close()
		open(f5, 'w').close()
		self.assertFalse(utils.targz(f1, f3, overwrite = False))
		utils.safeRemove(f3)
		self.assertTrue(utils.targz(f1, f3))
		self.assertFalse(utils.targz(f2, f4))
		self.assertTrue(path.isfile(f3))
		self.assertFalse(path.isfile(f4))
		
		self.assertFalse(utils.untargz(f3, f1, False))
		utils.safeRemove(f1)
		self.assertTrue(utils.untargz(f3, f1))
		self.assertTrue(path.isdir(f1))
		self.assertTrue(path.isfile(f5))
		
	def testGz(self):
		f1 = path.join(tempfile.gettempdir(), 'testTargz')
		f2 = path.join(tempfile.gettempdir(), 'testTargz2')
		f3 = path.join(tempfile.gettempdir(), 'testTargz.gz')
		f4 = path.join(tempfile.gettempdir(), 'testTargz2.gz')
		utils.safeRemove(f1)
		utils.safeRemove(f2)
		utils.safeRemove(f3)
		utils.safeRemove(f4)
		
		open(f1, 'w').close()
		open(f3, 'w').close()
		self.assertFalse(utils.gz(f1, f3, overwrite = False))
		utils.safeRemove(f3)
		self.assertTrue(utils.gz(f1, f3))
		self.assertFalse(utils.gz(f2, f4))
		self.assertTrue(path.isfile(f3))
		self.assertFalse(path.isfile(f4))
		
		self.assertFalse(utils.ungz(f3, f1, False))
		utils.safeRemove(f1)
		self.assertTrue(utils.ungz(f3, f1))
		self.assertTrue(path.isfile(f1))

		ret = utils.ungz("/a/b/c/NotExist", "x")
		self.assertFalse(ret)
		ret = utils.untargz("/a/b/c/NotExist", "x")
		self.assertFalse(ret)
		
	def testDirmtimeFilesig(self):
		d1 = path.join(tempfile.gettempdir(), 'testDirmtime')
		d2 = path.join(d1, 'testDirmtime2')
		utils.safeRemove(d2)
		self.assertEqual(utils.dirmtime(d2), 0)
		self.assertFalse(utils.filesig(d2))
		makedirs(d2)
		mtime = int(path.getmtime(d2))
		self.assertEqual(int(utils.dirmtime(d1)), mtime)
		self.assertEqual(utils.filesig(d1), [d1, int(mtime)])
		f1 = path.join(d2, 'a.txt')
		open(f1, 'w').close()
		mtime = int(path.getmtime(f1))
		self.assertEqual(int(utils.dirmtime(d1)), mtime)
		self.assertEqual(utils.filesig(d1), [d1, mtime])
		self.assertEqual(utils.filesig(f1), [f1, mtime])
		f2 = path.join(d2, 'a.link')
		symlink(f1, f2)
		self.assertEqual(int(utils.dirmtime(d1)), mtime)
		self.assertEqual(utils.filesig(d1), [d1, mtime])
		utils.safeRemove(f2)
		self.assertEqual(utils.dirmtime(f1), 0)
		
	def testChmodx(self):
		f = path.join(tempfile.gettempdir(), 'testChmodx')
		l = path.join(tempfile.gettempdir(), 'testChmodx.link')
		utils.safeRemove(f)
		self.assertRaises(Exception, utils.chmodX, f)
		with open(f, 'w') as fout:
			fout.write('#!/usr/bin/env python')
		self.assertEqual(utils.chmodX(f), [f])
		utils.safeLink(f, l)
		self.assertEqual(utils.chmodX(l), [f])

		self.assertRaises(Exception, utils.chmodX, '/a/b/c/NotExists')

	def testDumbPopen(self):
		cmd = ['ls', '-l', path.abspath(path.dirname(__file__))]
		with captured_output() as (out, err):
			rc = utils.dumbPopen(cmd).wait()	
		self.assertEqual(rc, 0)
		self.assertEqual(out.getvalue(), '')
		self.assertEqual(err.getvalue(), '')

		p = Popen(cmd, stdout=PIPE, stderr=PIPE)
		stdout, _ = p.communicate()
		self.assertTrue(path.basename(__file__) in str(stdout))

	def testParallel(self):
		globalVars = []
		def func(a, b):
			sleep(.5)
			globalVars.append(a)
			globalVars.append(b)
		
		t0 = time()
		utils.parallel(func, [(1,2), (3,4), (5,6), (7,8)], nthread = 4)
		t = time() - t0
		self.assertEqual(sorted(globalVars), [1,2,3,4,5,6,7,8])
		self.assertLess(t, 2)




if __name__ == '__main__':
	unittest.main(verbosity=2)