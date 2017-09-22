import path, unittest

import sys
import tempfile
from os import path
from time import sleep
from pyppl import Proc, logger, templates, utils, Channel, PyPPL, Job

from contextlib import contextmanager
from six import StringIO
@contextmanager
def captured_output():
	new_out, new_err = StringIO(), StringIO()
	old_out, old_err = sys.stdout, sys.stderr
	try:
		sys.stdout, sys.stderr = new_out, new_err
		yield sys.stdout, sys.stderr
	finally:
		sys.stdout, sys.stderr = old_out, old_err

tmpdir = tempfile.gettempdir()

class Aggr(object):
	def __init__(self, *ps):
		self.ends = ps

class RunnerTestNR(object):
	def __init__(self, job):
		self.job = job
	
	def isRunning(self):
		return False

	def submit(self):
		logger.logger.info('[submit]submit job %s\n' % self.job.index)
		p = utils.dumbPopen(['bash', self.job.script], shell=False)
		self.job.rc(p.wait())
	
	def wait(self):
		pass

	def finish(self):
		pass

class RunnerTestR(RunnerTestNR):
	
	def isRunning(self):
		return True


PyPPL.registerRunner(RunnerTestNR)
PyPPL.registerRunner(RunnerTestR)

import pyppl
pyppl.Aggr = Aggr

class TestProc (unittest.TestCase):

	# shorthands
	assertPathExists = lambda self, x: self.assertTrue(path.exists(x))
	assertPathNotExists = lambda self, x: self.assertFalse(path.exists(x))

	def testInit(self):
		self.assertRaises(ValueError, Proc, **{'tag': 'a b'})
		p = Proc()
		self.assertEqual(p.id, 'p')
		self.assertEqual(p.afterCmd, '')
		self.assertEqual(p.aggr, None)
		self.assertEqual(p.args, {})
		self.assertEqual(p.beforeCmd, '')
		self.assertEqual(p.brings, {})
		self.assertEqual(p.cache, True)
		self.assertEqual(p.callfront, None)
		self.assertEqual(p.callback, None)
		self.assertEqual(p.channel, [])
		self.assertEqual(p.depends, [])
		self.assertEqual(p.desc, 'No description.')
		self.assertEqual(p.echo, {})
		self.assertEqual(p.config['echo'], False)
		self.assertEqual(p.errhow, 'terminate')
		self.assertEqual(p.errntry, 3)
		self.assertEqual(p.exdir, '')
		self.assertEqual(p.exhow, 'move')
		self.assertEqual(p.exow, True)
		self.assertEqual(p.expart, [])
		self.assertEqual(p.expect, None)
		self.assertEqual(p.forks, 1)
		self.assertEqual(p.input, {})
		self.assertEqual(p.jobs, [])
		self.assertEqual(p.ncjobids, [])
		self.assertEqual(p.lang, 'bash')
		self.assertEqual(p.output, {})
		self.assertEqual(p.ppldir, path.abspath('./workdir'))
		self.assertEqual(p.procvars, {})
		self.assertEqual(p.rc, [0])
		self.assertEqual(p.resume, False)
		self.assertEqual(p.runner, 'local')
		self.assertEqual(p.script, None)
		self.assertEqual(p.sets, [])
		self.assertEqual(p.size, 0)
		self.assertEqual(p.suffix, '')
		self.assertEqual(p.tag, 'notag')
		self.assertEqual(p.template, None)
		self.assertEqual(p.tplenvs, {})
		self.assertEqual(p.workdir, '')
		self.assertEqual(p.lognline['_PREV_LOG'], '')

	def testGetSetAttrRepr(self):
		p = Proc()
		self.assertRaises(AttributeError, p.__getattr__, 'a')
		self.assertRaises(AttributeError, p.__setattr__, 'a', 'b')
		p.tag = 'newtag'
		self.assertEqual(p.tag, 'newtag')
		self.assertEqual(p.config['tag'], 'newtag')
		self.assertIn('<Proc(p.newtag) at', repr(p))
		p.args = {'a': 1}
		p.args.b = '2'
		self.assertEqual(dict(p.args), {'a': 1, 'b': '2'})
		p.input = 'a'
		p.input = [1]
		self.assertEqual(p.config['input'], {'a': [1]})

	def testLog(self):
		p = Proc()
		self.assertEqual(Proc.LOG_NLINE['EXPORT_CACHE_OUTFILE_EXISTS'], -3)
		with captured_output() as (out, err):
			logger.getLogger()
			p.log('Normal1')
			p.log('Normal2')
			p.log('Normal3')
			p.log('Normal4')
			p.log('Limit1', 'info', 'EXPORT_CACHE_OUTFILE_EXISTS')
			p.log('Limit2', 'info', 'EXPORT_CACHE_OUTFILE_EXISTS')
			p.log('Limit3', 'info', 'EXPORT_CACHE_OUTFILE_EXISTS')
			p.log('Limit4', 'info', 'EXPORT_CACHE_OUTFILE_EXISTS')
		self.assertIn('Normal1', err.getvalue())
		self.assertIn('Normal2', err.getvalue())
		self.assertIn('Normal3', err.getvalue())
		self.assertIn('Normal4', err.getvalue())
		self.assertIn('Limit1', err.getvalue())
		self.assertIn('Limit2', err.getvalue())
		self.assertIn('Limit3', err.getvalue())
		self.assertNotIn('Limit4', err.getvalue())
	
	def testCopy(self):
		p = Proc()
		p.aggr = 'aggr'
		p.workdir = './wdir'
		p.resume = 'skip'
		p.args = {'a':1,'b':2}
		p.props['depends'] = 1
		p2 = p.copy()
		self.assertEqual(p2.id, 'p2')
		p3 = p.copy(newid='p0', tag ='tag0', desc='ksks')
		self.assertEqual(p3.id, 'p0')
		self.assertEqual(p3.tag, 'tag0')
		self.assertEqual(p3.desc, 'ksks')
		self.assertEqual(p3.aggr, '')
		self.assertEqual(p3.workdir, '')
		p3.args.b = 3
		self.assertEqual(dict(p3.args), {'a':1, 'b':3})
		self.assertEqual(p3.resume, False)
		p3.tag = 'tag3'
		self.assertIn('tag', p3.sets)
		self.assertNotIn('tag', p.sets)
		self.assertEqual(p3.depends, [])
		self.assertEqual(p3.procvars, {})
		self.assertEqual(p3.jobs, [])
		self.assertEqual(p3.ncjobids, [])
		self.assertEqual(p3.suffix, '')

	def testSuffix(self):
		p = Proc()
		self.assertEqual(p.suffix, '')
		suffix1 = p._suffix()
		self.assertEqual(len(suffix1), 8)
		p.id = 'p1'
		# because suffix  computed
		self.assertEqual(suffix1, p._suffix())
		p.props['suffix'] = ''
		self.assertNotEqual(suffix1, p._suffix())
		p.tag = 'tag1'
		p.props['suffix'] = ''
		self.assertNotEqual(suffix1, p._suffix())
		p.input = {"a, b": lambda ch: ch.collapse()}
		p.props['suffix'] = ''
		self.assertNotEqual(suffix1, p._suffix())
		p.output = "{{a}}"
		p.props['suffix'] = ''
		self.assertNotEqual(suffix1, p._suffix())
		p.script = 'aa'
		p.props['suffix'] = ''
		self.assertNotEqual(suffix1, p._suffix())
		p.lang = 'Rscript'
		p.props['suffix'] = ''
		self.assertNotEqual(suffix1, p._suffix())
		suffix2 = p._suffix()
		p.echo = {'type': 'stdout'}
		p.props['suffix'] = ''
		self.assertEqual(suffix2, p._suffix())

	def testBuildProps(self):
		p = Proc(tag= 'buildprops')
		p._buildProps()
		# no procs with same id and tag
		p2 = Proc(tag = 'buildprops', id = 'p')
		self.assertRaises(ValueError, p2._buildProps)
		del PyPPL.PROCS[PyPPL.PROCS.index(p2)]
		# template
		self.assertIs(p.template, templates.TemplatePyPPL)
		try:
			import jinja2
			p.template = 'jinja2'
			p._buildProps()
			self.assertIs(p.template, templates.TemplateJinja2)
		except:
			pass

		# rc
		p.rc = "1, 2"
		p._buildProps()
		self.assertEqual(p.rc, [1,2])
		p.rc = [0,1]
		p._buildProps()
		self.assertEqual(p.rc, [0,1])
		p.rc = 2
		p._buildProps()
		self.assertEqual(p.rc, [2])

		# workdir
		p.props['workdir'] = ''
		p.workdir = './workdir/otherwdir'
		self.assertIn('workdir', p.sets)
		p._buildProps()
		self.assertEqual(p.workdir, './workdir/otherwdir')
		# skip+ proc must have workdir exists
		self.assertPathExists(p.workdir)
		utils.safeRemove(p.workdir)
		p.props['workdir'] = ''
		p.resume = 'skip+'
		p.workdir = './workdir/otherwdir'
		self.assertRaises(Exception, p._buildProps)
		# exdir
		p.resume = False
		p.exdir  = './workdir/exports'
		p._buildProps()
		self.assertPathExists(p.exdir)
		# echo
		self.assertEqual(p.echo, {'filter': '', 'jobs':[0], 'type': []})
		p.echo = True
		p._buildProps()
		self.assertEqual(p.echo, {'filter': '', 'jobs':[0], 'type': ['stderr', 'stdout']})
		p.echo = 'stdout'
		p._buildProps()
		self.assertEqual(p.echo, {'filter': '', 'jobs':[0], 'type': ['stdout']})

		# dryrunner
		self.assertEqual(p.runner, 'local')
		self.assertTrue(p.cache)
		p.runner = 'dry'
		p._buildProps()
		self.assertEqual(p.runner, 'dry')
		self.assertFalse(p.cache)

		# depends
		self.assertEqual(p.depends, [])
		p2 = Proc()
		p3 = Proc()
		p.depends = p2, p3
		p._buildProps()
		self.assertEqual(p.depends, [p2, p3])

		p.depends = p2
		p._buildProps()
		self.assertEqual(p.depends, [p2])
		p.depends = Aggr(p2, p3)
		p._buildProps()
		self.assertEqual(p.depends, [p2, p3])

		p.depends = p2, Aggr(p3)
		p.template = ''
		p._buildProps()
		self.assertEqual(p.depends, [p2, p3])

		#p.depends = p2, p3, 3
		self.assertRaises(TypeError, p.__setattr__, 'depends', (p2, p3, 3))

		# expect
		self.assertIsInstance(p.expect, templates.TemplatePyPPL)
		p.expect = "echo {{proc.id}}"
		p.depends = p2
		p._buildProps()
		self.assertEqual(p.expect.render({'proc': {'id': p.id}}), 'echo p')

		# expart
		p.expart = 'a, b'
		p._buildProps()
		self.assertIsInstance(p.expart, list)
		p.expart = ['a', '{{proc.id}}']
		p._buildProps()
		self.assertEqual(p.expart[0].render(), 'a')
		self.assertEqual(p.expart[1].render({'proc': {'id': p.id}}), 'p')
	
	def testBuildInput(self):
		p = Proc(tag = 'buildinput')
		# from argv
		p.input = 'ii, is'
		sys.argv = [sys.argv[0], '1,a', '2,b']
		p._buildProps()
		p._buildInput()
		self.assertEqual(p.input['ii']['data'], ['1', '2'])
		self.assertEqual(p.input['ii']['type'], 'var')
		self.assertEqual(p.input['is']['data'], ['a', 'b'])
		self.assertEqual(p.input['is']['type'], 'var')
		p.props['channel'] = Channel.fromArgv()

		# from one dependent
		p2 = Proc()
		p2.depends = p
		p2.input = "pi, ps"
		p2._buildProps()
		p2._buildInput()
		self.assertEqual(p2.input['pi']['data'], ['1', '2'])
		self.assertEqual(p2.input['pi']['type'], 'var')
		self.assertEqual(p2.input['ps']['data'], ['a', 'b'])
		self.assertEqual(p2.input['ps']['type'], 'var')

		# from multi depends
		p.props['channel'] = Channel.fromArgv().colAt(0)
		p2.props['channel'] = Channel.fromArgv().colAt(1)
		p3 = Proc()
		p3.depends = p, p2
		p3.input = "qi, qs"
		p3._buildProps()
		p3._buildInput()
		self.assertEqual(p3.input['qi']['data'], ['1', '2'])
		self.assertEqual(p3.input['qi']['type'], 'var')
		self.assertEqual(p3.input['qs']['data'], ['a', 'b'])
		self.assertEqual(p3.input['qs']['type'], 'var')

		# always list
		p3.input = "qi, qs"
		p3._buildProps()
		p3._buildInput()
		self.assertEqual(p3.input['qi']['data'], ['1', '2'])
		self.assertEqual(p3.input['qi']['type'], 'var')
		self.assertEqual(p3.input['qs']['data'], ['a', 'b'])
		self.assertEqual(p3.input['qs']['type'], 'var')
		p3.input = "qi, qs"
		p3._buildProps()
		p3._buildInput()
		self.assertEqual(p3.input['qi']['data'], ['1', '2'])
		self.assertEqual(p3.input['qi']['type'], 'var')
		self.assertEqual(p3.input['qs']['data'], ['a', 'b'])
		self.assertEqual(p3.input['qs']['type'], 'var')

		# invalid type
		p3.input = "qi:t, qs"
		p3._buildProps()
		self.assertRaises(TypeError, p3._buildInput)

		# lambda
		p.props['channel'] = Channel.fromArgv()
		p2.props['channel'] = Channel.fromArgv()
		p3.depends = p, p2
		p3.input = {'qi, qs': lambda ch1, ch2: ch1.colAt(0).cbind(ch2.colAt(1))}
		p3._buildProps()
		p3._buildInput()
		self.assertEqual(p3.input['qi']['data'], ['1', '2'])
		self.assertEqual(p3.input['qi']['type'], 'var')
		self.assertEqual(p3.input['qs']['data'], ['a', 'b'])
		self.assertEqual(p3.input['qs']['type'], 'var')

		p3.input = {'qi': lambda ch1, ch2: ch1.colAt(0), 'qs': lambda ch1, ch2: ch2.colAt(1)}
		p3._buildProps()
		p3._buildInput()
		self.assertEqual(p3.input['qi']['data'], ['1', '2'])
		self.assertEqual(p3.input['qi']['type'], 'var')
		self.assertEqual(p3.input['qs']['data'], ['a', 'b'])
		self.assertEqual(p3.input['qs']['type'], 'var')

		# list
		p.depends = []
		p.input   = {'a': list(range(5)), 'b': [5,6,7,8,9]}
		p._buildProps()
		p._buildInput()
		self.assertEqual(p.input['a']['data'], list(range(5)))
		self.assertEqual(p.input['a']['type'], 'var')
		self.assertEqual(p.input['b']['data'], [5,6,7,8,9])
		self.assertEqual(p.input['b']['type'], 'var')
		self.assertEqual(p.size, 5)
		self.assertEqual(p.jobs, [None] * 5)

		# not enough columns
		p3.input = {'qi, qa, qb': lambda ch1, ch2: ch1.colAt(0).cbind(ch2.colAt(1))}
		p3._buildProps()
		p3._buildInput()
		self.assertEqual(p3.input['qb']['data'], [''] * 2)

		# Cannot cbind
		p.depends = []
		p.input   = {'a': list(range(4)), 'b': [5,6,7,8,9]}
		p._buildProps()
		self.assertRaises(IndexError, p._buildInput)
		p.depends = []
		p.input   = {'a': [1], 'b': [5,6,7,8,9]}
		p._buildProps()
		self.assertRaises(IndexError, p._buildInput)

		# can cbind
		p.depends = []
		p.input   = {'a': list(range(5)), 'b': [5]}
		p._buildProps()
		p._buildInput()
		self.assertEqual(p.input['a']['data'], list(range(5)))
		self.assertEqual(p.input['a']['type'], 'var')
		self.assertEqual(p.input['b']['data'], [5]*5)
		self.assertEqual(p.input['b']['type'], 'var')
		self.assertEqual(p.size, 5)
		self.assertEqual(p.jobs, [None] * 5)

		# support empty input
		sys.argv = [sys.argv[0]]
		p4 = Proc()
		p4._buildProps()
		p4._buildInput()
		self.assertEqual(p4.input, {})

		# other types
		p.depends = []
		p.input   = {'a:file': list(range(5)), 'b:dir': [5]}
		p._buildProps()
		p._buildInput()
		self.assertEqual(p.input['a']['data'], list(range(5)))
		self.assertEqual(p.input['a']['type'], 'file')
		self.assertEqual(p.input['b']['data'], [5]*5)
		self.assertEqual(p.input['b']['type'], 'dir')
		

	def testBuildProcVars(self):
		sys.argv = ['']
		p = Proc(tag = 'procvars')
		p._buildProps()
		p._buildInput()
		p.args = {'a': 1, 'b': 2}

		with captured_output() as (out, err):
			logger.getLogger()
			p._buildProcVars()
		self.assertEqual(dict(p.procvars['args']), {'a': 1, 'b': 2})
		self.assertEqual(dict(p.procvars['proc']['args']), {'a': 1, 'b': 2})
		del p.procvars['proc']['args']
		self.assertIn(p.procvars['proc']['suffix'], p.procvars['proc']['workdir'])
		del p.procvars['proc']['workdir']
		self.assertIn(p.procvars['proc']['ppldir'], path.abspath('./workdir'))
		del p.procvars['proc']['ppldir']
		self.assertEqual(p.procvars['proc'], {
			'suffix': '4zbHysnh', 
			'runner': 'local', 
			'echo': {'filter': '', 'type': [], 'jobs': [0]}, 
			'tag': 'procvars', 
			'id': 'p', 
			'size': 0, 
			'cache': True, 
			'rc': [0], 
			'forks': 1, 
			'desc': 'No description.', 
			'aggr': None, 
			'resume': False, 
			'exhow': 'move', 
			'exow': True, 
			'errhow': 'terminate', 
			'lang': 'bash', 
			'exdir': '', 
			'procvars': {}, 
			'sets': ['args'], 
			'errntry': 3
		})

	def testBuildBrings(self):
		p = Proc('buildbrings')
		p.brings = {
			'a': "{{proc.id}}.*",
			'b': ['b1', 'b2{{proc.tag}}']
		}
		p._buildProps()
		p._buildInput()
		p._buildProcVars
		p._buildBrings()
		self.assertEqual(p.brings['a'][0].render({'proc': {'id': 'p'}}), 'p.*')
		self.assertEqual(p.brings['b'][0].render({'proc': {'id': 'p'}}), 'b1')
		self.assertEqual(p.brings['b'][1].render({'proc': {'tag': 'tag'}}), 'b2tag')

	def testBuildOutput(self):
		p = Proc('buildoutput')
		# string
		p.output = "a:b, c:d"
		p._buildProps()
		p._buildInput()
		p._buildProcVars
		p._buildBrings()
		p._buildOutput()
		self.assertEqual(p.output['a'][0], 'var')
		self.assertEqual(p.output['a'][1].render(), 'b')
		self.assertEqual(p.output['c'][0], 'var')
		self.assertEqual(p.output['c'][1].render(), 'd')

		# list
		p.output = ["a:b", "c:d"]
		p._buildProps()
		p._buildInput()
		p._buildProcVars
		p._buildBrings()
		p._buildOutput()
		self.assertEqual(p.output['a'][0], 'var')
		self.assertEqual(p.output['a'][1].render(), 'b')
		self.assertEqual(p.output['c'][0], 'var')
		self.assertEqual(p.output['c'][1].render(), 'd')

		# missing value
		p.output = ["a", "c:d"]
		p._buildProps()
		p._buildInput()
		p._buildProcVars
		p._buildBrings()
		self.assertRaises(ValueError, p._buildOutput)

		# no dict
		p.output = {'a': 'b', 'c': 'd'}
		p._buildProps()
		p._buildInput()
		p._buildProcVars
		p._buildBrings()
		self.assertRaises(TypeError, p._buildOutput)

		# type error
		p.output = ["a:b", "c:d:e"]
		p._buildProps()
		p._buildInput()
		p._buildProcVars
		p._buildBrings()
		self.assertRaises(TypeError, p._buildOutput)

		# other types
		p.output = ["a:var:a", "c:file:e"]
		p._buildProps()
		p._buildInput()
		p._buildProcVars
		p._buildBrings()
		p._buildOutput()
		self.assertEqual(p.output['a'][0], 'var')
		self.assertEqual(p.output['a'][1].render(), 'a')
		self.assertEqual(p.output['c'][0], 'file')
		self.assertEqual(p.output['c'][1].render(), 'e')

		# allow empty output
		p.output = ''
		p._buildProps()
		p._buildInput()
		p._buildProcVars
		p._buildBrings()
		p._buildOutput()

	def testBuildScript(self):
		p = Proc('buildscript')
		p.script = 'a {% if pid | lambda x: x == 1 %} b {% endif %}'
		p._buildProps()
		p._buildInput()
		p._buildProcVars
		p._buildBrings()
		p._buildOutput()
		p._buildScript()
		self.assertEqual(p.script.render({'pid': p}), '#!/usr/bin/env bash\na ')

	def testReadConfig(self):
		p = Proc('readconf')
		p._readConfig({'id': 'p2'})
		self.assertEqual(p.config['id'], 'p2')
		p.config['id'] = 'p'
		p.props['sets'] = ['id']
		p._readConfig({'id': 'p2'})
		self.assertEqual(p.config['id'], 'p')

	def testRunCmd(self):
		p = Proc('runcmd')
		p.beforeCmd = 'ls -l ' + path.join(path.dirname(__file__))
		p.afterCmd  = 'grep afterCmd {{file}}'
		p.tplenvs   = {
			'file': __file__
		}
		p._buildProps()
		with captured_output() as (out, err):
			logger.getLogger()
			p._runCmd('beforeCmd')
		self.assertIn(path.basename(__file__), err.getvalue())
		self.assertIn('p.runcmd: Running <beforeCmd> ...', err.getvalue())
		with captured_output() as (out, err):
			logger.getLogger()
			p._runCmd('afterCmd')
		self.assertIn('afterCmd', err.getvalue())
		# runtime rror
		p.beforeCmd = 'nosuchcmd'
		self.assertRaises(RuntimeError, p._runCmd, 'beforeCmd')

	def testBuildJobs(self):
		p = Proc('buildjobs')
		# empty output
		p.input = {'a': [1,2,3,4,5], 'b': [6,7,8,9,10]}
		#p.output = "outfile:file:out{{in.b}}.txt"
		#p.script = 'echo {{in.a}} > {{out.outfile}}'
		p._buildProps()
		p._buildInput()
		p._buildProcVars
		p._buildBrings()
		p._buildOutput()
		#p._buildScript()
		with captured_output() as (out, err):
			logger.getLogger()
		#	p._buildJobs()
		logger.getLogger()
		#self.assertEqual(p.size, 5)
		
		# output
		p.output = "outfile:file:out{{in.b}}.txt, o2:{{in.a}}2"
		p.script = 'echo {{in.a}} > {{out.outfile}}'
		p._buildProps()
		p._buildInput()
		p._buildProcVars
		p._buildBrings()
		p._buildOutput()
		p._buildScript()
		with captured_output() as (out, err):
			logger.getLogger()
			p._buildJobs()
		logger.getLogger()
		self.assertEqual(p.channel.outfile, [(path.join(p.workdir, str(i), 'output', 'out' + str(b) + '.txt'),) for i,b in enumerate([6,7,8,9,10])])
		self.assertEqual(p.channel.o2.flatten(), ['12', '22', '32', '42', '52'])

		self.assertEqual(p.size, 5)
		job = p.jobs[0]
		with open(job.script) as f:
			self.assertIn('echo 1 > ', f.read())
		
	def testName(self):
		p = Proc('name')
		self.assertEqual(p.name(), 'p.name')
		p.tag = 'notag'
		self.assertEqual(p.name(), 'p')
		p.aggr = 'aggr'
		self.assertEqual(p.name(), 'p@aggr')
		self.assertEqual(p.name(False), 'p')

	def testSaveSettings(self):
		p = Proc('savesettings')
		# empty output
		p.input = {'a': [1,2,3,4,5], 'b': [6,7,8,9,10]}
		p.output = "outfile:file:out{{in.b}}.txt, o2:{{in.a}}2"
		p.script = 'echo {{in.a}} > {{out.outfile}}'
		p._buildProps()
		p._buildInput()
		p._buildProcVars
		p._buildBrings()
		p._buildOutput()
		p._buildScript()
		# just expect no exceptions
		p._saveSettings()
		self.assertPathExists(path.join(p.workdir, 'proc.settings'))
	
	def testTidybeforeRun(self):
		with captured_output():
			logger.getLogger()
		p = Proc('tbr')
		# empty output
		p.input = {'a': [1,2,3,4,5], 'b': [6,7,8,9,10]}
		p.output = "outfile:file:out{{in.b}}.txt, o2:{{in.a}}2"
		p.script = 'echo {{in.a}} > {{out.outfile}}'
		p._tidyBeforeRun()
		settingfile = path.join(p.workdir, 'proc.settings')
		self.assertPathExists(settingfile)

		# callfront
		p.callfront = lambda p: setattr(p, 'resume', 'skip+')
		utils.safeRemove(settingfile)
		p._tidyBeforeRun()
		self.assertPathNotExists(settingfile)

		self.assertEqual(p.size, 5)
		for job in p.jobs:
			self.assertIsInstance(job, Job)

	def testCheckCached(self):
		logger.getLogger()
		p = Proc('testCheckCached')
		# empty output
		p.runner = 'testr'
		p.input = {'a': [1,2,3,4,5], 'b': [6,7,8,9,10]}
		p.output = "outfile:file:out{{in.b}}.txt, o2:{{in.a}}2"
		p.script = 'echo {{in.a}} > {{out.outfile}}'
		with captured_output() as (out, err):
			logger.getLogger()
			p._tidyBeforeRun()
			for i in [0,1,2,3,4]:
				utils.safeRemove(path.join(p.workdir, str(i)))
			self.assertFalse(p._checkCached())
		self.assertEqual(p.ncjobids, [0,1,2,3,4])
		self.assertIn('Truely cached jobs: []', err.getvalue())
		self.assertIn('Export cached jobs: []', err.getvalue())

		p._tidyBeforeRun()
		job = p.jobs[0]
		job.rc(utils.dumbPopen(['bash', job.script]).wait())
		job.cache()
		self.assertFalse(p._checkCached())
		self.assertIn('Truely cached jobs: [0]', err.getvalue())
		self.assertIn('Export cached jobs: []', err.getvalue())

	def testRunJobs(self):
		logger.getLogger()
		p = Proc('runjobs')
		# empty output
		p.runner = 'testr'
		p.input = {'a': [1,2,3,4,5], 'b': [6,7,8,9,10]}
		p.output = "outfile:file:out{{in.b}}.txt, o2:{{in.a}}2"
		p.script = 'echo {{in.a}} > {{out.outfile}}'
		with captured_output() as (out, err):
			logger.getLogger()
			p._tidyBeforeRun()
			for job in p.jobs:
				utils.safeRemove(job.data['out']['outfile'])
			p._checkCached()
			p._runJobs()
		for job in p.jobs:
			job.checkOutfiles()
			self.assertFalse(job.outfileOk)

		p.runner = 'nosuchrunner'
		p._tidyBeforeRun()
		p._checkCached()
		self.assertRaises(KeyError, p._runJobs)

		p.runner = 'testnr'
		with captured_output() as (out, err):
			logger.getLogger()
			p._tidyBeforeRun()
			for job in p.jobs:
				utils.safeRemove(job.data['out']['outfile'])
			p._checkCached()
			p._runJobs()
		for job in p.jobs:
			job.checkOutfiles()
			self.assertTrue(job.outfileOk)
	
	def testRun(self):
		logger.getLogger()
		p = Proc('testRun')
		# empty output
		p.runner = 'testr'
		p.input = {'a': [1,2,3,4,5], 'b': [6,7,8,9,10]}
		p.output = "outfile:file:out{{in.b}}.txt, o2:{{in.a}}2"
		p.script = 'echo {{in.a}} > {{out.outfile}}'
		p.runner = 'testnr'
		p.resume = 'skip'
		with captured_output() as (out, err):
			logger.getLogger()
			p.run()
		self.assertIn('Pipeline will resume from future processes', err.getvalue())

		logger.getLogger(levels = 'all')
		p.resume = True
		with captured_output() as (out, err):
			logger.getLogger()
			p.run()
		self.assertIn('RESUMED', err.getvalue())

		for job in p.jobs:
			job.done()

		p.resume = False
		with captured_output() as (out, err):
			logger.getLogger()
			p.run()
		self.assertIn('CACHED', err.getvalue())

if __name__ == '__main__':
	unittest.main(verbosity=2)