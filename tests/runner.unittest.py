import unittest, os
import sys
rootdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, rootdir)
from pyppl import runner_local, runner_sge, runner_ssh

def tryRemove (file):
	try: 
		os.remove(file)
	except:
		pass

class TestRunner (unittest.TestCase):

	def setUp (self):
		super(TestRunner, self).setUp()
		tmpdir = os.path.dirname(__file__)
		self.scripts = [
			os.path.join(tmpdir, 'runner1.py'),
			os.path.join(tmpdir, 'runner2.py'),
			os.path.join('/data2/junwenwang/jeffc/grna/bagel-for-knockout-screens-code', 'BAGEL.py'),
			os.path.join('/data2/junwenwang/jeffc/luna/test1', 'test2.R'),
			os.path.join(tmpdir, 'runner3.py'),
		]

		with open (self.scripts[0], 'w') as f:
			f.write ('#!/usr/bin/env python\n')
			f.write ('print "0"\n')
		with open (self.scripts[1], 'w') as f:
			f.write ('#!/usr/bin/env python\n')
			f.write ('print "1"\n')
			f.write ('__import__("time").sleep(8)\n')
			f.write ('print "2"\n')
		with open (self.scripts[4], 'w') as f:
			f.write ('#!/usr/bin/env python\n')
			f.write ('import sys\n')
			f.write ('print "2"\n')
			f.write ('sys.stderr.write("3")\n')
			f.write ('sys.exit(1)\n')

		self.configs = [
			{},
			{
				"retcodes": [0,1]
			}
		]

	def tearDown (self):
		super(TestRunner, self).tearDown()
		for script in self.scripts:
			tryRemove (script)
			tryRemove (script + '.rc') 
			tryRemove (script + '.stderr') 
			tryRemove (script + '.stdout') 
			tryRemove (script + '.sge')
			tryRemove (script + '.ssh') 

	def testLocalInit (self):
		for script in self.scripts[:2]:
			r = runner_local(script)
			self.assertTrue (isinstance(r, runner_local))
		self.assertRaises (Exception, runner_local, self.scripts[3])

	def testSGEInit (self):
		for script in self.scripts[:2]:
			r = runner_sge(script)
			self.assertTrue (isinstance(r, runner_sge))
		self.assertRaises (Exception, runner_sge, self.scripts[3])

	def testChmodX (self):
		self.assertEqual ([os.path.realpath(self.scripts[0])], runner_local.chmod_x(self.scripts[0]))
		self.assertEqual ([os.path.realpath(self.scripts[1])], runner_local.chmod_x(self.scripts[1]))
		self.assertEqual (['/usr/bin/python', self.scripts[2]], runner_local.chmod_x(self.scripts[2]))
		self.assertRaises (Exception, runner_local.chmod_x, self.scripts[3])

	def testConfig (self):
		r0 = runner_local(self.scripts[0], self.configs[0])
		r1 = runner_local(self.scripts[1], self.configs[1])
		self.assertEqual (r0._config('retcodes'), None)
		self.assertEqual (r0._config('retcodes', [0]), [0])
		self.assertEqual (r1._config('retcodes', [0]), [0, 1])
		r2 = runner_ssh(self.scripts[0], {
			'sshRunner': {'servers': ['franklin01']}
		})
		self.assertEqual (r2._config('sshRunner.servers', ['franklin02']), ['franklin01'])

	def testLocalRun (self):
		r0 = runner_local(self.scripts[0])
		r1 = runner_local(self.scripts[1])
		r2 = runner_local(self.scripts[4])

		r0.submit()
		r0.wait()
		self.assertTrue (os.path.exists(r0.rcfile))
		self.assertTrue (os.path.exists(r0.outfile))
		self.assertTrue (os.path.exists(r0.errfile))
		self.assertEqual (r0.rc(), 0)
		self.assertEqual (open(r0.outfile).read().strip(), '0')
		self.assertTrue (r0.isValid())

		r1.submit()
		r1.wait()
		self.assertTrue (os.path.exists(r1.rcfile))
		self.assertTrue (os.path.exists(r1.outfile))
		self.assertTrue (os.path.exists(r1.errfile))
		self.assertEqual (r1.rc(), 0)
		self.assertEqual (open(r1.outfile).read().strip(), '1\n2')
		self.assertTrue (r1.isValid())

		r2.submit()
		r2.wait()
		self.assertTrue (os.path.exists(r2.rcfile))
		self.assertTrue (os.path.exists(r2.outfile))
		self.assertTrue (os.path.exists(r2.errfile))
		self.assertEqual (r2.rc(), 1)
		self.assertEqual (open(r2.outfile).read().strip(), '2')
		self.assertEqual (open(r2.errfile).read().strip(), '3')
		self.assertFalse (r2.isValid())

	def testSSHRun (self):
		r0 = runner_ssh(self.scripts[0], {
			'sshRunner': {'servers': ['franklin01']}
		})
		r1 = runner_ssh(self.scripts[1], {
			'sshRunner': {'servers': ['franklin02']}
		})
		r2 = runner_ssh(self.scripts[4], {
			'sshRunner': {'servers': ['franklin03']}
		})

		r0.submit()
		r0.wait()
		self.assertTrue (os.path.exists(r0.rcfile))
		self.assertTrue (os.path.exists(r0.outfile))
		self.assertTrue (os.path.exists(r0.errfile))
		self.assertEqual (r0.rc(), 0)
		self.assertEqual (open(r0.outfile).read().strip(), '0')
		self.assertTrue (r0.isValid())

		r1.submit()
		r1.wait()
		self.assertTrue (os.path.exists(r1.rcfile))
		self.assertTrue (os.path.exists(r1.outfile))
		self.assertTrue (os.path.exists(r1.errfile))
		self.assertEqual (r1.rc(), 0)
		self.assertEqual (open(r1.outfile).read().strip(), '1\n2')
		self.assertTrue (r1.isValid())

		r2.submit()
		r2.wait()
		self.assertTrue (os.path.exists(r2.rcfile))
		self.assertTrue (os.path.exists(r2.outfile))
		self.assertTrue (os.path.exists(r2.errfile))
		self.assertEqual (r2.rc(), 1)
		self.assertEqual (open(r2.outfile).read().strip(), '2')
		self.assertEqual (open(r2.errfile).read().strip(), '3')
		self.assertFalse (r2.isValid())

		
	
	#@unittest.skip("Skipping SGE test...")
	def testSGERun (self):
		r0 = runner_sge(self.scripts[0], {
			'sgeRunner': {'sge_N': 'job_r0', 'sge_q': '1-hour', 'sge_M': 'Wang.Panwen@mayo.edu'}
		})
		r1 = runner_sge(self.scripts[1], {
			'echo': True,
			'sgeRunner': {'sge_N': 'job_r1', 'sge_q': '1-hour'}
		})
		r2 = runner_sge(self.scripts[4], {
			'sgeRunner': {'sge_N': 'job_r4', 'sge_q': '1-hour'}
		})

		r0.submit()
		r0.wait()
		self.assertTrue (os.path.exists(r0.rcfile))
		self.assertTrue (os.path.exists(r0.outfile))
		self.assertTrue (os.path.exists(r0.errfile))
		self.assertEqual (r0.rc(), 0)
		self.assertEqual (open(r0.outfile).read().strip(), '0')
		self.assertTrue (r0.isValid())

		r1.submit()
		r1.wait()
		self.assertTrue (os.path.exists(r1.rcfile))
		self.assertTrue (os.path.exists(r1.outfile))
		self.assertTrue (os.path.exists(r1.errfile))
		self.assertEqual (r1.rc(), 0)
		self.assertEqual (open(r1.outfile).read().strip(), '1\n2')
		self.assertTrue (r1.isValid())

		r2.submit()
		r2.wait()
		self.assertTrue (os.path.exists(r2.rcfile))
		self.assertTrue (os.path.exists(r2.outfile))
		self.assertTrue (os.path.exists(r2.errfile))
		self.assertEqual (r2.rc(), 1)
		self.assertEqual (open(r2.outfile).read().strip(), '2')
		self.assertEqual (open(r2.errfile).read().strip(), '3')
		self.assertFalse (r2.isValid())

if __name__ == '__main__':
	unittest.main()
