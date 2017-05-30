import os, sys, unittest, pickle, shutil, copy
rootdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, rootdir)
from pyppl import proc, aggr
from pyppl import channel, utils
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
		
		self.assertTrue (callable (proc.runners['test'].submit))
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
				
		signature = pickle.dumps (config)
		self.assertEqual (len(p._suffix()), 8)

	def testInit (self):
		p = proc ('tag')
		self.assertTrue (isinstance (p, proc))

		from tempfile import gettempdir
		# check initial varialbles
		self.assertEqual (p.id, 'p')
		self.assertEqual (p.tag, 'tag')
		self.assertEqual (p.cachefile, 'cached.jobs')
		self.assertEqual (p.input, {})
		self.assertEqual (p.output, {})
		self.assertEqual (p.nexts, [])
		self.assertEqual (p.tmpdir, os.path.abspath("./workdir"))
		self.assertEqual (p.forks, 1)
		self.assertEqual (p.cache, True)
		self.assertEqual (p.retcodes, [0])
		self.assertEqual (p.echo, False)
		self.assertEqual (p.runner, 'local')
		self.assertEqual (p.exportdir, '')
		self.assertEqual (p.exporthow, 'move')
		self.assertEqual (p.exportow, True)
		self.assertEqual (p.errorhow, 'terminate')
		self.assertEqual (p.errorntry, 1)
		self.assertEqual (p.defaultSh, 'bash')
		self.assertEqual (p.beforeCmd, '')
		self.assertEqual (p.afterCmd, '')
		self.assertEqual (p.workdir, '')

	def testSetattr (self):
		p = proc ('tag')

		self.assertRaises (ValueError, p.__setattr__, 'a', 1)
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

		self.assertEqual (p.cachefile, "cached.jobs")

	def testIscached (self):
		p = proc ('iscached')
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
		
		p.input = {"a": [1,2,3,4,5]}
		#p._tidyBeforeRun()
		p.run()
		self.assertTrue (p._isCached())
		
		#open (p.workdir + '/scripts/script.3', 'w').write('')
		#self.assertFalse (p._isCached())
		#self.assertEqual (p.ncjobids, [3])
		
	def testExportCache (self):
		p = proc ('ec')
		p.cache = 'export'
		p.input = {"a": [1,2,3,4,5]}
		p.output = "outfile:file:{{a}}.txt"
		p._buildProps()
		p._buildInput()
		p._buildOutput()
		exdir   = p.outdir + '/export/'
		p.exdir = exdir
		if not os.path.isdir (exdir):
			os.makedirs (exdir)
		for i in [1,2,4,5]:
			open (exdir + "%s.txt" % i, 'w').write ('')
		self.assertFalse (p._isCached())
		self.assertEqual (p.ncjobids, [2]) # a==3
		
		

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
		self.assertEqual (p1.id, 'p1')
		self.assertEqual (p2.id, 'p2')
		
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
			"c2.dir": c2.collapse().map(lambda t: (os.path.realpath(t[0]), )).toList() * 2,
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
			"c2.dir": c2.collapse().map(lambda t: (os.path.realpath(t[0]), )).toList() * 2, 
			"c2.fn": c2.map(lambda x: x[0][:-3]).toList(), 
			"c2.ext": channel.create([".py", ".py"]).toList()
		})
	
	def testInputFiles (self):
		self.maxDiff = None
		c2 = channel.create([(["channel.unittest.py", "proc.unittest.py"], )])
		c1 = [([1,2,3,4], )]
		p2 = proc('if')
		p2.input = {"c1:var": c1, "c2:files": c2}
		p2._buildProps()
		p2._buildInput()
		self.assertEqual (p2.input, {
			'#': [0],
			"c1": [[1,2,3,4]], 
			"c2": [map(lambda x: os.path.join(p2.indir, x), y) for y in c2[0]],
			"c2.bn": [["channel.unittest.py", "proc.unittest.py"]], 
			"c2.dir": [[os.path.abspath(os.path.dirname(__file__)), os.path.abspath(os.path.dirname(__file__))]],
			"c2.fn": [["channel.unittest", "proc.unittest"]], 
			"c2.ext": [[".py"]*2]
		})

	def testBuildOutput (self):
		c1 = channel.create (["aa", "bb"])
		c2 = channel.create ([1, 2])
		c3 = channel.create (sorted(["channel.unittest.py", "proc.unittest.py"]))
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

		pOP.props['channel'] = channel()
		pOP.props['outfiles'] = []
		pOP.output = "{{c1}}, o2:var:{{c2 | __import__('math').pow(float(_), 2.0)}}, o3:file:{{c3.fn}}2{{c3.ext}}"
		pOP._buildProps()
		pOP._buildInput()
		pOP._buildOutput()

		self.assertEqual (pOP.output['__out.1__'], ['aa', 'bb'])
		self.assertEqual (pOP.output['o2'], ['1.0', '4.0'])
		self.assertEqual (pOP.output['o3'], [os.path.join(pOP.outdir, "channel.unittest2.py"), os.path.join(pOP.outdir, "proc.unittest2.py")])

		self.assertEqual (pOP.channel, [
			('aa', '1.0', os.path.join(pOP.outdir, "channel.unittest2.py")), 
			('bb', '4.0', os.path.join(pOP.outdir, "proc.unittest2.py"))
		])
		
		pOP.props['channel'] = channel()
		pOP.props['outfiles'] = []
		pOP.forks = 5

		d = ["cc:{{c1}}", "var:{{c2 | __import__('math').pow(float(_), 2.0)}}, file:{{c3.fn}}{{proc.forks}}{{c3.ext}}"]
		pOP.output = d
		pOP._buildProps()
		pOP._buildInput()
		pOP._buildOutput()
		self.assertEqual (pOP.output['cc'], ['aa', 'bb'])
		self.assertEqual (pOP.output['__out.1__'], ['1.0', '4.0'])
		self.assertEqual (pOP.output['__out.2__'], [os.path.join(pOP.outdir, "channel.unittest5.py"), os.path.join(pOP.outdir, "proc.unittest5.py")])
		
		self.assertEqual (pOP.channel, [
			('aa', '1.0', os.path.join(pOP.outdir, "channel.unittest5.py")), 
			('bb', '4.0', os.path.join(pOP.outdir, "proc.unittest5.py"))
		])


	def testBuildScript(self):
		ps = proc ('script')
		# empty script does not raise Exception any more
		#self.assertRaises (Exception, ps._tidyBeforeRun)
		ps.input = {"input": ["input"]}
		ps.script = "ls"
		
		ps._tidyBeforeRun()
		scriptdir = os.path.join (ps.workdir, 'scripts')
		self.assertTrue (os.path.exists(scriptdir))

		ps.script = "template:" + __file__ + '_notexist'
		self.assertRaises (Exception, ps._tidyBeforeRun)

		tplfile = os.path.join (rootdir, 'tests', 'script.tpl')
		with open (tplfile, 'w') as f:
			f.write ('#!/usr/bin/env bash\n')
		ps.script = "template:" + tplfile
		ps.props['jobs'] = []
		ps._tidyBeforeRun ()

		self.assertEqual (map(lambda x: x.script, ps.jobs), [os.path.join(scriptdir, 'script.0')])
		self.assertTrue (open(ps.jobs[0].script).read().startswith("#!/usr/bin/env bash"))
		os.remove (tplfile)

		with open (tplfile, 'w') as f:
			f.write ('ls\n') # add shebang
		ps.script = "template:" + tplfile
		ps.props['jobs'] = []
		ps._tidyBeforeRun ()

		self.assertEqual (map(lambda x: x.script, ps.jobs), [os.path.join(scriptdir, 'script.0')])
		self.assertTrue (open(ps.jobs[0].script).read().startswith("#!/usr/bin/env bash"))
		os.remove (tplfile)

		ps.output = "output:var:{{input}}2"
		ps.args   = {'var1': 1, 'var2': '2'}
		ps.script = "ls {{proc.workdir}}\necho {{#}} {{input}}\necho {{output}}\necho {{proc.args.var1}} {{proc.args.var2}}"
		ps.props['jobs'] = []
		ps._tidyBeforeRun ()
		self.assertEqual (map(lambda x: x.script, ps.jobs), [os.path.join(scriptdir, 'script.0')])
		self.assertEqual (open(ps.jobs[0].script).read(), "#!/usr/bin/env bash\n\nls %s\necho 0 input\necho input2\necho 1 2" % ps.workdir)




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

		prc.beforeCmd = 'ls'
		prc.echo = True
		prc._tidyBeforeRun ()
		self.assertEqual (prc._runCmd('beforeCmd'), 0)


		prc.afterCmd = 'bash -c "echo 2 >&2; exit 1"'
		prc.echo = False # anyway print stderr
		prc._tidyBeforeRun ()
		self.assertEqual (prc._runCmd('afterCmd'), 1)

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
		exdir    = "./test/"
		p = proc('export')
		p.input  = {"rc": [0,1,0,0]} # job #1 failed
		p.output = "outfile:file:{{#}}.txt"
		p.script = 'echo {{rc}} > {{outfile}}; exit {{rc}}'
		p.exdir  = exdir
		self.assertRaises(SystemExit, p.run)
		self.assertTrue (os.path.exists(exdir + "0.txt"))
		self.assertTrue (os.path.exists(exdir + "2.txt"))
		self.assertTrue (os.path.exists(exdir + "3.txt"))
		self.assertFalse (os.path.exists(exdir + "1.txt"))
		shutil.rmtree (exdir)
		
	
	def testCheckStatus (self):
		p = proc('cs')
		p.script = 'echo {#}'

		p.input  = {'infile:file': channel.fromPath ("*.py")}
		p.output = 'outfile:file:{{infile.fn}}2{{infile.ext}}, var:{{infile.fn}}2{{infile.ext}}'
		p._tidyBeforeRun ()
		p.exportdir = p.outdir + '/export'
		
		self.assertEqual (p.forks, 1)
		p._runJobs()
		# output file not generated
		self.assertRaises (SystemExit, p._checkStatus)

	def testDoCache (self):
		p = proc('cache')
		p.script = 'cp {{infile}} {{outfile}}'

		p.input  = {'infile:file': channel.fromPath ("*.py")}
		p.output = 'outfile:file:{{infile.fn}}2{{infile.ext}}, var:{{infile.fn}}2{{infile.ext}}'
		p._readConfig({})
		p._tidyBeforeRun()
		
		cachefile = os.path.join (p.workdir, p.cachefile)
		if os.path.exists (cachefile):
			os.remove (cachefile)			
		self.assertFalse (p._isCached())
		p._runJobs()
		p._tidyAfterRun()
		self.assertTrue (p._isCached())

	def testCopy (self):
		p = proc('copy')
		p.script = 'echo {#}'

		p.exportdir = rootdir

		pCopy = p.copy('procCopy')
		self.assertEqual (pCopy.id, 'pCopy')
		self.assertEqual (pCopy.tag, 'procCopy')
		self.assertEqual (pCopy.exportdir, rootdir)
		self.assertEqual (pCopy.script, p.script)
		
	def testAlias (self):
		p = proc ('alias')
		p.input = {'a':[1]}
		testv = {}
		for k,v in proc.alias.iteritems():
			testv[v] = utils.randstr()
			if v == 'retcodes': testv[v] = [0,1,2]
			p.__setattr__ (k, testv[v])
		p._tidyBeforeRun()
		for k,v in proc.alias.iteritems():
			val1 = p.__getattr__(k)
			val2 = p.__getattr__(v)
			self.assertEqual (val1, testv[v])
			self.assertEqual (val2, testv[v])
			
	def testScriptTpl (self):
		p = proc('tpl')
		p.input  = {"a":[1]}
		p.script = "template:a.py"
		self.assertRaises(ValueError, p._buildScript)
		cwd      = os.path.dirname (os.path.abspath(__file__))
		tplfile  = os.path.join (cwd, "test", "a.py")
		if not os.path.exists(os.path.join(cwd, "test")):
			os.makedirs (os.path.join(cwd, "test"))
		open (tplfile, "w").write ("ls")
		p.script = "template:test/a.py"
		p.run()
		sfile    = os.path.join (p.workdir, "scripts", "script.0")
		self.assertEqual (open(sfile).read().strip(), "#!/usr/bin/env bash\n\nls")
		
		p.script = "template:../tests/test/a.py"
		p.run()
		self.assertEqual (open(sfile).read().strip(), "#!/usr/bin/env bash\n\nls")
		
		tplfile  = os.path.abspath(tplfile)
		p.script = "template:%s" % tplfile
		p.run()
		self.assertEqual (open(sfile).read().strip(), "#!/usr/bin/env bash\n\nls")
		
		shutil.rmtree (os.path.join(cwd, "test"))

if __name__ == '__main__':
	unittest.main()
