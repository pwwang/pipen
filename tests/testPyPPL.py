import path, unittest

import sys
import tempfile
import logging
from os import path, remove
from contextlib import contextmanager
from six import StringIO
from pyppl import PyPPL, utils, logger, ProcTree

def which(program):
	import os
	def is_exe(fpath):
		return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

	fpath, fname = os.path.split(program)
	if fpath:
		if is_exe(program):
			return program
	else:
		for path in os.environ["PATH"].split(os.pathsep):
			path = path.strip('"')
			exe_file = os.path.join(path, program)
			if is_exe(exe_file):
				return exe_file

	return None

class Proc(object):
	
	def __init__(self, id = None, tag = 'notag'):
		self.id = id
		if id is None:
			self.id  = utils.varname()
		self.tag = tag
		self.desc = ''
		self.aggr = ''
		self.depends = []
		self.exdir = ''
		self.resume = ''
		self.profile = ''
		self.props = {
			'resume': ''
		}
		PyPPL._registerProc(self)

	def __repr__(self):
		return '<Proc(id=%s,tag=%s)>' % (self.id, self.tag)

	def setAggr(self, aggr):
		self.aggr = aggr

	def addDepends(self, *ps):
		self.depends.extend(ps)

	def name(self, aggr = False):
		tag   = '.' + self.tag if self.tag and self.tag != 'notag' else ''
		aggr  = '@' + self.aggr if aggr and self.aggr else ''
		return self.id + tag + aggr

	def log(self, k1, k2 = 'log'):
		logger.logger.info('[%s] %s' % (k2, k1))

	def run(self, config):
		logger.logger.info('[ SUBMIT] Running %s' % self.name())

class Aggr(object):

	def __init__(self):
		self.starts = []
		self.ends   = []

import pyppl
pyppl.Proc = Proc
pyppl.Aggr = Aggr

@contextmanager
def captured_output():
	new_out, new_err = StringIO(), StringIO()
	old_out, old_err = sys.stdout, sys.stderr
	try:
		sys.stdout, sys.stderr = new_out, new_err
		yield sys.stdout, sys.stderr
	finally:
		sys.stdout, sys.stderr = old_out, old_err

class TestPyPPL (unittest.TestCase):

	def assertItemsEqual(self, x, y):
		for i in x:
			if i not in y:
				return False
		for i in y:
			if i not in x:
				return False
		return True
	
	def testInit(self):
		with captured_output() as (_, err):
			pyppl = PyPPL()
		self.assertIsInstance(pyppl, PyPPL)
		self.assertIn('Version', err.getvalue())
		self.assertIn('TIPS', err.getvalue())
		
		cfgfile = path.join(tempfile.gettempdir(), 'testInit.json')
		with open(cfgfile, 'w') as f:
			f.write('''{
				"proc": {"forks": 5}
			}
			''')
		
		with captured_output() as (out, err):
			pyppl = PyPPL(config = {
				'proc': {'forks': 10}
			}, cfgfile = cfgfile)
		self.assertIn('Read from %s' % cfgfile, err.getvalue())
		
		with captured_output() as (out, err):
			pyppl = PyPPL(config = {
				'log': {
					'levels': None,
					'file': True
				},
				'proc': {'forks': 10}
			}, cfgfile = cfgfile)
		self.assertNotIn('Read from %s' % cfgfile, err.getvalue())
		self.assertEqual(pyppl.config['proc']['forks'], 10)
		self.assertTrue(path.exists(path.splitext(sys.argv[0])[0] + '.pyppl.log'))
		remove(path.splitext(sys.argv[0])[0] + '.pyppl.log')
		self.assertFalse(path.exists(path.splitext(sys.argv[0])[0] + '.pyppl.log'))
		self.assertEqual(path.expanduser('~/.PyPPL'), PyPPL.DEFAULT_CFGFILES[1])
		self.assertEqual(path.expanduser('~/.PyPPL.json'), PyPPL.DEFAULT_CFGFILES[2])

	def testYamlConfig(self):
		try:
			import yaml
		except ImportError:
			return

		cfgfile = path.join(tempfile.gettempdir(), 'testInit.yaml')
		with open(cfgfile, 'w') as f:
			f.write('''
proc: 
	forks: 5
''')
		with captured_output() as (out, err):
			pyppl = PyPPL(cfgfile = cfgfile)
		self.assertEqual(pyppl.config['proc']['forks'], 5)
		
		with captured_output() as (out, err):
			pyppl = PyPPL(config = {
				'proc': {'forks': 10}
			}, cfgfile = cfgfile)
		self.assertIn('Read from %s' % cfgfile, err.getvalue())
		
		with captured_output() as (out, err):
			pyppl = PyPPL(config = {
				'log': {
					'levels': None,
					'file': True
				},
				'proc': {'forks': 10}
			}, cfgfile = cfgfile)
		self.assertNotIn('Read from %s' % cfgfile, err.getvalue())
		self.assertEqual(pyppl.config['proc']['forks'], 10)
		self.assertEqual(path.expanduser('~/.PyPPL.yaml'), PyPPL.DEFAULT_CFGFILES[0])


	def testRegisterRunner(self):
		class RunnerR1: pass
		PyPPL.registerRunner(RunnerR1)
		self.assertIn('r1', PyPPL.RUNNERS)
		self.assertEqual(PyPPL.RUNNERS['r1'], RunnerR1)

		class AnotherRunner: pass
		PyPPL.registerRunner(AnotherRunner)
		self.assertIn('AnotherRunner', PyPPL.RUNNERS)
		self.assertEqual(PyPPL.RUNNERS['AnotherRunner'], AnotherRunner)
	'''
	def testRegisterCheckProc(self):
		PyPPL.PROCS = []
		p1 = Proc('p1', 'tag')
		p2 = Proc('p2', 'tag')
		p3 = Proc('p1', 'tag')
		with captured_output() as (out, err):
			self.assertRaises(ValueError, PyPPL._checkProc, p3)
		self.assertEqual(len(PyPPL.PROCS), 3)
		self.assertIs(PyPPL.PROCS[0], p1)
		self.assertIs(PyPPL.PROCS[1], p2)
		self.assertIs(PyPPL.PROCS[2], p3)
	'''
	def testAny2Procs(self):
		from collections import OrderedDict
		ProcTree.NODES = OrderedDict()
		ap1  = Proc()
		ap2  = Proc()
		ap3  = Proc()
		ap4  = Proc()
		ap5  = Proc()
		ap6  = Proc(id = 'ap1', tag = 't')
		ap7  = Proc(id = 'ap2', tag = 't')
		ap8  = Proc(id = 'ap3', tag = 't')
		ap10 = Proc(id = 'ap5', tag = 't')
		aggr = Aggr()
		aggr.starts = [ap2, ap3, ap4]
		data = [
			(['ap1.t'], [ap6]),
			(['ap1'], [ap1, "ap1.t"]),
			([aggr], [ap2, ap3, ap4]),
			([ap1, ap2], [ap1, ap2])
		]
		for d in data:
			self.assertItemsEqual(PyPPL._any2procs(*d[0]), d[1])
		self.assertItemsEqual(PyPPL._any2procs(*[d[0] for d in data]), [ap1, ap2, ap3, ap4, ap6])
		self.assertRaises(ValueError, PyPPL._any2procs, 'abc')
		
	def testStart(self):
		from collections import OrderedDict
		ProcTree.NODES = OrderedDict()
		ap1  = Proc()
		ap2  = Proc()
		ap3  = Proc()
		ap4  = Proc()
		ap5  = Proc()
		ap6  = Proc(id = 'ap1', tag = 't')
		ap7  = Proc(id = 'ap2', tag = 't')
		ap8  = Proc(id = 'ap3', tag = 't')
		ap9  = Proc(id = 'ap4', tag = 't')
		ap10 = Proc(id = 'ap5', tag = 't')
		ap10.addDepends(ap1)
		aggr = Aggr()
		aggr.starts = [ap2, ap3, ap4]
		pyppl = PyPPL(config = {
			'log': {
				'levels': None,
				'file': None
			},
			'proc': {'forks': 10}
		})
		pyppl.start('ap1', aggr, ap1, ap2)
		self.assertEqual(len(pyppl.tree.getStarts()), 5)
		for p in [ap1, ap6, ap2, ap3, ap4]:
			self.assertIn(p, pyppl.tree.getStarts())
		
		with captured_output() as (out, err):
			pyppl = PyPPL(config = {
				'log': {
					'levels': 'all',
					'file': None
				}
			})
			pyppl.start(ap1, ap10)
		self.assertIn('Process ap5.t marked as start but will be ignored as it depends on other start processes.', err.getvalue())

	def testshowAllRoutes(self):
		p1 = Proc()
		p2 = Proc(tag = 't@a')
		p3 = Proc(tag = 't@a')
		p2.depends = [p1]
		p3.depends = [p2]
		with captured_output() as (out, err):
			ppl = PyPPL({'log': {'levels': 'all'}})
			ppl2 = ppl.start(p1).showAllRoutes()
		self.assertIs(ppl, ppl2)
		self.assertIn('ALL ROUTES', err.getvalue())
		

	'''
	def testProcRelations(self):
		"""
		         / p3  --- \ 
		p1 -- p2            \    / p8
		  \      \ p4 \       p7 
		    p10         p6  /    \ p9
		           p5 /
		"""
		self.maxDiff = None
		PyPPL.PROCS = []
		p1  = Proc()
		p2  = Proc()
		p3  = Proc()
		p4  = Proc()
		p5  = Proc()
		p6  = Proc()
		p7  = Proc()
		p8  = Proc()
		p9  = Proc()
		p10 = Proc()
		p2.addDepends(p1)
		p10.addDepends(p1)
		p3.addDepends(p2)
		p4.addDepends(p2)
		p6.addDepends(p4, p5)
		p7.addDepends(p3, p6)
		p8.addDepends(p7)
		p9.addDepends(p7)
		pyppl = PyPPL(config = {
			'log': {
				'levels': None,
				'file': None
			},
			'proc': {'forks': 10}
		})

		pyppl.start(p1, p5)
		nexts, ends, paths = pyppl._procRelations()
		self.assertItemsEqual(nexts[id(p1)], [p2, p10])
		self.assertItemsEqual(nexts[id(p2)], [p3, p4])
		self.assertItemsEqual(nexts[id(p3)], [p7])
		self.assertItemsEqual(nexts[id(p4)], [p6])
		self.assertItemsEqual(nexts[id(p5)], [p6])
		self.assertItemsEqual(nexts[id(p6)], [p7])
		self.assertItemsEqual(nexts[id(p7)], [p8, p9])
		self.assertItemsEqual(nexts[id(p8)], [])
		self.assertItemsEqual(nexts[id(p9)], [])
		self.assertItemsEqual(nexts[id(p10)], [])
		self.assertItemsEqual([p10, p8, p9], ends)
		self.assertItemsEqual(paths[id(p1)], [])
		self.assertItemsEqual(paths[id(p2)], [[p1]])
		self.assertItemsEqual(paths[id(p3)], [[p2, p1]])
		self.assertItemsEqual(paths[id(p4)], [[p2, p1]])
		self.assertItemsEqual(paths[id(p5)], [])
		self.assertItemsEqual(paths[id(p6)], [[p4, p2, p1], [p5]])
		self.assertItemsEqual(paths[id(p7)], [[p6, p5], [p6, p4, p2, p1], [p3, p2, p1]])
		self.assertItemsEqual(paths[id(p8)], [[p7, p6, p5], [p7, p6, p4, p2, p1], [p7, p3, p2, p1]])
		self.assertItemsEqual(paths[id(p9)], [[p7, p6, p5], [p7, p6, p4, p2, p1], [p7, p3, p2, p1]])
		self.assertItemsEqual(paths[id(p10)], [[p1]])

		pyppl.nexts = {}
		pyppl.start(p2, p5)
		nexts, ends, paths = pyppl._procRelations()
		self.assertItemsEqual(nexts[id(p1)], [p2, p10])
		self.assertItemsEqual(nexts[id(p2)], [p3, p4])
		self.assertItemsEqual(nexts[id(p3)], [p7])
		self.assertItemsEqual(nexts[id(p4)], [p6])
		self.assertItemsEqual(nexts[id(p5)], [p6])
		self.assertItemsEqual(nexts[id(p6)], [p7])
		self.assertItemsEqual(nexts[id(p7)], [p8, p9])
		self.assertItemsEqual(nexts[id(p8)], [])
		self.assertItemsEqual(nexts[id(p9)], [])
		self.assertItemsEqual(nexts[id(p10)], [])
		self.assertItemsEqual([p8, p9], ends)
		self.assertItemsEqual(paths[id(p1)], [])
		self.assertItemsEqual(paths[id(p2)], [])
		self.assertItemsEqual(paths[id(p3)], [[p2]])
		self.assertItemsEqual(paths[id(p4)], [[p2]])
		self.assertItemsEqual(paths[id(p5)], [])
		self.assertItemsEqual(paths[id(p6)], [[p4, p2], [p5]])
		self.assertItemsEqual(paths[id(p7)], [[p6, p5], [p6, p4, p2], [p3, p2]])
		self.assertItemsEqual(paths[id(p8)], [[p7, p6, p5], [p7, p6, p4, p2], [p7, p3, p2]])
		self.assertItemsEqual(paths[id(p9)], [[p7, p6, p5], [p7, p6, p4, p2], [p7, p3, p2]])
		self.assertItemsEqual(paths[id(p10)], [[p1]])

		PyPPL.PROCS = []
		pyppl._registerProc(p1)
		pyppl.nexts = {}
		pyppl.start(p1)
		nexts, ends, paths = pyppl._procRelations()
		self.assertEqual(nexts, {id(p1): []})
		self.assertEqual(ends, [p1])
		self.assertEqual(paths, {id(p1): []})

		# a simple one:
		PyPPL.PROCS = []
		pyppl.nexts = {}
		pa = Proc()
		pb = Proc()
		pc = Proc()
		pd = Proc()
		pd.addDepends(pc)
		PyPPL._registerProc(pa)
		PyPPL._registerProc(pb)
		PyPPL._registerProc(pc)
		PyPPL._registerProc(pd)
		pyppl.start(pc)
		nexts, ends, paths = pyppl._procRelations()
		self.assertEqual(nexts, {id(pb): [], id(pc): [pd], id(pa): [], id(pd): []})
		self.assertEqual(ends, [pd])
		self.assertEqual(paths, {id(pb): [], id(pc): [], id(pa): [], id(pd): [[pc]]})
	'''


	def testResumeResume2(self):
		self.maxDiff = None
		"""
		         / p3  --- \ 
		p1 -- p2            \    / p8
		  \      \ p4 \       p7 
		    p10         p6  /    \ p9
		           p5 /
		"""
		from collections import OrderedDict
		ProcTree.NODES = OrderedDict()
		p1  = Proc()
		p2  = Proc()
		p3  = Proc()
		p4  = Proc()
		p5  = Proc()
		p6  = Proc()
		p7  = Proc()
		p8  = Proc()
		p9  = Proc()
		p10 = Proc()
		p2.addDepends(p1)
		p10.addDepends(p1)
		p3.addDepends(p2)
		p4.addDepends(p2)
		p6.addDepends(p4, p5)
		p7.addDepends(p3, p6)
		p8.addDepends(p7)
		p9.addDepends(p7)
		pyppl = PyPPL(config = {
			'log': {
				'levels': None,
				'file': None
			},
			'proc': {'forks': 10}
		})

		pyppl.start(p1)
		self.assertRaises(ValueError, pyppl._resume, p4, **{'plus': False})
		pyppl2 = pyppl.resume(p3, p4, p5, p10)
		self.assertIs(pyppl2, pyppl)
		self.assertEqual(p1.resume, 'skip')
		self.assertEqual(p2.resume, 'skip')
		self.assertEqual(p3.resume, 'resume')
		self.assertEqual(p4.resume, 'resume')
		self.assertEqual(p5.resume, 'resume')
		self.assertEqual(p6.resume, '')
		self.assertEqual(p7.resume, '')
		self.assertEqual(p8.resume, '')
		self.assertEqual(p9.resume, '')
		self.assertEqual(p10.resume, 'resume')

		for p in [p1, p2, p3, p4, p5, p6, p7, p8, p9, p10]:
			p.resume = ''
			ProcTree.getNode(p).start = False

		pyppl.tree.starts = []
		pyppl.tree.ends   = []
		self.assertEqual( pyppl.tree.getStarts(), [] )
		pyppl.start(p5)
		self.assertEqual( pyppl.tree.getStarts(), [p5] )
		self.assertRaises(ValueError, pyppl.tree.getEnds)
		self.assertRaises(ValueError, pyppl._resume, p3, p4, **{'plus': True})

		pyppl.tree.starts = []
		pyppl.tree.ends   = []
		pyppl.start(p2, p5)
		self.assertEqual( len(pyppl.tree.getStarts()), 2 )
		self.assertIn(p2, pyppl.tree.getStarts())
		self.assertIn(p5, pyppl.tree.getStarts())
		pyppl2 = pyppl.resume2(p3, p6)
		self.assertIs(pyppl2, pyppl)
		self.assertEqual( len(pyppl.tree.getEnds()), 2 )
		self.assertIn(p8, pyppl.tree.getEnds())
		self.assertIn(p9, pyppl.tree.getEnds())
		self.assertEqual(p1.resume, '')
		self.assertEqual(p2.resume, 'skip+')
		self.assertEqual(p3.resume, 'resume+')
		self.assertEqual(p4.resume, 'skip+')
		self.assertEqual(p5.resume, 'skip+')
		self.assertEqual(p6.resume, 'resume+')
		self.assertEqual(p7.resume, '')
		self.assertEqual(p8.resume, '')
		self.assertEqual(p9.resume, '')
		self.assertEqual(p10.resume, '')
		'''
		with captured_output() as (out, err):
			pyppl = PyPPL(config = {
				'log': {
					'levels': 'all',
					'file': None
				},
				'proc': {'forks': 10}
			})
			pyppl.start(p2, p5)
			pyppl.resume(p3, p4, p6)
		self.assertIn('processes marked for resuming will be skipped, as a resuming process depends on them.', err.getvalue())
		'''

	@unittest.skipIf(not which('dot'), 'Graphviz not installed.')
	def testFlowchart(self):
		tmpdir  = tempfile.gettempdir()
		fcfile  = path.join(tmpdir, 'testFlowchart.svg')
		dotfile = path.join(tmpdir, 'testFlowchart.dot')
		"""
		         / p3  --- \ 
		p1 -- p2            \    / p8
		  \      \ p4 \       p7 
		    p10         p6  /    \ p9
		           p5 /
		"""
		from collections import OrderedDict
		ProcTree.NODES = OrderedDict()
		p1  = Proc()
		p2  = Proc()
		p3  = Proc()
		p4  = Proc()
		p5  = Proc()
		p6  = Proc()
		p7  = Proc()
		p8  = Proc()
		p9  = Proc()
		p10 = Proc()
		p2.addDepends(p1)
		p10.addDepends(p1)
		p3.addDepends(p2)
		p4.addDepends(p2)
		p6.addDepends(p4, p5)
		p7.addDepends(p3, p6)
		p8.addDepends(p7)
		p9.addDepends(p7)
		pyppl = PyPPL(config = {
			'log': {
				'levels': None,
				'file': None
			}
		}).start(p1, p5)
		pyppl2 = pyppl.flowchart(fcfile = fcfile, dotfile = dotfile)
		self.assertIs(pyppl, pyppl2)
		self.assertTrue(path.exists(fcfile))
		self.assertTrue(path.exists(dotfile))
		with open(dotfile) as f:
			a = f.read()
			self.assertFalse(set("""digraph PyPPL {
    "p2" -> "p3"
    "p2" -> "p4"
    "p3" -> "p7"
    "p1" -> "p2"
    "p1" -> "p10"
    "p6" -> "p7"
    "p7" -> "p8"
    "p7" -> "p9"
    "p4" -> "p6"
    "p5" -> "p6"
}
""".splitlines()) - set(a.splitlines()))

	def testRun(self):
		"""
		         / p3  --- \ 
		p1 -- p2            \    / p8
		  \      \ p4 \       p7 
		    p10         p6  /    \ p9
		           p5 /
		"""
		from collections import OrderedDict
		ProcTree.NODES = OrderedDict()
		p1  = Proc()
		p2  = Proc()
		p3  = Proc()
		p4  = Proc()
		p5  = Proc()
		p6  = Proc()
		p7  = Proc()
		p8  = Proc()
		p9  = Proc()
		p10 = Proc()
		p1.profile = 'proc'
		p2.addDepends(p1)
		p10.addDepends(p1)
		p3.addDepends(p2)
		p4.addDepends(p2)
		p6.addDepends(p4, p5)
		p7.addDepends(p3, p6)
		p8.addDepends(p7)
		p9.addDepends(p7)

		with captured_output() as (out, err):
			PyPPL(config = {
				'log': {
					'levels': 'all',
					'file': None
				}
			}).start(p1, p5).run()
		errmsgs = [e for e in err.getvalue().splitlines() if 'SUBMIT' in e]
		errmsgs = [e[(e.index('Running')+8):-4].strip() for e in errmsgs]
		self.assertEqual(errmsgs, ['p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'p7', 'p8', 'p9', 'p10'])

	def testUnRan(self):
		"""
		p3  --- p7 
		   _____/   
		p4 \      
		     p6  
		p5 /
		"""
		from collections import OrderedDict
		ProcTree.NODES = OrderedDict()
		p3  = Proc()
		p4  = Proc()
		p5  = Proc()
		p6  = Proc()
		p7  = Proc()
		p6.addDepends(p4, p5)
		p7.addDepends(p3, p4)
		
		with captured_output() as (out, err):
			ppl = PyPPL(config = {
				'log': {
					'levels': 'all',
					'file': None
				}
			})
			ppl2 = ppl.start(p3, p4).run()
		self.assertIs(ppl, ppl2)
		self.assertIn("p6 won't run as prior processes didn't run: [p5]", err.getvalue())


if __name__ == '__main__':
	unittest.main(verbosity=2)