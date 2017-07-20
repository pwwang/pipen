import os
import shutil
import sys
import unittest
import warnings
from time import sleep
from subprocess import Popen

rootdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, rootdir)
from pyppl import proc, job, runner_local, runner_sge, runner_ssh, utils, runner, runner_queue
from pyppl.runners import runner_slurm

class TestRunner(unittest.TestCase):

	testdir = "./tests"
	logger  = utils.getLogger('debug', 'TestRunner')
	def setUp (self):
		if not os.path.exists (self.testdir):
			os.makedirs(self.testdir)
	
	def tearDown (self):
		try:
			if os.path.exists (self.testdir):
				shutil.rmtree (self.testdir)
		except:
			sleep (1)
			self.tearDown()

	def testRunnerInit (self):
		p = proc('init')
		p.ppldir = self.testdir
		p.script = "echo 1"
		p.input = {'a': range(10)}
		p.props['logger'] = self.logger
		p._tidyBeforeRun ()
		r = runner(p.jobs[0])
		self.assertEqual (p.jobs[0], r.job)
		self.assertEqual ([p.jobs[0].script], r.script)
		self.assertEqual (p.jobs[0].script, r.cmd2run)
		self.assertEqual (0, r.ntry)
		self.assertEqual (None, r.p)

	def testRunnerSubmit (self):
		p = proc('submit')
		p.ppldir = self.testdir
		p.script = "echo1 {{a}}"
		p.input = {'a': range(10)}
		p.props['logger'] = self.logger
		p._tidyBeforeRun ()
		r = runner(p.jobs[0])
		script   = [x for x in r.script]

		# exception
		r.script = 1
		r.submit()
		self.assertIsNone (r.p)
		self.assertEqual (r.job.rc(), r.job.FAILED_RC)

		# no exception
		r.script = script
		r.submit ()
		self.assertIsNotNone (r.p)

	def testRunnerWait (self):
		p = proc('wait')
		p.ppldir = self.testdir
		p.script = "echo {{a}}"
		p.input = {'a': range(10)}
		p.props['logger'] = self.logger
		p._tidyBeforeRun ()
		r = runner(p.jobs[0])
		r.submit ()
		r.wait ()
		self.assertEqual (r.job.rc(), 0)
		self.assertEqual (open(r.job.outfile).read().strip(), '0')

	def testRunnerRetry (self):
		p = proc('retry')
		p.ppldir = self.testdir
		p.script = "echo1 {{a}}"
		p.input = {'a': range(10)}
		p.errhow = 'retry'
		p.props['logger'] = self.logger
		p._tidyBeforeRun ()
	
		r = runner(p.jobs[0])
		r.submit ()
		r.wait ()
		r.finish ()
		self.assertEqual (r.ntry, p.errntry + 1)
		self.assertEqual (r.job.rc(), 127)

	def testRunnerIsRunning (self):
		p = proc('isrunning')
		p.ppldir = self.testdir
		p.script = "sleep .5;echo {{a}}"
		p.input = {'a': range(10)}
		p.props['logger'] = self.logger
		p._tidyBeforeRun ()
	
		r = runner(p.jobs[0])
		self.assertFalse (r.isRunning())
		p = Popen (r.script, stdout=open(os.devnull, 'w'), stderr=open(os.devnull, 'w'), shell=False)
		r.job.id(str(p.pid))
		self.assertTrue (r.isRunning())
		p.wait()
		self.assertFalse (r.isRunning())

	def testSshInit (self):
		p = proc('sshinit')
		p.ppldir = self.testdir
		p.script = "sleep 3; echo {{a}}"
		p.input = {'a': range(4)}
		p.props['logger'] = self.logger
		p.sshRunner = {"servers": ['franklin01', 'franklin02']}
		p._tidyBeforeRun ()

		for j in p.jobs:
			r = runner_ssh (j)
			self.assertTrue (os.path.exists(j.script + '.ssh'))
			self.assertEqual (r.script, [os.path.realpath(j.script) + '.ssh'])

	@unittest.skip('')
	def testSshIsRunning (self):
		p = proc('sshisrunning')
		p.ppldir = self.testdir
		p.script = "sleep 3; echo {{a}}"
		p.input = {'a': range(4)}
		p.props['logger'] = self.logger
		p.sshRunner = {"servers": ['franklin01', 'franklin02']}
		p._tidyBeforeRun ()	
		for j in p.jobs:
			r = runner_ssh (j)
			self.assertFalse (r.isRunning())
			p = Popen (r.script, stdout=open(os.devnull, 'w'), stderr=open(os.devnull, 'w'))
			r.job.id(str(p.pid))
			self.assertTrue (r.isRunning())
			p.wait()
			self.assertFalse (r.isRunning())

	def testSgeInit (self):
		p = proc('sgeinit')
		p.ppldir = self.testdir
		p.script = "sleep 3; echo {{a}}"
		p.input = {'a': range(4)}
		p.props['logger'] = self.logger
		p.sgeRunner = {"sge_q": '1-hour'}
		p._tidyBeforeRun ()

		for j in p.jobs:
			r = runner_sge (j)
			self.assertTrue (os.path.exists(j.script + '.sge'))
			self.assertEqual (r.script, ['qsub', os.path.realpath(j.script) + '.sge'])

	@unittest.skip('')
	def testSgeIsRunning (self):
		p = proc('sgeisrunning')
		p.ppldir = self.testdir
		p.script = "sleep 3; echo {{a}}"
		p.input = {'a': range(1)}
		p.forks = 4
		p.props['logger'] = self.logger
		p.sgeRunner = {"sge_q": '1-hour'}
		p._tidyBeforeRun ()

		for j in p.jobs:
			r = runner_sge (j)
			self.assertFalse (r.isRunning())
			r.submit ()
			self.assertFalse (r.isRunning())
			r.p.wait()
			r.getpid()
			self.assertTrue (r.isRunning())

		# then delete the error jobs in queue
	
	def testLocalIsRunning (self):
		p = proc('localisrunning')
		p.ppldir = self.testdir
		p.script = "sleep 1; echo {{a}}"
		p.input = {'a': range(4)}
		p.forks = 4
		p.props['logger'] = self.logger
		p._tidyBeforeRun ()	
		for j in p.jobs:
			r = runner_local (j)
			self.assertFalse (r.isRunning())
			stdout = open(os.devnull, 'w')
			stderr = open(os.devnull, 'w')
			p = Popen (r.script, stdout=stdout, stderr=stderr)
			r.job.id(str(p.pid))
			self.assertTrue(r.isRunning())
			p.wait()
			self.assertFalse(r.isRunning())
			stdout.close()
			stderr.close()


if __name__ == '__main__':
	unittest.main()
