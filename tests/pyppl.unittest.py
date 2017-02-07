import unittest, tempfile, sys, pickle, os, shutil
rootdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, rootdir)
from md5 import md5
from multiprocessing import cpu_count
from pyppl import pyppl
from pyppl import proc
from pyppl import channel

class TestPipelineMethods (unittest.TestCase):

	def test_init (self):
		ppl = pyppl()

		self.assertTrue (isinstance(ppl, pyppl))
		self.assertEqual (ppl.config, {})
		self.assertEqual (ppl.heads, [])
	
	def test_factory (self):
		ppl = pyppl ({'proc' : {'tmpdir': '/local2/tmp/m161047/abc'}})
		
		p1 = proc('TAG')
		self.assertTrue (isinstance (p1, proc))
		self.assertEqual (p1.tag, 'TAG')

		inch = channel(['a', 'b', 'c'])
		p1.tag = 'CREATE_FILE'
		p1.input = {'input':inch}
		p1.script = "echo {{input}} > {{outfile}}"
		p1.output = "{{input}}, outfile:file:{{input}}.txt"
		p1.cache  = False

		p2 = proc("MOVE_FILE")
		p2.input = "input, infile:file"
		p2.output = "outfile:file:{{infile.fn}}-2.txt"
		p2.script = "mv {{infile}} {{outfile}}"
		p2.depends = p1
		p2.exportdir = './'
		p2.cache  = False

		ppl.starts (p1)
		ppl.run()

		self.assertTrue (os.path.exists('./a-2.txt'))
		self.assertTrue (os.path.exists('./b-2.txt'))
		self.assertTrue (os.path.exists('./c-2.txt'))

		os.remove ('./a-2.txt')
		os.remove ('./b-2.txt')
		os.remove ('./c-2.txt')

		self.assertFalse (os.path.exists('./a-2.txt'))
		self.assertFalse (os.path.exists('./b-2.txt'))
		self.assertFalse (os.path.exists('./c-2.txt'))

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
		p1.input  = {"input": channel(['a'])}
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
		ppl.starts(p1, p8, p9).run()
		self.assertEqual(sorted(ppl.dot().split("\n")), 
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
	"p1.A" [shape=box, style=filled, color="#c9fcb3"]
	"p8.H" [shape=box, style=filled, color="#c9fcb3"]
	"p9.I" [shape=box, style=filled, color="#c9fcb3"]
	"p7.G" [shape=box, style=filled, color="#fcc9b3" fontcolor=red]
	"p4.D" [shape=box, style=filled, color="#f0f998", fontcolor=red]
}
""".split("\n")))

	def test_multideps (self):
		ppl = pyppl ()
		pr1 = proc("A")
		pr2 = proc("B")
		pr3 = proc("C")
		
		p1ch = [('a',), ('b',), ('c',)]
		p2ch = [(1,), (2,), (3,)]
		pr1.input = {'input': channel(p1ch)}
		pr2.input = {'input': channel(p2ch)}
		pr1.output = '{{input}}'
		pr2.output = '{{input}}'
		pr3.input = 'in1, in2'
		pr3.depends = [pr1, pr2]

		pr1.script = "echo {{input}}"
		pr2.script = "echo {{input}}"
		pr3.script = "echo {{in1}}{{in2}}"
		#p1.echo = True
		#p2.echo = True
		#p3.echo = True
		#print p3.props['indata'], 'xxxxxxxxxxxxxxxxxxxxxxx'
		ppl.starts(pr1, pr2).run()
		

		self.assertEqual (open(os.path.join(pr3.workdir, 'scripts/script.0.stdout')).read().strip(), 'a1')
		self.assertEqual (open(os.path.join(pr3.workdir, 'scripts/script.1.stdout')).read().strip(), 'b2')
		self.assertEqual (open(os.path.join(pr3.workdir, 'scripts/script.2.stdout')).read().strip(), 'c3')
		
	@unittest.skip('')
	def test_sge (self):
		ppl = pyppl ()
		p1 = proc ()
		p1.input = {"input": channel([('a')] * 10)}
		p1.workdir = './test-sge'
		p1.forks = 3
		p1.script = "echo {input}"
		#ppl.add(p1).run('sge')

	def test_batchjobs (self):
		p = proc ('batch')
		p.input = {'input': channel([5, 2, 5, 2, 5, 2])}
		p.script = "cat {{proc.workdir}}/scripts/script.{{#}}.ssh | grep franklin"
		p.echo = True
		p.cache = False
		p.forks = 3
		p.errorhow = 'retry'
		p.runner = 'ssh'
		pyppl({
			'proc': {
				'sshRunner': {	
					'servers': ['franklin01', 'franklin02', 'franklin03', 'franklin04', 'franklin05', 'franklin06', 'franklin07', 'franklin08']
				}
			},
			'loglevel': 'debug'
		}).starts(p).run()

	def testCallback (self):
		p1 = proc ('callback')
		p2 = proc ('callback')

		def callback2 (s):
			ch = channel.create ([('a1','b'), ('x', 'y')])
			s.channel.merge (ch)

		sys.argv = [0, 1, 2]
		p1.input = {"input": channel.fromArgv(1)}
		p1.output = "output:{{input}}2"
		p1.script = "echo {{output}}"
		p1.callback = callback2
		p2.depends = p1
		p2.input = "input, in1, in2"
		p2.script = "echo {{output}}"
		p2.output = "output:{{input}}.{{in1}}.{{in2}}"
		pyppl ().starts(p1).run()

if __name__ == '__main__':
	unittest.main()
