import unittest, os
import sys, shutil
rootdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, rootdir)
from pyppl import runner_local, runner_sge, runner_ssh, utils, job

def tryRemove (file):
	try: 
		os.remove(file)
	except:
		pass

class TestRunner (unittest.TestCase):

	def setUp (self):
		super(TestRunner, self).setUp()
		tmpdir = os.path.join(os.path.dirname(__file__), 'test')
		if not os.path.exists  (os.path.join(tmpdir, 'scripts')):
			os.makedirs (os.path.join(tmpdir, 'scripts'))
		self.scripts = [
			os.path.join(tmpdir, 'runner1.py'),
			os.path.join(tmpdir, 'runner2.py'),
			os.path.join('/data2/junwenwang/jeffc/grna/bagel-for-knockout-screens-code', 'BAGEL.py'),
			os.path.join('/data2/junwenwang/jeffc/luna/test1', 'test2.R'),
			os.path.join(tmpdir, 'runner3.py'),
			os.path.join(tmpdir, 'runner4.bash'),
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
		with open (self.scripts[5], 'w') as f:
			f.write ('#!/usr/bin/env bash\n')
			f.write ('sleep 3\n')
			
		self.jobs = []
		for i, script in enumerate(self.scripts):
			if not os.path.exists(os.path.join(tmpdir, 'scripts', 'script.%s' % i)):
				os.symlink (os.path.abspath(script), os.path.join(tmpdir, 'scripts', 'script.%s' % i))
			self.jobs.append (job (i, tmpdir))

		self.configs = [
			{},
			{
				"retcodes": [0,1]
			}
		]

	def tearDown (self):
		super(TestRunner, self).tearDown()
		#shutil.rmtree (os.path.join(os.path.dirname(__file__), 'test'))

	def testLocalInit (self):
		for j in self.jobs[:2]:
			r = runner_local(j)
			self.assertTrue (isinstance(r, runner_local))
		self.assertRaises (Exception, runner_local, self.jobs[3])

	def testSGEInit (self):
		for script in self.jobs[:2]:
			r = runner_sge(script)
			self.assertTrue (isinstance(r, runner_sge))
		self.assertRaises (Exception, runner_sge, self.jobs[3])

	def testChmodX (self):
		self.assertEqual ([os.path.realpath(self.scripts[0])], utils.chmodX(self.scripts[0]))
		self.assertEqual ([os.path.realpath(self.scripts[1])], utils.chmodX(self.scripts[1]))
		self.assertEqual (['/usr/bin/python', self.scripts[2]], utils.chmodX(self.scripts[2]))
		self.assertRaises (Exception, utils.chmodX, self.scripts[3])

	def testConfig (self):
		r0 = runner_local(self.jobs[0], self.configs[0])
		r1 = runner_local(self.jobs[1], self.configs[1])
		self.assertEqual (r0._config('retcodes'), None)
		self.assertEqual (r0._config('retcodes', [0]), [0])
		self.assertEqual (r1._config('retcodes', [0]), [0, 1])
		r2 = runner_ssh(self.jobs[0], {
			'sshRunner': {'servers': ['franklin01']}
		})
		self.assertEqual (r2._config('sshRunner.servers', ['franklin02']), ['franklin01'])

	def testLocalRun (self):
		r0 = runner_local(self.jobs[0])
		r1 = runner_local(self.jobs[1])
		r2 = runner_local(self.jobs[4])

		r0.submit()
		r0.wait()
		self.assertTrue (os.path.exists(r0.job.rcfile))
		self.assertTrue (os.path.exists(r0.job.outfile))
		self.assertTrue (os.path.exists(r0.job.errfile))
		self.assertEqual (r0.job.rc(), 0)
		self.assertEqual (open(r0.job.outfile).read().strip(), '0')
		self.assertTrue (r0.isValid())

		r1.submit()
		r1.wait()
		self.assertTrue (os.path.exists(r1.job.rcfile))
		self.assertTrue (os.path.exists(r1.job.outfile))
		self.assertTrue (os.path.exists(r1.job.errfile))
		self.assertEqual (r1.job.rc(), 0)
		self.assertEqual (open(r1.job.outfile).read().strip(), '1\n2')
		self.assertTrue (r1.isValid())

		r2.submit()
		r2.wait()
		self.assertTrue (os.path.exists(r2.job.rcfile))
		self.assertTrue (os.path.exists(r2.job.outfile))
		self.assertTrue (os.path.exists(r2.job.errfile))
		self.assertEqual (r2.job.rc(), 1)
		self.assertEqual (open(r2.job.outfile).read().strip(), '2')
		self.assertEqual (open(r2.job.errfile).read().strip(), '3')
		self.assertFalse (r2.isValid())

	def testSSHRun (self):
		r0 = runner_ssh(self.jobs[0], {
			'sshRunner': {'servers': ['franklin01']}
		})
		r1 = runner_ssh(self.jobs[1], {
			'sshRunner': {'servers': ['franklin02']}
		})
		r2 = runner_ssh(self.jobs[4], {
			'sshRunner': {'servers': ['franklin03']}
		})

		r0.submit()
		r0.wait()
		self.assertTrue (os.path.exists(r0.job.rcfile))
		self.assertTrue (os.path.exists(r0.job.outfile))
		self.assertTrue (os.path.exists(r0.job.errfile))
		self.assertEqual (r0.job.rc(), 0)
		self.assertEqual (open(r0.job.outfile).read().strip(), '0')
		self.assertTrue (r0.isValid())

		r1.submit()
		r1.wait()
		self.assertTrue (os.path.exists(r1.job.rcfile))
		self.assertTrue (os.path.exists(r1.job.outfile))
		self.assertTrue (os.path.exists(r1.job.errfile))
		self.assertEqual (r1.job.rc(), 0)
		self.assertEqual (open(r1.job.outfile).read().strip(), '1\n2')
		self.assertTrue (r1.isValid())

		r2.submit()
		r2.wait()
		self.assertTrue (os.path.exists(r2.job.rcfile))
		self.assertTrue (os.path.exists(r2.job.outfile))
		self.assertTrue (os.path.exists(r2.job.errfile))
		self.assertEqual (r2.job.rc(), 1)
		self.assertEqual (open(r2.job.outfile).read().strip(), '2')
		self.assertEqual (open(r2.job.errfile).read().strip(), '3')
		self.assertFalse (r2.isValid())

		
	
	@unittest.skip("Skipping SGE test...")
	def testSGERun (self):
		r0 = runner_sge(self.jobs[0], {
			'sgeRunner': {'sge_N': 'job_r0', 'sge_q': '1-hour', 'sge_M': 'Wang.Panwen@mayo.edu'}
		})
		r1 = runner_sge(self.jobs[1], {
			'echo': True,
			'sgeRunner': {'sge_N': 'job_r1', 'sge_q': '1-hour'}
		})
		r2 = runner_sge(self.jobs[4], {
			'sgeRunner': {'sge_N': 'job_r4', 'sge_q': '1-hour'}
		})

		r0.submit()
		r0.wait()
		self.assertTrue (os.path.exists(r0.job.rcfile))
		self.assertTrue (os.path.exists(r0.job.outfile))
		self.assertTrue (os.path.exists(r0.job.errfile))
		self.assertEqual (r0.job.rc(), 0)
		self.assertEqual (open(r0.job.outfile).read().strip(), '0')
		self.assertTrue (r0.isValid())

		r1.submit()
		r1.wait()
		self.assertTrue (os.path.exists(r1.job.rcfile))
		self.assertTrue (os.path.exists(r1.job.outfile))
		self.assertTrue (os.path.exists(r1.job.errfile))
		self.assertEqual (r1.job.rc(), 0)
		self.assertEqual (open(r1.job.outfile).read().strip(), '1\n2')
		self.assertTrue (r1.isValid())

		r2.submit()
		r2.wait()
		self.assertTrue (os.path.exists(r2.job.rcfile))
		self.assertTrue (os.path.exists(r2.job.outfile))
		self.assertTrue (os.path.exists(r2.job.errfile))
		self.assertEqual (r2.job.rc(), 1)
		self.assertEqual (open(r2.job.outfile).read().strip(), '2')
		self.assertEqual (open(r2.job.errfile).read().strip(), '3')
		self.assertFalse (r2.isValid())
	
	@unittest.skip("Skipping isRunning test...")	
	def testIsRunning (self):
		r0 = runner_local (self.jobs[5])
		r0.job.clearOutput()
		r0.submit ()
		self.assertFalse (r0.isRunning())
		r0.job.clearOutput()
		
		r1 = runner_sge (self.jobs[5])
		if not r1.isRunning(): 
			r1.job.clearOutput()
			r1.submit ()
			self.assertTrue (r1.isRunning())
		r1.job.clearOutput()
			
		r2 = runner_ssh (self.jobs[5], {
			'sshRunner': {'servers': ['franklin03']}	
		})
		if not r2.isRunning(): 
			r2.job.clearOutput()
			from subprocess import Popen
			Popen (r2.script)
			self.assertTrue (r2.isRunning())
		

if __name__ == '__main__':
	unittest.main()
