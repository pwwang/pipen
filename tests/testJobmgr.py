import helpers, testly, sys
from os import path, makedirs
from shutil import rmtree
from tempfile import gettempdir

from pyppl import Proc
from pyppl.jobmgr import Jobmgr

# just high-level tests
class TestJobmgr(testly.TestCase):
	
	def setUpMeta(self):
		self.testdir = path.join(gettempdir(), 'PyPPL_unittest', 'TestJobmgr')
		if path.exists(self.testdir):
			rmtree(self.testdir)
		makedirs(self.testdir)

	def testJmNoJobs(self):
		with helpers.log2str():
			pNoJobs = Proc()
			pNoJobs.run()

	def testJm1(self):
		with helpers.log2str():
			p = Proc()
			p.script = 'echo 123'
			p.forks  = 1
			p.input = {'a': [1, 2]}
			p.run()

	def testJm2(self):
		with helpers.log2str():
			p1 = Proc()
			p1.script = 'echo 123'
			p1.forks = Jobmgr.PBAR_SIZE * 2
			p1.input = {'a': list(range(Jobmgr.PBAR_SIZE * 2))}
			p1.run()

	def testJm3(self):
		with helpers.log2str():
			p2 = Proc()
			p2.script = '__err__ 123'
			p2.forks = 20
			p2.input = {'a': list(range(20))}
			p2.errhow = 'halt'
			try:
				p2.run()
			except SystemExit:
				pass

	def testJm4(self):
		with helpers.log2str():
			from time import time
			p3         = Proc()
			p3.forks   = 1
			p3.lang    = sys.executable
			p3.args.i  = time()
			p3.input   = {'a': [0]}
			p3.errntry = 10
			p3.errhow  = 'retry'
			p3.script  = '''#
			# PYPPL INDENT REMOVE
			from time import sleep, time
			sleep(.1)
			t = time() - {{args.i}}
			if t < 1:
				exit(1)
			'''
			p3.run()

	
if __name__ == '__main__':
	testly.main(verbosity=2)
