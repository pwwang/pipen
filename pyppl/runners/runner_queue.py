from multiprocessing import Lock, cpu_count
from time import sleep

from .runner import Runner

lock = Lock()

class RunnerQueue (Runner):
	"""
	The base queue runner class

	@static variables:
		`maxsubmit`: Maximum jobs submitted at one time. Default cpu_count()/2
		`interval` :  The interval to submit next batch of jobs. Default 30
	"""
	
	maxsubmit = int (cpu_count()/2)
	interval  = 30
	
	def __init__ (self, job):
		"""
		Constructor
		@params:
			`job`:    The job object
		"""
		super(RunnerQueue, self).__init__(job)
	
	def wait(self):
		"""
		Wait for the job to finish
		"""
		ferr = open (self.job.errfile)
		fout = open (self.job.outfile)
		
		# wait for submission process first
		super(RunnerQueue, self).wait(False, fout, ferr)
		self.getpid()
			
		lastout = ''
		lasterr = ''
		while self.job.rc() == -1: # pragma: no cover
			sleep (30)
			(lastout, lasterr) = self._flushOut (fout, ferr, lastout, lasterr)
			
		self._flushOut(fout, ferr, lastout, lasterr, True)
			
		ferr.close()
		fout.close()
