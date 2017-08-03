import os
import shutil
import sys
import unittest
from os import utime

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
			("The directory is: {{path | dirname}}", "The directory is: /a/b", {"path": "/a/b/c.txt"}),
			("The basename is: {{path | basename}}", "The basename is: c.txt", {"path": "/a/b/c.txt"}),
			("The basename is: {{path | basename.orig}}", "The basename is: c[1].txt", {"path": "/a/b/c[1].txt"}),
			("The basename is: {{path | basename}}", "The basename is: c.txt", {"path": "/a/b/c[1].txt"}),
			("The filename is: {{path | filename}}", "The filename is: c", {"path": "/a/b/c.txt"}),
			("The filename is: {{path | fn}}", "The filename is: c", {"path": "/a/b/c.txt"}),
			("The filename is: {{path | fn.orig}}", "The filename is: c[1]", {"path": "/a/b/c[1].txt"}),
			("The filename is: {{path | fn}}", "The filename is: c", {"path": "/a/b/c[1].txt"}),
			("The ext is: {{path | ext}}", "The ext is: .txt", {"path": "/a/b/c.txt"}),
			("The prefix is: {{path | prefix}}", "The prefix is: /a/b/c.d", {"path": "/a/b/c.d.txt"}),
			("The prefix is: {{path | prefix.orig}}", "The prefix is: /a/b/c.d[1]", {"path": "/a/b/c.d[1].txt"}),
			("The prefix is: {{path | prefix}}", "The prefix is: /a/b/c.d", {"path": "/a/b/c.d[1].txt"}),
			("The directory is: {{path | __import__('os').path.dirname(_)}}", "The directory is: ../c/d", {"path": "../c/d/x.txt"}),
			("The directory is: {{path | dirname}}", "The directory is: ../c/d", {"path": "../c/d/x.txt"}),
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
			("{{v | list(map(str, _)) | (lambda x: '_'.join(x))(_)}}", "1_2_3_4", {"v": [1,2,3,4]}),
			("{{v | (lambda x: x['a'] if 'a' in x else '')(_)}}", '1', {"v": {"a": 1, "b": 2}}),
			("{{v | __import__('json').dumps(_)}}", '{"a": 1}', {"v": {"a": 1}}),
			("{{a|Rbool}},{{b|Rbool}},{{c|Rbool}},{{d|Rbool}}", "TRUE,FALSE,TRUE,FALSE", {"a":1, "b":0, "c":True, "d":False}),
			("{{a|realpath}}", os.path.realpath(__file__), {"a":__file__}),
			("{{a|quote}}", '"a"', {"a":'a'}),
			("{{a|asquote}}", '"a" "b" "c"', {"a":['a', 'b', 'c']}),
			("{{a|acquote}}", '"a","b","c"', {"a":['a', 'b', 'c']}),
			("{{a|squote}}", "'a'", {"a":'a'}),
		]
		for d in data:
			self.assertEqual (utils.format(d[0], d[2]), d[1])

	def testDefineFormatShortCuts (self):
		utils.format.shorts['aaa'] = "lambda x: x.replace('aaa', 'bbb')"
		self.assertEqual (utils.format("{{a|aaa}}", {"a": "1aaa2"}), "1bbb2")

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
		self.assertEqual (utils.funcsig(func1).strip(), "def func1 ():\n\t\t\tpass")
		self.assertEqual (utils.funcsig(func2).strip(), "func2 = lambda x: x")
		self.assertEqual (utils.funcsig(func3), "None")
		
	def testUid (self):
		import random, string
		
		def randomword(length):
		   return ''.join(random.choice(list('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890')) for i in range(length)).encode('utf-8')
		
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
		with open(thefile, 'w') as f:
			f.write('')
		sig = utils.filesig (thefile)
		from time import sleep
		sleep (1)
		utime (thefile, None)
		self.assertNotEqual (sig, utils.filesig(thefile))
		shutil.rmtree ("./test/")
		
	def testAlwaysList(self):
		string = "a,b, c, 'd,e'"
		l = utils.alwaysList (string)
		self.assertEqual (l, ['a', 'b', 'c', "'d,e'"])
		string = ["o1:var:{{c1}}", "o2:var:{{c2 | __import__('math').pow(float(_), 2.0)}}", "o3:file:{{c3.fn}}2{{c3.ext}}"]
		l = utils.alwaysList (string)
		self.assertEqual (l, string)
	
	def testChmodX (self):
		
		if os.path.exists ("./test/"):
			shutil.rmtree ("./test/")
		os.makedirs ("./test/")
		thefile = "./test/chmodx.txt"
		open(thefile, 'w').close()
		self.assertEqual ([os.path.realpath(thefile)], utils.chmodX (thefile))
		shutil.rmtree ("./test/")
		
if __name__ == '__main__':
	unittest.main()
