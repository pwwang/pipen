from os import environ
environ['PYPPL_default__log'] = 'py:{"levels": "all"}'
import helpers, testly, unittest

from os import path, remove, makedirs
from shutil import rmtree
from tempfile import gettempdir
from collections import OrderedDict
from glob import glob
from pyppl import Proc, PyPPL, ProcTree, Aggr
from pyppl.runners import RunnerLocal, RunnerSge, RunnerSlurm, RunnerSsh, RunnerDry
from pyppl.exception import PyPPLProcRelationError, PyPPLConfigError
from pyppl.utils import config

class TestPyPPL(testly.TestCase):

	def setUpMeta(self):
		self.testdir = path.join(gettempdir(), 'PyPPL_unittest', 'TestPyPPL')
		if path.exists(self.testdir):
			rmtree(self.testdir)
		makedirs(self.testdir)
		
	def dataProvider_testInit(self):
		yield {'_log': {'file': False}}, None, {}, {'theme': 'default'}, [], ['PYPPL', 'TIPS']
		yield {'forks': 8, '_log': {'file': False}}, None, {'forks': 8}, {'theme': 'default'}, [], ['PYPPL', 'TIPS']
		
		# default conf files
		if helpers.moduleInstalled('yaml'):
			ymlfile = path.join(self.testdir, 'config.yaml')
			helpers.writeFile(ymlfile, [
				'default:',
				'  forks: 10'
			])
		
		j1file = path.join(self.testdir, 'config1.json')
		helpers.writeFile(j1file, '{"default": {"forks": 8}}')
		
		j2file = path.join(self.testdir, 'config2.json')
		helpers.writeFile(j2file, '{"default": {"forks": 6}}')
		
		logfile = path.join(self.testdir, 'init.log')
		
		yield {'_flowchart': {'theme': 'dark'}, '_log': {'file': False}}, None, {'forks': 8}, {'theme': 'dark'}, [j1file]
		yield {'_log': {'file': False}, '_flowchart': {'theme': 'default'}}, None, {'forks': 6}, {'theme': 'default'}, [j1file, j2file]
		yield {'_log': {'file': False}}, None, {'forks': 8}, {'theme': 'default'}, [j2file, j1file]
		yield {'_log': {'file': False}}, j1file, {'forks': 8}, {'theme': 'default'}, [j2file]
		yield {'forks': 4, '_log': {'file': False} }, j1file, {'forks': 4}, {'theme': 'default'}, [j2file]
		
		if helpers.moduleInstalled('yaml'):
			yield {'_log': {'file': False}}, ymlfile, {'forks': 10}, {'theme': 'default'}, [j2file, j1file]
			yield {'forks': 4, '_log': {'file': False}}, ymlfile, {'forks': 4}, {'theme': 'default'}, [j2file, j1file]
			yield {'forks': 4, '_log': {'file': False}}, j1file, {'forks': 4}, {'theme': 'default'}, [j2file, ymlfile]
		
	def testInit(self, cfg, cfgfile, outconf, outfcconf, dftconffiles = [], errs = []):
		config._load(*dftconffiles)
		with helpers.captured_output() as (out, err):
			pp = PyPPL(cfg, cfgfile)
		stderr = err.getvalue()
		self.assertIsInstance(pp, PyPPL)
		self.assertIsInstance(pp.tree, ProcTree)
		pp.config.forks = pp.config.int('forks')
		self.assertDictContains(outconf, pp.config)
		self.assertDictEqual(pp.config._flowchart, outfcconf)
		for err in errs:
			self.assertIn(err, stderr)
			stderr = stderr[(stderr.find(err) + len(err)):]
			
	
	def dataProvider_testRegisterProc(self):
		pRegisterProc = Proc()
		pRegisterProc1 = Proc()
		yield pRegisterProc,
		yield pRegisterProc1,
	
	def testRegisterProc(self, p):
		PyPPL._registerProc(p)
		node = ProcTree.NODES[p]
		self.assertIs(node.proc, p)
		
	def dataProvider_testAny2Procs(self):
		pAny2Procs1 = Proc()
		pAny2Procs2 = Proc()
		pAny2Procs3 = Proc()
		pAny2Procs4 = Proc()
		pAny2Procs51 = Proc(tag = '51', id = 'pAny2Procs5')
		pAny2Procs52 = Proc(tag = '52', id = 'pAny2Procs5')
		pAny2Procs6 = Proc()
		pAny2Procs7 = Proc()
		aAggr = Aggr(pAny2Procs6, pAny2Procs7)
		aAggr.starts = [aAggr.pAny2Procs6, aAggr.pAny2Procs7]
		yield [pAny2Procs1], [pAny2Procs1]
		yield ['abc'], []
		yield [aAggr], [aAggr.pAny2Procs6, aAggr.pAny2Procs7]
		yield ['pAny2Procs5'], [pAny2Procs51, pAny2Procs52]
		yield ['pAny2Procs5.51'], [pAny2Procs51]
		yield ['pAny2Procs1.notag'], [pAny2Procs1]
		yield ['pAny2Procs5', aAggr, [pAny2Procs2, 'pAny2Procs1.notag']], [pAny2Procs51, pAny2Procs52, pAny2Procs1, pAny2Procs2, aAggr.pAny2Procs6, aAggr.pAny2Procs7]
		
	def testAny2Procs(self, args, procs):
		self.assertCountEqual(PyPPL._any2procs(args), procs)
			
	def dataProvider_testStart(self):
		'''
		         / p3  --- \ 
		p1 -- p2            \    / p8
		  \      \ p4 \       p7 
		    p10         p6  /    \ p9
		           p5 /
		'''
		with helpers.log2str():
			pp = PyPPL({'_log': {'file': None}})
		pStart1 = Proc()
		pStart2 = Proc()
		pStart3 = Proc()
		pStart4 = Proc()
		pStart5 = Proc()
		pStart6 = Proc()
		pStart7 = Proc()
		pStart8 = Proc()
		pStart9 = Proc()
		pStart10 = Proc()
		pStart9.depends = pStart7
		pStart8.depends = pStart7
		pStart7.depends = pStart3, pStart6
		pStart3.depends = pStart2
		pStart6.depends = pStart4, pStart5
		pStart3.depends = pStart2
		pStart4.depends = pStart2
		pStart2.depends = pStart1
		pStart10.depends = pStart1
		
		yield pp, pStart1, [pStart1]
		yield pp, [pStart1, pStart5], [pStart1, pStart5]
		yield pp, [pStart1, pStart5, pStart2], [pStart1, pStart5], [
			'WARNING',
			'Start process pStart2 ignored, depending on [pStart1]'
		]
			
	def testStart(self, pp, starts, outstarts, errs = []):
		with helpers.log2str(levels = 'all') as (out, err):
			self.assertIs(pp.start(starts), pp)
		for outstart in outstarts:
			self.assertTrue(ProcTree.NODES[outstart].start)
		stderr = err.getvalue()
		for err in errs:
			self.assertIn(err, stderr)
			stderr = stderr[(stderr.find(err) + len(err)):]
			
	def dataProvider_test_resume(self):
		'''
		         / p3  --- \ 
		p1 -- p2            \    / p8
		  \      \ p4 \       p7 
		    p10         p6  /    \ p9
		           p5 /
		'''
		with helpers.log2str():
			pp = PyPPL({'_log': {'file': None}})
		p_resume1 = Proc()
		p_resume2 = Proc()
		p_resume3 = Proc()
		p_resume4 = Proc()
		p_resume5 = Proc()
		p_resume6 = Proc()
		p_resume7 = Proc()
		p_resume8 = Proc()
		p_resume9 = Proc()
		p_resume10 = Proc()
		p_resume9.depends = p_resume7
		p_resume8.depends = p_resume7
		p_resume7.depends = p_resume3, p_resume6
		p_resume3.depends = p_resume2
		p_resume6.depends = p_resume4, p_resume5
		p_resume3.depends = p_resume2
		p_resume4.depends = p_resume2
		p_resume2.depends = p_resume1
		p_resume10.depends = p_resume1
		yield pp, [p_resume1, p_resume5], [p_resume2, p_resume6], True, [p_resume1, p_resume5], PyPPLProcRelationError, 'One of the routes cannot be achived from resumed processes: \'p_resume10 <- \[p_resume1\]\''
		yield pp, [p_resume1, p_resume5], [p_resume1, p_resume6], True, [p_resume5]
		yield pp, [p_resume1, p_resume5], [p_resume1, p_resume3, p_resume6], False, [p_resume5, p_resume2, p_resume4]
			
	def test_resume(self, pp, starts, resumes, plus, skips, exception = None, msg = None):
		pp.tree = ProcTree()
		for node in ProcTree.NODES.values():
			node.proc.resume = ''
		pp.start(starts)
		#helpers.log2sys()
		skip   = 'skip+' if plus else 'skip'
		resume = 'resume+' if plus else 'resume'
		if exception:
			self.assertRaisesRegex(exception, msg, pp._resume, *resumes, plus = plus)
		else:
			pp._resume(*resumes, plus = plus)
			for r in resumes:
				self.assertEqual(r.resume, resume)
			for s in skips:
				self.assertEqual(s.resume, skip)
				
	def dataProvider_testResume1(self):
		with helpers.log2str():
			pp = PyPPL({'_log': {'file': None}})
		pResume11 = Proc()
		pResume12 = Proc()
		pResume13 = Proc()
		pResume13.depends = pResume12
		pResume12.depends = pResume11
		yield pp, pResume11, []
		yield pp, pResume11, [pResume12]
		
	def testResume1(self, pp, start, procs):
		pp.tree = ProcTree()
		pp.start(start).resume(procs)
		if not procs:
			for node in ProcTree.NODES.values():
				self.assertEqual(node.proc.resume, '')
		else:
			for node in ProcTree.NODES.values():
				self.assertIn(node.proc.resume, ['', 'skip', 'resume'])
				
	def dataProvider_testResume2(self):
		with helpers.log2str():
			pp = PyPPL({'_log': {'file': None}})
		pResume21 = Proc()
		pResume22 = Proc()
		pResume23 = Proc()
		pResume23.depends = pResume22
		pResume22.depends = pResume21
		yield pp, pResume21, []
		yield pp, pResume21, [pResume22]
		
	def testResume2(self, pp, start, procs):
		pp.tree = ProcTree()
		pp.start(start).resume2(procs)
		if not procs:
			for proc in ProcTree.NODES.keys():
				if not proc.id.startswith('pResume2'): continue
				self.assertEqual(proc.resume, '')
		else:
			for proc in ProcTree.NODES.keys():
				if not proc.id.startswith('pResume2'): continue
				self.assertIn(proc.resume, ['', 'skip+', 'resume+'])
	'''			
	def dataProvider_testGetProfile(self):
		yield {'log': {'file': None}, 'proc': {'id': 'a'}}, 'proc', {}, PyPPLConfigError, 'Cannot set a universal id for all process in configuration: \'a\''
		yield {'log': {'file': None}, 'proc': {}, 'sge': {}}, 'sge', {'runner': 'sge'}
		yield {'log': {'file': None}, 'proc': {}, 'haha': {'tag': 'new'}}, 'haha', {'runner': 'local', 'tag': 'new'}, None, None, [
			'WARNING',
			'No runner specified in profile \'haha\', will use local runner.'
		]
		
	def testGetProfile(self, inconf, profile, config, exception = None, msg = None, errs = []):
		PyPPL.DEFAULT_CFGFILES = []
		with helpers.log2str():
			pp = PyPPL(inconf)
		if exception:
			self.assertRaisesRegex(exception, msg, pp._getProfile, profile)
		else:
			with helpers.log2str(levels = 'all') as (out, err):
				c = pp._getProfile(profile)
			stderr = err.getvalue()
			self.assertEqual(c, config)
			for err in errs:
				self.assertIn(err, stderr)
	'''			
	def dataProvider_testShowAllRoutes(self):
		'''
		         / p3  --- \ 
		p1 -- p2            \    / p8
		  \      \ p4 \       p7 
		    p10         p6  /    \ p9
		           p5 /
		'''
		pShowAllRoutes1 = Proc()
		pShowAllRoutes2 = Proc()
		pShowAllRoutes3 = Proc()
		pShowAllRoutes4 = Proc()
		pShowAllRoutes5 = Proc()
		pShowAllRoutes6 = Proc()
		pShowAllRoutes7 = Proc()
		pShowAllRoutes8 = Proc()
		pShowAllRoutes9 = Proc()
		pShowAllRoutes10 = Proc()
		pShowAllRoutes3.depends = pShowAllRoutes2
		pShowAllRoutes6.depends = pShowAllRoutes4, pShowAllRoutes5
		pShowAllRoutes3.depends = pShowAllRoutes2
		pShowAllRoutes4.depends = pShowAllRoutes2
		pShowAllRoutes2.depends = pShowAllRoutes1
		pShowAllRoutes10.depends = pShowAllRoutes1
		aAggr = Aggr(
			pShowAllRoutes7,
			pShowAllRoutes8,
			pShowAllRoutes9
		)
		aAggr.starts = [aAggr.pShowAllRoutes7]
		aAggr.pShowAllRoutes8.depends = aAggr.pShowAllRoutes7
		aAggr.pShowAllRoutes9.depends = aAggr.pShowAllRoutes7
		aAggr.depends = [pShowAllRoutes3, pShowAllRoutes6]
		yield [pShowAllRoutes1, pShowAllRoutes5], [
			'DEBUG',
			'* pShowAllRoutes1 -> pShowAllRoutes10',
			'pShowAllRoutes1 -> pShowAllRoutes2 -> pShowAllRoutes3 -> [aAggr]',
			'* pShowAllRoutes1 -> pShowAllRoutes2 -> pShowAllRoutes4 -> pShowAllRoutes6 -> [aAggr]',
			'* pShowAllRoutes5 -> pShowAllRoutes6 -> [aAggr]'
		]
				
	def testShowAllRoutes(self, start, errs):
		with helpers.log2str():
			pp = PyPPL({'_log': {'file': None}})
		pp.start(start)
		with helpers.log2str(levels = 'all') as (out, err):
			pp.showAllRoutes()
		stderr = err.getvalue()
		for err in errs:
			self.assertIn(err, stderr)
			stderr = stderr[(stderr.find(err) + len(err)):]
	
	def dataProvider_testFlowchart(self):
		'''
		         / p3  --- \ 
		p1 -- p2            \    / p8
		  \      \ p4 \       p7 
		    p10         p6  /    \ p9
		           p5 /
		'''
		pFlowchart1 = Proc()
		pFlowchart2 = Proc()
		pFlowchart3 = Proc()
		pFlowchart4 = Proc()
		pFlowchart5 = Proc()
		pFlowchart6 = Proc()
		pFlowchart7 = Proc()
		pFlowchart8 = Proc()
		pFlowchart9 = Proc()
		pFlowchart10 = Proc()
		pFlowchart3.depends = pFlowchart2
		pFlowchart6.depends = pFlowchart4, pFlowchart5
		pFlowchart3.depends = pFlowchart2
		pFlowchart4.depends = pFlowchart2
		pFlowchart2.depends = pFlowchart1
		pFlowchart10.depends = pFlowchart1
		aAggr = Aggr(
			pFlowchart7,
			pFlowchart8,
			pFlowchart9
		)
		aAggr.starts = [aAggr.pFlowchart7]
		aAggr.pFlowchart8.depends = aAggr.pFlowchart7
		aAggr.pFlowchart9.depends = aAggr.pFlowchart7
		aAggr.depends = [pFlowchart3, pFlowchart6]
		
		dotfile = path.join(self.testdir, 'test.dot')
		fcfile  = path.join(self.testdir, 'test.svg')
		yield [pFlowchart1, pFlowchart5], fcfile, dotfile, [
			'DEBUG',
			'* pFlowchart1 -> pFlowchart10',
			'pFlowchart1 -> pFlowchart2 -> pFlowchart3 -> [aAggr]',
			'* pFlowchart1 -> pFlowchart2 -> pFlowchart4 -> pFlowchart6 -> [aAggr]',
			'* pFlowchart5 -> pFlowchart6 -> [aAggr]',
			'INFO',
			'Flowchart file saved to: %s' % fcfile,
			'DOT file saved to: %s' % dotfile,
		]
		
		yield [pFlowchart1, pFlowchart5], fcfile, None, [
			'DEBUG',
			'* pFlowchart1 -> pFlowchart10',
			'pFlowchart1 -> pFlowchart2 -> pFlowchart3 -> [aAggr]',
			'* pFlowchart1 -> pFlowchart2 -> pFlowchart4 -> pFlowchart6 -> [aAggr]',
			'* pFlowchart5 -> pFlowchart6 -> [aAggr]',
			'INFO',
			'Flowchart file saved to: %s' % fcfile,
			'DOT file saved to: %s' % dotfile,
		]

	@unittest.skipIf(not helpers.moduleInstalled('graphviz'), 'graphviz not installed.')
	def testFlowchart(self, start, fcfile, dotfile, errs = []):

		with helpers.log2str():
			pp = PyPPL({'_log': {'file': None}})
		pp.start(start)
		with helpers.log2str(levels = 'all') as (out, err):
			pp.flowchart(fcfile = fcfile, dotfile = dotfile)
		self.assertTrue(path.isfile(fcfile))
		self.assertTrue(path.isfile(dotfile or path.splitext(fcfile)[0] + '.dot'))
		stderr = err.getvalue()
		for err in errs:
			self.assertIn(err, stderr)
			stderr = stderr[(stderr.find(err) + len(err)):]
	
	def dataProvider_testRun(self):
		'''
		         / p3  --- \ 
		p1 -- p2            \    / p8
		  \      \ p4 \       p7 
		    p10         p6  /    \ p9
		           p5 /
		'''
		pRun0 = Proc()
		pRun1 = pRun0.copy()
		pRun2 = Proc()
		pRun3 = Proc()
		pRun4 = Proc()
		pRun5 = Proc()
		pRun6 = Proc()
		pRun7 = Proc()
		pRun8 = Proc()
		pRun9 = Proc()
		pRun10 = Proc()
		pRun3.depends = pRun2
		pRun6.depends = pRun4, pRun5
		pRun3.depends = pRun2
		pRun4.depends = pRun2
		pRun2.depends = pRun1
		pRun10.depends = pRun1
		aAggr = Aggr(
			pRun7,
			pRun8,
			pRun9
		)
		aAggr.starts = [aAggr.pRun7]
		aAggr.pRun8.depends = aAggr.pRun7
		aAggr.pRun9.depends = aAggr.pRun7
		aAggr.depends = [pRun3, pRun6]
		yield [pRun1, pRun5], 'profile', 'sge', [
			'pRun1 (pRun0): No description.',
			'pRun2: No description.',
			'pRun3: No description.',
			'pRun4: No description.',
			'pRun5: No description.',
			'pRun6: No description.',
			'pRun10: No description.',
			'pRun7@aAggr: No description.',
			'pRun8@aAggr: No description.',
			'pRun9@aAggr: No description.',
		]

		# pRun21 -> pRun22
		# pRun23 -/
		#       \-> pRun24
		pRun21 = Proc()
		pRun23 = Proc()
		pRun22 = Proc()
		pRun22.depends = pRun21, pRun23
		yield [pRun21], 'profile', 'local', ["pRun22 won't run as path can't be reached: pRun22 <- pRun23"]


			
	def testRun(self, start, profile, runner, errs = []):
		with helpers.log2str():
			pp = PyPPL({'_log': {'file': None}, 'ppldir': self.testdir, 'runner': runner})
		import sys
		pp.start(start)
		argv = sys.argv
		sys.argv = [sys.argv[0]]
		#helpers.log2sys()
		pp.config._load({profile: dict(runner = runner)})
		with helpers.log2str(levels = 'all') as (out, err):
			pp.run(profile)
		#print out.getvalue()
		#print err.getvalue()
		sys.argv = argv
		for s in start:
			self.assertEqual(s.config.runner, profile, msg = ('Profile different: %s, %s for ' % (s.config.runner, profile)) + repr(s))
			self.assertEqual(s.runner, runner, msg = ('Real runner differnet: %s, %s for ' % (s.runner, runner)) + repr(s))
		stderr = err.getvalue()
		for err in errs:
			self.assertIn(err, stderr)
			stderr = stderr[(stderr.find(err) + len(err)):]
			
	def dataProvider_testRegisterRunner(self):
		yield RunnerLocal, 'local'
		yield RunnerSsh, 'ssh'
		yield RunnerDry, 'dry'
		yield RunnerSge, 'sge'
		yield RunnerSlurm, 'slurm'
		class xxx(object): pass
		yield xxx, 'xxx'
		class RunnerYyy(object): pass
		yield RunnerYyy, 'yyy'
		
		
	def testRegisterRunner(self, runner, name):
		if name in PyPPL.RUNNERS:
			del PyPPL.RUNNERS[name]
		PyPPL.registerRunner(runner)
		self.assertIs(PyPPL.RUNNERS[name], runner)
		

if __name__ == '__main__':
	testly.main(verbosity=2)