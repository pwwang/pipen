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
	
	def __init__ (self, job):
		"""
		Constructor
		@params:
			`job`:    The job object
		"""
		super(runner_queue, self).__init__(job)
	
	def wait(self):
		"""
		Wait for the job to finish
		"""
		ferr = open (self.job.errfile)
		fout = open (self.job.outfile)
		
		# wait for submission process first
		super(runner_queue, self).wait(False, fout, ferr)
			
		lastout = ''
		lasterr = ''
		while self.job.rc() == pjob.EMPTY_RC:
			sleep (30)
			(lastout, lasterr) = self._flushOut (fout, ferr, lastout, lasterr)
			
		self._flushOut(fout, ferr, lastout, lasterr)
			
		ferr.close()
		fout.close()
