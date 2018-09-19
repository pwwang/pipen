import helpers, testly, sys, json

from time import time
from glob import glob
from os import path, symlink, makedirs, utime
from tempfile import gettempdir
from collections import OrderedDict
from shutil import rmtree
from copy import deepcopy
from liquid import LiquidRenderError
from pyppl.job import Job
from pyppl.jobmgr import Jobmgr
from pyppl.exception import JobInputParseError, JobOutputParseError
from pyppl.template import TemplateLiquid
from pyppl import Proc, logger, utils

class TestJob(testly.TestCase):

	def setUpMeta(self):
		self.testdir = path.join(gettempdir(), 'PyPPL_unittest', 'TestJob')
		if path.exists(self.testdir):
			rmtree(self.testdir)
		makedirs(self.testdir)

	def file2indir(workdir, index, f, suffix = ''):
		(prefix, _, ext) = path.basename(f).rpartition('.')
		return path.join(workdir, str(index + 1), 'input', prefix + suffix + '.' + ext)

	def dataProvider_testInit0(self):
		p = Proc()
		p.props['workdir'] = path.join(self.testdir, 'workdir')
		yield 0, p
		yield 1, p

	def testInit0(self, index, proc):
		job  = Job(index, proc)
		self.assertIsInstance(job, Job)
		self.assertIsInstance(job.proc, Proc)
		self.assertEqual(job.dir, path.join(proc.workdir, str(index + 1)))
		self.assertEqual(job.indir, path.join(job.dir, 'input'))
		self.assertEqual(job.outdir, path.join(job.dir, 'output'))
		self.assertEqual(job.script, path.join(job.dir, 'job.script'))
		self.assertEqual(job.rcfile, path.join(job.dir, 'job.rc'))
		self.assertEqual(job.outfile, path.join(job.dir, 'job.stdout'))
		self.assertEqual(job.errfile, path.join(job.dir, 'job.stderr'))
		self.assertEqual(job.cachefile, path.join(job.dir, 'job.cache'))
		self.assertEqual(job.pidfile, path.join(job.dir, 'job.pid'))
		self.assertEqual(job.index, index)
		self.assertIs(job.proc, proc)
		self.assertEqual(job.input, {})
		self.assertEqual(job.output, {})
		#self.assertEqual(job.brings, {})
		self.assertEqual(job.data, {
			'job': {
				'index'   : job.index,
				'indir'   : job.indir,
				'outdir'  : job.outdir,
				'dir'     : job.dir,
				'outfile' : job.outfile,
				'errfile' : job.errfile,
				'pidfile' : job.pidfile
			},
			'i'   : {},
			'o'  : {},
			#'bring': {}
		})

	def dataProvider_testPrepInput(self):
		p = Proc()
		# make sure the infile renaming log output
		p.LOG_NLINE['INFILE_RENAMING'] = -1
		p.props['workdir'] = path.join(self.testdir, 'workdir')
		filec0 = path.join(self.testdir, 'filec0.txt')
		filec1 = path.join(self.testdir, 'filec1.txt')
		filec2 = path.join(self.testdir, 'filec2.txt')
		filed0 = path.join(self.testdir, 'filed0.txt')
		filed1 = path.join(self.testdir, 'filed1.txt')
		filed2 = path.join(self.testdir, 'filed2.txt')
		filed3 = path.join(self.testdir, 'filed3.txt')
		filed4 = path.join(self.testdir, 'filed4.txt')
		filed20 = path.join(self.testdir, 'filed20.txt')
		filed21 = path.join(self.testdir, 'filed21.txt')
		filed22 = path.join(self.testdir, 'filed22.txt')
		filed23 = path.join(self.testdir, 'filed23.txt')
		filed24 = path.join(self.testdir, 'filed24.txt')
		filed30 = path.join(self.testdir, 'filed30.txt')
		filed31 = path.join(self.testdir, 'filed31.txt')
		filed32 = path.join(self.testdir, 'filed32.txt')
		filed33 = path.join(self.testdir, 'filed33.txt')
		filed34 = path.join(self.testdir, 'filed34.txt')
		filed35 = path.join(self.testdir, 'filed35', 'filec2.txt')
		for f in [
			# filec1 not exists
			filec0, filec2, filed0, filed1, filed2, filed3, 
			filed4, filed20, filed21, filed22, filed23, filed24, filed30, 
			filed31, filed32, filed33, filed34]:
			helpers.writeFile(f)
		makedirs(path.dirname(filed35))
		symlink(filed34, filed35)
		p.props['input']   = {
			'a': {'type': 'var', 'data': [1, 2, 3, 4, 5, 6, 7]},
			'b': {'type': 'var', 'data': ['a', 'b', 'c', 'd', 'e', 'f', 'g']},
			'c': {'type': 'file', 'data': ['', filec1, [], filec0, filec0, filec0, filec2]},
			'd': {'type': 'files', 'data': [
				[filed0, filed1],
				[filed2],
				[filed3, filed4],
				{},
				[[], filed4],
				[filec1, filed4],
				[filed4, filed4],
			]},
			'd2': {'type': 'files', 'data': [
				[filed20],
				[filed21, filed22],
				[filed23, filed24],
				[filed24],
				[filed24],
				[filed24],
				[''],
			]}, 
			'd3': {'type': 'files', 'data': [
				[filed30, filed31],
				[filed32, filed33],
				[filed34],
				[filed34],
				[filed34],
				[filed34],
				[filed35],
			]}, 
		}
		p2 = p.copy()
		p2.props['workdir'] = path.join(self.testdir, 'workdir2')
		p2.infile = 'real'
		p3 = p.copy()
		p3.props['workdir'] = path.join(self.testdir, 'workdir3')
		p3.infile = 'origin'

		yield 0, p2, {
			'a': {'type': 'var', 'data': 1},
			'b': {'type': 'var', 'data': 'a'},
			'c': {'type': 'file', 'orig':'', 'data': ''},
			'd': {'type': 'files', 'orig':[filed0, filed1], 'data': [
				self.file2indir(p2.workdir, 0, filed0), 
				self.file2indir(p2.workdir, 0, filed1)
			]},
			'd2': {'type': 'files', 'orig': [filed20], 'data': [
				self.file2indir(p2.workdir, 0, filed20)
			]},
			'd3': {'type': 'files', 'orig': [filed30, filed31], 'data': [
				self.file2indir(p2.workdir, 0, filed30),
				self.file2indir(p2.workdir, 0, filed31)
			]}, 
		}, {
			'a': 1,
			'b': 'a',
			'c': path.realpath(''),
			'IN_c': '',
			'OR_c': '',
			'RL_c': path.realpath(''),
			'd': [
				path.realpath(filed0), 
				path.realpath(filed1)
			],
			'IN_d': [
				self.file2indir(p2.workdir, 0, filed0), 
				self.file2indir(p2.workdir, 0, filed1)
			],
			'OR_d': [filed0, filed1],
			'RL_d': [path.realpath(filed0), path.realpath(filed1)],
			'd2': [
				path.realpath(filed20)
			],
			'IN_d2': [
				self.file2indir(p2.workdir, 0, filed20)
			],
			'OR_d2': [filed20],
			'RL_d2': [path.realpath(filed20)],
			'd3': [
				path.realpath(filed30),
				path.realpath(filed31)
			], 
			'IN_d3': [
				self.file2indir(p2.workdir, 0, filed30),
				self.file2indir(p2.workdir, 0, filed31)
			], 
			'OR_d3': [filed30, filed31], 
			'RL_d3': [path.realpath(filed30), path.realpath(filed31)], 
		}

		yield 1, p, {}, {}, JobInputParseError, 'File not exists for input type'
		yield 2, p, {}, {}, JobInputParseError, 'Not a string for input type'
		yield 3, p, {}, {}, JobInputParseError, 'Not a list for input type'
		yield 4, p, {}, {}, JobInputParseError, 'Not a string for element of input type'
		yield 5, p, {}, {}, JobInputParseError, 'File not exists for element of input type'
		yield 6, p3, OrderedDict([ # make sure c comes first, instead of d3
			('a', {'type': 'var', 'data': 7}),
			('b', {'type': 'var', 'data': 'g'}),
			('c', {'type': 'file', 'orig': filec2, 'data': self.file2indir(p3.workdir, 6, filec2)}),
			('d', {'type': 'files', 'orig':[filed4, filed4], 'data': [
				self.file2indir(p3.workdir, 6, filed4), 
				self.file2indir(p3.workdir, 6, filed4)
			]}),
			('d2', {'type': 'files', 'orig': [''], 'data': [
				''
			]}),
			#                               not file34
			('d3', {'type': 'files', 'orig': [filed35], 'data': [
				self.file2indir(p3.workdir, 6, filed35, '[1]')
			]})
		]), {
			'a': 7,
			'b': 'g',
			'c': filec2,
			'IN_c': self.file2indir(p3.workdir, 6, filec2),
			'OR_c': filec2,
			'RL_c': path.realpath(filec2),
			'd': [
				filed4, 
				filed4
			],
			'IN_d': [
				self.file2indir(p3.workdir, 6, filed4), 
				self.file2indir(p3.workdir, 6, filed4)
			],
			'OR_d': [filed4, filed4],
			'RL_d': [path.realpath(filed4), path.realpath(filed4)],
			'd2': [''],
			'IN_d2': [''],
			'OR_d2': [''],
			'RL_d2': [path.realpath('')],
			'd3': [
				filed35
			], 
			'IN_d3': [
				self.file2indir(p3.workdir, 6, filed35, '[1]')
			], 
			'OR_d3': [filed35], 
			'RL_d3': [path.realpath(filed35)]
		}, None, None, 'Input file renamed: filec2.txt -> filec2[1].txt'
		
		p21 = Proc()
		# make sure the infile renaming log output
		p21.LOG_NLINE['INFILE_RENAMING'] = -1
		p21.infile = 'origin'
		p21.props['workdir'] = path.join(self.testdir, 'workdir-p21')
		p21.props['input']   = OrderedDict([
			('c1', {'type': 'file', 'data': [filec2]}),
			('c2', {'type': 'file', 'data': [filed35]}),
		])
		yield 0, p21, OrderedDict([
			('c1', {'type': 'file', 'orig': filec2, 'data': self.file2indir(p21.workdir, 0, filec2)}),
			('c2', {'type': 'file', 'orig': filed35, 'data': self.file2indir(p21.workdir, 0, filed35, '[1]')}),
		
		]), {
			'c1': filec2,
			'IN_c1': self.file2indir(p21.workdir, 0, filec2),
			'OR_c1': filec2,
			'RL_c1': path.realpath(filec2),
			'c2': filed35,
			'IN_c2': self.file2indir(p21.workdir, 0, filed35, '[1]'),
			'OR_c2': filed35,
			'RL_c2': path.realpath(filed35),
		}, None, None, 'Input file renamed: filec2.txt -> filec2[1].txt'

	def testPrepInput(self, index, proc, jobinput, indata, exception = None, msg = None, errmsg = None):
		self.maxDiff = None
		job = Job(index, proc)
		if path.isdir(job.indir):
			rmtree(job.indir)
		self.assertFalse(path.isdir(job.indir))
		if exception:
			self.assertRaisesRegex(exception, msg, job._prepInput)
			self.assertTrue(path.isdir(job.indir))
		else:
			with helpers.log2str() as (out, err):
				job._prepInput()
			if errmsg:
				self.assertIn(errmsg, err.getvalue())
			self.assertTrue(path.isdir(job.indir))
			self.assertDictEqual(job.input, jobinput)
			self.assertDictEqual(job.data['i'], indata)
	
	def dataProvider_testPrepOutput(self):
		pPrepOutput = Proc()
		pPrepOutput.props['workdir'] = path.join(self.testdir, 'pPrepOutput', 'workdir')
		yield 0, pPrepOutput, {
			'a': {'type': 'var', 'data': [0]}
		}, '', {}, {}, AssertionError
		yield 0, pPrepOutput, {
			'a': {'type': 'var', 'data': [0]}
		}, {}, {}, {}
		yield 0, pPrepOutput, {
			'a': {'type': 'var', 'data': [0]}
		}, {'a': ('var', TemplateLiquid('{{x}}'))}, {}, {}, LiquidRenderError, "NameError: name 'x' is not defined"
		yield 0, pPrepOutput, {
			'a': {'type': 'var', 'data': [0]}
		}, {'a': ('var', TemplateLiquid('1{{i.a}}'))}, {
			'a': {'type': 'var', 'data': '10'}
		}, {
			'a': '10'
		}
		yield 0, pPrepOutput, {
			'a': {'type': 'var', 'data': [0]}
		}, {
			'a': ('file', TemplateLiquid('/a/b/1{{i.a}}'))
		}, {}, {}, JobOutputParseError, 'Absolute path not allowed for output file/dir'
		yield 0, pPrepOutput, {
			'a': {'type': 'var', 'data': [0]}
		}, {
			'a': ('file', TemplateLiquid('{{i.a}}.out')),
			'b': ('stdout', TemplateLiquid('{{i.a}}.stdout')),
			'c': ('stderr', TemplateLiquid('{{i.a}}.stderr')),
		}, {
			'a': {'type': 'file', 'data': path.join(pPrepOutput.workdir, '1', 'output', '0.out')},
			'b': {'type': 'stdout', 'data': path.join(pPrepOutput.workdir, '1', 'output', '0.stdout')},
			'c': {'type': 'stderr', 'data': path.join(pPrepOutput.workdir, '1', 'output', '0.stderr')},
		}, {
			'a': path.join(pPrepOutput.workdir, '1', 'output', '0.out'),
			'b': path.join(pPrepOutput.workdir, '1', 'output', '0.stdout'),
			'c': path.join(pPrepOutput.workdir, '1', 'output', '0.stderr'),
		}
		
	def testPrepOutput(self, index, proc, input, output, jobout, outdata, exception = None, msg = None):
		self.maxDiff = None
		proc.props['input']  = input
		proc.props['output'] = output
		job = Job(index, proc)
		job._prepInput()
		if exception:
			self.assertRaisesRegex(exception, msg, job._prepOutput)
		else:
			job._prepOutput()
			self.assertTrue(path.isdir(job.outdir))
			self.assertDictEqual(dict(job.output), jobout)
			self.assertDictEqual(job.data['o'], outdata)

	def dataProvider_testPrepScript(self):
		pPrepScript = Proc()
		pPrepScript.LOG_NLINE['SCRIPT_EXISTS'] = -1
		pPrepScript.props['workdir'] = path.join(self.testdir, 'pPrepScript', 'workdir')
		yield 0, pPrepScript, {}, {}, TemplateLiquid('{{x}}'), '', LiquidRenderError, "NameError: name 'x' is not defined"
		
		sfile = path.join(pPrepScript.workdir, '1', 'job.script')
		makedirs(path.dirname(sfile))
		helpers.writeFile(sfile)
		yield 0, pPrepScript, {'x': {'type': 'var', 'data': [0]}}, {}, TemplateLiquid('1{{i.x}}'), '10', None, None, 'Script file updated'
		
		sfile = path.join(pPrepScript.workdir, '2', 'job.script')
		makedirs(path.dirname(sfile))
		helpers.writeFile(sfile, '11')
		yield 1, pPrepScript, {'x': {'type': 'var', 'data': [0, 1]}}, {}, TemplateLiquid('1{{i.x}}'), '11'

	def testPrepScript(self, index, proc, input, output, script, scriptout, exception = None, msg = None, errmsg = None):
		proc.props['input']  = input
		proc.props['output'] = output
		proc.props['script'] = script
		job = Job(index, proc)
		job._prepInput()
		job._prepOutput()
		if exception:
			self.assertRaisesRegex(exception, msg, job._prepScript)
		else:
			with helpers.log2str(levels = 'all') as (out, err):
				job._prepScript()
			if errmsg:
				self.assertIn(errmsg, err.getvalue())
			self.assertTrue(path.isfile(job.script))
			helpers.assertInFile(self, scriptout, job.script)

	def dataProvider_testLinkInfile(self):
		file1 = path.join(self.testdir, 'testLinkInfile1.txt')
		helpers.writeFile(file1)
		yield [file1, file1], ['testLinkInfile1.txt', 'testLinkInfile1.txt']

		dir2 = path.join(self.testdir, 'testLinkInfileDir')
		makedirs(dir2)
		file2 = path.join(dir2, 'testLinkInfile1.txt')
		helpers.writeFile(file2)
		yield [file1, file2], ['testLinkInfile1.txt', 'testLinkInfile1[1].txt']
		yield [file1, file2, file2], ['testLinkInfile1.txt', 'testLinkInfile1[1].txt', 'testLinkInfile1[1].txt']

		dir3 = path.join(self.testdir, 'testLinkInfileDir3')
		makedirs(dir3)
		file3 = path.join(dir3, 'testLinkInfile1.txt')
		helpers.writeFile(file3)
		yield [file1, file2, file3], ['testLinkInfile1.txt', 'testLinkInfile1[1].txt', 'testLinkInfile1[2].txt']

	def testLinkInfile(self, orgfiles, inbns):
		pLinkInfile = Proc()
		pLinkInfile.props['workdir'] = path.join(self.testdir, 'pLinkInfile', 'workdir')
		job = Job(0, pLinkInfile)
		job._prepInput()
		for i, orgfile in enumerate(orgfiles):
			job._linkInfile(orgfile)
			self.assertTrue(path.samefile(orgfile, path.join(job.indir, inbns[i])))

	def dataProvider_testInit(self):
		pInit = Proc()
		pInit.props['workdir'] = path.join(self.testdir, 'pInit', 'workdir')
		pInit.props['script']  = TemplateLiquid('')
		yield 0, pInit

	def testInit(self, index, proc):
		self.maxDiff = None
		job = Job(index, proc)
		predata = deepcopy(job.data)
		job.init()
		self.assertTrue(path.exists(job.dir))
		self.assertTrue(path.exists(job.indir))
		self.assertTrue(path.exists(job.outfile))
		self.assertTrue(path.exists(job.errfile))
		self.assertDictEqual(predata['job'], job.data['job'])

	def dataProvider_testReportItem(self):
		pReportItem = Proc()
		pReportItem.props['workdir'] = path.join(self.testdir, 'pReportItem', 'workdir')
		pReportItem.props['size'] = 128
		yield 0, pReportItem, 'a', 5, 'hello', 'input', ['INPUT', '[001/128] a     => hello']
		yield 1, pReportItem, 'a', 5, [], 'input', ['INPUT', '[002/128] a     => [  ]']
		yield 1, pReportItem, 'a', 5, ['x'], 'input', ['INPUT', '[002/128] a     => [ x ]']
		yield 1, pReportItem, 'a', 5, ['x', 'y'], 'input', ['INPUT', '[002/128] a     => [ x,', '[002/128]            y ]']
		yield 1, pReportItem, 'a', 5, ['x', 'y', 'z'], 'input', ['INPUT', '[002/128] a     => [ x,', '[002/128]            y,', '[002/128]            z ]']
		yield 1, pReportItem, 'a', 5, ['x', 'y', '', '', 'z'], 'output', ['OUTPUT', '[002/128] a     => [ x,', '[002/128]            y,', '[002/128]            ... (2),', '[002/128]            z ]']
	
	def dataProvider_testIndexIndicator(self):
		pIndexIndicator = Proc()
		yield 0, pIndexIndicator, 100, "[001/100]"
		yield 1, pIndexIndicator, 9, "[2/9]"
		yield 2, pIndexIndicator, 10, "[03/10]"
	
	def testIndexIndicator(self, index, proc, size, out):
		proc.props['size'] = size
		job = Job(index, proc)
		self.assertEqual(job._indexIndicator(), out)
		
	def testReportItem(self, index, proc, key, maxlen, data, loglevel, outs):
		job = Job(index, proc)
		with helpers.log2str() as (out, err):
			job._reportItem(key, maxlen, data, loglevel)
		for o in outs:
			self.assertIn(o, err.getvalue())

	def dataProvider_testReport(self):
		pReport = Proc()
		pReport.props['workdir'] = path.join(self.testdir, 'pReport', 'workdir')
		fileprdir = path.join(self.testdir, 'pReportDir')
		makedirs(fileprdir)
		filepb0 = path.join(fileprdir, 'testReport.br')
		filepb1 = path.join(fileprdir, 'whatever.txt')
		filepb2 = path.join(self.testdir, 'testReport.txt')
		helpers.writeFile(filepb1)
		symlink(filepb1, filepb2)
		helpers.writeFile(filepb0)
		pReport.props['input']   = {
			'a': {'type': 'file', 'data': [filepb2]},
			'b': {'type': 'var', 'data': ['hello']}
		}
		pReport.props['output']  = {'a': ('var', TemplateLiquid('1{{i.a}}'))}
		pReport.props['size']    = 100
		pReport.props['script']  = TemplateLiquid('{{i.a | fn}}.script')
		yield 0, pReport, [
			'INPUT',
			'OUTPUT',
			# 'BRINGS',
			'[001/100]',
			'b => hello',
			'a => 1/'
		]

	def testReport(self, index, proc, outs):
		job = Job(index, proc)
		job.init()
		with helpers.log2str() as (out, err):
			job.report()
		for o in outs:
			self.assertIn(o, err.getvalue())

	def dataProvider_testRc(self):
		pRc = Proc()
		pRc.props['workdir'] = path.join(self.testdir, 'pRc', 'workdir')
		job = Job(0, pRc)
		job1 = Job(1, pRc)
		job2 = Job(2, pRc)
		makedirs(path.join(pRc.workdir, '1'))
		makedirs(path.join(pRc.workdir, '2'))
		makedirs(path.join(pRc.workdir, '3'))
		helpers.writeFile(job1.rcfile)
		helpers.writeFile(job2.rcfile, '-8')
		yield job, None, Job.RC_NOTGENERATE
		yield job1, None, Job.RC_NOTGENERATE
		yield job2, None, -8
		yield job, 1, 1
		yield job, None, 1

	def testRc(self, job, val, exprc):
		if val is None:
			rc = job.rc()
			self.assertEqual(rc, exprc)
		else:
			job.rc(val)
			self.assertEqual(helpers.readFile(job.rcfile, int), exprc)

	def dataProvider_testPid(self):
		pPid = Proc()
		pPid.props['workdir'] = path.join(self.testdir, 'pPid', 'workdir')
		job = Job(0, pPid)
		job1 = Job(1, pPid)
		job2 = Job(2, pPid)
		makedirs(path.join(pPid.workdir, '1'))
		makedirs(path.join(pPid.workdir, '2'))
		makedirs(path.join(pPid.workdir, '3'))
		helpers.writeFile(job1.pidfile)
		helpers.writeFile(job2.pidfile, 'a pid')
		yield job, None, ''
		yield job1, None, ''
		yield job2, None, 'a pid'
		yield job, 1, '1'
		yield job, None, '1'

	def testPid(self, job, val, expid):
		if val is None:
			pid = job.pid()
			self.assertEqual(pid, expid)
		else:
			job.pid(val)
			self.assertEqual(helpers.readFile(job.pidfile), expid)
			
	def dataProvider_testSucceed(self):
		yield 0, [0], True
		yield 1, [0], False
		yield 1, [0,1], True
		yield 2, [0,1], False
			
	def testSucceed(self, jobrc, procrc, out):
		pSucceed = Proc()
		pSucceed.props['workdir'] = path.join(self.testdir, 'pSucceed', 'workdir')
		pSucceed.props['rc'] = procrc
		job = Job(0, pSucceed)
		if not path.isdir(job.dir):
			makedirs(job.dir)
		job.rc(jobrc)
		self.assertEqual(job.succeed(), out)
		
	def dataProvider_testCheckoutfiles(self):
		pCheckoutfiles1 = Proc()
		pCheckoutfiles1.props['workdir'] = path.join(self.testdir, 'pCheckoutfiles1', 'workdir')
		pCheckoutfiles1.props['expect'] = TemplateLiquid('grep content {{o.a}}')
		pCheckoutfiles1.props['script'] = TemplateLiquid('')
		pCheckoutfiles1.props['output'] = {
			'a': ('var', TemplateLiquid('whatever'))
		}
		job1 = Job(0, pCheckoutfiles1)
		job1.init()
		job1.rc(0)
		yield job1, False, 0
		yield job1, True, Job.RC_EXPECTFAIL
		
		pCheckoutfiles2 = Proc()
		pCheckoutfiles2.props['workdir'] = path.join(self.testdir, 'pCheckoutfiles2', 'workdir')
		pCheckoutfiles2.props['expect'] = TemplateLiquid('grep content {{o.a}}')
		pCheckoutfiles2.props['script'] = TemplateLiquid('')
		pCheckoutfiles2.props['output'] = {
			'a': ('file', TemplateLiquid('whatever.txt'))
		}
		job2 = Job(0, pCheckoutfiles2)
		job2.init()
		job2.rc(0)
		helpers.writeFile(path.join(job2.outdir, 'whatever.txt'), 'xxx')
		yield job2, True, Job.RC_EXPECTFAIL
		yield job2, False, 0
		
		pCheckoutfiles3 = Proc()
		pCheckoutfiles3.props['workdir'] = path.join(self.testdir, 'pCheckoutfiles3', 'workdir')
		pCheckoutfiles3.props['expect'] = TemplateLiquid('grep content {{o.a}}')
		pCheckoutfiles3.props['script'] = TemplateLiquid('')
		pCheckoutfiles3.props['output'] = {
			'a': ('file', TemplateLiquid('whatever.txt'))
		}
		job3 = Job(0, pCheckoutfiles3)
		job3.init()
		job3.rc(0)
		helpers.writeFile(path.join(job3.outdir, 'whatever.txt'), '1content2')
		yield job3, True, 0
		yield job3, False, 0
		
		pCheckoutfiles4 = Proc()
		pCheckoutfiles4.props['workdir'] = path.join(self.testdir, 'pCheckoutfiles4', 'workdir')
		pCheckoutfiles4.props['script'] = TemplateLiquid('')
		pCheckoutfiles4.props['output'] = {
			'a': ('file', TemplateLiquid('whatever.txt'))
		}
		job4 = Job(0, pCheckoutfiles4)
		job4.init()
		job4.rc(0)
		yield job4, False, Job.RC_NOOUTFILE
			
	def testCheckoutfiles(self, job, expect, outrc):
		with helpers.log2str():
			job.checkOutfiles(expect)
		self.assertEqual(job.rc(), outrc)
		job.rc(0)
		
	def dataProvider_testExportSingle(self):
		pExportSingle1 = Proc()
		pExportSingle1.props['workdir'] = path.join(self.testdir, 'pExportSingle1', 'workdir')
		job1 = Job(0, pExportSingle1)
		yield job1, [], []
		
		pExportSingle2 = Proc()
		pExportSingle2.props['workdir'] = path.join(self.testdir, 'pExportSingle2', 'workdir')
		pExportSingle2.props['exdir'] = path.join(self.testdir, 'notexist')
		job2 = Job(1, pExportSingle2)
		yield job2, [], [], AssertionError
		
		pExportSingle3 = Proc()
		pExportSingle3.props['workdir'] = path.join(self.testdir, 'pExportSingle3', 'workdir')
		pExportSingle3.props['exdir'] = path.join(self.testdir, 'exdir')
		pExportSingle3.props['expart'] = 1
		job3 = Job(1, pExportSingle3)
		if not path.exists(pExportSingle3.exdir):
			makedirs(pExportSingle3.exdir)
		yield job3, [], [], AssertionError
		
		pExportSingle4 = Proc()
		pExportSingle4.props['workdir'] = path.join(self.testdir, 'pExportSingle4', 'workdir')
		pExportSingle4.props['script'] = TemplateLiquid('')
		pExportSingle4.props['exdir'] = path.join(self.testdir, 'exdir')
		pExportSingle4.props['exhow'] = 'move'
		pExportSingle4.props['output'] = {
			'a': ('file', TemplateLiquid('whatever.txt'))
		}
		job4 = Job(0, pExportSingle4)
		job4.init()
		afile4    = path.join(job4.outdir, 'whatever.txt')
		afile4_ex = path.join(pExportSingle4.exdir, 'whatever.txt')
		helpers.writeFile(afile4)
		yield job4, [(path.isfile, afile4_ex), (path.exists, afile4), (path.islink, afile4)], [(path.islink, afile4_ex)]
		
		pExportSingle5 = Proc()
		pExportSingle5.props['workdir'] = path.join(self.testdir, 'pExportSingle5', 'workdir')
		pExportSingle5.props['script']  = TemplateLiquid('')
		pExportSingle5.props['exdir']   = path.join(self.testdir, 'exdir')
		pExportSingle5.props['exow']    = True
		pExportSingle5.props['exhow']   = 'move'
		pExportSingle5.props['output']  = {
			'a': ('file', TemplateLiquid('whatever.txt'))
		}
		job5 = Job(0, pExportSingle5)
		job5.init()
		afile5    = path.join(job5.outdir, 'whatever.txt')
		afile5_ex = path.join(pExportSingle5.exdir, 'whatever.txt')
		helpers.writeFile(afile5)
		helpers.writeFile(afile5_ex, 'afile5_ex')
		yield job5, [(path.isfile, afile5_ex), (path.exists, afile5), (path.islink, afile5)], [(path.islink, afile5_ex), (lambda x: helpers.readFile(x) == 'afile5_ex', afile5_ex)]
		
		pExportSingle6 = Proc()
		pExportSingle6.props['workdir'] = path.join(self.testdir, 'pExportSingle6', 'workdir')
		pExportSingle6.props['script']  = TemplateLiquid('')
		pExportSingle6.props['exdir']   = path.join(self.testdir, 'exdir')
		pExportSingle6.props['exow']    = True
		pExportSingle6.props['exhow']   = 'gz'
		pExportSingle6.props['output']  = {
			'a': ('file', TemplateLiquid('whatever.txt')),
			'b': ('dir', TemplateLiquid('whatever.dir'))
		}
		job6 = Job(0, pExportSingle6)
		job6.init()
		afile6    = path.join(job6.outdir, 'whatever.txt')
		afile6_ex = path.join(pExportSingle6.exdir, 'whatever.txt.gz')
		bfile6    = path.join(job6.outdir, 'whatever.dir')
		bfile6_ex = path.join(pExportSingle6.exdir, 'whatever.dir.tgz')
		helpers.writeFile(afile6)
		makedirs(bfile6)
		yield job6, [(path.isfile, afile6_ex), (path.isfile, bfile6_ex), (path.isdir, bfile6), (path.exists, afile6)], []
		
		pExportSingle7 = Proc()
		pExportSingle7.props['workdir'] = path.join(self.testdir, 'pExportSingle7', 'workdir')
		pExportSingle7.props['script']  = TemplateLiquid('')
		pExportSingle7.props['exdir']   = path.join(self.testdir, 'exdir')
		pExportSingle7.props['exow']    = True
		pExportSingle7.props['exhow']   = 'gz'
		pExportSingle7.props['output']  = {
			'a': ('file', TemplateLiquid('whatever7.txt'))
		}
		job7 = Job(0, pExportSingle7)
		job7.init()
		afile7    = path.join(job7.outdir, 'whatever7.txt')
		afile7_ex = path.join(pExportSingle7.exdir, 'whatever7.txt')
		helpers.writeFile(afile7)
		# same file
		symlink(afile7, afile7_ex)
		yield job7, [(path.isfile, afile7_ex), (path.isfile, afile7), (lambda x: path.samefile(afile7_ex, x), afile7)], []
		
		# copy
		pExportSingle8 = Proc()
		pExportSingle8.props['workdir'] = path.join(self.testdir, 'pExportSingle8', 'workdir')
		pExportSingle8.props['script']  = TemplateLiquid('')
		pExportSingle8.props['exdir']   = path.join(self.testdir, 'exdir')
		pExportSingle8.props['exow']    = True
		pExportSingle8.props['exhow']   = 'copy'
		pExportSingle8.props['output']  = {
			'a': ('file', TemplateLiquid('whatever8.txt'))
		}
		job8 = Job(0, pExportSingle8)
		job8.init()
		afile8    = path.join(job8.outdir, 'whatever8.txt')
		afile8_ex = path.join(pExportSingle8.exdir, 'whatever8.txt')
		helpers.writeFile(afile8)
		yield job8, [(path.isfile, afile8_ex), (path.isfile, afile8)], [(path.islink, afile8_ex), (path.islink, afile8)]
		
		# link
		pExportSingle9 = Proc()
		pExportSingle9.props['workdir'] = path.join(self.testdir, 'pExportSingle9', 'workdir')
		pExportSingle9.props['script']  = TemplateLiquid('')
		pExportSingle9.props['exdir']   = path.join(self.testdir, 'exdir')
		pExportSingle9.props['exow']    = True
		pExportSingle9.props['exhow']   = 'link'
		pExportSingle9.props['output']  = {
			'a': ('file', TemplateLiquid('whatever9.txt'))
		}
		job9 = Job(0, pExportSingle9)
		job9.init()
		afile9    = path.join(job9.outdir, 'whatever9.txt')
		afile9_ex = path.join(pExportSingle9.exdir, 'whatever9.txt')
		helpers.writeFile(afile9)
		yield job9, [(path.islink, afile9_ex), (path.isfile, afile9)], []
		
		# expart (glob)
		pExportSingle10 = Proc()
		pExportSingle10.props['workdir'] = path.join(self.testdir, 'pExportSingle10', 'workdir')
		pExportSingle10.props['script']  = TemplateLiquid('')
		pExportSingle10.props['exdir']   = path.join(self.testdir, 'exdir')
		pExportSingle10.props['expart']  = [TemplateLiquid('*.txt')]
		pExportSingle10.props['output']  = {
			'a': ('file', TemplateLiquid('whatever10.txt'))
		}
		job10 = Job(0, pExportSingle10)
		job10.init()
		afile10    = path.join(job10.outdir, 'whatever10.txt')
		afile10_ex = path.join(pExportSingle10.exdir, 'whatever10.txt')
		helpers.writeFile(afile10)
		yield job10, [(path.isfile, afile10_ex), (path.islink, afile10)], []
		
		# expart (outkey)
		pExportSingle11 = Proc()
		pExportSingle11.props['workdir'] = path.join(self.testdir, 'pExportSingle11', 'workdir')
		pExportSingle11.props['script']  = TemplateLiquid('')
		pExportSingle11.props['exdir']   = path.join(self.testdir, 'exdir')
		pExportSingle11.props['expart']  = [TemplateLiquid('a')]
		pExportSingle11.props['output']  = {
			'a': ('file', TemplateLiquid('whatever11.txt'))
		}
		job11 = Job(0, pExportSingle11)
		job11.init()
		afile11    = path.join(job11.outdir, 'whatever11.txt')
		afile11_ex = path.join(pExportSingle11.exdir, 'whatever11.txt')
		helpers.writeFile(afile11)
		yield job11, [(path.isfile, afile11_ex), (path.islink, afile11)], []
		
		# expart (no matches)
		pExportSingle12 = Proc()
		pExportSingle12.props['workdir'] = path.join(self.testdir, 'pExportSingle12', 'workdir')
		pExportSingle12.props['script']  = TemplateLiquid('')
		pExportSingle12.props['exdir']   = path.join(self.testdir, 'exdir')
		pExportSingle12.props['expart']  = [TemplateLiquid('b')]
		pExportSingle12.props['output']  = {
			'a': ('file', TemplateLiquid('whatever12.txt'))
		}
		job12 = Job(0, pExportSingle12)
		job12.init()
		afile12    = path.join(job12.outdir, 'whatever12.txt')
		afile12_ex = path.join(pExportSingle12.exdir, 'whatever12.txt')
		helpers.writeFile(afile12)
		yield job12, [(path.isfile, afile12)], [(path.isfile, afile12_ex), (path.islink, afile12)]
		
		pExportSingle13 = Proc()
		pExportSingle13.props['workdir'] = path.join(self.testdir, 'pExportSingle13', 'workdir')
		pExportSingle13.props['script'] = TemplateLiquid('')
		pExportSingle13.props['exdir'] = path.join(self.testdir, 'exdir')
		pExportSingle13.props['exhow'] = 'move'
		pExportSingle13.props['output'] = {
			'a': ('stdout', TemplateLiquid('whatever.out')),
			'b': ('stderr', TemplateLiquid('whatever.err'))
		}
		job13 = Job(0, pExportSingle13)
		job13.init()
		afile13    = path.join(job13.outdir, 'whatever.out')
		afile13_ex = path.join(pExportSingle13.exdir, 'whatever.out')
		bfile13    = path.join(job13.outdir, 'whatever.err')
		bfile13_ex = path.join(pExportSingle13.exdir, 'whatever.err')
		helpers.writeFile(afile13)
		helpers.writeFile(bfile13)
		yield job13, [(path.isfile, afile13_ex), (path.isfile, bfile13_ex)], [(path.islink, afile13_ex), (path.islink, bfile13_ex)]
		
	def testExportSingle(self, job, truths, falsehoods, exception = None):
		if exception:
			self.assertRaises(exception, job.export)
		else:
			with helpers.log2str():
				job.export()
			for func, outfile in truths:
				self.assertTrue(func(outfile))
			for func, outfile in falsehoods:
				self.assertFalse(func(outfile))
				
	def dataProvider_testExport(self):
		pExport = Proc()
		pExport.props['workdir'] = path.join(self.testdir, 'pExport', 'workdir')
		pExport.props['script']  = TemplateLiquid('')
		pExport.props['exdir']   = path.join(self.testdir, 'exdir')
		pExport.props['output']  = {
			'a': ('file', TemplateLiquid('pexport-multiple.txt'))
		}
		somefile = path.join(self.testdir, 'somefile')
		helpers.writeFile(somefile)
		if not path.exists(pExport.exdir):
			makedirs(pExport.exdir)
		truths = [(path.isfile, somefile), (path.isfile, path.join(pExport.exdir, 'pexport-multiple.txt'))]
		falsehoolds = [(path.islink, somefile), (path.islink, path.join(pExport.exdir, 'pexport-multiple.txt'))]
		tappend = truths.append
		fappend = falsehoolds.append
		jobs = []
		for i in range(2):
			job = Job(i, pExport)
			jobs.append(job)
			job.init()
			outfile = path.join(job.outdir, 'pexport-multiple.txt')
			symlink(somefile, outfile)
			tappend((path.islink, outfile))
		
		jobs1 = []
		truths1 = []
		falsehoolds1 = []
		tappend1 = truths1.append
		fappend1 = falsehoolds1.append
		for i in range(2, 20):
			job = Job(i, pExport)
			jobs1.append(job)
			job.init()
			outfile = path.join(job.outdir, 'pexport-multiple.txt')
			symlink(somefile, outfile)
			tappend1((path.isfile, outfile))
			
		jobs2 = []
		truths2 = []
		falsehoolds2 = []
		tappend2 = truths2.append
		fappend2 = falsehoolds2.append
		for i in range(20, 100):
			job = Job(i, pExport)
			jobs2.append(job)
			job.init()
			outfile = path.join(job.outdir, 'pexport-multiple.txt')
			symlink(somefile, outfile)
			tappend2((path.isfile, outfile))
		yield jobs, truths, falsehoolds
		yield jobs1, truths1, falsehoolds1
		yield jobs2, truths2, falsehoolds2
						
	def testExport(self, jobs, truths, falsehoods):
		def export_func(i):
			with self.assertLogs():
				jobs[i].export()
		utils.parallel.Parallel(len(jobs), 'thread').run(export_func, [(i,) for i in range(len(jobs))])
		#utils.parallel(func = export_func, args = [(i,) for i in range(len(jobs))], nthread = len(jobs), method = 'process')
		i = 0
		for func, outfile in truths:
			self.assertTrue(func(outfile))
		for func, outfile in falsehoods:
			self.assertFalse(func(outfile))
			
	def dataProvider_testReset(self):
		pReset = Proc()
		pReset.props['workdir'] = path.join(self.testdir, 'pReset', 'workdir')
		pReset.props['script']  = TemplateLiquid('')
		pReset.props['output']  = {
			'a': ('file', TemplateLiquid('preset.txt')),
			'b': ('dir', TemplateLiquid('preset.dir')),
			'c': ('stdout', TemplateLiquid('stdout.txt')),
			'd': ('stderr', TemplateLiquid('stderr.txt'))
		}
		job = Job(0, pReset)
		job.init()
		helpers.writeFile(job.rcfile, 0)
		helpers.writeFile(job.pidfile)
		job1 = Job(1, pReset)
		job1.init()
		helpers.writeFile(job1.rcfile, 0)
		helpers.writeFile(job1.pidfile)
		job2 = Job(2, pReset)
		job2.init()
		helpers.writeFile(job2.rcfile, 0)
		helpers.writeFile(job2.pidfile)
		job3 = Job(3, pReset)
		job3.init()
		helpers.writeFile(job3.rcfile, 0)
		helpers.writeFile(job3.pidfile)
		makedirs(path.join(job3.dir, 'retry.8'))
		yield job, 0, ['preset.txt'], ['preset.dir']
		yield job1, 1, ['preset.txt'], ['preset.dir']
		yield job2, 2, ['preset.txt'], ['preset.dir']
		yield job3, 0, ['preset.txt'], ['preset.dir']
		
	def testReset(self, job, retry, outfiles = [], outdirs = []):
		job.reset(retry)
		if not retry:
			retrydirs = glob(path.join(job.dir, 'retry.*'))
			self.assertListEqual(retrydirs, [])
		else:
			retrydir = path.join(job.dir, 'retry.' + str(retry))
			self.assertTrue(path.isdir(retrydir))
			self.assertTrue(path.exists(path.join(retrydir, path.basename(job.rcfile))))
			self.assertTrue(path.exists(path.join(retrydir, path.basename(job.outfile))))
			self.assertTrue(path.exists(path.join(retrydir, path.basename(job.errfile))))
			self.assertTrue(path.exists(path.join(retrydir, path.basename(job.pidfile))))
			self.assertTrue(path.exists(path.join(retrydir, path.basename(job.outdir))))
		self.assertFalse(path.exists(job.rcfile))
		self.assertFalse(path.exists(job.outfile))
		self.assertFalse(path.exists(job.errfile))
		self.assertFalse(path.exists(job.pidfile))
		self.assertTrue(path.exists(job.outdir))
		for outfile in outfiles:
			self.assertFalse(path.exists(path.join(job.outdir, outfile)))
		for outdir in outdirs:
			self.assertTrue(path.exists(path.join(job.outdir, outdir)))
		
	def dataProvider_testShowError(self):
		# ignore
		pShowError = Proc()
		pShowError.props['workdir'] = path.join(self.testdir, 'pShowError', 'workdir')
		pShowError.props['script']  = TemplateLiquid('')
		pShowError.props['errhow']  = 'ignore'
		pShowError.props['size']    = 1
		job = Job(0, pShowError)
		job.init()
		job.rc(Job.RC_NOOUTFILE)
		yield job, 1, ['WARNING', '[1/1] failed but ignored (totally 1). Return code: %s (%s)' % (Job.RC_NOOUTFILE, Job.MSG_RC_NOOUTFILE)], ['ERROR']
		
		# empty stderr
		pShowError1 = Proc()
		pShowError1.props['workdir'] = path.join(self.testdir, 'pShowError1', 'workdir')
		pShowError1.props['script']  = TemplateLiquid('')
		pShowError1.props['echo']    = {'jobs': [0], 'type': []}
		pShowError1.props['size']    = 10
		job1 = Job(0, pShowError1)
		job1.init()
		job1.rc(Job.RC_NOTGENERATE)
		yield job1, 10, ['ERROR', '[01/10] failed (totally 10). Return code: %s (%s)' % (Job.RC_NOTGENERATE, Job.MSG_RC_NOTGENERATE), '<EMPTY STDERR>']
		
		# errors less than 20 lines
		pShowError2 = Proc()
		pShowError2.props['workdir'] = path.join(self.testdir, 'pShowError2', 'workdir')
		pShowError2.props['script']  = TemplateLiquid('')
		pShowError2.props['echo']    = {'jobs': [0], 'type': []}
		pShowError2.props['size']    = 10
		job2 = Job(0, pShowError2)
		job2.init()
		job2.rc(Job.RC_EXPECTFAIL)
		helpers.writeFile(job2.errfile, '\n'.join(['Error' + str(i) for i in range(5)]))
		yield job2, 10, ['ERROR', '[01/10] failed (totally 10). Return code: %s (%s)' % (Job.RC_EXPECTFAIL, Job.MSG_RC_EXPECTFAIL), 'Error0', 'Error1', 'Error2', 'Error3', 'Error4'], ['Error5', 'ignored'] 
		
		# errors more than 20 lines
		pShowError3 = Proc()
		pShowError3.props['workdir'] = path.join(self.testdir, 'pShowError3', 'workdir')
		pShowError3.props['script']  = TemplateLiquid('')
		pShowError3.props['echo']    = {'jobs': [0], 'type': []}
		pShowError3.props['size']    = 10
		job3 = Job(0, pShowError3)
		job3.init()
		job3.rc(Job.RC_SUBMITFAIL)
		helpers.writeFile(job3.errfile, '\n'.join(['Error' + str(i) for i in range(25)]))
		yield job3, 10, ['ERROR', '[01/10] failed (totally 10). Return code: %s (%s)' % (Job.RC_SUBMITFAIL, Job.MSG_RC_SUBMITFAIL), 'Error5', 'Error15', 'Error19', 'Error24'], ['Error0', 'Error4']
		# Error1, Error2 will be found as Error10, Error20 are there
		# Error3 will be found because pShowError3
		
		# not in echo, don't print stderr
		pShowError4 = Proc()
		pShowError4.props['workdir'] = path.join(self.testdir, 'pShowError4', 'workdir')
		pShowError4.props['script']  = TemplateLiquid('')
		pShowError4.props['echo']    = {'jobs': [0], 'type': ['stderr']}
		pShowError4.props['size']    = 10
		job4 = Job(0, pShowError4)
		job4.init()
		job4.rc(140)
		helpers.writeFile(job4.errfile, '\n'.join(['Error' + str(i) for i in range(25)]))
		yield job4, 10, ['ERROR', '[01/10] failed (totally 10). Return code: %s (%s)' % (140, Job.MSG_RC_OTHER)], ['Error0', 'Error5', 'Error15', 'Error19', 'Error24']
	
	def testShowError(self, job, totalfailed, errs, errsnotin = []):
		with helpers.log2str() as (out, err):
			job.showError(totalfailed)
		stderr = err.getvalue()
		for err in errs:
			self.assertIn(err, stderr)
		for err in errsnotin:
			self.assertNotIn(err, stderr)
			
	def dataProvider_testSignature(self):
		# empty script
		pSignature = Proc()
		pSignature.props['workdir'] = path.join(self.testdir, 'pSignature', 'workdir')
		pSignature.props['script']  = TemplateLiquid('')
		pSignature.props['size']    = 10
		pSignature.LOG_NLINE['CACHE_EMPTY_CURRSIG'] = -1
		job = Job(0, pSignature)
		job.init()
		#utils.safeRemove(job.script)
		utils.safefs.remove(job.script)
		yield job, '', ['DEBUG', '[01/10] Empty signature because of script file']
		
		# input file empty
		infile1 = path.join(self.testdir, 'pSignature1.txt')
		helpers.writeFile(infile1)
		pSignature1 = Proc()
		pSignature1.props['workdir'] = path.join(self.testdir, 'pSignature1', 'workdir')
		pSignature1.props['script']  = TemplateLiquid('')
		pSignature1.props['size']    = 10
		pSignature1.props['input']   = {
			'a': {'type': 'file', 'data': [infile1]}
		}
		pSignature1.LOG_NLINE['CACHE_EMPTY_CURRSIG'] = -1
		job1 = Job(0, pSignature1)
		job1.init()
		#utils.safeRemove(infile1)
		utils.safefs.remove(infile1)
		yield job1, '', ['DEBUG', '[01/10] Empty signature because of input file']
		
		# input files empty
		infile2 = path.join(self.testdir, 'pSignature2.txt')
		helpers.writeFile(infile2)
		pSignature2 = Proc()
		pSignature2.props['workdir'] = path.join(self.testdir, 'pSignature2', 'workdir')
		pSignature2.props['script']  = TemplateLiquid('')
		pSignature2.props['size']    = 10
		pSignature2.props['input']   = {
			'a': {'type': 'files', 'data': [[infile2]]}
		}
		pSignature2.LOG_NLINE['CACHE_EMPTY_CURRSIG'] = -1
		job2 = Job(0, pSignature2)
		job2.init()
		#utils.safeRemove(infile2)
		utils.safefs.remove(infile2)
		yield job2, '', ['DEBUG', '[01/10] Empty signature because of one of input files']
		
		# outfile empty
		pSignature3 = Proc()
		pSignature3.props['workdir'] = path.join(self.testdir, 'pSignature3', 'workdir')
		pSignature3.props['script']  = TemplateLiquid('')
		pSignature3.props['size']    = 10
		pSignature3.props['output']  = {
			'a': ('file', TemplateLiquid('pSignature3.txt'))
		}
		pSignature3.LOG_NLINE['CACHE_EMPTY_CURRSIG'] = -1
		job3 = Job(0, pSignature3)
		job3.init()
		yield job3, '', ['DEBUG', '[01/10] Empty signature because of output file']
		
		# outdir empty
		pSignature4 = Proc()
		pSignature4.props['workdir'] = path.join(self.testdir, 'pSignature4', 'workdir')
		pSignature4.props['script']  = TemplateLiquid('')
		pSignature4.props['size']    = 10
		pSignature4.props['output']  = {
			'a': ('dir', TemplateLiquid('pSignature4.dir'))
		}
		pSignature4.LOG_NLINE['CACHE_EMPTY_CURRSIG'] = -1
		job4 = Job(0, pSignature4)
		job4.init()
		yield job4, '', ['DEBUG', '[01/10] Empty signature because of output dir']
		
		# normal signature
		infile5 = path.join(self.testdir, 'pSignature5.txt')
		infile5_1 = path.join(self.testdir, 'pSignature5_1.txt')
		infile5_2 = path.join(self.testdir, 'pSignature5_2.txt')
		helpers.writeFile(infile5)
		helpers.writeFile(infile5_1)
		helpers.writeFile(infile5_2)
		pSignature5 = Proc()
		pSignature5.props['workdir'] = path.join(self.testdir, 'pSignature5', 'workdir')
		pSignature5.props['script']  = TemplateLiquid('')
		pSignature5.props['size']    = 10
		pSignature5.props['input']   = {
			'a': {'type': 'file', 'data': [infile5]},
			'b': {'type': 'files', 'data': [[infile5_1, infile5_2]]}
		}
		pSignature5.props['output']  = {
			'a': ('file', TemplateLiquid('pSignature5.txt')),
			'b': ('dir', TemplateLiquid('pSignature5.dir'))
		}
		pSignature5.LOG_NLINE['CACHE_EMPTY_CURRSIG'] = -1
		job5 = Job(0, pSignature5)
		job5.init()
		ina = path.join(job5.indir, 'pSignature5.txt')
		inb1 = path.join(job5.indir, 'pSignature5_1.txt')
		inb2 = path.join(job5.indir, 'pSignature5_2.txt')
		outa = path.join(job5.outdir, 'pSignature5.txt')
		outb = path.join(job5.outdir, 'pSignature5.dir')
		helpers.writeFile(outa)
		makedirs(outb)
		yield job5, {
			'i': {
				'file': {
					'a': [ina, int(path.getmtime(ina))]
				},
				'files': {
					'b': [
						[inb1, int(path.getmtime(inb1))],
						[inb2, int(path.getmtime(inb2))],
					]
				},
				'var': {}
			},
			'o': {
				'dir': {
					'b': [outb, int(path.getmtime(outb))]
				},
				'file': {
					'a': [outa, int(path.getmtime(outa))]
				},
				'var': {}
			},
			'script': [job5.script, int(path.getmtime(job5.script))]
		}
			
	def testSignature(self, job, outsig, errs = []):
		self.maxDiff = None
		with helpers.log2str(levels = 'all') as (out, err):
			sig = job.signature()
		if isinstance(sig, dict):
			self.assertDictEqual(sig, outsig)
		else:
			self.assertEqual(sig, outsig)
		stderr = err.getvalue()
		for err in errs:
			self.assertIn(err, stderr)
	
	def dataProvider_testCache(self):		
		# normal signature
		infile = path.join(self.testdir, 'pCache.txt')
		infile_1 = path.join(self.testdir, 'pCache_1.txt')
		infile_2 = path.join(self.testdir, 'pCache_2.txt')
		helpers.writeFile(infile)
		helpers.writeFile(infile_1)
		helpers.writeFile(infile_2)
		pCache = Proc()
		pCache.props['workdir'] = path.join(self.testdir, 'pCache', 'workdir')
		pCache.props['script']  = TemplateLiquid('')
		pCache.props['cache']   = True
		pCache.props['size']    = 10
		pCache.LOG_NLINE['CACHE_EMPTY_CURRSIG'] = -1
		pCache.props['input']   = {
			'a': {'type': 'file', 'data': [infile]},
			'b': {'type': 'files', 'data': [[infile_1, infile_2]]}
		}
		pCache.props['output']  = {
			'a': ('file', TemplateLiquid('pCache.txt')),
			'b': ('dir', TemplateLiquid('pCache.dir'))
		}
		pCache.LOG_NLINE['CACHE_EMPTY_CURRSIG'] = -1
		job = Job(0, pCache)
		job.init()
		ina = path.join(job.indir, 'pCache.txt')
		inb1 = path.join(job.indir, 'pCache_1.txt')
		inb2 = path.join(job.indir, 'pCache_2.txt')
		outa = path.join(job.outdir, 'pCache.txt')
		outb = path.join(job.outdir, 'pCache.dir')
		helpers.writeFile(outa)
		makedirs(outb)
		yield job, True, {
			'i': {
				'file': {
					'a': [ina, int(path.getmtime(ina))]
				},
				'files': {
					'b': [
						[inb1, int(path.getmtime(inb1))],
						[inb2, int(path.getmtime(inb2))],
					]
				},
				'var': {}
			},
			'o': {
				'dir': {
					'b': [outb, int(path.getmtime(outb))]
				},
				'file': {
					'a': [outa, int(path.getmtime(outa))]
				},
				'var': {}
			},
			'script': [job.script, int(path.getmtime(job.script))]
		}
		
		#
		pCache1 = Proc()
		pCache1.props['workdir'] = path.join(self.testdir, 'pCache1', 'workdir')
		pCache1.props['script']  = TemplateLiquid('')
		pCache1.props['cache']   = False
		pCache1.LOG_NLINE['CACHE_EMPTY_CURRSIG'] = -1
		job1 = Job(0, pCache1)
		job1.init()
		yield job1, False, {}
		
	def testCache(self, job, cache, outsig):
		helpers.log2sys(levels = 'all')
		job.cache()
		if not cache:
			self.assertFalse(path.exists(job.cachefile))
		else:
			self.assertDictEqual(helpers.readFile(job.cachefile, json.loads), outsig)
			
	def dataProvider_testIsTrulyCached(self):
		# no cache file
		pIsTrulyCached = Proc()
		pIsTrulyCached.props['workdir'] = path.join(self.testdir, 'pIsTrulyCached', 'workdir')
		pIsTrulyCached.props['script']  = TemplateLiquid('')
		pIsTrulyCached.LOG_NLINE['CACHE_SIGFILE_NOTEXISTS'] = -1
		job = Job(0, pIsTrulyCached)
		job.init()
		yield job, False, ['DEBUG', 'not cached as cache file not exists.']
		
		# empty cache file
		pIsTrulyCached1 = Proc()
		pIsTrulyCached1.props['workdir'] = path.join(self.testdir, 'pIsTrulyCached1', 'workdir')
		pIsTrulyCached1.props['script']  = TemplateLiquid('')
		pIsTrulyCached1.LOG_NLINE['CACHE_EMPTY_PREVSIG'] = -1
		job1 = Job(0, pIsTrulyCached1)
		job1.init()
		helpers.writeFile(job1.cachefile)
		yield job1, False, ['DEBUG', 'not cached because previous signature is empty.']
		
		# current signature empty
		infile = path.join(self.testdir, 'pIsTrulyCached2.txt')
		infile_1 = path.join(self.testdir, 'pIsTrulyCached2_1.txt')
		infile_2 = path.join(self.testdir, 'pIsTrulyCached2_2.txt')
		helpers.writeFile(infile)
		helpers.writeFile(infile_1)
		helpers.writeFile(infile_2)
		pIsTrulyCached2 = Proc()
		pIsTrulyCached2.props['workdir'] = path.join(self.testdir, 'pIsTrulyCached2', 'workdir')
		pIsTrulyCached2.props['script']  = TemplateLiquid('')
		pIsTrulyCached2.props['cache']   = True
		pIsTrulyCached2.props['size']    = 10
		pIsTrulyCached2.LOG_NLINE['CACHE_EMPTY_CURRSIG'] = -1
		pIsTrulyCached2.props['input']   = {
			'a': {'type': 'file', 'data': [infile]},
			'b': {'type': 'files', 'data': [[infile_1, infile_2]]}
		}
		pIsTrulyCached2.props['output']  = {
			'a': ('file', TemplateLiquid('pIsTrulyCached2.txt')),
			'b': ('dir', TemplateLiquid('pIsTrulyCached2.dir'))
		}
		del pIsTrulyCached2.LOG_NLINE['CACHE_EMPTY_CURRSIG']
		job2 = Job(0, pIsTrulyCached2)
		job2.init()
		ina = path.join(job2.indir, 'pIsTrulyCached2.txt')
		inb1 = path.join(job2.indir, 'pIsTrulyCached2_1.txt')
		inb2 = path.join(job2.indir, 'pIsTrulyCached2_2.txt')
		outa = path.join(job2.outdir, 'pIsTrulyCached2.txt')
		outb = path.join(job2.outdir, 'pIsTrulyCached2.dir')
		helpers.writeFile(outa)
		makedirs(outb)
		with helpers.log2str():
			job2.cache()
		#utils.safeRemove(outb)
		utils.safefs.remove(outb)
		yield job2, False, ['DEBUG', 'mpty', 'signature', 'because']
		
		# script file newer
		infile = path.join(self.testdir, 'pIsTrulyCached3.txt')
		infile_1 = path.join(self.testdir, 'pIsTrulyCached3_1.txt')
		infile_2 = path.join(self.testdir, 'pIsTrulyCached3_2.txt')
		helpers.writeFile(infile)
		helpers.writeFile(infile_1)
		helpers.writeFile(infile_2)
		pIsTrulyCached3 = Proc()
		pIsTrulyCached3.props['workdir'] = path.join(self.testdir, 'pIsTrulyCached3', 'workdir')
		pIsTrulyCached3.props['script']  = TemplateLiquid('')
		pIsTrulyCached3.props['cache']   = True
		pIsTrulyCached3.props['size']    = 10
		pIsTrulyCached3.LOG_NLINE['CACHE_EMPTY_CURRSIG'] = -1
		pIsTrulyCached3.props['input']   = {
			'a': {'type': 'file', 'data': [infile]},
			'b': {'type': 'files', 'data': [[infile_1, infile_2]]},
			'c': {'type': 'var', 'data': ['var_c']}
		}
		pIsTrulyCached3.props['output']  = {
			'a': ('file', TemplateLiquid('pIsTrulyCached3.txt')),
			'b': ('dir', TemplateLiquid('pIsTrulyCached3.dir'))
		}
		del pIsTrulyCached3.LOG_NLINE['CACHE_EMPTY_CURRSIG']
		del pIsTrulyCached3.LOG_NLINE['CACHE_SCRIPT_NEWER']
		job3 = Job(0, pIsTrulyCached3)
		job3.init()
		ina = path.join(job3.indir, 'pIsTrulyCached3.txt')
		inb1 = path.join(job3.indir, 'pIsTrulyCached3_1.txt')
		inb2 = path.join(job3.indir, 'pIsTrulyCached3_2.txt')
		outa = path.join(job3.outdir, 'pIsTrulyCached3.txt')
		outb = path.join(job3.outdir, 'pIsTrulyCached3.dir')
		helpers.writeFile(outa)
		makedirs(outb)
		with helpers.log2str():
			job3.cache()
		utime(job3.script, (time() + 10, time() + 10))
		yield job3, False, ['DEBUG', 'not cached because script file(script) is newer:', '- Previous:', '- Current']
		
		# script file newer
		infile = path.join(self.testdir, 'pIsTrulyCached4.txt')
		infile_1 = path.join(self.testdir, 'pIsTrulyCached4_1.txt')
		infile_2 = path.join(self.testdir, 'pIsTrulyCached4_2.txt')
		helpers.writeFile(infile)
		helpers.writeFile(infile_1)
		helpers.writeFile(infile_2)
		pIsTrulyCached4 = Proc()
		pIsTrulyCached4.props['workdir'] = path.join(self.testdir, 'pIsTrulyCached4', 'workdir')
		pIsTrulyCached4.props['script']  = TemplateLiquid('')
		pIsTrulyCached4.props['cache']   = True
		pIsTrulyCached4.props['size']    = 10
		pIsTrulyCached4.LOG_NLINE['CACHE_EMPTY_CURRSIG'] = -1
		pIsTrulyCached4.props['input']   = {
			'a': {'type': 'file', 'data': [infile]},
			'b': {'type': 'files', 'data': [[infile_1, infile_2]]},
			'c': {'type': 'var', 'data': ['var_c']}
		}
		pIsTrulyCached4.props['output']  = {
			'a': ('file', TemplateLiquid('pIsTrulyCached4.txt')),
			'b': ('dir', TemplateLiquid('pIsTrulyCached4.dir'))
		}
		del pIsTrulyCached4.LOG_NLINE['CACHE_EMPTY_CURRSIG']
		del pIsTrulyCached4.LOG_NLINE['CACHE_SIGINVAR_DIFF']
		job4 = Job(0, pIsTrulyCached4)
		job4.init()
		ina = path.join(job4.indir, 'pIsTrulyCached4.txt')
		inb1 = path.join(job4.indir, 'pIsTrulyCached4_1.txt')
		inb2 = path.join(job4.indir, 'pIsTrulyCached4_2.txt')
		outa = path.join(job4.outdir, 'pIsTrulyCached4.txt')
		outb = path.join(job4.outdir, 'pIsTrulyCached4.dir')
		helpers.writeFile(outa)
		makedirs(outb)
		with helpers.log2str():
			job4.cache()
		job4.input['c'] = {'type': 'var', 'data': 'd'}
		yield job4, False, ['DEBUG', 'not cached because input variable(c) is different:', '- Previous: var_c', '- Current : d']
		
		# input file different
		infile = path.join(self.testdir, 'pIsTrulyCached5.txt')
		infile_1 = path.join(self.testdir, 'pIsTrulyCached5_1.txt')
		infile_2 = path.join(self.testdir, 'pIsTrulyCached5_2.txt')
		helpers.writeFile(infile)
		helpers.writeFile(infile_1)
		helpers.writeFile(infile_2)
		pIsTrulyCached5 = Proc()
		pIsTrulyCached5.props['workdir'] = path.join(self.testdir, 'pIsTrulyCached5', 'workdir')
		pIsTrulyCached5.props['script']  = TemplateLiquid('')
		pIsTrulyCached5.props['cache']   = True
		pIsTrulyCached5.props['size']    = 10
		pIsTrulyCached5.LOG_NLINE['CACHE_EMPTY_CURRSIG'] = -1
		pIsTrulyCached5.props['input']   = {
			'a': {'type': 'file', 'data': [infile]},
			'b': {'type': 'files', 'data': [[infile_1, infile_2]]},
			'c': {'type': 'var', 'data': ['var_c']}
		}
		pIsTrulyCached5.props['output']  = {
			'a': ('file', TemplateLiquid('pIsTrulyCached5.txt')),
			'b': ('dir', TemplateLiquid('pIsTrulyCached5.dir'))
		}
		del pIsTrulyCached5.LOG_NLINE['CACHE_EMPTY_CURRSIG']
		del pIsTrulyCached5.LOG_NLINE['CACHE_SIGINFILE_DIFF']
		job5 = Job(0, pIsTrulyCached5)
		job5.init()
		ina = path.join(job5.indir, 'pIsTrulyCached5.txt')
		inb1 = path.join(job5.indir, 'pIsTrulyCached5_1.txt')
		inb2 = path.join(job5.indir, 'pIsTrulyCached5_2.txt')
		outa = path.join(job5.outdir, 'pIsTrulyCached5.txt')
		outb = path.join(job5.outdir, 'pIsTrulyCached5.dir')
		helpers.writeFile(outa)
		makedirs(outb)
		with helpers.log2str():
			job5.cache()
		job5.input['a'] = {'type': 'file', 'data': infile_1}
		yield job5, False, ['DEBUG', 'not cached because input file(a) is different:']
		
		# input file newer
		infile = path.join(self.testdir, 'pIsTrulyCached6.txt')
		infile_1 = path.join(self.testdir, 'pIsTrulyCached6_1.txt')
		infile_2 = path.join(self.testdir, 'pIsTrulyCached6_2.txt')
		helpers.writeFile(infile)
		helpers.writeFile(infile_1)
		helpers.writeFile(infile_2)
		pIsTrulyCached6 = Proc()
		pIsTrulyCached6.props['workdir'] = path.join(self.testdir, 'pIsTrulyCached6', 'workdir')
		pIsTrulyCached6.props['script']  = TemplateLiquid('')
		pIsTrulyCached6.props['cache']   = True
		pIsTrulyCached6.props['size']    = 10
		pIsTrulyCached6.LOG_NLINE['CACHE_EMPTY_CURRSIG'] = -1
		pIsTrulyCached6.props['input']   = {
			'a': {'type': 'file', 'data': [infile]},
			'b': {'type': 'files', 'data': [[infile_1, infile_2]]},
			'c': {'type': 'var', 'data': ['var_c']}
		}
		pIsTrulyCached6.props['output']  = {
			'a': ('file', TemplateLiquid('pIsTrulyCached6.txt')),
			'b': ('dir', TemplateLiquid('pIsTrulyCached6.dir'))
		}
		del pIsTrulyCached6.LOG_NLINE['CACHE_EMPTY_CURRSIG']
		del pIsTrulyCached6.LOG_NLINE['CACHE_SIGINFILE_NEWER']
		job6 = Job(0, pIsTrulyCached6)
		job6.init()
		ina = path.join(job6.indir, 'pIsTrulyCached6.txt')
		inb1 = path.join(job6.indir, 'pIsTrulyCached6_1.txt')
		inb2 = path.join(job6.indir, 'pIsTrulyCached6_2.txt')
		outa = path.join(job6.outdir, 'pIsTrulyCached6.txt')
		outb = path.join(job6.outdir, 'pIsTrulyCached6.dir')
		helpers.writeFile(outa)
		makedirs(outb)
		with helpers.log2str():
			job6.cache()
		utime(infile, (time() + 1, time() + 1))
		yield job6, False, ['DEBUG', 'not cached because input file(a) is newer:']
		
		# input files diff
		infile = path.join(self.testdir, 'pIsTrulyCached7.txt')
		infile_1 = path.join(self.testdir, 'pIsTrulyCached7_1.txt')
		infile_2 = path.join(self.testdir, 'pIsTrulyCached7_2.txt')
		helpers.writeFile(infile)
		helpers.writeFile(infile_1)
		helpers.writeFile(infile_2)
		pIsTrulyCached7 = Proc()
		pIsTrulyCached7.props['workdir'] = path.join(self.testdir, 'pIsTrulyCached7', 'workdir')
		pIsTrulyCached7.props['script']  = TemplateLiquid('')
		pIsTrulyCached7.props['cache']   = True
		pIsTrulyCached7.props['size']    = 10
		pIsTrulyCached7.LOG_NLINE['CACHE_EMPTY_CURRSIG'] = -1
		pIsTrulyCached7.props['input']   = {
			'a': {'type': 'file', 'data': [infile]},
			'b': {'type': 'files', 'data': [[infile_1, infile_2]]},
			'c': {'type': 'var', 'data': ['var_c']}
		}
		pIsTrulyCached7.props['output']  = {
			'a': ('file', TemplateLiquid('pIsTrulyCached7.txt')),
			'b': ('dir', TemplateLiquid('pIsTrulyCached7.dir'))
		}
		del pIsTrulyCached7.LOG_NLINE['CACHE_EMPTY_CURRSIG']
		del pIsTrulyCached7.LOG_NLINE['CACHE_SIGINFILES_DIFF']
		job7 = Job(0, pIsTrulyCached7)
		job7.init()
		ina = path.join(job7.indir, 'pIsTrulyCached7.txt')
		inb1 = path.join(job7.indir, 'pIsTrulyCached7_1.txt')
		inb2 = path.join(job7.indir, 'pIsTrulyCached7_2.txt')
		outa = path.join(job7.outdir, 'pIsTrulyCached7.txt')
		outb = path.join(job7.outdir, 'pIsTrulyCached7.dir')
		helpers.writeFile(outa)
		makedirs(outb)
		with helpers.log2str():
			job7.cache()
		job7.input['b']['data'].append(infile_2)
		yield job7, False, ['DEBUG', 'not cached because file 3 is different for input files(b):']
		
		# input files diff 2
		infile = path.join(self.testdir, 'pIsTrulyCached71.txt')
		infile_1 = path.join(self.testdir, 'pIsTrulyCached71_1.txt')
		infile_2 = path.join(self.testdir, 'pIsTrulyCached71_2.txt')
		helpers.writeFile(infile)
		helpers.writeFile(infile_1)
		helpers.writeFile(infile_2)
		pIsTrulyCached71 = Proc()
		pIsTrulyCached71.props['workdir'] = path.join(self.testdir, 'pIsTrulyCached71', 'workdir')
		pIsTrulyCached71.props['script']  = TemplateLiquid('')
		pIsTrulyCached71.props['cache']   = True
		pIsTrulyCached71.props['size']    = 10
		pIsTrulyCached71.props['input']   = {
			'a': {'type': 'file', 'data': [infile]},
			'b': {'type': 'files', 'data': [[infile_1, infile_2]]},
			'c': {'type': 'var', 'data': ['var_c']}
		}
		pIsTrulyCached71.props['output']  = {
			'a': ('file', TemplateLiquid('pIsTrulyCached71.txt')),
			'b': ('dir', TemplateLiquid('pIsTrulyCached71.dir'))
		}
		job71 = Job(0, pIsTrulyCached71)
		job71.init()
		ina = path.join(job71.indir, 'pIsTrulyCached71.txt')
		inb1 = path.join(job71.indir, 'pIsTrulyCached71.txt')
		inb2 = path.join(job71.indir, 'pIsTrulyCached71.txt')
		outa = path.join(job71.outdir, 'pIsTrulyCached71.txt')
		outb = path.join(job71.outdir, 'pIsTrulyCached71.dir')
		helpers.writeFile(outa)
		makedirs(outb)
		with helpers.log2str():
			job71.cache()
		del job71.input['b']['data'][1]
		yield job71, False, ['DEBUG', 'not cached because file 2 is different for input files(b):']
		
		# input files newer
		infile = path.join(self.testdir, 'pIsTrulyCached8.txt')
		infile_1 = path.join(self.testdir, 'pIsTrulyCached8_1.txt')
		infile_2 = path.join(self.testdir, 'pIsTrulyCached8_2.txt')
		helpers.writeFile(infile)
		helpers.writeFile(infile_1)
		helpers.writeFile(infile_2)
		pIsTrulyCached8 = Proc()
		pIsTrulyCached8.props['workdir'] = path.join(self.testdir, 'pIsTrulyCached8', 'workdir')
		pIsTrulyCached8.props['script']  = TemplateLiquid('')
		pIsTrulyCached8.props['cache']   = True
		pIsTrulyCached8.props['size']    = 10
		pIsTrulyCached8.LOG_NLINE['CACHE_EMPTY_CURRSIG'] = -1
		pIsTrulyCached8.props['input']   = {
			'a': {'type': 'file', 'data': [infile]},
			'b': {'type': 'files', 'data': [[infile_1, infile_2]]},
			'c': {'type': 'var', 'data': ['var_c']}
		}
		pIsTrulyCached8.props['output']  = {
			'a': ('file', TemplateLiquid('pIsTrulyCached8.txt')),
			'b': ('dir', TemplateLiquid('pIsTrulyCached8.dir'))
		}
		del pIsTrulyCached8.LOG_NLINE['CACHE_EMPTY_CURRSIG']
		del pIsTrulyCached8.LOG_NLINE['CACHE_SIGINFILES_NEWER']
		job8 = Job(0, pIsTrulyCached8)
		job8.init()
		ina = path.join(job8.indir, 'pIsTrulyCached8.txt')
		inb1 = path.join(job8.indir, 'pIsTrulyCached8_1.txt')
		inb2 = path.join(job8.indir, 'pIsTrulyCached8_2.txt')
		outa = path.join(job8.outdir, 'pIsTrulyCached8.txt')
		outb = path.join(job8.outdir, 'pIsTrulyCached8.dir')
		helpers.writeFile(outa)
		makedirs(outb)
		with helpers.log2str():
			job8.cache()
		utime(job8.input['b']['data'][0], (time() + 1, time() + 1))
		yield job8, False, ['DEBUG', 'not cached because file 1 is newer for input files(b):']
		
		# out var diff
		infile = path.join(self.testdir, 'pIsTrulyCached9.txt')
		infile_1 = path.join(self.testdir, 'pIsTrulyCached9_1.txt')
		infile_2 = path.join(self.testdir, 'pIsTrulyCached9_2.txt')
		helpers.writeFile(infile)
		helpers.writeFile(infile_1)
		helpers.writeFile(infile_2)
		pIsTrulyCached9 = Proc()
		pIsTrulyCached9.props['workdir'] = path.join(self.testdir, 'pIsTrulyCached9', 'workdir')
		pIsTrulyCached9.props['script']  = TemplateLiquid('')
		pIsTrulyCached9.props['cache']   = True
		pIsTrulyCached9.props['size']    = 10
		pIsTrulyCached9.LOG_NLINE['CACHE_EMPTY_CURRSIG'] = -1
		pIsTrulyCached9.props['input']   = {
			'a': {'type': 'file', 'data': [infile]},
			'b': {'type': 'files', 'data': [[infile_1, infile_2]]},
			'c': {'type': 'var', 'data': ['var_c']}
		}
		pIsTrulyCached9.props['output']  = {
			'a': ('file', TemplateLiquid('pIsTrulyCached9.txt')),
			'b': ('dir', TemplateLiquid('pIsTrulyCached9.dir')),
			'c': ('var', TemplateLiquid('hello_c')),
		}
		del pIsTrulyCached9.LOG_NLINE['CACHE_EMPTY_CURRSIG']
		del pIsTrulyCached9.LOG_NLINE['CACHE_SIGOUTVAR_DIFF']
		job9 = Job(0, pIsTrulyCached9)
		job9.init()
		ina = path.join(job9.indir, 'pIsTrulyCached9.txt')
		inb1 = path.join(job9.indir, 'pIsTrulyCached9_1.txt')
		inb2 = path.join(job9.indir, 'pIsTrulyCached9_2.txt')
		outa = path.join(job9.outdir, 'pIsTrulyCached9.txt')
		outb = path.join(job9.outdir, 'pIsTrulyCached9.dir')
		helpers.writeFile(outa)
		makedirs(outb)
		with helpers.log2str():
			job9.cache()
		job9.output['c']['data'] = 'new_c'
		yield job9, False, ['DEBUG', 'not cached because output variable(c) is different:']
		
		# out file diff
		infile = path.join(self.testdir, 'pIsTrulyCached10.txt')
		infile_1 = path.join(self.testdir, 'pIsTrulyCached10_1.txt')
		infile_2 = path.join(self.testdir, 'pIsTrulyCached10_2.txt')
		helpers.writeFile(infile)
		helpers.writeFile(infile_1)
		helpers.writeFile(infile_2)
		pIsTrulyCached10 = Proc()
		pIsTrulyCached10.props['workdir'] = path.join(self.testdir, 'pIsTrulyCached10', 'workdir')
		pIsTrulyCached10.props['script']  = TemplateLiquid('')
		pIsTrulyCached10.props['cache']   = True
		pIsTrulyCached10.props['size']    = 10
		pIsTrulyCached10.props['input']   = {
			'a': {'type': 'file', 'data': [infile]},
			'b': {'type': 'files', 'data': [[infile_1, infile_2]]},
			'c': {'type': 'var', 'data': ['var_c']}
		}
		pIsTrulyCached10.props['output']  = {
			'a': ('file', TemplateLiquid('pIsTrulyCached10.txt')),
			'b': ('dir', TemplateLiquid('pIsTrulyCached10.dir')),
			'c': ('var', TemplateLiquid('hello_c')),
		}
		del pIsTrulyCached10.LOG_NLINE['CACHE_SIGOUTFILE_DIFF']
		job10 = Job(0, pIsTrulyCached10)
		job10.init()
		ina = path.join(job10.indir, 'pIsTrulyCached10.txt')
		inb1 = path.join(job10.indir, 'pIsTrulyCached10_1.txt')
		inb2 = path.join(job10.indir, 'pIsTrulyCached10_2.txt')
		outa = path.join(job10.outdir, 'pIsTrulyCached10.txt')
		outb = path.join(job10.outdir, 'pIsTrulyCached10.dir')
		helpers.writeFile(outa)
		makedirs(outb)
		with helpers.log2str():
			job10.cache()
		job10.output['a']['data'] = infile
		yield job10, False, ['DEBUG', 'not cached because output file(a) is different:']
		
		# out dir diff
		infile = path.join(self.testdir, 'pIsTrulyCached11.txt')
		infile_1 = path.join(self.testdir, 'pIsTrulyCached11_1.txt')
		infile_2 = path.join(self.testdir, 'pIsTrulyCached11_2.txt')
		helpers.writeFile(infile)
		helpers.writeFile(infile_1)
		helpers.writeFile(infile_2)
		pIsTrulyCached11 = Proc()
		pIsTrulyCached11.props['workdir'] = path.join(self.testdir, 'pIsTrulyCached11', 'workdir')
		pIsTrulyCached11.props['script']  = TemplateLiquid('')
		pIsTrulyCached11.props['cache']   = True
		pIsTrulyCached11.props['size']    = 10
		pIsTrulyCached11.props['input']   = {
			'a': {'type': 'file', 'data': [infile]},
			'b': {'type': 'files', 'data': [[infile_1, infile_2]]},
			'c': {'type': 'var', 'data': ['var_c']}
		}
		pIsTrulyCached11.props['output']  = {
			'a': ('file', TemplateLiquid('pIsTrulyCached11.txt')),
			'b': ('dir', TemplateLiquid('pIsTrulyCached11.dir')),
			'c': ('var', TemplateLiquid('hello_c')),
		}
		del pIsTrulyCached11.LOG_NLINE['CACHE_SIGOUTDIR_DIFF']
		job11 = Job(0, pIsTrulyCached11)
		job11.init()
		ina = path.join(job11.indir, 'pIsTrulyCached11.txt')
		inb1 = path.join(job11.indir, 'pIsTrulyCached11_1.txt')
		inb2 = path.join(job11.indir, 'pIsTrulyCached11_2.txt')
		outa = path.join(job11.outdir, 'pIsTrulyCached11.txt')
		outb = path.join(job11.outdir, 'pIsTrulyCached11.dir')
		helpers.writeFile(outa)
		makedirs(outb)
		with helpers.log2str():
			job11.cache()
		job11.output['b']['data'] = infile
		yield job11, False, ['DEBUG', 'not cached because output dir file(b) is different:']
		
		# True
		infile = path.join(self.testdir, 'pIsTrulyCached12.txt')
		infile_1 = path.join(self.testdir, 'pIsTrulyCached12_1.txt')
		infile_2 = path.join(self.testdir, 'pIsTrulyCached12_2.txt')
		helpers.writeFile(infile)
		helpers.writeFile(infile_1)
		helpers.writeFile(infile_2)
		pIsTrulyCached12 = Proc()
		pIsTrulyCached12.props['workdir'] = path.join(self.testdir, 'pIsTrulyCached12', 'workdir')
		pIsTrulyCached12.props['script']  = TemplateLiquid('')
		pIsTrulyCached12.props['cache']   = True
		pIsTrulyCached12.props['size']    = 10
		pIsTrulyCached12.props['input']   = {
			'a': {'type': 'file', 'data': [infile]},
			'b': {'type': 'files', 'data': [[infile_1, infile_2]]},
			'c': {'type': 'var', 'data': ['var_c']}
		}
		pIsTrulyCached12.props['output']  = {
			'a': ('file', TemplateLiquid('pIsTrulyCached12.txt')),
			'b': ('dir', TemplateLiquid('pIsTrulyCached12.dir')),
			'c': ('var', TemplateLiquid('hello_c')),
		}
		job12 = Job(0, pIsTrulyCached12)
		job12.init()
		ina = path.join(job12.indir, 'pIsTrulyCached12.txt')
		inb1 = path.join(job12.indir, 'pIsTrulyCached12_1.txt')
		inb2 = path.join(job12.indir, 'pIsTrulyCached12_2.txt')
		outa = path.join(job12.outdir, 'pIsTrulyCached12.txt')
		outb = path.join(job12.outdir, 'pIsTrulyCached12.dir')
		helpers.writeFile(outa)
		makedirs(outb)
		with helpers.log2str():
			job12.cache()
		yield job12, True
		
	def testIsTrulyCached(self, job, ret, errs = []):
		#helpers.log2sys(levels = 'all')
		with helpers.log2str(levels = 'all') as (out, err):
			r = job.isTrulyCached()
		self.assertEqual(r, ret)
		if r: self.assertEqual(job.rc(), 0)
		stderr = err.getvalue()
		for err in errs:
			self.assertIn(err, stderr)
	
	def dataProvider_testIsExptCached(self):
		pIsExptCached = Proc()
		pIsExptCached.props['workdir'] = path.join(self.testdir, 'pIsExptCached', 'workdir')
		pIsExptCached.props['cache']   = True
		job = Job(0, pIsExptCached)
		yield job, False
		
		pIsExptCached1 = Proc()
		pIsExptCached1.props['workdir'] = path.join(self.testdir, 'pIsExptCached1', 'workdir')
		pIsExptCached1.props['cache']   = 'export'
		pIsExptCached1.props['exhow']   = 'link'
		pIsExptCached1.__dict__['LOG_NLINE'] = {}
		job1 = Job(0, pIsExptCached1)
		yield job1, False, ['WARNING', 'Job is not export-cached using symlink export.']
		
		pIsExptCached2 = Proc()
		pIsExptCached2.props['workdir'] = path.join(self.testdir, 'pIsExptCached2', 'workdir')
		pIsExptCached2.props['cache']   = 'export'
		pIsExptCached2.props['expart']   = [TemplateLiquid('link')]
		job2 = Job(0, pIsExptCached2)
		yield job2, False, ['WARNING', 'Job is not export-cached using partial export.']
		
		pIsExptCached3 = Proc()
		pIsExptCached3.props['workdir'] = path.join(self.testdir, 'pIsExptCached3', 'workdir')
		pIsExptCached3.props['cache'] = 'export'
		job3 = Job(0, pIsExptCached3)
		yield job3, False, ['DEBUG', 'Job is not export-cached since export directory is not set.']
		
		# tgz, but file not exists
		pIsExptCached4 = Proc()
		pIsExptCached4.props['workdir'] = path.join(self.testdir, 'pIsExptCached4', 'workdir')
		pIsExptCached4.props['cache'] = 'export'
		pIsExptCached4.props['exhow'] = 'gz'
		pIsExptCached4.props['exdir'] = path.join(self.testdir, 'exdir')
		pIsExptCached4.props['script'] = TemplateLiquid('')
		pIsExptCached4.props['output']  = {
			'b': ('dir', TemplateLiquid('pIsExptCached4.dir')),
		}
		
		job4 = Job(0, pIsExptCached4)
		job4.init()
		# generate output files
		outb = path.join(job4.outdir, 'pIsExptCached4.dir')
		outbfile = path.join(outb, 'pIsExptCached4.txt')
		makedirs(outb)
		helpers.writeFile(outbfile, 'pIsExptCached4')
		# file not exists
		#job4.export()
		yield job4, False, ['DEBUG', 'Job is not export-cached since exported file not exists: ']
		
		# tgz
		pIsExptCached5 = Proc()
		pIsExptCached5.props['workdir'] = path.join(self.testdir, 'pIsExptCached5', 'workdir')
		pIsExptCached5.props['cache'] = 'export'
		pIsExptCached5.props['exhow'] = 'gz'
		pIsExptCached5.props['exdir'] = path.join(self.testdir, 'exdir')
		pIsExptCached5.props['script'] = TemplateLiquid('')
		pIsExptCached5.__dict__['LOG_NLINE'] = {}
		pIsExptCached5.props['output']  = {
			'b': ('dir', TemplateLiquid('pIsExptCached5.dir')),
		}		
		job5 = Job(0, pIsExptCached5)
		job5.init()
		# generate output files
		outb = path.join(job5.outdir, 'pIsExptCached5.dir')
		outbfile = path.join(outb, 'pIsExptCached5.txt')
		makedirs(outb)
		helpers.writeFile(outbfile, 'pIsExptCached5')
		if not path.exists(path.join(self.testdir, 'exdir')):
			makedirs(path.join(self.testdir, 'exdir'))
		with helpers.log2str():
			job5.export()
		yield job5, True
		
		# gz: file not exists
		pIsExptCached6 = Proc()
		pIsExptCached6.props['workdir'] = path.join(self.testdir, 'pIsExptCached6', 'workdir')
		pIsExptCached6.props['cache'] = 'export'
		pIsExptCached6.props['exhow'] = 'gz'
		pIsExptCached6.props['exdir'] = path.join(self.testdir, 'exdir')
		pIsExptCached6.props['script'] = TemplateLiquid('')
		pIsExptCached6.__dict__['LOG_NLINE'] = {}
		pIsExptCached6.props['output']  = {
			'a': ('file', TemplateLiquid('pIsExptCached6.txt')),
		}		
		job6 = Job(0, pIsExptCached6)
		job6.init()
		# generate output files
		outb = path.join(job6.outdir, 'pIsExptCached6.dir')
		outbfile = path.join(outb, 'pIsExptCached6.txt')
		makedirs(outb)
		helpers.writeFile(outbfile, 'pIsExptCached6')
		yield job6, False, ['DEBUG', 'Job is not export-cached since exported file not exists: ']
		
		# gz
		pIsExptCached7 = Proc()
		pIsExptCached7.props['workdir'] = path.join(self.testdir, 'pIsExptCached7', 'workdir')
		pIsExptCached7.props['cache'] = 'export'
		pIsExptCached7.props['exhow'] = 'gz'
		pIsExptCached7.props['exdir'] = path.join(self.testdir, 'exdir')
		pIsExptCached7.props['script'] = TemplateLiquid('')
		pIsExptCached7.__dict__['LOG_NLINE'] = {}
		pIsExptCached7.props['output']  = {
			'a': ('file', TemplateLiquid('pIsExptCached7.txt')),
		}		
		job7 = Job(0, pIsExptCached7)
		job7.init()
		# generate output files
		outa = path.join(job7.outdir, 'pIsExptCached7.txt')
		helpers.writeFile(outa)
		job7.export()
		yield job7, True
		
		# other: file not exist
		pIsExptCached8 = Proc()
		pIsExptCached8.props['workdir'] = path.join(self.testdir, 'pIsExptCached8', 'workdir')
		pIsExptCached8.props['cache'] = 'export'
		pIsExptCached8.props['exhow'] = 'copy'
		pIsExptCached8.props['exdir'] = path.join(self.testdir, 'exdir')
		pIsExptCached8.props['script'] = TemplateLiquid('')
		pIsExptCached8.__dict__['LOG_NLINE'] = {}
		pIsExptCached8.props['output']  = {
			'a': ('file', TemplateLiquid('pIsExptCached8.txt')),
		}		
		job8 = Job(0, pIsExptCached8)
		job8.init()
		# generate output files
		outa = path.join(job8.outdir, 'pIsExptCached8.txt')
		helpers.writeFile(outa)
		yield job8, False, ['DEBUG', 'Job is not export-cached since exported file not exists: ']
		
		# other: same file
		pIsExptCached9 = Proc()
		pIsExptCached9.props['workdir'] = path.join(self.testdir, 'pIsExptCached9', 'workdir')
		pIsExptCached9.props['cache'] = 'export'
		pIsExptCached9.props['exhow'] = 'copy'
		pIsExptCached9.props['exdir'] = path.join(self.testdir, 'exdir')
		pIsExptCached9.props['script'] = TemplateLiquid('')
		pIsExptCached9.__dict__['LOG_NLINE'] = {}
		pIsExptCached9.props['output']  = {
			'a': ('file', TemplateLiquid('pIsExptCached9.txt')),
		}		
		job9 = Job(0, pIsExptCached9)
		job9.init()
		# generate output files
		outa = path.join(job9.outdir, 'pIsExptCached9.txt')
		helpers.writeFile(outa)
		symlink(outa, path.join(self.testdir, 'exdir', 'pIsExptCached9.txt'))
		yield job9, True
		
		# other: overwrite
		pIsExptCached10 = Proc()
		pIsExptCached10.props['workdir'] = path.join(self.testdir, 'pIsExptCached10', 'workdir')
		pIsExptCached10.props['cache'] = 'export'
		pIsExptCached10.props['exhow'] = 'copy'
		pIsExptCached10.props['exdir'] = path.join(self.testdir, 'exdir')
		pIsExptCached10.props['script'] = TemplateLiquid('')
		del pIsExptCached10.LOG_NLINE['EXPORT_CACHE_OUTFILE_EXISTS']
		pIsExptCached10.props['output']  = {
			'a': ('file', TemplateLiquid('pIsExptCached10.txt')),
		}		
		job10 = Job(0, pIsExptCached10)
		job10.init()
		# generate output files
		outa = path.join(job10.outdir, 'pIsExptCached10.txt')
		helpers.writeFile(outa)
		job10.export()
		yield job10, True, ['WARNING', 'Overwrite file for export-caching: ']
			
	def testIsExptCached(self, job, ret, errs = []):
		with helpers.log2str(levels = 'all') as (out, err):
			r = job.isExptCached()
		stderr = err.getvalue()
		self.assertEqual(r, ret)
		for err in errs:
			self.assertIn(err, stderr)
		if ret:
			self.assertEqual(job.rc(), 0)
			self.assertTrue(job.isTrulyCached())
			
	def dataProvider_testDone(self):
		# other: overwrite
		pDone = Proc()
		pDone.props['workdir'] = path.join(self.testdir, 'pDone', 'workdir')
		pDone.props['script']  = TemplateLiquid('')
		pDone.props['expect']  = TemplateLiquid('')
		pDone.props['output']  = {
			'a': ('file', TemplateLiquid('pDone.txt')),
		}		
		job = Job(0, pDone)
		job.init()
		# generate output files
		outa = path.join(job.outdir, 'pDone.txt')
		helpers.writeFile(outa)
		helpers.writeFile(job.rcfile, 0)
		yield job,
			
	def testDone(self, job):
		with helpers.log2str():
			job.done()
		self.assertEqual(job.rc(), 0)


if __name__ == '__main__':
	testly.main(verbosity=2)