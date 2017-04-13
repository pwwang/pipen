import unittest
import sys
import os, shutil
rootdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, rootdir)
from pyppl import utils

class TestUtils (unittest.TestCase):

	def testSplit (self):
		data = [
			("a|b|c", ["a", "b", "c"]),
			('a|b\|c', ["a", "b\\|c"]),
			('a|b\|c|(|)', ["a", "b\\|c", "(|)"]),
			('a|b\|c|(\)|)', ["a", "b\\|c", "(\\)|)"]),
			('a|b\|c|(\)\\\'|)', ["a", "b\\|c", "(\\)\\'|)"]),
		]
		for d in data:
			self.assertEqual (utils.split(d[0], "|"), d[1])

	def testFormat (self):
		data = [
			("The directory is: {{path | __import__('os').path.dirname(_)}}", "The directory is: /a/b", {"path": "/a/b/c.txt"}),
			("The directory is: {{path | __import__('os').path.dirname(_)}}", "The directory is: ../c/d", {"path": "../c/d/x.txt"}),
			("{{v | .upper()}}", "HELLO", {"v": "hello"}),
			("{{v | .find('|')}}", '3', {"v": "hel|lo"}),
			("{{v | len(_)}}", '5', {"v": "world"}),
			("{{v | (lambda x: x[0].upper() + x[1:])(_)}}", "World", {"v": "world"}),
			("{{v | .upper() | (lambda x: x+'_suffix')(_)}}", "HELLO_suffix", {"v": "hello"}),
			("{{v | .upper() | [2:]}}", "LLO", {"v": "hello"}),
			("{{c2 | __import__('math').pow(_, 2.0) }}", '4.0', {"c2": 2}),
			("{{genefile.fn | .split('_') | [1] }}", '4', {"genefile.fn": "gene_4"}),
			("{{genefile.fn | .split('_')[0] }}", 'gene', {"genefile.fn": "gene_4"}),
			("{{v | sum(_)}}", "10", {"v": [1,2,3,4]}),
			("{{v | map(str, _) | (lambda x: '_'.join(x))(_)}}", "1_2_3_4", {"v": [1,2,3,4]}),
			("{{v | (lambda x: x['a'] if x.has_key('a') else '')(_)}}", '1', {"v": {"a": 1, "b": 2}}),
			("{{v | __import__('json').dumps(_)}}", '{"a": 1, "b": 2}', {"v": {"a": 1, "b": 2}}),
		]
		for d in data:
			self.assertEqual (utils.format(d[0], d[2]), d[1])

	def testVarname (self):
		def func ():
			return utils.varname(func.__name__)
		
		funcName = func()
		self.assertEqual(funcName, 'funcName')
		self.assertTrue(func().startswith('func_')) 
		
		funcName2= func (
			
		)
		self.assertEqual(funcName2, 'funcName2')
		
		class aclass (object):
			def __init__ (self):
				self.id = utils.varname (self.__class__.__name__)
				
			def method (self):
				return utils.varname ('\w+\.' + self.method.__name__)
		obj = aclass()
		self.assertEqual (obj.id, 'obj')
		
		objMethod = obj.method()
		self.assertEqual (objMethod, 'objMethod')
		
	def testDictUpdate (self):
		ref1  = {"c": 3, "d": 9}
		ref2  = {"c": 4}
		orig = {"a":1, "b":ref1}
		newd = {"b":ref2, "c":8}
		utils.dictUpdate (orig, newd)
		self.assertEqual (orig, {"a":1, "b":{"c":4, "d":9}, "c":8})
		orig2 = {"a":1, "b":ref1}
		newd2 = {"b":ref2, "c":8}
		orig2.update(newd2)
		self.assertEqual (orig2, {"a":1, "b":ref2, "c":8})
		
	def testFuncSig (self):
		def func1 ():
			pass
		
		func2 = lambda x: x
		func3 = ""
		self.assertEqual (utils.funcSig(func1).strip(), "def func1 ():\n\t\t\tpass")
		self.assertEqual (utils.funcSig(func2).strip(), "func2 = lambda x: x")
		self.assertEqual (utils.funcSig(func3), "None")
		
	def testUid (self):
		import random, string
		
		def randomword(length):
		   return ''.join(random.choice(string.lowercase) for i in range(length))
		
		uids = {}
		for i in range (10000):
			s = randomword (10)
			uid = utils.uid (s)
			uids[uid] = 1
		self.assertEqual (len (uids.keys()), 10000)
		
	def testTargz (self):
		if os.path.exists ("./test/"):
			shutil.rmtree ("./test/")
		testdir = "./test/tgzfiles/tgzdir"
		if not os.path.exists (testdir):
			os.makedirs (testdir)
		tgzfile = "./test/test.tgz"
		open("./test/tgzfiles/a.txt", 'w').close()
		open("./test/tgzfiles/b.txt", 'w').close()
		open("./test/tgzfiles/tgzdir/b.txt", 'w').close()
		open("./test/tgzfiles/tgzdir/c.txt", 'w').close()
		utils.targz (tgzfile, "./test/tgzfiles")
		self.assertTrue (os.path.exists(tgzfile))
		
		shutil.rmtree ("./test/tgzfiles")
		os.makedirs ("./test/tgzfiles")
		utils.untargz (tgzfile, "./test/tgzfiles")
		self.assertTrue (os.path.exists("./test/tgzfiles/a.txt"))
		self.assertTrue (os.path.exists("./test/tgzfiles/b.txt"))
		self.assertTrue (os.path.exists("./test/tgzfiles/tgzdir/b.txt"))
		self.assertTrue (os.path.exists("./test/tgzfiles/tgzdir/c.txt"))
		shutil.rmtree ("./test/")
		
	def testGz (self):
		if os.path.exists ("./test/"):
			shutil.rmtree ("./test/")
		os.makedirs ("./test/")
		orfile = "./test/gz.txt"
		gzfile = orfile + '.gz'
		open(orfile, 'w').close()
		utils.gz (gzfile, orfile)
		self.assertTrue (os.path.exists(gzfile))
		os.remove (orfile)
		self.assertFalse (os.path.exists(orfile))
		utils.ungz (gzfile, orfile)
		self.assertTrue (os.path.exists(orfile))
		shutil.rmtree ("./test/")
		
	def testFileSig (self):
		if os.path.exists ("./test/"):
			shutil.rmtree ("./test/")
		os.makedirs ("./test/")
		thefile = "./test/filesig.txt"
		open(thefile, 'w').write('')
		sig = utils.fileSig (thefile)
		from time import sleep
		sleep (.1)
		open(thefile, 'w').write('')
		self.assertNotEqual (sig, utils.fileSig(thefile))
		shutil.rmtree ("./test/")
		
	def testAlwaysList(self):
		string = "a,b, c, 'd,e'"
		l = utils.alwaysList (string)
		self.assertEqual (l, ['a', 'b', 'c', "'d,e'"])
		string = ["o1:var:{{c1}}", "o2:var:{{c2 | __import__('math').pow(float(_), 2.0)}}", "o3:file:{{c3.fn}}2{{c3.ext}}"]
		l = utils.alwaysList (string)
		self.assertEqual (l, string)
		
	def testSanitizeOutKey (self):
		testdata = [
			["a", ('__out.1__', 'var', 'a')],
			["key:val", ('key', 'var', 'val')],
			["file:val", ('__out.2__', 'file', 'val')],
			["a:var:c", ("a", "var", "c")]
		]
		for data in testdata:
			self.assertEqual(utils.sanitizeOutKey(data[0]), data[1])
			
	def testChmodX (self):
		
		if os.path.exists ("./test/"):
			shutil.rmtree ("./test/")
		os.makedirs ("./test/")
		thefile = "./test/chmodx.txt"
		open(thefile, 'w').close()
		self.assertEqual ([os.path.realpath(thefile)], utils.chmodX (thefile))
		shutil.rmtree ("./test/")
		
	def testLogger (self):
		logger1 = utils.getLogger(name='logger1')
		logger2 = utils.getLogger(name='logger2')
		logger1.info ('logger1')
		logger2.info ('logger2')
		
		logger2 = logger1
		logger2.info ('logger3')
		
if __name__ == '__main__':
	unittest.main()
