import glob
import json
import os
import shutil
import sys
import unittest
from time import sleep

rootdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, rootdir)
from pyppl import job, proc, utils

class TestJob (unittest.TestCase):
	
	testdir = "./tests"
	wdir    = "./workdir"
	dirname = os.path.dirname (os.path.abspath(__file__))
	logger  = utils.getLogger('debug', 'TestJob')

	def testConstruct (self):
		self.maxDiff = None
		p = proc ()
		p.ppldir = self.wdir
		p.props['logger'] = self.logger
		p.output = "a:1"
		p._buildProps()
		j = job (0, p)
		workdir = os.path.abspath(p.workdir)
		self.assertEqual (j.script, os.path.join(workdir, '0', 'job.script'))
		self.assertEqual (j.rcfile, os.path.join(workdir, '0', 'job.rc'))
		self.assertEqual (j.outfile, os.path.join(workdir, '0', 'job.stdout'))
		self.assertEqual (j.errfile, os.path.join(workdir, '0', 'job.stderr'))
		self.assertEqual (j.cachefile, os.path.join(workdir, '0', 'job.cache'))
		self.assertEqual (j.indir, os.path.join(workdir, '0', 'input'))
		self.assertEqual (j.outdir, os.path.join(workdir, '0', 'output'))
		self.assertEqual (j.dir, os.path.join(workdir, '0'))
		self.assertEqual (j.proc, p)
		self.assertEqual (j.input, {})
		self.assertEqual (j.output, {})
		self.assertEqual (j.brings, {})
		self.assertEqual (j.data, {
			'#': j.index,
			'job.id': '',
			'job.index': j.index,
			'job.indir': j.indir,
			'job.outdir': j.outdir,
			'job.dir': j.dir,
			'job.outfile': j.outfile,
			'job.errfile': j.errfile,
			'job.idfile': j.idfile
		})
		self.assertEqual (j.index,  0)
		
	def testMakeJobDir (self):
		p = proc ('makejobdir')
		p.ppldir = self.wdir
		p.props['logger'] = self.logger
		p.output = "a:1"
		p._buildProps()
		j = job (0, p)
		if os.path.isdir (j.dir):
			shutil.rmtree (j.dir)
		self.assertFalse (os.path.isdir (j.dir))
		j.init ()
		self.assertTrue (os.path.isdir (j.dir))

	def testMakeOutDir (self):
		p = proc ('makeoutdir')
		p.ppldir = self.wdir
		p.props['logger'] = self.logger
		p.input = {"a":[1]}
		p.output = "outdir:dir:{{a}}"
		p._tidyBeforeRun()
		j = p.jobs[0]
		self.assertTrue (os.path.exists(os.path.join(j.outdir, "1")))
		
	def testUpdateData (self):
		p = proc ('dataupdate')
		p.ppldir = self.wdir
		p.props['logger'] = self.logger
		p.output = "a:1"
		p._buildProps()
		j = job (0, p)
		self.assertEqual (j.data, {
			'#': j.index,
			'job.id': '',
			'job.index': j.index,
			'job.indir': j.indir,
			'job.outdir': j.outdir,
			'job.dir': j.dir,
			'job.outfile': j.outfile,
			'job.errfile': j.errfile,
			'job.idfile': j.idfile
		})
		j.init ()
		self.assertEqual (j.data, {
			'#': j.index,
			'job.id': '',
			'job.index': j.index,
			'job.indir': j.indir,
			'job.outdir': j.outdir,
			'job.dir': j.dir,
			'job.outfile': j.outfile,
			'job.errfile': j.errfile,
			'job.idfile': j.idfile,
			'a': '1'
		})

	def testId (self):
		p = proc ('id')
		p.ppldir = self.wdir
		p.props['logger'] = self.logger
		p.output = "a:1"
		p._buildProps()
		j = job (0, p)
		j.init()
		j.id ('aaa')
		
		self.assertEqual(j.id(), 'aaa')
		
	def testPrepInput (self):
		self.maxDiff = None
		p1 = proc ('prepinput')
		p1.ppldir = self.wdir
		p1.props['logger'] = self.logger
		p1.output = "o:1"
		p1.input  = {"a, b:file, c:files": [(1, __file__, "./*.py")] * 3}
		p1._buildProps()
		p1._buildInput()
		j = job (2, p1)
		if not os.path.exists(j.dir):
			os.makedirs (j.dir)
		j._prepInput()
		self.assertEqual (j.input['a'], {'type': 'var', 'data': 1})
		self.assertEqual (j.input['b'], {'type': 'file', 'orig': os.path.realpath(__file__), 'data': os.path.join(j.indir, os.path.basename(__file__))})
		self.assertEqual (j.input['c']['type'], 'files')
		self.assertEqual(sorted(map(os.path.realpath, j.input['c']['data'])), sorted(glob.glob (self.dirname + "/*.py")))
		for infile in glob.glob (self.dirname + "/*.py"):
			self.assertTrue (utils.isSamefile(infile, os.path.join(j.indir, os.path.basename(infile))))
		self.assertEqual (j.data['#'], j.index)
		self.assertEqual (j.data['job.index'], j.index)
		self.assertEqual (j.data['job.indir'], j.indir)
		self.assertEqual (j.data['job.outdir'], j.outdir)
		self.assertEqual (j.data['job.dir'], j.dir)
		self.assertEqual (j.data['job.outfile'], j.outfile)
		self.assertEqual (j.data['job.errfile'], j.errfile)
		self.assertEqual (j.data['job.idfile'], j.idfile)
		self.assertEqual (j.data['a'], 1)
		self.assertEqual (j.data['b'], os.path.join (j.indir, os.path.basename(__file__)))
		self.assertEqual (j.data['b.orig'], os.path.join (self.dirname, os.path.basename(__file__)))
		self.assertEqual (sorted(map(os.path.abspath, j.data['c.orig'])), sorted(glob.glob (self.dirname + "/*.py")))
		self.assertEqual (sorted(j.data['c']), sorted(glob.glob (j.indir + "/*.py")))
		
		p2 = proc ()
		p2.ppldir = self.wdir
		p2.props['logger'] = self.logger
		p2.output = "o:1"
		p2.input  = {"a, b:file": [(1, __file__)], "c:files": ["./*.py"]}
		p2._buildProps()
		p2._buildInput()
		j = job (0, p2)
		if not os.path.exists(j.dir):
			os.makedirs (j.dir)
		j._prepInput()
		self.assertEqual (j.input['a'], {'type': 'var', 'data': 1})
		self.assertEqual (j.input['b'], {'type': 'file', 'orig': os.path.abspath(__file__), 'data': os.path.join(j.indir, os.path.basename(__file__))})
		self.assertEqual (j.input['c']['type'], 'files')
		self.assertEqual(sorted(map(os.path.realpath, j.input['c']['data'])), sorted(glob.glob (self.dirname + "/*.py")))
		for infile in glob.glob (self.dirname + "/*.py"):
			self.assertTrue (utils.isSamefile(infile, os.path.join(j.indir, os.path.basename(infile))))
		self.assertEqual (j.data['#'], j.index)
		self.assertEqual (j.data['job.index'], j.index)
		self.assertEqual (j.data['job.indir'], j.indir)
		self.assertEqual (j.data['job.outdir'], j.outdir)
		self.assertEqual (j.data['job.dir'], j.dir)
		self.assertEqual (j.data['job.outfile'], j.outfile)
		self.assertEqual (j.data['job.errfile'], j.errfile)
		self.assertEqual (j.data['a'], 1)
		self.assertEqual (j.data['b'], os.path.join (j.indir, os.path.basename(__file__)))
		self.assertEqual (j.data['b.orig'], os.path.join (self.dirname, os.path.basename(__file__)))
		self.assertEqual (sorted(map(os.path.abspath, j.data['c.orig'])), sorted(glob.glob (self.dirname + "/*.py")))
		self.assertEqual (sorted(j.data['c']), sorted(glob.glob (j.indir + "/*.py")))
	
	def testPrepBrings (self):
		p1 = proc ()
		p1.ppldir = self.wdir
		p1.props['logger'] = self.logger
		p1.output = "o:1"
		p1.input  = {"a, b:file": [(1, os.path.abspath(__file__))] * 3}
		p1.brings = {"b": "aggr.unittest{{b | ext}}", "b#": "pyppl.unittest{{b | ext}}"}
		p1._buildProps()
		p1._buildInput()
		j = job (2, p1)
		if not os.path.exists(j.dir):
			os.makedirs (j.dir)
		j._prepInput()
		j._prepBrings()
		self.assertTrue (utils.isSamefile(j.brings['b'], os.path.join (j.indir, "aggr.unittest.py")))
		self.assertTrue (utils.isSamefile(j.brings['b#'], os.path.join (j.indir, "pyppl.unittest.py")))
		self.assertTrue (utils.isSamefile(j.data['bring.b'], j.data['bring.b.orig']))
		self.assertTrue (utils.isSamefile(j.data['bring.b#'], j.data['bring.b#.orig']))
		
	def testPrepOutput (self):
		p1 = proc ('prepoutput')
		p1.ppldir = self.wdir
		p1.props['logger'] = self.logger
		p1.output = "o:1, o2:file:{{b|fn}}.txt"
		p1.input  = {"a, b:file": [(1, os.path.abspath(__file__))] * 3}
		p1.brings = {"b": "aggr.unittest{{b | ext}}", "b#": "pyppl.unittest{{b | ext}}"}
		p1._buildProps()
		p1._buildInput()
		j = job (2, p1)
		if not os.path.exists(j.dir):
			os.makedirs (j.dir)
		j._prepInput()
		j._prepBrings()
		j._prepOutput()
		self.assertEqual (j.data['o'], '1')
		self.assertEqual (j.data['o2'], os.path.join(j.outdir, 'job.unittest.txt'))
		
	def testPrepScript(self):
		ps = proc ('script')
		ps.ppldir = self.wdir
		ps.props['logger'] = self.logger
		# empty script does not raise Exception any more
		#self.assertRaises (Exception, ps._tidyBeforeRun)
		ps.input = {"input": ["input"]}
		
		ps.script = "ls {{proc.workdir}}\necho {{#}} {{input}}\necho {{output}}\necho {{args.var1}} {{args.var2}}"
		ps.args   = {'var1': 1, 'var2': '2'}
		ps.output = "output:var:{{input}}2"
		ps._buildProps()
		ps._buildInput()
		ps._buildProcVars()
		j = job (0, ps)
		if not os.path.exists(j.dir):
			os.makedirs (j.dir)
		j.data.update (j.proc.procvars)
		j._prepInput()
		j._prepBrings()
		j._prepOutput()
		j._prepScript()
		f = open(j.script)
		self.assertEqual (f.read(), "#!/usr/bin/env bash\n\nls %s\necho 0 input\necho input2\necho 1 2" % ps.workdir)
		f.close()
	
	def testScriptTpl (self):
		p = proc('tpl')
		p.ppldir = self.wdir
		p.input  = {"a":[1]}
		p.output = "x:{{a}}2"
		# not exists
		p.script = "template:a.py" 
		j = job (0, p)
		self.assertRaises(ValueError, j._prepScript)
		
		# relpath
		p.script = "template:%s/a.py" % self.wdir
		p.props['logger'] = self.logger
		p._buildProps()
		p._buildInput()
		if not os.path.exists(self.wdir):
			os.makedirs (self.wdir)
		if not os.path.exists (p.script):
			f = open ("%s/a.py" % self.wdir, "w")
			f.write("echo {{a}}")
			f.close()
		j = job (0, p)
		j.init()
		f = open (j.script)
		self.assertTrue ("echo 1" in f.read())
		f.close()
		
		# abspath
		p.input  = {"a": [2]}
		p._buildInput()
		p.script = "template:%s/a.py" % os.path.abspath(self.wdir)
		j.init()
		f = open(j.script)
		self.assertTrue ("echo 2" in f.read())
		f.close()
		#print (open(j.script).read())
		
	def tearDown (self):
		if os.path.isdir (self.testdir):
			shutil.rmtree (self.testdir)
		if os.path.isdir (self.wdir):
			shutil.rmtree (self.wdir)
	
	def testSignature (self):
		p = proc('sig')
		p.ppldir = self.wdir
		p.input  = {"a":[1]}
		p.output = "x:{{a}}2"
		p.props['logger'] = self.logger
		p.script = "echo 123"
		p._buildProps()
		p._buildInput()
		j = job (0, p)
		j.init()
		sig = j.signature()
		self.assertIsInstance(sig, dict)
		self.assertEqual (sig['in'], {'var': {'a': 1}, 'files': {}, 'file': {}})
		self.assertEqual (sig['out'], {'var': {'x': '12'}, 'dir': {}, 'file': {}})
		self.assertTrue ('0/job.oscript@' in sig['script'])
	
	def testCache (self):
		p = proc('cache')
		p.ppldir = self.wdir
		p.input  = {"a":[1]}
		p.output = "x:{{a}}2"
		p.script = "echo 888"
		p.props['logger'] = self.logger
		p._buildProps()
		p._buildInput()
		j = job (0, p)
		j.init()
		sig = j.signature()
		j.cache()
		f = open(j.cachefile)
		self.assertEqual (f.read(), json.dumps(sig))
		self.assertTrue (j.isTrulyCached())
		f.close()
		
	def testExptCached (self):
		p = proc('exptcache')
		p.ppldir = self.wdir
		p.input  = {"a":[1]}
		p.output = "x:{{a}}2"
		p.props['logger'] = self.logger
		p._buildProps()
		p._buildInput()
		p.cache  = True
		p.exhow  = "gzip"
		p.exdir  = self.wdir
		j = job (0, p)
		self.assertFalse (j.isExptCached())
		p.cache  = 'export'
		p.exhow  = "symlink"
		p.exdir  = self.wdir
		self.assertFalse (j.isExptCached())
		p.cache  = 'export'
		p.exhow  = "gzip"
		p.exdir  = ''
		self.assertFalse (j.isExptCached())
		p.cache  = 'export'
		p.exhow  = "gzip"
		p.exdir  = self.wdir
		
		j.init()
		self.assertTrue (j.isExptCached())
		# gzip: file
		p.output = "outfile:file:{{a}}.txt"
		j.init ()
		self.assertFalse (j.isExptCached())
		exfile = "%s/1.txt" % (self.wdir)
		f = open (exfile, 'w')
		f.write('')
		f.close()
		self.assertTrue (os.path.exists("%s" % exfile))
		os.system ("gzip  -c %s > %s.%s.gz" % (exfile, exfile, p._name(False)))
		self.assertTrue (os.path.exists("%s.%s.gz" % (exfile, p._name(False))))
		self.assertTrue (j.isExptCached())
		self.assertTrue (os.path.exists("%s/1.txt" % j.outdir))
		
		# gzip: dir
		p.output = "outdir:dir:dir-{{a}}"
		j.input  = {}
		j.output = {}
		j.init ()
		self.assertFalse (j.isExptCached())
		exfile = "%s/dir-1.%s" % (self.wdir, p._name(False))
		os.makedirs (exfile)
		self.assertTrue (os.path.isdir("%s" % exfile))
		os.system ("tar zcf %s.tgz %s/ -C %s . --warning=no-file-changed" % (exfile, exfile, self.wdir))
		self.assertTrue (os.path.exists("%s.tgz" % exfile))
		self.assertTrue (j.isExptCached())
		self.assertTrue (os.path.exists("%s/dir-1" % j.outdir))
		
		# other
		p.exhow  = "copy"
		p.input  = {"a": range(4)}
		p.output = "outfile:file:{{a}}.txt"
		p.props['length'] = 0
		p._buildInput()
		
		for i in range(4):
			j = job(i, p)
			j.input  = {}
			j.output = {}
			j.init ()
			exfile   = "%s/%s.txt" % (self.wdir, i)
			f = open (exfile, 'w')
			f.write('') # just test logs
			f.close()
			f = open ("%s/%s.txt" % (j.outdir, i), 'w')
			f.write('')
			f.close()
			self.assertTrue (j.isExptCached())
			self.assertTrue (os.path.islink("%s/%s.txt" % (j.outdir, i)))
		
		p.log ("test log")
	
	def testRc (self):
		p = proc('rc')
		p.ppldir = self.wdir
		p.input  = {"a":[1]}
		p.output = "xfile:file:{{a}}2"
		p.props['logger'] = self.logger
		p._buildProps()
		p._buildInput()
		j = job(0, p)
		j.init ()
		self.assertEqual (j.rc(), job.EMPTY_RC)
		j.rc (140)
		self.assertEqual (j.rc(), 140)
		j.rc (job.NOOUT_RC)
		self.assertEqual (j.rc(), -140)
		
		j.rc (0)
		self.assertEqual (j.rc(), 0)
		j.checkOutfiles ()
		self.assertEqual (j.rc(), job.NOOUT_RC)
		f = open(j.rcfile)
		rc = f.read()
		f.close()
		self.assertEqual (rc, "-0")
		self.assertFalse (j.succeed())
		
		j.rc (0)
		f = open (j.outdir + "/12", 'w')
		f.write('')
		f.close()
		j.checkOutfiles ()
		self.assertEqual (j.rc(), 0)
		self.assertTrue (j.succeed())
		
		
	def testExport (self):
		p = proc('export')
		p.ppldir = self.wdir
		p.input  = {"a":[1]}
		p.output = "xfile:file:{{a}}2.txt"
		p.props['logger'] = self.logger
		p._buildProps()
		p._buildInput()
		p.exdir  = self.wdir
		
		# gzip file
		p.exhow  = 'gzip'
		j = job(0, p)
		j.init ()
		f = open (j.outdir + "/12.txt", 'w')
		f.write('')
		f.close()
		j.export()
		self.assertTrue (os.path.exists(self.wdir + '/12.txt.%s.gz' % p._name(False)))
		
		# gzip folder
		p.output = "xfile:dir:dir-{{a}}"
		j.output = {}
		j.init ()
		j.export()
		self.assertTrue (os.path.exists(self.wdir + '/dir-1.%s.tgz' % p._name(False)))
		
		# copy file
		p.exhow  = "copy"
		p.output = "xfile:file:{{a}}2.txt"
		j.output = {}
		j.init ()
		f = open (j.outdir + "/12.txt", 'w')
		f.write('')
		f.close()
		j.export()
		self.assertTrue (os.path.isfile(self.wdir + '/12.txt'))
		self.assertTrue (os.path.isfile(j.outdir + '/12.txt'))
		
		# copy dir
		p.output = "xfile:dir:dir-{{a}}"
		j.output = {}
		j.init ()
		if not os.path.exists (j.outdir + "/dir-1"):
			os.makedirs (j.outdir + "/dir-1")
		j.export()
		self.assertTrue (os.path.isdir(self.wdir + '/dir-1'))
		self.assertTrue (os.path.isdir(j.outdir + '/dir-1'))
		
		# move
		p.exhow  = "mv"
		j.export()
		self.assertTrue (os.path.isdir(self.wdir + '/dir-1'))
		self.assertTrue (os.path.islink(j.outdir + '/dir-1'))
		
	def testReset (self):
		p = proc('reset')
		p.ppldir = self.wdir
		p.input  = {"a":[1]}
		p.output = "xfile:file:{{a}}2.txt"
		p.props['logger'] = self.logger
		p._buildProps()
		p._buildInput()
		j = job (0, p)
		j.init ()
		
		self.assertFalse (os.path.exists(j.rcfile))
		self.assertFalse (os.path.exists(j.outfile))
		self.assertFalse (os.path.exists(j.errfile))
		self.assertFalse (os.path.exists(j.outdir + '/12.txt'))
		f = open (j.rcfile, 'w')
		f.write('')
		f.close()
		f = open (j.outfile, 'w')
		f.write('')
		f.close()
		f = open (j.errfile, 'w')
		f.write('')
		f.close()
		f = open (j.outdir + '/12.txt', 'w')
		f.write('')
		f.close()
		self.assertTrue (os.path.exists(j.rcfile))
		self.assertTrue (os.path.exists(j.outfile))
		self.assertTrue (os.path.exists(j.errfile))
		self.assertTrue (os.path.exists(j.outdir + '/12.txt'))
		j.reset()
		self.assertFalse (os.path.exists(j.rcfile))
		self.assertFalse (os.path.exists(j.outfile))
		self.assertFalse (os.path.exists(j.errfile))
		self.assertFalse (os.path.exists(j.outdir + '/12.txt'))
		
	def testExpect (self):
		p = proc('expect')
		p.ppldir = self.wdir
		#p.cache = False
		p.input  = {"a":[1]}
		p.output = "xfile:file:{{a}}2.txt"
		p.script = "echo {{a}} > {{xfile}}"
		p.props['logger'] = self.logger
		p.run()
		j = job (0, p)
		self.assertEqual (j.rc(), 0)
		
		p.expect = "grep 1 {{xfile}}"
		p.props['suffix'] = ''
		p.run()
		j = job (0, p)
		self.assertEqual (j.rc(), 0)
		
		p.expect = "grep 2 {{xfile}}"
		p.props['suffix'] = ''
		try:
			p.run()
		except:
			pass
		j = job (0, p)
		self.assertEqual (j.rc(), -1000)
		
		
if __name__ == '__main__':
	unittest.main()
