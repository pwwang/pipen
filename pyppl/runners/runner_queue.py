import sys
from multiprocessing import Lock, cpu_count
from random import randint
from time import sleep

from .runner import runner

from ..helpers.job import job as pjob

lock = Lock()

class runner_queue (runner):
	"""
	The base queue runner class
	@static variables:
		maxsubmit: Maximum jobs submitted at one time. Default cpu_count()/2
		interval:  The interval to submit next batch of jobs. Default 30
	"""
	
	maxsubmit = int (cpu_count()/2)
	interval  = 30 
	
	def wait(self):
		"""
		Wait for the job to finish
		"""
		if self.job.rc() == pjob.FAILED_RC: 
			return
			
		ferr = open (self.job.errfile)
		fout = open (self.job.outfile)
		if self.p:
			self.p.wait()
			if self.job.proc.echo:
				lock.acquire()
				sys.stderr.write (ferr.read())
				sys.stdout.write (fout.read())
				lock.release()
		
		if not self.isRunning(True):
			ferr.close()
			fout.close()
			return
		
		while self.job.rc() == pjob.EMPTY_RC:
			sleep (randint(20, 40))
			if self.job.proc.echo:
				lock.acquire()
				sys.stderr.write (''.join(ferr.readlines()))
				sys.stdout.write (''.join(fout.readlines()))
				lock.release()
				
			if not self.isRunning(True):
				break
			
		ferr.close()
		fout.close()
