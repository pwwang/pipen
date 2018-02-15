import helpers, unittest

from os import path, symlink, makedirs
from shutil import rmtree
from copy import deepcopy
from pyppl.job import JobMan, Job
from pyppl.exception import JobInputParseError, JobBringParseError, TemplatePyPPLRenderError, JobOutputParseError
from pyppl.templates import TemplatePyPPL
from pyppl import Proc, logger

class TestJob(helpers.TestCase):

	def file2indir(workdir, index, f, suffix = ''):
		(prefix, _, ext) = path.basename(f).rpartition('.')
		return path.join(workdir, str(index), 'input', prefix + suffix + '.' + ext)

	def dataProvider_testInit0(self, testdir):
		p = Proc()
		p.props['workdir'] = path.join(testdir, 'workdir')
		yield 0, p
		yield 1, p

	def testInit0(self, index, proc):
		job  = Job(index, proc)
		self.assertIsInstance(job, Job)
		self.assertIsInstance(job.proc, Proc)
		self.assertEqual(job.dir, path.join(proc.workdir, str(index)))
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
		self.assertEqual(job.brings, {})
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
			'in'   : {},
			'out'  : {},
			'bring': {}
		})

	def dataProvider_testPrepInput(self, testdir):
		p = Proc()
		# make sure the infile renaming log output
		p.LOG_NLINE['INFILE_RENAMING'] = -1
		p.props['workdir'] = path.join(testdir, 'workdir')
		filec0 = path.join(testdir, 'filec0.txt')
		filec1 = path.join(testdir, 'filec1.txt')
		filec2 = path.join(testdir, 'filec2.txt')
		filed0 = path.join(testdir, 'filed0.txt')
		filed1 = path.join(testdir, 'filed1.txt')
		filed2 = path.join(testdir, 'filed2.txt')
		filed3 = path.join(testdir, 'filed3.txt')
		filed4 = path.join(testdir, 'filed4.txt')
		filed20 = path.join(testdir, 'filed20.txt')
		filed21 = path.join(testdir, 'filed21.txt')
		filed22 = path.join(testdir, 'filed22.txt')
		filed23 = path.join(testdir, 'filed23.txt')
		filed24 = path.join(testdir, 'filed24.txt')
		filed30 = path.join(testdir, 'filed30.txt')
		filed31 = path.join(testdir, 'filed31.txt')
		filed32 = path.join(testdir, 'filed32.txt')
		filed33 = path.join(testdir, 'filed33.txt')
		filed34 = path.join(testdir, 'filed34.txt')
		filed35 = path.join(testdir, 'filed35', 'filec2.txt')
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
				[filed24],
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

		yield 0, p, {
			'a': {'type': 'var', 'data': 1},
			'b': {'type': 'var', 'data': 'a'},
			'c': {'type': 'file', 'orig':'', 'data': ''},
			'd': {'type': 'files', 'orig':[filed0, filed1], 'data': [
				self.file2indir(p.workdir, 0, filed0), 
				self.file2indir(p.workdir, 0, filed1)
			]},
			'd2': {'type': 'files', 'orig': [filed20], 'data': [
				self.file2indir(p.workdir, 0, filed20)
			]},
			'd3': {'type': 'files', 'orig': [filed30, filed31], 'data': [
				self.file2indir(p.workdir, 0, filed30),
				self.file2indir(p.workdir, 0, filed31)
			]}, 
		}, {
			'a': 1,
			'b': 'a',
			'c': '',
			'_c': '',
			'd': [
				self.file2indir(p.workdir, 0, filed0), 
				self.file2indir(p.workdir, 0, filed1)
			],
			'_d': [filed0, filed1],
			'd2': [
				self.file2indir(p.workdir, 0, filed20)
			],
			'_d2': [filed20],
			'd3': [
				self.file2indir(p.workdir, 0, filed30),
				self.file2indir(p.workdir, 0, filed31)
			], 
			'_d3': [filed30, filed31], 
		}

		yield 1, p, {}, {}, JobInputParseError, 'File not exists for input type'
		yield 2, p, {}, {}, JobInputParseError, 'Not a string for input type'
		yield 3, p, {}, {}, JobInputParseError, 'Not a list for input type'
		yield 4, p, {}, {}, JobInputParseError, 'Not a string for element of input type'
		yield 5, p, {}, {}, JobInputParseError, 'File not exists for element of input type'
		yield 6, p, {
			'a': {'type': 'var', 'data': 7},
			'b': {'type': 'var', 'data': 'g'},
			'c': {'type': 'file', 'orig': filec2, 'data': self.file2indir(p.workdir, 6, filec2)},
			'd': {'type': 'files', 'orig':[filed4, filed4], 'data': [
				self.file2indir(p.workdir, 6, filed4), 
				self.file2indir(p.workdir, 6, filed4)
			]},
			'd2': {'type': 'files', 'orig': [filed24], 'data': [
				self.file2indir(p.workdir, 6, filed24)
			]},
			#                               not file34
			'd3': {'type': 'files', 'orig': [filed35], 'data': [
				self.file2indir(p.workdir, 6, filed35, '[1]')
			]}, 
		}, {
			'a': 7,
			'b': 'g',
			'c': self.file2indir(p.workdir, 6, filec2),
			'_c': filec2,
			'd': [
				self.file2indir(p.workdir, 6, filed4), 
				self.file2indir(p.workdir, 6, filed4)
			],
			'_d': [filed4, filed4],
			'd2': [
				self.file2indir(p.workdir, 6, filed24)
			],
			'_d2': [filed24],
			'd3': [
				self.file2indir(p.workdir, 6, filed35, '[1]')
			], 
			'_d3': [filed35], 
		}, None, None, 'p: Input file renamed: filec2.txt -> filec2[1].txt'

	def testPrepInput(self, index, proc, jobinput, indata, exception = None, msg = None, errmsg = None):
		self.maxDiff = None
		job = Job(index, proc)
		if path.isdir(job.indir):
			rmtree(job.indir)
		self.assertFalse(path.isdir(job.indir))
		if exception:
			self.assertRaisesStr(exception, msg, job._prepInput)
			self.assertTrue(path.isdir(job.indir))
		else:
			with helpers.log2str() as (out, err):
				job._prepInput()
			if errmsg:
				self.assertIn(errmsg, err.getvalue())
			self.assertTrue(path.isdir(job.indir))
			self.assertDictEqual(job.input, jobinput)
			self.assertDictEqual(job.data['in'], indata)

	def dataProvider_testPrepBrings(self, testdir):
		pPrepBrings1 = Proc()
		pPrepBrings1.props['workdir'] = path.join(testdir, 'pPrepBrings1', 'workdir')
		pPrepBrings1.props['input']   = {
			'a': {'type': 'var', 'data': [1]},
		}
		pPrepBrings1.props['brings']  = {'a': ''}
		yield 0, pPrepBrings1, {}, JobBringParseError, 'Cannot bring files for a non-file type input'

		pPrepBrings2 = Proc()
		pPrepBrings2.props['workdir'] = path.join(testdir, 'pPrepBrings1', 'workdir')
		filepbdir2 = path.join(testdir, 'testPrepBringDir2')
		makedirs(filepbdir2)
		filepb20 = path.join(filepbdir2, 'testPrepBring2.br')
		filepb21 = path.join(filepbdir2, 'whatever2.txt')
		filepb22 = path.join(testdir, 'testPrepBring2.txt')
		symlink(filepb21, filepb22)
		helpers.writeFile(filepb21)
		pPrepBrings2.props['input']   = {
			'a': {'type': 'file', 'data': [filepb22]},
		}
		pPrepBrings2.props['brings']  = {'a': TemplatePyPPL('{{x}}.br')}
		yield 0, pPrepBrings2, {}, TemplatePyPPLRenderError, 'unknown template variable: "x"'

		pPrepBrings3 = Proc()
		pPrepBrings3.props['workdir'] = path.join(testdir, 'pPrepBrings1', 'workdir')
		filepbdir3 = path.join(testdir, 'testPrepBringDir3')
		makedirs(filepbdir3)
		filepb30 = path.join(filepbdir3, 'testPrepBring3.br')
		filepb31 = path.join(filepbdir3, 'whatever3.txt')
		filepb32 = path.join(testdir, 'testPrepBring3.txt')
		helpers.writeFile(filepb31)
		symlink(filepb31, filepb32)
		helpers.writeFile(filepb30)
		pPrepBrings3.props['input']   = {
			'a': {'type': 'file', 'data': [filepb32]},
		}
		pPrepBrings3.props['brings']  = {'a': TemplatePyPPL('{{in.a | fn}}.br')}
		yield 0, pPrepBrings3, {
			'a': [self.file2indir(pPrepBrings3.workdir, 0, filepb30)],
			'_a': [filepb30],
		}

		# no bring-in file
		pPrepBrings4 = Proc()
		pPrepBrings4.props['workdir'] = path.join(testdir, 'pPrepBrings1', 'workdir')
		pPrepBrings4.LOG_NLINE['BRINGFILE_NOTFOUND'] = -1
		filepbdir4 = path.join(testdir, 'testPrepBringDir4')
		makedirs(filepbdir4)
		filepb41 = path.join(filepbdir4, 'whatever4.txt')
		filepb42 = path.join(testdir, 'testPrepBring4.txt')
		helpers.writeFile(filepb41)
		symlink(filepb41, filepb42)
		pPrepBrings4.props['input']   = {
			'a': {'type': 'file', 'data': [filepb42]},
		}
		pPrepBrings4.props['brings']  = {'a': TemplatePyPPL('{{in.a | fn}}.br')}
		yield 0, pPrepBrings4, {'a': [''], '_a': ['']}, None, None, 'No bring-in file found'

		# input file renamed
		pPrepBrings5 = Proc()
		pPrepBrings5.props['workdir'] = path.join(testdir, 'pPrepBrings1', 'workdir')
		filepbdir5 = path.join(testdir, 'testPrepBringDir5')
		makedirs(filepbdir5)
		filepb50 = path.join(filepbdir5, 'testPrepBring5.br')
		filepb51 = path.join(filepbdir5, 'whatever5.txt')
		filepb52 = path.join(testdir, 'testPrepBring5.txt')
		filepb53 = path.join(filepbdir5, 'testPrepBring5.txt')
		helpers.writeFile(filepb51)
		helpers.writeFile(filepb53)
		symlink(filepb51, filepb52)
		helpers.writeFile(filepb50)
		pPrepBrings5.props['input']   = {
			'a': {'type': 'file', 'data': [filepb53]},
			'b': {'type': 'file', 'data': [filepb52]},
		}
		pPrepBrings5.props['brings']  = {'b': TemplatePyPPL('{{in.b | fn}}.br')}
		yield 0, pPrepBrings5, {
			'b': [self.file2indir(pPrepBrings3.workdir, 0, filepb50, '[1]')],
			'_b': [filepb50],
		}

	def testPrepBrings(self, index, proc, brdata, exception = None, msg = None, errmsg = None):
		self.maxDiff = None
		job = Job(index, proc)
		job._prepInput()
		if exception:
			self.assertRaisesStr(exception, msg, job._prepBrings)
		else:
			with helpers.log2str() as (out, err):
				job._prepBrings()
			if errmsg:
				self.assertIn(errmsg, err.getvalue())
			self.assertDictEqual(job.brings, brdata)
			self.assertDictEqual(job.data['bring'], brdata)

	def dataProvider_testPrepOutput(self, testdir):
		pPrepOutput = Proc()
		pPrepOutput.props['workdir'] = path.join(testdir, 'pPrepOutput', 'workdir')
		yield 0, pPrepOutput, {
			'a': {'type': 'var', 'data': [0]}
		}, '', {}, {}, AssertionError
		yield 0, pPrepOutput, {
			'a': {'type': 'var', 'data': [0]}
		}, {}, {}, {}
		yield 0, pPrepOutput, {
			'a': {'type': 'var', 'data': [0]}
		}, {'a': ('var', TemplatePyPPL('{{x}}'))}, {}, {}, TemplatePyPPLRenderError, 'unknown template variable'
		yield 0, pPrepOutput, {
			'a': {'type': 'var', 'data': [0]}
		}, {'a': ('var', TemplatePyPPL('1{{in.a}}'))}, {
			'a': {'type': 'var', 'data': '10'}
		}, {
			'a': '10'
		}
		yield 0, pPrepOutput, {
			'a': {'type': 'var', 'data': [0]}
		}, {'a': ('file', TemplatePyPPL('/a/b/1{{in.a}}'))}, {}, {}, JobOutputParseError, 'Absolute path not allowed for output file/dir'
		
	def testPrepOutput(self, index, proc, input, output, jobout, outdata, exception = None, msg = None):
		proc.props['input']  = input
		proc.props['output'] = output
		job = Job(index, proc)
		job._prepInput()
		if exception:
			self.assertRaisesStr(exception, msg, job._prepOutput)
		else:
			job._prepOutput()
			self.assertTrue(path.isdir(job.outdir))
			self.assertDictEqual(job.output, jobout)
			self.assertDictEqual(job.data['out'], outdata)

	def dataProvider_testPrepScript(self, testdir):
		pPrepScript = Proc()
		pPrepScript.LOG_NLINE['SCRIPT_EXISTS'] = -1
		pPrepScript.props['workdir'] = path.join(testdir, 'pPrepScript', 'workdir')
		yield 0, pPrepScript, {}, {}, TemplatePyPPL('{{x}}'), '', TemplatePyPPLRenderError, 'unknown template variable'
		sfile = path.join(pPrepScript.workdir, '0', 'job.script')
		makedirs(path.dirname(sfile))
		helpers.writeFile(sfile)
		yield 0, pPrepScript, {'x': {'type': 'var', 'data': [0]}}, {}, TemplatePyPPL('1{{in.x}}'), '10', None, None, 'Script file updated'

	def testPrepScript(self, index, proc, input, output, script, scriptout, exception = None, msg = None, errmsg = None):
		proc.props['input']  = input
		proc.props['output'] = output
		proc.props['script'] = script
		job = Job(index, proc)
		job._prepInput()
		job._prepOutput()
		if exception:
			self.assertRaisesStr(exception, msg, job._prepScript)
		else:
			with helpers.log2str(levels = 'all') as (out, err):
				job._prepScript()
			if errmsg:
				self.assertIn(errmsg, err.getvalue())
			self.assertTrue(path.isfile(job.script))
			self.assertInFile(scriptout, job.script)

	def dataProvider_testLinkInfile(self, testdir):
		file1 = path.join(testdir, 'testLinkInfile1.txt')
		helpers.writeFile(file1)
		yield testdir, [file1, file1], ['testLinkInfile1.txt', 'testLinkInfile1.txt']

		dir2 = path.join(testdir, 'testLinkInfileDir')
		makedirs(dir2)
		file2 = path.join(dir2, 'testLinkInfile1.txt')
		helpers.writeFile(file2)
		yield testdir, [file1, file2], ['testLinkInfile1.txt', 'testLinkInfile1[1].txt']
		yield testdir, [file1, file2, file2], ['testLinkInfile1.txt', 'testLinkInfile1[1].txt', 'testLinkInfile1[1].txt']

		dir3 = path.join(testdir, 'testLinkInfileDir3')
		makedirs(dir3)
		file3 = path.join(dir3, 'testLinkInfile1.txt')
		helpers.writeFile(file3)
		yield testdir, [file1, file2, file3], ['testLinkInfile1.txt', 'testLinkInfile1[1].txt', 'testLinkInfile1[2].txt']

	def testLinkInfile(self, testdir, orgfiles, inbns):
		pLinkInfile = Proc()
		pLinkInfile.props['workdir'] = path.join(testdir, 'pLinkInfile', 'workdir')
		job = Job(0, pLinkInfile)
		job._prepInput()
		for i, orgfile in enumerate(orgfiles):
			job._linkInfile(orgfile)
			self.assertTrue(path.samefile(orgfile, path.join(job.indir, inbns[i])))

	def dataProvider_testInit(self, testdir):
		pInit = Proc()
		pInit.props['workdir'] = path.join(testdir, 'pInit', 'workdir')
		pInit.props['script']  = TemplatePyPPL('')
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

'''


class TestJob (unittest.TestCase):

	def testInitSelf(self):
		proc = Proc()
		job  = Job(0, proc)
		scriptExists = path.exists(job.script)
		with captured_output() as (out, err):
			job.init()
		self.assertEqual(job.data['a'], 1)
		self.assertEqual(job.data['b'], 2)
		# input
		self.assertEqual(job.input, {
			'a': {
				'type': 'var',
				'data': 1,
			},
			'b': {
				'type': 'var',
				'data': 'a',
			},
			'c': {
				'type': 'file',
				'orig': path.realpath(__file__),
				'data': path.join(job.indir, path.basename(__file__)),
			},
			'd': {
				'type': 'files',
				'orig': [path.realpath(__file__)],
				'data': [path.join(job.indir, path.basename(__file__))],
			},
			'd2': {
				'type': 'files',
				'orig': [path.realpath(__file__)],
				'data': [path.join(job.indir, path.basename(__file__))],
			},
			'd3': {
				'type': 'files',
				'orig': [path.realpath(__file__)],
				'data': [path.join(job.indir, path.basename(__file__))],
			}
		})
		self.assertEqual(job.data['in'], {
			'a': 1,
			'b': 'a',
			'c': path.join(job.indir, path.basename(__file__)),
			'_c': path.realpath(__file__),
			'd': [path.join(job.indir, path.basename(__file__))],
			'_d': [path.realpath(__file__)],
			'd2': [path.join(job.indir, path.basename(__file__))],
			'_d2': [path.realpath(__file__)],
			'd3': [path.join(job.indir, path.basename(__file__))],
			'_d3': [path.realpath(__file__)],
		})
		# brings
		self.assertItemsEqual(job.data['bring']['_c'], list(map(path.abspath, glob(path.join(path.dirname(__file__), 'test*.py')))))
		self.assertItemsEqual(job.data['bring']['c'], list(map(lambda x: path.join(job.indir, path.basename(x)), glob(path.join(path.dirname(__file__), 'test*.py')))))
		self.assertItemsEqual(job.brings['_c'], list(map(path.abspath, glob(path.join(path.dirname(__file__), 'test*.py')))))
		self.assertItemsEqual(job.brings['c'], list(map(lambda x: path.join(job.indir, path.basename(x)), glob(path.join(path.dirname(__file__), 'test*.py')))))
		# output
		self.assertEqual(job.data['out'], {
			'a': '1_1',
			'b': path.join(job.outdir, path.basename(__file__)),
			'c': path.join(job.outdir, path.basename(__file__)[:-3]),
		})
		self.assertEqual(job.output['a']['type'], 'var')
		self.assertEqual(job.output['b']['type'], 'file')
		self.assertEqual(job.output['c']['type'], 'dir')
		self.assertEqual(job.output['a']['data'], '1_1')
		self.assertEqual(job.output['b']['data'], path.join(job.outdir, path.basename(__file__)))
		self.assertEqual(job.output['c']['data'], path.join(job.outdir, path.basename(__file__)[:-3]))
		#script
		if scriptExists:
			self.assertIn('Script file exists', err.getvalue())
		self.assertTrue(path.exists(job.script))
		with open(job.script) as f:
			self.assertEqual(f.read(), """
import os
print "1"
print "1_1"

print "a"

""")

	def testIsTrulyCached(self):
		proc = Proc()
		job  = Job(0, proc)
		utils.safeRemove(job.cachefile)
		# no cache file
		with captured_output() as (out, err):
			self.assertFalse(job.isTrulyCached())
		self.assertIn('not cached as cache file not exists', err.getvalue())

		# empty cache file
		open(job.cachefile, 'w').close()
		with captured_output() as (out, err):
			self.assertFalse(job.isTrulyCached())
		self.assertIn('not cached because previous signature is empty', err.getvalue())

		# do a normal cache first
		with captured_output() as (out, err):
			job.init()
		open(job.data['out']['b'], 'w').close()
		utils.safeRemove(job.data['out']['c'])
		makedirs(job.data['out']['c'])
		open(job.script, 'w').close()
		job.cache()
		
		# script file newer
		utime(job.script, (time() + 1, time() + 1))
		with captured_output() as (out, err):
			self.assertFalse(job.isTrulyCached())
		self.assertIn('not cached because script file newer', err.getvalue())
		job.cache()

		# input variable different
		job.input['a']['data'] = 3.14
		with captured_output() as (out, err):
			self.assertFalse(job.isTrulyCached())
		self.assertIn('not cached because input variable', err.getvalue())
		job.cache()

		# infile different
		job.input['c']['data'] = path.join(tmpdir, 'infile-different')
		open(job.input['c']['data'], 'w').close()
		with captured_output() as (out, err):
			self.assertFalse(job.isTrulyCached())
		self.assertIn('not cached because input file', err.getvalue())
		self.assertIn('is different', err.getvalue())
		job.cache()

		# infile newer
		utime(job.input['c']['data'] , (time() + 1, time() + 1))
		with captured_output() as (out, err):
			self.assertFalse(job.isTrulyCached())
		self.assertIn('not cached because input file', err.getvalue())
		self.assertIn('is newer', err.getvalue())
		job.cache()

		# infiles different
		job.input['d']['data'] = [path.join(tmpdir, 'infile-different2')]
		open(job.input['d']['data'][0], 'w').close()
		with captured_output() as (out, err):
			self.assertFalse(job.isTrulyCached())
		self.assertIn('not cached because input files', err.getvalue())
		self.assertIn('are different', err.getvalue())
		job.cache()

		# infiles newer
		utime(job.input['d']['data'][0] , (time() + 1, time() + 1))
		with captured_output() as (out, err):
			self.assertFalse(job.isTrulyCached())
		self.assertIn('not cached because one of input files', err.getvalue())
		self.assertIn('is newer', err.getvalue())
		job.cache()

		# outvar different
		job.output['a']['data'] = '1_2'
		with captured_output() as (out, err):
			self.assertFalse(job.isTrulyCached())
		self.assertIn('not cached because output variable', err.getvalue())
		job.cache()

		# outfile different
		job.output['b']['data'] = path.join(tmpdir, 'infile-different3')
		open(job.output['b']['data'], 'w').close()
		with captured_output() as (out, err):
			self.assertFalse(job.isTrulyCached())
		self.assertIn('not cached because output file', err.getvalue())
		self.assertIn('is different:', err.getvalue())
		job.cache()

		# outdir different
		job.output['c']['data'] = path.join(tmpdir, 'infile-different4')
		utils.safeRemove(job.output['c']['data'])
		makedirs(job.output['c']['data'])
		with captured_output() as (out, err):
			self.assertFalse(job.isTrulyCached())
		self.assertIn('not cached because output dir', err.getvalue())
		self.assertIn('is different:', err.getvalue())
		job.cache()

		self.assertTrue(job.isTrulyCached())

	def testIsExportCached(self):
		proc = Proc()
		job  = Job(0, proc)
		utils.safeRemove(job.dir)
		makedirs(job.dir)
		# cache != 'export'
		proc.cache = True
		self.assertFalse(job.isExptCached())
		# exhow == 'link'
		proc.cache = 'export'
		proc.exhow = 'link'
		with captured_output() as (out, err):
			self.assertFalse(job.isExptCached())
		self.assertIn('Job not export-cached using symlink export.', err.getvalue())
		# expart
		proc.exhow = 'move'
		proc.expart = [TemplatePyPPL('1')]
		with captured_output() as (out, err):
			self.assertFalse(job.isExptCached())
		self.assertIn('Job not export-cached using partial export.', err.getvalue())
		# exdir
		proc.expart = []
		proc.exdir  = ''
		with captured_output() as (out, err):
			self.assertFalse(job.isExptCached())
		self.assertIn('Job not export-cached since export directory is not set.', err.getvalue())
		# export: gz
		proc.exhow = 'gz'
		proc.exdir = path.join(tmpdir, 'testIsExportCached-exdir')
		utils.safeRemove(proc.exdir)
		makedirs(proc.exdir)
		with captured_output() as (out, err):
			job.init()
			open(job.data['out']['b'], 'w').close()
			utils.safeRemove(job.data['out']['c'])
			makedirs(job.data['out']['c'])
			open(job.script, 'w').close()
			job.export()
		excfile = path.join(proc.exdir, path.basename(job.data['out']['c']) + '.tgz')
		exbfile = path.join(proc.exdir, path.basename(job.data['out']['b']) + '.gz')
		self.assertPathExists(exbfile)
		self.assertPathExists(excfile)
		# tgz file not exists
		utils.safeMove(exbfile, exbfile + '2')
		with captured_output() as (out, err):
			self.assertFalse(job.isExptCached())
		self.assertIn('Job not export-cached since exported file not exists', err.getvalue())
		self.assertIn(exbfile, err.getvalue())
		utils.safeMove(exbfile + '2', exbfile)

		# gzfile not exists
		utils.safeMove(excfile, excfile + '2')
		with captured_output() as (out, err):
			self.assertFalse(job.isExptCached())
		self.assertIn('Job not export-cached since exported file not exists', err.getvalue())
		self.assertIn(excfile, err.getvalue())
		utils.safeMove(excfile + '2', excfile)

		# dir exists:
		# make sure not popup msg for b file
		utils.safeRemove(job.data['out']['b'])
		with captured_output() as (out, err):
			self.assertTrue(job.isExptCached())
		self.assertIn('Overwrite file for export-caching:', err.getvalue())
		self.assertIn(job.data['out']['c'], err.getvalue())

		open(job.data['out']['b'], 'w').close()
		utils.safeRemove(job.data['out']['c'])
		with captured_output() as (out, err):
			self.assertTrue(job.isExptCached())
		self.assertIn('Overwrite file for export-caching:', err.getvalue())
		self.assertIn(job.data['out']['b'], err.getvalue())
		
		# export: move
		proc.exhow = 'move'
		proc.exdir = path.join(tmpdir, 'testIsExportCached-exdir')
		utils.safeRemove(proc.exdir)
		makedirs(proc.exdir)
		with captured_output() as (out, err):
			job.init()
			open(job.data['out']['b'], 'w').close()
			utils.safeRemove(job.data['out']['c'])
			makedirs(job.data['out']['c'])
			open(job.script, 'w').close()
			job.export()
		excfile = path.join(proc.exdir, path.basename(job.data['out']['c']))
		exbfile = path.join(proc.exdir, path.basename(job.data['out']['b']))
		self.assertPathExists(exbfile)
		self.assertPathExists(excfile)

		utils.safeRemove(excfile)
		with captured_output() as (out, err):
			self.assertFalse(job.isExptCached())
		self.assertIn('Job not export-cached since exported file not exists', err.getvalue())
		self.assertIn(excfile, err.getvalue())
		makedirs(excfile)

		self.assertTrue(job.isExptCached())
		self.assertTrue(job.isTrulyCached())
		self.assertEqual(job.rc(), 0)

		# export: copy
		proc.exhow = 'copy'
		proc.exdir = path.join(tmpdir, 'testIsExportCached-exdir')
		utils.safeRemove(proc.exdir)
		makedirs(proc.exdir)
		utils.safeRemove(job.dir)
		makedirs(job.dir)
		with captured_output() as (out, err):
			job.init()
			open(job.data['out']['b'], 'w').close()
			utils.safeRemove(job.data['out']['c'])
			makedirs(job.data['out']['c'])
			open(job.script, 'w').close()
			job.export()
		excfile = path.join(proc.exdir, path.basename(job.data['out']['c']))
		exbfile = path.join(proc.exdir, path.basename(job.data['out']['b']))
		self.assertPathExists(exbfile)
		self.assertPathExists(excfile)

		utils.safeRemove(exbfile)
		with captured_output() as (out, err):
			self.assertFalse(job.isExptCached())
		self.assertIn('Job not export-cached since exported file not exists', err.getvalue())
		self.assertIn(exbfile, err.getvalue())
		open(exbfile, 'w').close()

		with captured_output() as (out, err):
			self.assertTrue(job.isExptCached())
		self.assertIn('Overwrite file for export-caching:', err.getvalue())
		self.assertIn(job.data['out']['c'], err.getvalue())
		self.assertIn(job.data['out']['b'], err.getvalue())

		self.assertTrue(job.isTrulyCached())
		self.assertEqual(job.rc(), 0)

	def testShowError(self):
		proc = Proc()
		job  = Job(0, proc)
		job.rc(1)
		proc.echo['jobs'] = []
		proc.errhow = 'terminate'

		utils.safeRemove(job.errfile)
		with captured_output() as (out, err):
			logger.getLogger()
			job.showError()
		self.assertIn('Return code: 1 (Script error).', err.getvalue())
		self.assertIn(job.script, err.getvalue())
		self.assertIn(job.outfile, err.getvalue())
		self.assertIn(job.errfile, err.getvalue())
		self.assertIn('check STDERR below', err.getvalue())
		self.assertIn('<EMPTY STDERR>', err.getvalue())

		with open(job.errfile, 'w') as ferr:
			ferr.write('Error1\nError2\nError3' + ('\nx'*23))
		with captured_output() as (out, err):
			logger.getLogger()
			job.showError()
		self.assertIn('check STDERR below', err.getvalue())
		self.assertIn('x', err.getvalue())
		self.assertIn('hidden', err.getvalue())

		with captured_output() as (out, err):
			logger.getLogger()
			proc.errhow = 'ignore'
			job.showError()
		self.assertIn('Job #0 (total 1) failed but ignored.', err.getvalue())

	def testDone(self):
		proc = Proc()
		proc.errhow = 'ignore'
		job  = Job(0, proc)
		with captured_output() as (out, err):
			job.init()
			with open(job.data['out']['b'], 'w') as fb:
				fb.write('a')
			utils.safeRemove(job.data['out']['c'])
			makedirs(job.data['out']['c'])
			open(job.script, 'w').close()
			job.rc(0)
			job.done()
		self.assertIn('JOBDONE', err.getvalue())

	def testReport(self):
		proc = Proc()
		job  = Job(0, proc)
		with captured_output() as (out, err):
			job.init()
			job.report()
		self.assertIn('[  input] [0/4] a   => 1', err.getvalue())
		self.assertIn('[  input] [0/4] b   => a', err.getvalue())
		self.assertIn('[  input] [0/4]  c  => /', err.getvalue())
		self.assertIn('[  input] [0/4] _c  => /', err.getvalue())
		self.assertIn('[  input] [0/4]  d  => [', err.getvalue())
		self.assertIn('[  input] [0/4] _d  => [', err.getvalue())
		self.assertIn('[  input] [0/4]  d2 => [', err.getvalue())
		self.assertIn('[  input] [0/4] _d2 => [', err.getvalue())
		self.assertIn('[  input] [0/4]  d3 => [', err.getvalue())
		self.assertIn('[  input] [0/4] _d3 => [', err.getvalue())
		self.assertIn('[ brings] [0/4]  c  => [', err.getvalue())
		self.assertIn('[ brings] [0/4]         /', err.getvalue())
		self.assertIn('[ brings] [0/4]         ...,', err.getvalue())
		self.assertIn('[ brings] [0/4] _c  => [', err.getvalue())
		self.assertIn('[ output] [0/4] a   => 1_1', err.getvalue())
		self.assertIn('[ output] [0/4] b   => /', err.getvalue())
		self.assertIn('[ output] [0/4] c   => /', err.getvalue())

	def testRc(self):
		proc = Proc()
		job  = Job(0, proc)
		with captured_output() as (out, err):
			job.init()
		utils.safeRemove(job.rcfile)
		self.assertEqual(job.rc(), -1)
		job.rc(1)
		self.assertEqual(job.rc(), 1)

	def testPid(self):
		proc = Proc()
		job  = Job(0, proc)
		with captured_output() as (out, err):
			job.init()
		utils.safeRemove(job.pidfile)
		self.assertEqual(job.pid(), '')
		job.pid(1)
		self.assertEqual(job.pid(), '1')

	def testCache(self):
		proc = Proc()
		proc.cache = False
		job  = Job(0, proc)
		utils.safeRemove(job.cachefile)
		job.cache()
		# p.cache = False
		self.assertPathNotExists(job.cachefile)

		proc.cache = True
		with captured_output() as (out, err):
			job.init()
		open(job.data['out']['b'], 'w').close()
		utils.safeRemove(job.data['out']['c'])
		makedirs(job.data['out']['c'])
		open(job.script, 'w').close()
		job.cache()
		self.assertPathExists(job.cachefile)
		with open(job.cachefile) as f:
			sig = json.load(f)
		out_b = job.data['out']['b']
		out_c = job.data['out']['c']
		in_c  = job.data['in']['c']
		in_d  = job.data['in']['d']
		in_d2 = job.data['in']['d2']
		in_d3 = job.data['in']['d3']
		self.assertEqual(sig['script'], [job.script, int(path.getmtime(job.script))])
		self.assertEqual(sig['in'], {'var': {'a': 1, 'b': 'a'}, 'files': {'d': [[fd, int(path.getmtime(fd))] for fd in in_d], 'd2': [[fd, int(path.getmtime(fd))] for fd in in_d2], 'd3': [[fd, int(path.getmtime(fd))] for fd in in_d3]}, 'file': {'c': [in_c, int(path.getmtime(in_c))]}})
		self.assertEqual(sig['out'], {'var': {'a': '1_1'}, 'dir': {'c': [out_c, int(path.getmtime(out_c))]}, 'file': {'b': [out_b, int(path.getmtime(out_b))]}})

	def testSignature(self):
		proc = Proc()
		dfile = path.join(tmpdir, 'testSignature_d')
		open(dfile, 'w').close()
		proc.input['d']['data'] = [[dfile]] * 5
		job  = Job(0, proc)
		with captured_output() as (out, err):
			job.init()
			open(job.data['out']['b'], 'w').close()
			utils.safeRemove(job.data['out']['c'])
			makedirs(job.data['out']['c'])
		out_b = job.data['out']['b']
		out_c = job.data['out']['c']
		in_c  = job.data['in']['c']
		in_d  = job.data['in']['d']
		in_d2 = job.data['in']['d2']
		in_d3 = job.data['in']['d3']
		utils.safeRemove(job.script)
		# script file not exists
		with captured_output() as (out, err):
			self.assertEqual(job.signature(), '')
		self.assertIn('Empty signature because of script file', err.getvalue())
		# all available
		open(job.script, 'w').close()
		with captured_output() as (out, err):
			sig = job.signature()
			self.assertEqual(sig['script'], [job.script, int(path.getmtime(job.script))])
			self.assertEqual(sig['in'], {'var': {'a': 1, 'b': 'a'}, 'files': {'d': [[fd, int(path.getmtime(fd))] for fd in in_d], 'd2': [[fd, int(path.getmtime(fd))] for fd in in_d2], 'd3': [[fd, int(path.getmtime(fd))] for fd in in_d3]}, 'file': {'c': [in_c, int(path.getmtime(in_c))]}})
			self.assertEqual(sig['out'], {'var': {'a': '1_1'}, 'dir': {'c': [out_c, int(path.getmtime(out_c))]}, 'file': {'b': [out_b, int(path.getmtime(out_b))]}})
		# no input file
		#if path.islink(in_c):
		utils.safeRemove(in_c)
		with captured_output() as (out, err):
			sig = job.signature()
			self.assertEqual(sig, '')
		self.assertIn('Empty signature because of input file', err.getvalue())
		open(in_c, 'w').close()

		# no input files
		#if path.islink(in_d[0]):
		utils.safeRemove(in_d[0])
		with captured_output() as (out, err):
			sig = job.signature()
			self.assertEqual(sig, '')
		self.assertIn('Empty signature because of one of input files', err.getvalue())
		open(in_d[0], 'w').close()

		# no outfile
		utils.safeRemove(out_b)
		with captured_output() as (out, err):
			sig = job.signature()
			self.assertEqual(sig, '')
		self.assertIn('Empty signature because of output file', err.getvalue())
		open(out_b, 'w').close()

		# no outdir
		utils.safeRemove(out_c)
		with captured_output() as (out, err):
			sig = job.signature()
			self.assertEqual(sig, '')
		self.assertIn('Empty signature because of output dir', err.getvalue())



	def testCheckOutfiles(self):
		with captured_output() as (out, err): 
			logger.getLogger()
			proc = Proc()
			job  = Job(0, proc)
			job.init()
			# no output file
			utils.safeRemove(job.data['out']['b'])
			job.checkOutfiles()
		self.assertFalse(job.succeed())
		self.assertIn('outfile not generated:', err.getvalue())

		# expectation not meet
		with captured_output() as (out, err): 
			logger.getLogger()
			open(job.data['out']['b'], 'w').close()
			job.checkOutfiles()
		self.assertIn('check expectation', err.getvalue())
		self.assertFalse(job.succeed())

		# dont check expectation
		job.rc(0)
		with captured_output() as (out, err): 
			logger.getLogger()
			job.checkOutfiles(expect = False)
		self.assertTrue(job.succeed())

		job.rc(0)
		# check expectation
		job.proc.expect = TemplatePyPPL('grep "Expecttion" {{out.b}}')
		with open(job.data['out']['b'], 'w') as f: f.write('Expecttion')
		with captured_output() as (out, err): 
			logger.getLogger()
			job.checkOutfiles(expect = True)
		self.assertTrue(job.succeed())

	def testSucceed(self):
		proc = Proc()
		job  = Job(0, proc)
		utils.safeRemove(job.dir)
		makedirs(job.dir)
		with captured_output() as (out, err):
			job.init()
		job.rc(0)
		outfile = path.join(job.outdir, path.basename(__file__))
		open(outfile, 'w').close()
		self.assertTrue(job.succeed())

		# rc not meet
		job.rc(1)
		with captured_output() as (out, err):
			job.checkOutfiles()
		self.assertFalse(job.succeed())

		proc.errhow = 'ignore'
		

		# outfile not ok
		job.rc(0)
		utils.safeRemove(outfile)
		with captured_output() as (out, err):
			job.checkOutfiles()
		self.assertFalse(job.succeed())

	def testExport(self):
		proc = Proc()
		job  = Job(0, proc)
		with captured_output() as (out, err):
			job.init()
		outfile_b = job.data['out']['b']
		outfile_c = job.data['out']['c']
		job.export() # nothing happened. exportdir == ''
		exdir = path.join(tmpdir, 'testExport-export')
		job.proc.exdir = exdir
		# exdir has to exist
		utils.safeRemove(exdir)
		self.assertRaises(AssertionError, job.export)

		makedirs(exdir)
		open(outfile_b, 'w').close()
		utils.safeRemove(outfile_c)
		makedirs(outfile_c)
		# gzip
		job.proc.exhow = 'gz'
		with captured_output() as (out, err):
			logger.getLogger()
			job.export()
		exfile_b = path.join(exdir, path.basename(job.data['out']['b']) + '.gz')
		exfile_c = path.join(exdir, path.basename(job.data['out']['c']) + '.tgz')
		self.assertIn('[ export] Job #0  : exporting to: /', err.getvalue())
		self.assertIn('testJob.py.gz', err.getvalue())
		self.assertIn('testJob.tgz', err.getvalue())
		self.assertPathExists(exfile_b)
		self.assertPathExists(exfile_c)

		# tgz a folder link
		proc2 = Proc()
		proc2.exdir = exdir
		job2 = Job(0, proc2)
		link2c = path.join(job2.outdir, 'Whatever')
		proc2.output['d'] = ['file',  TemplatePyPPL(path.basename(link2c))]
		utils.safeLink(outfile_c, link2c)
		with captured_output() as (out, err):
			job2.init()
		exfile_d = path.join(exdir, path.basename(job2.data['out']['d']) + '.tgz')
		job2.proc.exhow = 'gz'
		with captured_output() as (out, err):
			job2.export()
		self.assertIn('[ export] Job #0  : overwriting: /', err.getvalue())
		self.assertIn('[ export] Job #0  : exporting to: /', err.getvalue())
		self.assertIn('Whatever.tgz', err.getvalue())
		self.assertPathExists(exfile_d)

		# test overwrite = False
		proc2.exow = False
		with captured_output() as (out, err):
			job2.export()
		self.assertEqual(err.getvalue().count('[ export] Job #0  : skipped (target exists): /'), 3)

		# test copy
		utils.safeRemove(exdir)
		makedirs(exdir)
		proc3 = Proc()
		proc3.exdir = exdir
		proc3.exhow = 'copy'
		job3 = Job(0, proc3)
		exfile_b = path.join(exdir, path.basename(job.data['out']['b']))
		exfile_c = path.join(exdir, path.basename(job.data['out']['c']))
		with captured_output() as (out, err):
			job3.init()
			job3.export()
		self.assertTrue(path.isfile(exfile_b))
		self.assertTrue(path.isfile(job.data['out']['b']))
		self.assertTrue(path.isdir(exfile_c))
		self.assertTrue(path.isdir(job.data['out']['c']))
		
		# test link
		utils.safeRemove(exdir)
		makedirs(exdir)
		proc4 = Proc()
		proc4.exdir = exdir
		proc4.exhow = 'link'
		job4 = Job(0, proc4)
		with captured_output() as (out, err):
			job4.init()
			job4.export()
		self.assertTrue(path.islink(exfile_b))
		self.assertTrue(path.isfile(job.data['out']['b']))
		self.assertTrue(path.islink(exfile_c))
		self.assertTrue(path.isdir(job.data['out']['c']))

	def testExportMove(self):
		exdir = path.join(tmpdir, 'testExport-export')
		utils.safeRemove(exdir)
		makedirs(exdir)
		makedirs(path.join(exdir, path.basename(__file__) + '0'))
		proc = Proc()
		proc.exdir = exdir
		proc.exhow = 'move'
		proc.output = OrderedDict([
			('a', ['var',  TemplatePyPPL('{{in.a}}_1')]),
			('b', ['file', TemplatePyPPL('{{in.c | bn}}{{job.index}}')]),
			('c', ['dir',  TemplatePyPPL('{{in.c | fn}}{{job.index}}')]),
		])
		job = Job(0, proc)
		with captured_output() as (out, err):
			logger.getLogger()
			job.init()
			open(job.data['out']['b'], 'w').close()
			utils.safeRemove(job.data['out']['c'])
			makedirs(job.data['out']['c'])
			job.export()
		exfile_b = path.join(exdir, path.basename(job.data['out']['b']))
		exfile_c = path.join(exdir, path.basename(job.data['out']['c']))
		self.assertTrue(path.isfile(exfile_b))
		self.assertTrue(path.islink(job.data['out']['b']))
		self.assertTrue(path.isdir(exfile_c))
		self.assertTrue(path.islink(job.data['out']['c']))

		def multiJobTest(jobs, generateB):
			from multiprocessing import JoinableQueue, Process
			sq = JoinableQueue()
			with captured_output() as (out, err):
				for job in jobs: 
					job.init()
					generateB(job)
					utils.safeRemove(job.data['out']['c'])
					makedirs(job.data['out']['c'])

			def worker(q):
				while True:
					if q.empty(): break
					try:
						index = q.get()
					except:
						break
					if index is None: break

					try:
						job = jobs[index]
						with captured_output() as (out, err):
							logger.getLogger()
							job.export()
					except:
						raise
					finally:
						q.task_done()


			for i in range(len(jobs)):
				sq.put(i)

			for i in range(len(jobs)):
				t = Process(target = worker, args = (sq, ))
				t.daemon = True
				t.start()
			sq.join()

		proc.output['b'] = ['file', TemplatePyPPL('{{in.c | bn}}')]
		for key, val in proc.input.items():
			proc.input[key]['data'] = [val['data'][0]] * 20
		jobs = [Job(i, proc) for i in range(20)]
		with captured_output() as (out, err):
			logger.getLogger()
			multiJobTest(jobs, lambda job: open(job.data['out']['b'], 'w').close())
		for job in jobs:
			exfile_b = path.join(exdir, path.basename(job.data['out']['b']))
			exfile_c = path.join(exdir, path.basename(job.data['out']['c']))
			self.assertTrue(path.isfile(exfile_b))
			self.assertTrue(path.islink(job.data['out']['b']))
			self.assertTrue(path.isdir(exfile_c))
			self.assertTrue(path.islink(job.data['out']['c']))

		utils.safeRemove(exdir)
		makedirs(exdir)
		[utils.safeRemove(job.dir) for job in jobs]
		def generateB(job):
			outb = job.data['out']['b']
			utils.safeRemove(outb)
			if jobs.index(job) == 0:
				with open(outb, 'w') as fout:
					fout.write('job0')
			else:
				utils.safeLink(jobs[0].data['out']['b'], outb)
		#with captured_output() as (out, err):
		multiJobTest(jobs, generateB)
		for job in jobs:
			exfile_b = path.join(exdir, path.basename(job.data['out']['b']))
			exfile_c = path.join(exdir, path.basename(job.data['out']['c']))
			self.assertTrue(path.isfile(exfile_b))
			self.assertTrue(path.islink(job.data['out']['b']))
			self.assertTrue(path.isdir(exfile_c))
			self.assertTrue(path.islink(job.data['out']['c']))
			with open(exfile_b) as f:
				self.assertEqual(f.read(), 'job0')

	def testExportPartial(self):

		exdir = path.join(tmpdir, 'testExport-export')
		utils.safeRemove(exdir)
		makedirs(exdir)
		proc = Proc()
		proc.exdir = exdir
		proc.exhow = 'copy'
		proc.expart = [TemplatePyPPL('b')]
		job = Job(0, proc)
		utils.safeRemove(job.dir)
		with captured_output() as (out, err):
			job.init()
			open(job.data['out']['b'], 'w').close()
			utils.safeRemove(job.data['out']['c'])
			makedirs(job.data['out']['c'])
		exfile_b = path.join(exdir, path.basename(job.data['out']['b']))
		exfile_c = path.join(exdir, path.basename(job.data['out']['c']))
		with captured_output() as (out, err):
			logger.getLogger()
			job.export()
		self.assertPathExists(exfile_b)
		self.assertPathNotExists(exfile_c)
		
		# the other output
		utils.safeRemove(exdir)
		makedirs(exdir)
		proc.expart = [TemplatePyPPL('c')]
		with captured_output() as (out, err):
			job.export()
		self.assertPathExists(exfile_c)
		self.assertPathNotExists(exfile_b)
		
		# glob
		utils.safeRemove(exdir)
		makedirs(exdir)
		proc.expart = [TemplatePyPPL('*.py')]
		with captured_output() as (out, err):
			job.export()
		self.assertPathExists(exfile_b)
		self.assertPathNotExists(exfile_c)

	def testReset(self):
		proc = Proc()
		job = Job(0, proc)
		with captured_output() as (out, err):
			job.init()
			open(job.rcfile, 'w').close()
			open(job.outfile, 'w').close()
			open(job.errfile, 'w').close()
			open(job.pidfile, 'w').close()
			outc = job.data['out']['c']
			utils.safeRemove(outc)
			makedirs(path.join(outc, 'something'))
			self.assertPathExists(job.rcfile)
			self.assertPathExists(job.outfile)
			self.assertPathExists(job.errfile)
			self.assertPathExists(job.pidfile)
			self.assertPathExists(path.join(outc, 'something'))
			job.reset()
		self.assertPathNotExists(job.rcfile)
		self.assertPathNotExists(job.outfile)
		self.assertPathNotExists(job.errfile)
		self.assertPathNotExists(job.pidfile)
		self.assertPathNotExists(path.join(outc, 'something'))
		self.assertPathExists(outc)
		#self.assertIn('Output directory created after reset:', err.getvalue())

		# retry:
		with captured_output() as (out, err):
			job.init()
			open(job.rcfile, 'w').close()
			open(job.outfile, 'w').close()
			open(job.errfile, 'w').close()
			open(job.pidfile, 'w').close()
			outc = job.data['out']['c']
			utils.safeRemove(outc)
			makedirs(path.join(outc, 'something'))
			self.assertPathExists(job.rcfile)
			self.assertPathExists(job.outfile)
			self.assertPathExists(job.errfile)
			self.assertPathExists(job.pidfile)
			self.assertPathExists(path.join(outc, 'something'))
			job.reset(1)
		retrydir = path.join(job.dir, 'retry.1')
		self.assertPathNotExists(job.rcfile)
		self.assertPathNotExists(job.outfile)
		self.assertPathNotExists(job.errfile)
		self.assertPathNotExists(job.pidfile)
		self.assertPathNotExists(path.join(outc, 'something'))
		self.assertPathExists(outc)
		#self.assertIn('Output directory created after reset:', err.getvalue())

		self.assertPathExists(retrydir)
		self.assertPathExists(path.join(retrydir, path.basename(job.rcfile)))
		self.assertPathExists(path.join(retrydir, path.basename(job.outfile)))
		self.assertPathExists(path.join(retrydir, path.basename(job.errfile)))
		self.assertPathExists(path.join(retrydir, path.basename(job.pidfile)))
		self.assertPathExists(path.join(retrydir, path.basename(job.outdir), path.basename(outc), 'something'))

'''

if __name__ == '__main__':
	unittest.main(verbosity=2)