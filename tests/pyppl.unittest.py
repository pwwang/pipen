"""
Test module pyppl
"""
import os
import shutil
import sys
from time import sleep
import unittest
import warnings
warnings.filterwarnings("ignore")

rootdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, rootdir)
from pyppl import aggr, channel, proc, pyppl, utils

class TestPipelineMethods (unittest.TestCase):

	def tearDown (self):
		try:
			if os.path.exists ('./workdir'):
				#shutil.rmtree ('./workdir')
				pass
		except:
			sleep (1)
			self.tearDown()
	
	def test_init (self):
		ppl = pyppl({}, '')

		self.assertTrue (isinstance(ppl, pyppl))
		self.assertEqual (ppl.config, {})
		self.assertEqual (ppl.heads, [])
	
	def test_factory (self):
	
		ppl = pyppl ({'proc' : {'ppldir': './workdir'}})
		
		p1 = proc('TAG')
		self.assertTrue (isinstance (p1, proc))
		self.assertEqual (p1.tag, 'TAG')
		
		inch = channel.create(['a', 'b', 'c'])
		p1.tag = 'CREATE_FILE'
		p1.input = {'input':inch}
		p1.script = "echo {{input}} > {{outfile}}"
		p1.output = "o:{{input}}, outfile:file:{{input}}.txt"
		p1.cache  = False
		
		p2 = proc("MOVE_FILE")
		p2.input     = "input, infile:file"
		p2.output    = "outfile:file:{{infile | fn}}-2.txt"
		p2.script    = "mv {{infile}} {{outfile}}; cp {{outfile}} {{infile}}"
		p2.depends   = p1
		p2.exportdir = './workdir'
		p2.cache     = False
		p2.forks     = 3
		ppl.starts (p1)
		
		ppl.run()
		
		self.assertTrue (os.path.exists('./workdir/a-2.txt'))
		self.assertTrue (os.path.exists('./workdir/b-2.txt'))
		self.assertTrue (os.path.exists('./workdir/c-2.txt'))
		
	
	def test_dot (self):
		self.maxDiff = None
		ppl = pyppl ()
		p1 = proc("A")
		p2 = proc("B")
		p3 = proc("C")
		p4 = proc("D")
		p5 = proc("E")
		p6 = proc("F")
		p7 = proc("G")
		p8 = proc("H")
		p9 = proc("I")
		p1.script = "echo 1"
		p1.input  = {"input": channel.create(['a'])}
		p8.input  = {"input": channel.create(['a'])}
		p9.input  = {"input": channel.create(['a'])}
		p2.input  = "input"
		p3.input  = "input"
		p4.input  = "input"
		p5.input  = "input"
		p6.input  = "input"
		p7.input  = "input"
		p1.output = "{{input}}" 
		p2.script = "echo 1"
		p2.output = "{{input}}" 
		p3.script = "echo 1"
		p3.output = "{{input}}" 
		p4.script = "echo 1"
		p4.output = "{{input}}" 
		p5.script = "echo 1"
		p5.output = "{{input}}" 
		p6.script = "echo 1"
		p6.output = "{{input}}" 
		p7.script = "echo 1"
		p7.output = "{{input}}" 
		p8.script = "echo 1"
		p8.output = "{{input}}" 
		p9.script = "echo 1"
		p9.output = "{{input}}" 
		
		"""
					   1A         8H
					/      \      /
				 2B           3C
				    \      /
					  4D(e)       9I
					/      \      /
				 5E          6F(e)
				    \      /
					  7G(e)
		"""
		p2.depends = p1
		p3.depends = [p1, p8]
		p4.depends = [p2, p3]
		p4.exportdir  = "./"
		p5.depends = p4
		p6.depends = [p4, p9]
		p6.exportdir  = "./"
		p7.depends = [p5, p6]
		p7.exportdir  = "./"
		ppl.starts(p1, p8, p9).flowchart("/tmp/pyppl.flowchart.dot", None, "")
		with open("/tmp/pyppl.flowchart.dot") as f:
			self.assertEqual(sorted(f.read().strip().split("\n")), 
sorted("""digraph PyPPL {
	"p1.A" -> "p2.B"
	"p1.A" -> "p3.C"
	"p8.H" -> "p3.C"
	"p2.B" -> "p4.D"
	"p3.C" -> "p4.D"
	"p4.D" -> "p5.E"
	"p4.D" -> "p6.F"
	"p9.I" -> "p6.F"
	"p5.E" -> "p7.G"
	"p6.F" -> "p7.G"
	"p6.F" [shape=box, style=filled, color="#f0f998", fontcolor=red]
	"p1.A" [shape=box, style=filled, color="#c9fcb3" ]
	"p8.H" [shape=box, style=filled, color="#c9fcb3" ]
	"p9.I" [shape=box, style=filled, color="#c9fcb3" ]
	"p7.G" [shape=box, style=filled, color="#fcc9b3" fontcolor=red]
	"p4.D" [shape=box, style=filled, color="#f0f998", fontcolor=red]
}""".split("\n")))
	
	def test_multideps (self):
		ppl = pyppl ()
		pr1 = proc("A")
		pr2 = proc("B")
		pr3 = proc("C")
		
		p1ch = [('a',), ('b',), ('c',)]
		p2ch = [(1,), (2,), (3,)]
		pr1.input = {'input': channel.create(p1ch)}
		pr2.input = {'input': channel.create(p2ch)}
		pr1.output = 'o:{{input}}'
		pr2.output = 'o:{{input}}'
		pr3.input = 'in1, in2'
		pr3.output = 'o:{{in1}}{{in2}}'
		pr3.depends = [pr1, pr2]

		pr1.script = "echo {{input}}"
		pr2.script = "echo {{input}}"
		pr3.script = "echo {{in1}}{{in2}}"
		#pr3.echo   = True
		#p1.echo = True
		#p2.echo = True
		#p3.echo = True
		#print p3.props['indata'], 'xxxxxxxxxxxxxxxxxxxxxxx'
		ppl.starts(pr1, pr2).run()
		
		out1 = os.path.join(pr3.workdir, '0/job.stdout')
		out2 = os.path.join(pr3.workdir, '1/job.stdout')
		out3 = os.path.join(pr3.workdir, '2/job.stdout')
		self.assertTrue (os.path.exists(out1))
		self.assertTrue (os.path.exists(out2))
		self.assertTrue (os.path.exists(out3))
		with open(out1) as f:
			self.assertEqual (f.read().strip(), 'a1')
		with open(out2) as f:
			self.assertEqual (f.read().strip(), 'b2')
		with open(out3) as f:
			self.assertEqual (f.read().strip(), 'c3')
		
	@unittest.skip('')
	def test_sge (self):
		ppl = pyppl ()
		p1 = proc ()
		p1.input = {"input": channel.create([('a')] * 10)}
		p1.workdir = './workdir'
		p1.forks = 3
		p1.script = "echo {input}"
		ppl.starts(p1).run('sge')
	
	@unittest.skip('')
	def test_batchjobs (self):
		p = proc ('batch')
		p.input = {'input': channel.create(range(10))}
		p.script = "cat {{proc.workdir}}/{{#}}/job.script.ssh | grep franklin; sleep 3"
		p.echo = True
		p.cache = False
		p.forks = 3
		#p.errorhow = 'retry'
		#p.runner = 'ssh'
		p.beforeCmd = 'mkdir ./workdir/test_batchjobs -p'
		p.tmpdir = './workdir/test_batchjobs'
		pyppl({
			'proc': {
				'sshRunner': {	
					'servers': ['franklin01', 'franklin02', 'franklin03', 'franklin04', 'franklin05', 'franklin06', 'franklin07', 'franklin08']
				}
			},
			'loglevels': 'all'
		}).starts(p).run('ssh')
		shutil.rmtree ('./workdir/test_batchjobs')
	
	def testCallback (self):
		p1 = proc ('callback')
		p2 = proc ('callback')
		
		def callback2 (s):
			ch = channel.create ([('a1','b'), ('x', 'y')])
			s.channel.merge (ch)
		argv     = sys.argv[:]
		sys.argv = ['0', '1', '2']
		p1.input = {"input": channel.fromArgv()}
		p1.output = "output:{{input}}2"
		p1.script = "echo {{output}}"
		p1.callback = callback2
		p2.depends = p1
		p2.input = "input, in1, in2"
		p2.script = "echo {{output}}"
		p2.output = "output:{{input}}.{{in1}}.{{in2}}"
		pyppl ().starts(p1).run()
		sys.argv  = argv[:]
	
	def testAggr (self):
		pa = proc ('aggr')
		pb = proc ('aggr')
		pa.script = 'echo 1'
		pb.script = 'echo 2'
		a  = aggr (pa, pb)
		pe = proc('end')
		pe.depends = a
		a.pa.input  = "input"
		a.pa.output = "out:{{input}}.{{proc.id}}.{{proc.tag}}"
		a.pb.input  = "input"
		a.pb.output = "out:{{input}}.{{proc.id}}.{{proc.tag}}"
		a.input          = ["AGGR"]
		pe.input         = "input"
		pe.output        = "out:{{input}}.{{proc.id}}.{{proc.tag}}"
		self.assertRaises (SystemExit,pyppl().starts(a).run)
		self.assertEqual (pe.channel, [('AGGR.pa.%s.pb.%s.pe.end' % (utils.uid(a.id, 4), utils.uid(a.id, 4)),)])
		
	def testConfig (self):
		config = {
			'proc': {},
			'sge': {'runner': 'ssh', 'sshRunner': {'servers':['franklin01']}},
			'ssh2': {'runner': 'local'},
			'ssh': {'sshRunner': {'servers':['franklin01']}}
		}
		p = proc()
		p.script = "echo 1"
		p.input = {'a':[1]}
		pyppl (config, '').starts(p).run()
		self.assertEqual (p.runner, 'local')
		pyppl (config, '').starts(p).run('ssh')
		self.assertEqual (p.runner, 'ssh')
		pyppl (config, '').starts(p).run('ssh2')
		self.assertEqual (p.runner, 'local')
		pyppl (config, '').starts(p).run('sge')
		self.assertEqual (p.runner, 'ssh')
		
	
	# To test if comment out the @skip statement
	# run: python pyppl.unittest.py TestPipelineMethods.testIsRunning
	# and then CTRL+C to quite the main thread
	# run it again see whether it shows job is already running
	@unittest.skip('')
	def testIsRunning (self):
		pIsRunning = proc ()
		pIsRunning.input  = {"a": [1,2,3,4,5]}
		pIsRunning.script = "sleep 5"  # takes time to start
		pIsRunning.runner = "sge"
		pIsRunning.forks  = 5
		
		pyppl ().starts(pIsRunning).run()
		
	@unittest.skip('')	
	def testFlushFile (self):
		pFF = proc ()
		pFF.input = {"input": [1]}
		pFF.script = """
		for i in $(seq 1 60); do
		echo $i
		sleep 1
		done
		"""
		pFF.echo  = True
		
		pyppl().starts(pFF).run('sge')
		
	def testError (self):
		pError = proc ()
		pError.input  = {"input": [1]}
		pError.output = "outfile:file:a.txt"
		pError.script = "echo {{input}} > {{outfile}}; exit $(($RANDOM % 3))"
		pError.errhow = "retry"
		pError.errntry= 10
		pError.cache  = False
		pyppl().starts(pError).run()
		
	def testIgnore (self):
		pIgnore = proc ()
		pIgnore.input  = {"input": [1]}
		pIgnore.output = "outfile:file:a.txt"
		pIgnore.script = "echo {{input}} > {{outfile}}; exit $(($RANDOM % 4))"
		pIgnore.errhow = "ignore"
		pIgnore.cache  = False
		pyppl().starts(pIgnore).run()
		
	def testBrings (self):
		tdir = "./workdir/"
		if not os.path.exists (tdir):
			os.makedirs(tdir)
		if not os.path.exists ("./workdir/aaa"):
			os.makedirs ("./workdir/aaa")
		infile = os.path.abspath("./workdir/aaa/1.txt")
		with open (infile, 'w') as f:
			f.write('')
		if not os.path.exists ("./workdir/1.txt"):
			os.symlink (infile, os.path.abspath("./workdir/1.txt"))
		brfile = "./workdir/aaa/1.txi"
		with open (brfile, 'w') as f:
			f.write('')
		pBrings = proc ()
		pBrings.script = "echo 1"
		pBrings.input  = {"infile:file": ["./workdir/1.txt"]}
		pBrings.brings = {"infile": "{{infile | fn}}.txi"}
		pyppl().starts(pBrings).run()
		self.assertTrue (os.path.exists( os.path.join(pBrings.jobs[0].indir, "1.txi") ))
		
	def testEcho(self):
		pFalse = proc(desc = 'Echo off')
		pFalse.echo = False
		pFalse.forks = 2
		pFalse.input = {'in': [0, 1]}
		pFalse.output = 'out:{{in}}'
		pFalse.script = """
		echo STDOUT:{{in}}
		echo STDERR:{{in}} 1>&2
		"""
		
		pTrue = proc(desc = 'Echo on')
		pTrue.echo = True
		pTrue.forks = 2
		pTrue.depends = pFalse
		pTrue.input = 'in'
		pTrue.output = 'out:{{in}}'
		pTrue.script = """
		echo STDOUT:{{in}}
		echo STDERR:{{in}} 1>&2
		"""
		
		pJobs = proc(desc = 'Echo jobs')
		pJobs.echo = {'jobs': [0, 1]}
		pJobs.forks = 2
		pJobs.depends = pTrue
		pJobs.input = 'in'
		pJobs.output = 'out:{{in}}'
		pJobs.script = """
		echo STDOUT:{{in}}
		echo STDERR:{{in}} 1>&2
		"""
		
		pStderrOnly = proc(desc = 'Echo StderrOnly')
		pStderrOnly.echo = 'stderr'
		pStderrOnly.forks = 2
		pStderrOnly.depends = pJobs
		pStderrOnly.input = 'in'
		pStderrOnly.output = 'out:{{in}}'
		pStderrOnly.script = """
		echo STDOUT:{{in}}
		echo STDERR:{{in}} 1>&2
		"""
		
		pFilter = proc(desc = 'Echo filtered')
		pFilter.echo = {'filter': r'ERR'}
		pFilter.forks = 2
		pFilter.depends = pStderrOnly
		pFilter.input = 'in'
		pFilter.output = 'out:{{in}}'
		pFilter.script = """
		echo STDOUT:{{in}}
		echo STDERR:{{in}} 1>&2
		"""
		
		pLog = proc(desc = 'Echo log')
		pLog.echo = False
		pLog.forks = 2
		pLog.depends = pFilter
		pLog.input = 'in'
		pLog.output = 'out:{{in}}'
		pLog.script = """
		echo STDOUT:{{in}}
		echo pyppl.log.hhh:{{in}} 1>&2
		echo pyppl.log:The log 1>&2
		"""
		
		
		pyppl().starts(pFalse).run()
		
	def testJobExportLock(self):
		p = proc('jobexportlock')
		p.input  = {'in': range(20)}
		p.output = "outfile:file:a.txt"
		p.forks  = 20
		p.script = """
		if [[ {{#}} -eq 0 ]]; then
			touch {{outfile}}
		else
			ln -s {{proc.workdir}}/0/output/a.txt {{outfile}}
		fi
		"""
		p.exdir = './workdir'
		pyppl().starts(p).run()

if __name__ == '__main__':
	unittest.main()
