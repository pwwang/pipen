import copy
import glob
import os
import pickle
import shutil
import sys
import unittest
from inspect import getsource
from StringIO import StringIO

from md5 import md5

rootdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, rootdir)
from pyppl import aggr, channel, proc, utils

class TestProc (unittest.TestCase):

	workdir = './workdir'
	logger  = utils.getLogger('debug', 'TestProc')

	def testRegisterRunner (self):
		if not os.path.exists (self.workdir):
			os.makedirs(self.workdir)

		testfile = os.path.join(self.workdir, 'runner_test.py')
		open(testfile, 'w').write ("""import os, sys
rootdir = "%s"
sys.path.insert(0, rootdir)
from pyppl import runner
class runner_test (runner):

	def __init__ (self, script, config = {}):
		pass
""" % rootdir)
		self.assertTrue (os.path.exists(testfile))
		sys.path.insert(0, self.workdir)
		from runner_test import runner_test
		proc.registerRunner(runner_test)
		
		self.assertTrue (callable (proc.RUNNERS['test'].submit))
		
	def tearDown (self):
		if os.path.exists(self.workdir):
			shutil.rmtree(self.workdir)

	def testInit (self):
		p = proc ('tag')
		self.assertTrue (isinstance (p, proc))

		#from tempfile import gettempdir
		# check initial varialbles
		self.assertEqual (p.id, 'p')
		self.assertEqual (p.tag, 'tag')
		self.assertEqual (p.input, '')
		self.assertEqual (p.indata, {})
		#self.assertEqual (p.output, {})
		self.assertEqual (p.nexts, [])
		self.assertEqual (p.ppldir, os.path.abspath("./workdir"))
		self.assertEqual (p.forks, 1)
		self.assertEqual (p.cache, True)
		self.assertEqual (p.retcodes, [0])
		self.assertEqual (p.echo, False)
		self.assertEqual (p.runner, 'local')
		self.assertEqual (p.exportdir, '')
		self.assertEqual (p.exporthow, 'move')
		self.assertEqual (p.exportow, True)
		self.assertEqual (p.errorhow, 'terminate')
		self.assertEqual (p.errorntry, 3)
		self.assertEqual (p.defaultSh, 'bash')
		self.assertEqual (p.beforeCmd, '')
		self.assertEqual (p.afterCmd, '')
		self.assertEqual (p.workdir, '')
		self.assertEqual (p.sets, [])
		self.assertEqual (p.procvars, {})
		self.assertEqual (p.logger, None)
		self.assertEqual (p.args, {})
		self.assertEqual (p.aggr, None)
		self.assertEqual (p.callback, None)
		self.assertEqual (p.brings, {})
		lognline = {key:0 for key in proc.LOG_NLINE.keys()}
		lognline['prevlog']  = ''
		self.assertEqual (p.lognline, lognline)

	def testGetattr (self):
		p = proc ('getattr')
		self.assertRaises(ValueError, p.__getattr__, 'a')
		# alias
		self.assertEqual (p.lang, 'bash')
		self.assertEqual (p.defaultSh, 'bash')


	def testSetattr (self):
		p = proc ('setattr')

		self.assertRaises (ValueError, p.__setattr__, 'a', 1)
		p.tag = 'setattr2'
		self.assertEqual (p.tag, 'setattr2')
		self.assertEqual (p.config['tag'], 'setattr2')
		self.assertIn ('tag', p.sets)

		# alias
		p.exdir = "./"
		self.assertEqual (p.exportdir, "./")

		# input
		p.input = {"a": [1]}
		self.assertEqual (p.indata, {})
		self.assertEqual (p.config['input'], {'a':[1]})

		# depends
		p2 = proc ('setattr')
		p.depends = p2
		p3 = proc ('setattr')
		self.assertIn (p2, p.depends)
		self.assertIn (p, p2.nexts)
		p.depends = p3
		self.assertNotIn (p2, p.depends)
		self.assertNotIn (p, p2.nexts)
		self.assertIn (p3, p.depends)
		self.assertIn (p, p3.nexts)

	def testCopy (self):
		p = proc('copy')
		p.script = 'echo {#}'

		p.exportdir = rootdir

		pCopy = p.copy('procCopy')
		self.assertEqual (pCopy.id, 'pCopy')
		self.assertEqual (pCopy.tag, 'procCopy')
		self.assertEqual (pCopy.exportdir, rootdir)
		self.assertEqual (pCopy.script, p.script)

	def testSuffix (self):
		p = proc ('tag_unique')
		config        = { key:val for key, val in p.config.iteritems() if key not in ['workdir', 'forks', 'cache', 'retcodes', 'echo', 'runner', 'exportdir', 'exporthow', 'exportow', 'errorhow', 'errorntry'] or key.endswith ('Runner') }
		config['id']  = p.id
		config['tag'] = p.tag
		if config.has_key ('callback'):
			config['callback'] = utils.funcsig(config['callback'])
		# proc is not picklable
		if config.has_key('depends'):
			depends = config['depends']
			pickable_depends = []
			if isinstance(depends, proc):
				depends = [depends]
			elif isinstance(depends, aggr):
				depends = depends.procs
			for depend in depends:
				pickable_depends.append(depend.id + '.' + depend.tag)
			config['depends'] = pickable_depends
			
		if config.has_key ('input') and isinstance(config['input'], dict):
			config['input'] = copy.deepcopy(config['input'])
			for key, val in config['input'].iteritems():
				config['input'][key] = utils.funcSig(val) if callable(val) else val
		
		signature = pickle.dumps (str(config))
		self.assertEqual (p._suffix(), utils.uid(signature))

	def testName (self):
		p = proc('name')
		p.aggr = 'aggr'
		self.assertEqual (p._name (True), "p.name@aggr")
		self.assertEqual (p._name (False), "p.name")

	def testBuildProps (self):
		p1 = proc ('tag1')
		p2 = proc ('tag2')
		p2.depends = p1
		p2.retcodes = "0, 1"
		p2._buildProps()
		self.assertEqual (p2.depends, [p1])
		self.assertEqual (p2.retcodes, [0, 1])
		self.assertEqual (p2.workdir, os.path.join (p2.ppldir, "PyPPL.%s.%s"%(p2._name(False), p2._suffix())))
		self.assertTrue (os.path.exists(p2.workdir))
		self.assertEqual (p1.nexts, [p2])
		self.assertEqual (p1.id, 'p1')
		self.assertEqual (p2.id, 'p2')
		self.assertEqual (p2.jobs, [])
		
		p2 = proc('tag2')
		self.assertRaises (Exception, p2._buildProps)

	def testBuildInput (self):
		self.maxDiff = None
		# argv
		p = proc ('input')
		sys.argv = ["", '1', '2', '3']
		p.input  = "a"
		p._buildInput()
		self.assertEqual (p.indata, {"a": {'data': ['1', '2', '3'], 'type': 'var'}})

		# channels from depends
		p2 = proc ('input')
		p3 = proc ('input')
		p2.props['channel'] = channel.create([1,2,3])
		p3.props['channel'] = channel.create([4,5,6])
		p.depends = [p2, p3]
		p.input   = "a,b"
		p._buildInput()
		self.assertEqual (p.indata, {
			"a": {'data': [1, 2, 3], 'type': 'var'},
			"b": {'data': [4, 5, 6], 'type': 'var'}
		})

		# callable input
		p.input = {"a,b": lambda ch1, ch2: ch1.merge(ch2.map(lambda x: (x[0]*2, )))}
		p._buildInput()
		self.assertEqual (p.indata, {
			"a": {'data': [1, 2, 3], 'type': 'var'},
			"b": {'data': [8, 10, 12], 'type': 'var'}
		})

		# callable different keys
		p.input = {"a": lambda ch1, ch2: ch1, "b": lambda ch1, ch2: ch2.map(lambda x: (x[0]*2,))}
		p._buildInput()
		self.assertEqual (p.indata, {
			"a": {'data': [1, 2, 3], 'type': 'var'},
			"b": {'data': [8, 10, 12], 'type': 'var'}
		})

		# files pattern
		p.input = {"a,b":lambda ch1,ch2:ch1.merge(ch2.map(lambda x: (x[0]*2, ))), "c:files":["./*.py"]*3}
		p._buildInput()
		self.assertEqual (p.indata['a'], {'data': [1, 2, 3], 'type': 'var'})
		self.assertEqual (p.indata['b'], {'data': [8, 10, 12], 'type': 'var'})
		self.assertEqual (p.indata['c']['type'], 'files')
		self.assertEqual (len(p.indata['c']['data']), 3)
		self.assertItemsEqual (p.indata['c']['data'][0], glob.glob("./*.py"))
		self.assertItemsEqual (p.indata['c']['data'][1], glob.glob("./*.py"))
		self.assertItemsEqual (p.indata['c']['data'][2], glob.glob("./*.py"))
		self.assertEqual (p.length, 3)
		self.assertEqual (p.jobs, [None] * 3)
		
		# not enough data
		p.input = {"a,b":[1]}
		self.assertRaisesRegexp(ValueError, r"Not enough", p._buildInput)

		# expect same length channels
		p.input = {"a": [1], "b": [1,2,3]}
		self.assertRaisesRegexp(ValueError, r"Expect same", p._buildInput)

	def testBuildProcVars (self):
		self.maxDiff = None
		p = proc ('pvars')
		p.props['logger'] = self.logger
		p.args = {"a":1, "b":2}
		p._buildProcVars()
		#{'proc.errhow': 'terminate', 'proc.exow': True, 'proc.forks': 1, 'proc.echo': False, 'proc.exdir': '', 'proc.cache': True, 'proc.exhow': 'move', 'proc.errntry': 1, 'proc.workdir': '', 'proc.runner': 'local', 'proc.ppldir': '/data2/junwenwang/panwen/tools/pyppl/tests/workdir', 'proc.args': {}, 'proc.id': 'p', 'proc.lang': 'bash', 'proc.tag': 'pvars', 'proc.length': 0}
		self.assertDictEqual (p.procvars, {
			'proc.errhow': 'terminate', 
			'proc.errorhow': 'terminate', 
			'proc.exow': True, 
			'proc.exportow': True, 
			'proc.forks': 1, 
			'proc.echo': False, 
			'proc.exdir': '', 
			'proc.exportdir': '', 
			'proc.cache': True, 
			'proc.exhow': 'move', 
			'proc.exporthow': 'move', 
			'proc.errntry': 3, 
			'proc.errorntry': 3, 
			'proc.workdir': '', 
			'proc.runner': 'local', 
			'proc.ppldir': '/data2/junwenwang/panwen/tools/pyppl/tests/workdir', 
			'proc.tmpdir': '/data2/junwenwang/panwen/tools/pyppl/tests/workdir', 
			'proc.args': {"a":1, "b":2}, 
			'proc.args.a': 1,
			'proc.args.b': 2,
			'proc.id': 'p', 
			'proc.lang': 'bash', 
			'proc.defaultSh': 'bash', 
			'proc.tag': 'pvars', 
			'proc.length': 0})

	def testBuildJobs (self):
		p = proc ('buildjobs')
		p.props['logger'] = self.logger
		p.input = {"a": range(10)}
		p.output = "x:{{a | lambda x: x*2}}"
		
		p._tidyBeforeRun ()
		self.assertEqual (len(p.jobs), 10)
		self.assertEqual (p.channel.map(lambda x: (int(x[0]),)), channel.create(xrange(0, 20, 2)))
		

	def testReadconfig (self):
		p = proc ('tag')
		p.tag = 'notag'
		p.forks = 1
		config = {
			'tag': 'whatevertag',
			'forks': 10
		}
		p._readConfig (config)
		self.assertEqual (p.tag, 'notag')
		self.assertEqual (p.forks, 1)  # props not changed
		self.assertEqual (p.config['forks'], 1) # props not changed


	def testIscached (self):
		p = proc ('iscached')
		p.props['logger'] = self.logger
		p.script = "echo 1"

		# cache is False
		p.cache = False
		self.assertFalse (p._isCached())

		# dependent
		p.cache = True
		p2 = proc ('iscached')
		p2.props['cached'] = False
		p.depends = p2
		self.assertFalse (p._isCached())

		p.depends = []
		p.input   = {'a': range(10)}
		p._tidyBeforeRun()
		self.assertFalse (p._isCached())
		self.assertEqual (p.ncjobids, range(10))
		
		p.jobs[0].init()
		p.jobs[0].cache()
		self.assertTrue (p.jobs[0].isTrulyCached())
		self.assertFalse (p._isCached())
		self.assertEqual (p.ncjobids, range(1,10))

	def testRunCmd (self):
		prc = proc ()
		prc.props['logger'] = self.logger
		prc.input  = {"input": ["a"]}
		prc.script = 'ls'
		prc._tidyBeforeRun ()
		self.assertEqual (prc._runCmd('beforeCmd'), 0)
		self.assertEqual (prc._runCmd('afterCmd'), 0)

		prc.beforeCmd = 'ls'
		prc.afterCmd = 'bash -c "exit 1"' # error
		prc._tidyBeforeRun ()
		self.assertEqual (prc._runCmd('beforeCmd'), 0)
		self.assertEqual (prc._runCmd('afterCmd'), 1)

		prc.beforeCmd = 'ls'
		prc.echo = True
		prc._tidyBeforeRun ()
		self.assertEqual (prc._runCmd('beforeCmd'), 0)


		prc.afterCmd = 'bash -c "echo 2 >&2; exit 1"'
		prc.echo = False # anyway print stderr
		prc._tidyBeforeRun ()
		self.assertEqual (prc._runCmd('afterCmd'), 1)


		
	def testAlias (self):
		p = proc ('alias')
		p.ppldir = self.workdir
		p.props['logger'] = self.logger
		p.input = {'a':[1]}
		testv = {}
		for k,v in proc.ALIAS.iteritems():
			testv[v] = utils.randstr()
			if k == 'ppldir':   testv[v] = self.workdir
			if v == 'retcodes': testv[v] = [0,1,2]
			p.__setattr__ (k, testv[v])
		p._tidyBeforeRun()
		for k,v in proc.ALIAS.iteritems():
			val1 = p.__getattr__(k)
			val2 = p.__getattr__(v)
			self.assertEqual (val1, testv[v])
			self.assertEqual (val2, testv[v])

if __name__ == '__main__':
	unittest.main()
