import path, unittest

import sys
import tempfile
import json
from time import sleep, time
from os import path, makedirs, utime
from contextlib import contextmanager
from collections import OrderedDict
from six import StringIO
from glob import glob
from pyppl import utils, logger
from pyppl.job import Job
from pyppl.templates import TemplatePyPPL

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
class Proc(object):
	def __init__(self, workdir = ''):
		self.workdir = workdir
		if not self.workdir:
			self.workdir = path.join(tmpdir, 'TestJob-wdir')
		if not path.exists(self.workdir):
			makedirs(self.workdir)

		self.procvars = {

			'a': 1,
			'b': 2
		}

		self.IN_VARTYPE = ['var']
		self.OUT_VARTYPE = ['var']
		self.IN_FILETYPE = ['file']
		self.OUT_FILETYPE = ['file']
		self.IN_FILESTYPE = ['files']
		self.OUT_DIRTYPE = ['dir']
		self.EX_GZIP = ['gz']
		self.EX_MOVE = ['move']
		self.EX_COPY = ['copy']
		self.EX_LINK = ['link']

		self.input = {
			'a': {
				'type': 'var',
				'data': [1,2,3,4,5],
			},
			'b': {
				'type': 'var',
				'data': ['a', 'b', 'c', 'd', 'e'],
			},
			'c': {
				'type': 'file',
				'data': [__file__] * 5,
			},
			'd': {
				'type': 'files',
				'data': [[__file__]] * 5
			}
		}
		self.output = OrderedDict([
			('a', ['var',  TemplatePyPPL('{{in.a}}_1')]),
			('b', ['file', TemplatePyPPL('{{in.c | bn}}')]),
			('c', ['dir',  TemplatePyPPL('{{in.c | fn}}')]),
		])

		self.size = 5
		self.rc = [0]
		self.exdir = ''
		self.expart = []
		self.exhow = 'move'
		self.exow = True
		self.cache = True
		self.errhow = 'terminate'
		self.echo = {
			'jobs': [0],
			'type': ['stderr', 'stdout']
		}

		self.brings = {
			'c': TemplatePyPPL('{{in.c | fn | [:4]}}*{{in.c | ext}}')
		}

		self.expect = TemplatePyPPL('grep a {{out.b}}')

		self.script = TemplatePyPPL("""
import os
print "{{in.a}}"
print "{{out.a}}"
{% if in.a %}
print "{{in.b}}"
{% else %}
print "not a"
{% endif %}
""")
	
	def log(self, msg, level, mark = ''):
		sys.stderr.write('[%7s] %s\n' % (level, msg))

class TestJob (unittest.TestCase):

	assertItemsEqual = lambda self, x, y: self.assertEqual(sorted(x), sorted(y))
	assertPathExists = lambda self, x: self.assertTrue(path.exists(x))
	assertPathNotExists = lambda self, x: self.assertFalse(path.exists(x))

	def testInit(self):
		proc = Proc()
		job  = Job(0, proc)
		self.assertIsInstance(job, Job)
		self.assertIsInstance(job.proc, Proc)
		self.assertTrue(job.outfileOk)
		self.assertEqual(job.dir, path.join(tmpdir, 'TestJob-wdir', '0'))
		self.assertEqual(job.indir, path.join(job.dir, 'input'))
		self.assertEqual(job.outdir, path.join(job.dir, 'output'))
		self.assertEqual(job.script, path.join(job.dir, 'job.script'))
		self.assertEqual(job.rcfile, path.join(job.dir, 'job.rc'))
		self.assertEqual(job.outfile, path.join(job.dir, 'job.stdout'))
		self.assertEqual(job.errfile, path.join(job.dir, 'job.stderr'))
		self.assertEqual(job.cachefile, path.join(job.dir, 'job.cache'))
		self.assertEqual(job.pidfile, path.join(job.dir, 'job.pid'))
		self.assertEqual(job.index, 0)
		self.assertIs(job.proc, proc)
		self.assertEqual(job.input, {})
		self.assertEqual(job.output, {})
		self.assertEqual(job.brings, {})
		self.assertEqual(job.data, {
			'job': {
				'index'   : job.index,
				'pid'     : '',
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

	def testPrepInput(self):
		proc = Proc()
		job  = Job(0, proc)
		job._prepInput()
		self.assertTrue(path.exists(job.indir))
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
			}
		})
		self.assertEqual(job.data['in'], {
			'a': 1,
			'b': 'a',
			'c': path.join(job.indir, path.basename(__file__)),
			'_c': path.realpath(__file__),
			'd': [path.join(job.indir, path.basename(__file__))],
			'_d': [path.realpath(__file__)],
		})
		proc.input['c']['data'][0] = __file__ + '.noexist'
		self.assertRaises(OSError, job._prepInput)
		proc.input['c']['data'][0] = __file__
		proc.input['d']['data'][0][0] = __file__ + '.noexist'
		self.assertRaises(OSError, job._prepInput)

		file1 = path.join(tmpdir, path.basename(__file__))
		open(file1, 'w').close()
		proc.input['d']['data'][0][0] = file1
		job.input = {}
		job.data['in'] = {}

		with captured_output() as (out, err):
			job._prepInput()
		self.assertIn('Input file renamed: testJob.py -> testJob[1].py', err.getvalue())
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
				'orig': [path.realpath(file1)],
				'data': [path.join(job.indir, path.splitext(path.basename(file1))[0] + '[1].py')],
			}
		})
		self.assertEqual(job.data['in'], {
			'a': 1,
			'b': 'a',
			'c': path.join(job.indir, path.basename(__file__)),
			'_c': path.realpath(__file__),
			'd': [path.join(job.indir, path.splitext(path.basename(file1))[0] + '[1].py')],
			'_d': [path.realpath(file1)],
		})

	def testPrepBrings(self):
		proc = Proc()
		job  = Job(0, proc)
		job._prepInput()
		orgbrings = {k:v for k,v in proc.brings.items()}
		proc.brings = {'a': ''}
		self.assertRaises(ValueError, job._prepBrings)
		proc.brings = {
			'c': TemplatePyPPL('{{in.c | fn | [:4]}}111*{{in.c | ext}}')
		}
		self.assertRaises(ValueError, job._prepBrings)
		proc.brings = orgbrings
		job._prepBrings()
		self.assertItemsEqual(job.data['bring']['_c'], list(map(path.abspath, glob('./test*.py'))))
		self.assertItemsEqual(job.data['bring']['c'], list(map(lambda x: path.join(job.indir, path.basename(x)), glob('./test*.py'))))
		self.assertItemsEqual(job.brings['_c'], list(map(path.abspath, glob('./test*.py'))))
		self.assertItemsEqual(job.brings['c'], list(map(lambda x: path.join(job.indir, path.basename(x)), glob('./test*.py'))))

		# test rename and bring through links
		utils.safeRemove(job.indir)
		self.assertFalse(path.exists(job.indir))
		file1   = path.join(tmpdir, path.basename(__file__))
		file2   = path.join(tmpdir, 't', path.basename(__file__))
		utils.safeRemove(path.join(tmpdir, 't'))
		makedirs(path.join(tmpdir, 't'))
		brfile1 = path.join(tmpdir, path.basename(__file__)) + '.idx'
		open(file1, 'w').close()
		open(brfile1, 'w').close()
		utils.safeLink(file1, file2)
		proc2 = Proc()
		proc2.input = {
			'f1': {
				'type': 'file',
				'data': [__file__]
			},
			'f2': {
				'type': 'file',
				'data': [file2]
			}
		}
		proc2.brings = {
			'f2': TemplatePyPPL('{{in.f2 | bn}}.idx')
		}
		job2 = Job(0, proc2)
		with captured_output() as (out, err):
			job2._prepInput()
		self.assertIn('Input file renamed: testJob.py -> testJob[1].py', err.getvalue())
		job2._prepBrings()
		self.assertEqual(job2.data['bring']['f2'], [path.join(job2.indir, 'testJob[1].py.idx')])
		self.assertEqual(job2.data['bring']['_f2'], [brfile1])
		self.assertEqual(job2.brings['f2'], [path.join(job2.indir, 'testJob[1].py.idx')])
		self.assertEqual(job2.brings['_f2'], [brfile1])
		self.assertEqual(job2.data['in']['f1'], path.join(job2.indir, 'testJob.py'))
		self.assertEqual(job2.data['in']['_f1'], path.abspath(__file__))

	def testPrepOutput(self):
		proc = Proc()
		job  = Job(0, proc)
		job._prepInput()
		job._prepOutput()
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

	def testPrepScript(self):
		proc = Proc()
		job  = Job(0, proc)
		job._prepInput()
		job._prepOutput()
		# job.script may not contain the real script in this test suite
		utils.safeRemove(job.script)
		scriptExists = path.exists(job.script)
		with captured_output() as (out, err):
			job._prepScript()
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

	def testInitSelf(self):
		proc = Proc()
		job  = Job(0, proc)
		scriptExists = path.exists(job.script)
		with captured_output() as (out, err):
			job.init()
		self.assertTrue(path.exists(job.dir))
		self.assertEqual(job.data['a'], 1)
		self.assertEqual(job.data['b'], 2)
		self.assertTrue(path.exists(job.indir))
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
			}
		})
		self.assertEqual(job.data['in'], {
			'a': 1,
			'b': 'a',
			'c': path.join(job.indir, path.basename(__file__)),
			'_c': path.realpath(__file__),
			'd': [path.join(job.indir, path.basename(__file__))],
			'_d': [path.realpath(__file__)],
		})
		# brings
		self.assertItemsEqual(job.data['bring']['_c'], list(map(path.abspath, glob('./test*.py'))))
		self.assertItemsEqual(job.data['bring']['c'], list(map(lambda x: path.join(job.indir, path.basename(x)), glob('./test*.py'))))
		self.assertItemsEqual(job.brings['_c'], list(map(path.abspath, glob('./test*.py'))))
		self.assertItemsEqual(job.brings['c'], list(map(lambda x: path.join(job.indir, path.basename(x)), glob('./test*.py'))))
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
		proc.expart = [1]
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
		job.rc(0)
		job.outfileOk = False
		proc.echo['jobs'] = []
		proc.errhow = 'terminate'

		utils.safeRemove(job.errfile)
		with captured_output() as (out, err):
			logger.getLogger()
			job.showError()
		self.assertIn('failed. Return code: 0, all output files: not generated or expectation not met', err.getvalue())
		self.assertIn(job.script, err.getvalue())
		self.assertIn(job.outfile, err.getvalue())
		self.assertIn(job.errfile, err.getvalue())
		self.assertIn('check STDERR below', err.getvalue())
		self.assertIn('<EMPTY STDERR>', err.getvalue())

		with open(job.errfile, 'w') as ferr:
			ferr.write('Error1\nError2\nError3')
		with captured_output() as (out, err):
			logger.getLogger()
			job.showError()
		self.assertIn('check STDERR below', err.getvalue())
		self.assertIn('Error1', err.getvalue())
		self.assertIn('Error2', err.getvalue())
		self.assertIn('Error3', err.getvalue())

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
		self.assertIn('[  input] [0/4] a  => 1', err.getvalue())
		self.assertIn('[  input] [0/4] b  => a', err.getvalue())
		self.assertIn('[  input] [0/4]  c => /', err.getvalue())
		self.assertIn('[  input] [0/4] _c => /', err.getvalue())
		self.assertIn('[  input] [0/4]  d => [', err.getvalue())
		self.assertIn('[  input] [0/4] _d => [', err.getvalue())
		self.assertIn('[ brings] [0/4]  c => [', err.getvalue())
		self.assertIn('[ brings] [0/4]        /', err.getvalue())
		self.assertIn('[ brings] [0/4]        ...,', err.getvalue())
		self.assertIn('[ brings] [0/4] _c => [', err.getvalue())
		self.assertIn('[ output] [0/4] a  => 1_1', err.getvalue())
		self.assertIn('[ output] [0/4] b  => /', err.getvalue())
		self.assertIn('[ output] [0/4] c  => /', err.getvalue())

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
		self.assertEqual(sig['script'], [job.script, int(path.getmtime(job.script))])
		self.assertEqual(sig['in'], {'var': {'a': 1, 'b': 'a'}, 'files': {'d': [[fd, int(path.getmtime(fd))] for fd in in_d]}, 'file': {'c': [in_c, int(path.getmtime(in_c))]}})
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
			self.assertEqual(sig['in'], {'var': {'a': 1, 'b': 'a'}, 'files': {'d': [[fd, int(path.getmtime(fd))] for fd in in_d]}, 'file': {'c': [in_c, int(path.getmtime(in_c))]}})
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
		proc = Proc()
		job  = Job(0, proc)
		with captured_output() as (out, err):
			job.init()
		outfile = path.join(job.outdir, path.basename(__file__))
		utils.safeRemove(outfile)
		# no output file
		job.outfileOk = True
		with captured_output() as (out, err):
			job.checkOutfiles()
		self.assertFalse(job.outfileOk)
		self.assertIn('outfile not generated:', err.getvalue())

		# expectation not meet
		job.outfileOk = True
		with open(outfile, 'w') as fout:
			fout.write('Expecttion') # no a
		with captured_output() as (out, err):
			job.checkOutfiles()
		self.assertIn('check expectation', err.getvalue())
		self.assertFalse(job.outfileOk)

		# dont check expectation
		job.outfileOk = True
		with captured_output() as (out, err):
			job.checkOutfiles(expect = False)
		self.assertTrue(job.outfileOk)

		# check expectation
		job.outfileOk = True
		job.proc.expect = TemplatePyPPL('grep "Expecttion" {{out.b}}')
		with captured_output() as (out, err):
			job.checkOutfiles(expect = True)
		self.assertTrue(job.outfileOk)

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
		job.outfileOk = True
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
		self.assertIn('Output directory created after reset:', err.getvalue())

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
		self.assertIn('Output directory created after reset:', err.getvalue())

		self.assertPathExists(retrydir)
		self.assertPathExists(path.join(retrydir, path.basename(job.rcfile)))
		self.assertPathExists(path.join(retrydir, path.basename(job.outfile)))
		self.assertPathExists(path.join(retrydir, path.basename(job.errfile)))
		self.assertPathExists(path.join(retrydir, path.basename(job.pidfile)))
		self.assertPathExists(path.join(retrydir, path.basename(job.outdir), path.basename(outc), 'something'))



if __name__ == '__main__':
	unittest.main(verbosity=2)