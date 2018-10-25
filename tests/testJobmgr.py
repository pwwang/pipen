import helpers, testly
from os import path, makedirs
from shutil import rmtree
from tempfile import gettempdir
from time import sleep
from six.moves.queue import Empty
from multiprocessing import JoinableQueue, Process
from threading import Thread

from pyppl import Proc, utils
from pyppl.job import Job
from pyppl.jobmgr import Jobmgr
from pyppl.runners import RunnerLocal

def createJob(testdir, index = 0, config = None):
	config = config or {}
	config['workdir']  = testdir
	config['procsize'] = config.get('procsize', 1)
	config['proc']     = config.get('proc', 'pTestRunner')
	config['tag']      = config.get('tag', 'notag')
	config['suffix']   = config.get('suffix', 'suffix')
	jobdir = path.join(testdir, str(index+1))
	if not path.exists(jobdir):
		makedirs(jobdir)
	with open(path.join(jobdir, 'job.script'), 'w') as f:
		f.write('#!/usr/bin/env bash')
		f.write(config.get('_script', ''))
	open(path.join(jobdir, 'job.stdout'), 'w').close()
	open(path.join(jobdir, 'job.stderr'), 'w').close()
	return Job(index, config)

class TestJobmgr(testly.TestCase):
	
	def setUpMeta(self):
		self.testdir = path.join(gettempdir(), 'PyPPL_unittest', 'TestJobmgr')
		if path.exists(self.testdir):
			rmtree(self.testdir)
		makedirs(self.testdir)

	def dataProvider_testKillJob(self):
		jobs = [job for job in Job()]

	def testKillJob(self, jm):
		with self.assertStdOE() as (out, err):
			jm.killJob(0)
		self.assertIn('abc', err)
	
if __name__ == '__main__':
	testly.main(verbosity=2)
