import os, sys, unittest, pickle, shutil, copy
rootdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, rootdir)
from pyppl import proc
from pyppl import channel
from md5 import md5
from StringIO import StringIO
from inspect import getsource

class TestProc (unittest.TestCase):

	def testRegisterRunner (self):
		testfile = os.path.join(rootdir, 'tests', 'runner_test.py')
		with open(testfile, 'w') as f:
			f.write ("""import os, sys
rootdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(rootdir)
from pyppl import runner_local
class runner_test (runner_local):

	def __init__ (self, script, config = {}):
		pass
"""			)
		self.assertTrue (os.path.exists(testfile))
		from runner_test import runner_test
		proc.registerRunner(runner_test)
		
		self.assertTrue (callable (proc.runners['test'].run))
		os.remove (testfile)
		try: 
			os.remove (testfile + 'c')
		except:
			pass
		self.assertFalse (os.path.exists (testfile))

	def testSuffix (self):
		p = proc ('tag_unique')
		config = copy.copy(p.config)
		del config['workdir']
		def getFuncSig (func):
			if callable (func):
				try:
					sig = getsource(func)
				except:
					sig = func.__name__
			else:
				sig = 'None'
			return sig
				
		if config.has_key ('callback'):
			config['callback'] = getFuncSig(config['callback'])
	
		if config.has_key ('callfront'):
			config['callfront'] = getFuncSig(config['callfront'])
		
		if config.has_key ('input') and isinstance(config['input'], dict):
			config['input'] = copy.deepcopy(config['input'])
			for key, val in config['input'].iteritems():
				config['input'][key] = getFuncSig(val) if callable(val) else val
		signature = pickle.dumps (config) + '@' + pickle.dumps(sorted(sys.argv))
		self.assertEqual (p._suffix(), md5(signature).hexdigest()[:8])

	def testInit (self):
		p = proc ('tag')
		self.assertTrue (isinstance (p, proc))

		from tempfile import gettempdir
		# check initial varialbles
		self.assertEqual (p.id, 'p')
		self.assertEqual (p.tag, 'tag')
		self.assertEqual (p.cachefile, '')
		self.assertEqual (p.input, {})
		self.assertEqual (p.output, {})
		self.assertEqual (p.nexts, [])
		self.assertEqual (p.tmpdir, gettempdir())
		self.assertEqual (p.forks, 1)
		self.assertEqual (p.cache, True)
		self.assertEqual (p.retcodes, [0])
		self.assertEqual (p.echo, False)
		self.assertEqual (p.runner, 'local')
		self.assertEqual (p.exportdir, '')
		self.assertEqual (p.exporthow, 'copy')
		self.assertEqual (p.exportow, True)
		self.assertEqual (p.errorhow, 'terminate')
		self.assertEqual (p.errorntry, 1)
		self.assertEqual (p.defaultSh, 'bash')
		self.assertEqual (p.beforeCmd, '')
		self.assertEqual (p.afterCmd, '')
		self.assertEqual (p.workdir, '')

	def testSetattr (self):
		p = proc ('tag')

		self.assertRaises (AttributeError, p.__setattr__, 'a', 1)
		p. tag = 'notag'
		self.assertEqual (p.tag, 'notag')
		self.assertEqual (p.config['tag'], 'notag')
		self.assertEqual (p.sets, ['tag'])

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

		self.assertEqual (p.cachefile, "PyPPL.%s.%s.%s.cache" % (
			p.id,
			p.tag,
			p._suffix()
		))

	def testIscached (self):
		p = proc ('tag')
		p.cache = False
		self.assertFalse (p._isCached())
		p.cache = True
		config = {"forks": 100}
		p._readConfig(config)
		cachefile = os.path.join (p.tmpdir, p.cachefile)
		try:
			os.remove (cachefile)
		except:
			pass
		self.assertFalse (p._isCached())
		with open (cachefile, 'w') as f:
			pickle.dump(config, f)
		self.assertTrue (p._isCached())
		self.assertEqual (p.forks, 100)

	def testBuildProps (self):
		p1 = proc ('tag1')
		p2 = proc ('tag')
		p2.depends = p1
		p2.retcodes = "0, 1"
		if os.path.exists (p2.workdir):
			shutil.rmtree(p2.workdir)
		p2._buildProps()
		self.assertEqual (p2.depends, [p1])
		self.assertEqual (p2.retcodes, [0, 1])
		self.assertTrue (os.path.exists(p2.workdir))
		self.assertEqual (p1.nexts, [p2])
		p2 = proc('tag')
		self.assertRaises (Exception, p2._buildProps)


	def testBuildInput (self):
		self.maxDiff = None
		p1 = proc('tag1')
		p1.props['channel'] = [("aa", 1), ("bb", 2)]

		p2 = proc('tag2')
		p2.depends = p1
		
		p2.input   = ["char", "number"]
		p2._buildProps()
		p2._buildInput()
		self.assertEqual (p2.input, {"char": ["aa", "bb"], '#': [0, 1], "number": [1, 2]})

		p2.input   = "c, n"
		p2._buildProps()
		p2._buildInput()
		self.assertEqual (p2.input, {"c": ["aa", "bb"], '#': [0, 1], "n": [1, 2]})

		c1 = channel.create (["aa", "bb"])
		c2 = channel.create ([1, 2])
		p2.input   = {"x": c1, "y": c2}
		p2._buildProps()
		p2._buildInput()
		self.assertEqual (p2.input, {"x": ["aa","bb"], '#': [0, 1], "y": [1, 2]})

		p2.input   = {"a,b": channel.fromChannels(c1,c2)}
		p2._buildProps()
		p2._buildInput()
		self.assertEqual (p2.input, {"a": ["aa", "bb"], "b": [1, 2], '#': [0, 1]})
		
		p2.tag = "file"
		
		c2 = channel.create (sorted(["channel.unittest.py", "proc.unittest.py"]))
		c1 = c2.map (lambda x: x[0][:-12])
		
		p2.input   = {"c1, c2:file": channel.fromChannels(c1, c2)}
		p2._buildProps()
		p2._buildInput()
		self.assertEqual (p2.input, {
			'#': [0, 1],
			"c1": ["channel","proc"], 
			"c2": c2.map(lambda x: os.path.join(p2.indir, x[0])).toList(), 
			"c2.bn": c2.toList(), 
			"c2.fn": c2.map(lambda x: x[0][:-3]).toList(), 
			"c2.ext": [".py", ".py"]
		})
		
		p2.tag   = 'varfile'
		p2.input = {"c1:var": c1, "c2:file": c2}
		p2._buildProps()
		p2._buildInput()
		self.assertEqual (p2.input, {
			'#': [0, 1],
			"c1": ["channel","proc"], 
			"c2": c2.map(lambda x: os.path.join(p2.indir, x[0])).toList(), 
			"c2.bn": c2.toList(), 
			"c2.fn": c2.map(lambda x: x[0][:-3]).toList(), 
			"c2.ext": channel.create([".py", ".py"]).toList()
		})

	def testBuildOutput (self):
		c1 = channel (["aa", "bb"])
		c2 = channel ([1, 2])
		c3 = channel (sorted(["channel.unittest.py", "proc.unittest.py"]))
		pOP = proc()
		pOP.input = {'c1': c1, 'c2': c2, 'c3:file': c3}
		
		pOP.output = ["o1:var:{{c1}}", "o2:var:{{c2 | __import__('math').pow(float(_), 2.0)}}", "o3:file:{{c3.fn}}2{{c3.ext}}"]
		pOP._buildProps()
		pOP._buildInput()
		pOP._buildOutput()
		self.assertEqual (pOP.output['o1'], ['aa', 'bb'])

		self.assertEqual (pOP.output['o2'], ['1.0', '4.0'])
		self.assertEqual (pOP.output['o3'], [os.path.join(pOP.outdir, "channel.unittest2.py"), os.path.join(pOP.outdir, "proc.unittest2.py")])
		self.assertEqual (pOP.channel, [
			('aa', '1.0', os.path.join(pOP.outdir, "channel.unittest2.py")), 
			('bb', '4.0', os.path.join(pOP.outdir, "proc.unittest2.py"))
		])
		self.assertEqual (pOP.outfiles, pOP.output['o3'])

		pOP.props['channel'] = channel()
		pOP.props['outfiles'] = []
		pOP.output = "{{c1}}, o2:var:{{c2 | __import__('math').pow(float(_), 2.0)}}, o3:file:{{c3.fn}}2{{c3.ext}}"
		pOP._buildProps()
		pOP._buildInput()
		pOP._buildOutput()
		self.assertEqual (pOP.output['__out1__'], ['aa', 'bb'])
		self.assertEqual (pOP.output['o2'], ['1.0', '4.0'])
		self.assertEqual (pOP.output['o3'], [os.path.join(pOP.outdir, "channel.unittest2.py"), os.path.join(pOP.outdir, "proc.unittest2.py")])

		self.assertEqual (pOP.channel, [
			('aa', '1.0', os.path.join(pOP.outdir, "channel.unittest2.py")), 
			('bb', '4.0', os.path.join(pOP.outdir, "proc.unittest2.py"))
		])
		self.assertEqual (pOP.outfiles, pOP.output['o3'])
		
		pOP.props['channel'] = channel()
		pOP.props['outfiles'] = []
		pOP.forks = 5
		c1 = channel()
		c2 = channel()
		d = [("cc:{{c1}}", c1), ("var:{{c2 | __import__('math').pow(float(_), 2.0)}}, file:{{c3.fn}}{{proc.forks}}{{c3.ext}}", c2)]
		pOP.output = d
		pOP._buildProps()
		pOP._buildInput()
		pOP._buildOutput()
		self.assertEqual (pOP.output['cc'], ['aa', 'bb'])
		self.assertEqual (pOP.output['__out1__'], ['1.0', '4.0'])
		self.assertEqual (pOP.output['__out2__'], [os.path.join(pOP.outdir, "channel.unittest5.py"), os.path.join(pOP.outdir, "proc.unittest5.py")])
		
		self.assertEqual (c1, [('aa',), ('bb', )])
		self.assertEqual (c2, [
			('1.0', os.path.join(pOP.outdir, "channel.unittest5.py")), 
			('4.0', os.path.join(pOP.outdir, "proc.unittest5.py"))
		])
		self.assertEqual (pOP.channel, [
			('aa', '1.0', os.path.join(pOP.outdir, "channel.unittest5.py")), 
			('bb', '4.0', os.path.join(pOP.outdir, "proc.unittest5.py"))
		])
		self.assertEqual (pOP.outfiles, pOP.output['__out2__'])


	def testBuildScript(self):
		ps = proc ('script')
		self.assertRaises (Exception, ps._tidyBeforeRun)
		ps.input = {"input": ["input"]}
		ps.script = "ls"
		scriptdir = os.path.join (ps.workdir, 'scripts')
		if os.path.exists (scriptdir):
			shutil.rmtree (scriptdir)
		ps._tidyBeforeRun()
		self.assertTrue (os.path.exists(scriptdir))

		ps.script = "template:" + __file__ + '_notexist'
		self.assertRaises (Exception, ps._tidyBeforeRun)

		tplfile = os.path.join (rootdir, 'tests', 'script.tpl')
		with open (tplfile, 'w') as f:
			f.write ('#!/usr/bin/env bash\n')
		ps.script = "template:" + tplfile
		ps.props['jobs'] = []
		ps._tidyBeforeRun ()

		self.assertEqual (ps.jobs, [os.path.join(scriptdir, 'script.0')])
		self.assertTrue (open(ps.jobs[0]).read().startswith("#!/usr/bin/env bash"))
		os.remove (tplfile)

		with open (tplfile, 'w') as f:
			f.write ('ls\n') # add shebang
		ps.script = "template:" + tplfile
		ps.props['jobs'] = []
		ps._tidyBeforeRun ()

		self.assertEqual (ps.jobs, [os.path.join(scriptdir, 'script.0')])
		self.assertTrue (open(ps.jobs[0]).read().startswith("#!/usr/bin/env bash"))
		os.remove (tplfile)

		ps.output = "output:var:{{input}}2"
		ps.args   = {'var1': 1, 'var2': '2'}
		ps.script = "ls {{proc.workdir}}\necho {{#}} {{input}}\necho {{output}}\necho {{proc.args.var1}} {{proc.args.var2}}"
		ps.props['jobs'] = []
		ps._tidyBeforeRun ()
		self.assertEqual (ps.jobs, [os.path.join(scriptdir, 'script.0')])
		self.assertEqual (open(ps.jobs[0]).read(), "#!/usr/bin/env bash\n\nls %s\necho 0 input\necho input2\necho 1 2" % ps.workdir)




	def testRunCmd (self):
		prc = proc ()
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

		saved_stdout = sys.stdout
		try:
			out = StringIO()
			sys.stdout = out
			prc.beforeCmd = 'ls'
			prc.echo = True
			prc._tidyBeforeRun ()
			self.assertEqual (prc._runCmd('beforeCmd'), 0)
			self.assertTrue ("proc.unittest.py" in out.getvalue())
		finally:
			sys.stdout = saved_stdout

		saved_stderr = sys.stderr
		try:
			out = StringIO()
			sys.stderr = out
			prc.afterCmd = 'bash -c "echo 2 >&2; exit 1"'
			prc.echo = False # anyway print stderr
			prc._tidyBeforeRun ()
			self.assertEqual (prc._runCmd('afterCmd'), 1)
			self.assertTrue ("2" in out.getvalue())
		finally:
			sys.stderr = saved_stderr

	def testRunJobs (self):
		pr = proc()
		pr.script = 'echo {{#}}'
		pr.input  = {'input': range(3)}
		pr._tidyBeforeRun ()
		
		self.assertEqual (pr.length, 3)
		self.assertEqual (pr.forks, 1)

		pr._runJobs()
		for i in range(3):
			self.assertTrue (os.path.exists( os.path.join(pr.workdir, 'scripts', 'script.%s' % i) ))
			self.assertTrue (os.path.exists( os.path.join(pr.workdir, 'scripts', 'script.%s.stderr' % i) ))
			self.assertTrue (os.path.exists( os.path.join(pr.workdir, 'scripts', 'script.%s.stdout' % i) ))
			self.assertTrue (os.path.exists( os.path.join(pr.workdir, 'scripts', 'script.%s.rc' % i) ))
			self.assertEqual (open( os.path.join(pr.workdir, 'scripts', 'script.%s.stdout' % i)).read().strip(), str(i))
		
	def testExport (self):
		p = proc('export')
		p.script = 'cp {{infile}} {{outfile}}'

		p.input  = {'infile:file': channel.fromPath ("*.py")}
		p.output = 'outfile:file:{{infile.fn}}2{{infile.ext}}, var:{{infile.fn}}2{{infile.ext}}'
		p.exportdir = rootdir
		p._tidyBeforeRun ()
		
		self.assertEqual (p.forks, 1)

		p._runJobs()
		p._export()
		for (_, bn) in p.channel:
			exfile = os.path.join (rootdir, bn)
			self.assertTrue (os.path.exists (exfile))
			os.remove(exfile)
	
	def testCheckStatus (self):
		p = proc('cs')
		p.script = 'echo {#}'

		p.input  = {'infile:file': channel.fromPath ("*.py")}
		p.output = 'outfile:file:{{infile.fn}}2{{infile.ext}}, var:{{infile.fn}}2{{infile.ext}}'
		p.exportdir = rootdir
		p._tidyBeforeRun ()
		
		self.assertEqual (p.forks, 1)
		p._runJobs()
		self.assertRaises (Exception, p._checkStatus)

	def testDoCache (self):
		p = proc('cache')
		p.script = 'cp {{infile}} {{outfile}}'

		p.input  = {'infile:file': channel.fromPath ("*.py")}
		p.output = 'outfile:file:{{infile.fn}}2{{infile.ext}}, var:{{infile.fn}}2{{infile.ext}}'
		p._readConfig({})
		cachefile = os.path.join (p.tmpdir, p.cachefile)
		if os.path.exists (cachefile):
			self.assertTrue (p._isCached())
			#os.utime (p.infiles[0], None)
			#self.assertFalse (p._isCached())
		else:			
			self.assertFalse (p._isCached())
			p._tidyBeforeRun()
			p._runJobs()
			p._tidyAfterRun()

	def testCopy (self):
		p = proc('copy')
		p.script = 'echo {#}'

		p.exportdir = rootdir

		pCopy = p.copy('procCopy')
		self.assertEqual (pCopy.pid, 'pCopy')
		self.assertEqual (pCopy.tag, 'procCopy')
		self.assertEqual (pCopy.exportdir, rootdir)
		self.assertEqual (pCopy.script, p.script)

	

if __name__ == '__main__':
	unittest.main()
