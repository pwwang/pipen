"""
The base runner class
"""
import sys
import re
from os import path
from time import sleep
from multiprocessing import Value, Lock
from subprocess import list2cmdline

from ..utils import safefs

flushlock = Lock()

class Runner (object):
	"""
	The base runner class
	"""
	
	INTERVAL = 1
	
	def __init__ (self, job):
		"""
		Constructor
		@params:
			`job`:    The job object
		"""
		self.job       = job
		self.helper    = None
		self.script    = safefs.SafeFs(self.job.script).chmodX()
		self.cmd2run   = list2cmdline (self.script)
		self.ntry      = Value('i', 0, lock = Lock())

	def kill(self):
		"""
		Try to kill the running jobs if I am exiting
		"""
		if self.helper:
			self.helper.kill()

	def submit (self):
		"""
		Try to submit the job
		"""
		indexstr = self.job._indexIndicator()
		if self.job.index not in self.job.proc.ncjobids:
			return True
		elif self.isRunning():
			self.job.proc.log ("%s is already running at %s, skip submission." % (indexstr, self.helper.pid), 'submit')
			return True
		else:
			self.job.reset(self.ntry.value)
			r = self.helper.submit()
			if r.rc != 0:
				if r.stderr: # pragma: no cover
					with open(self.job.errfile, 'w') as ferr:
						ferr.write(r.stderr)
				self.job.proc.log ('%s Submission failed with return code: %s.' % (indexstr, r.rc), 'error')
				self.job.rc(self.job.RC_SUBMITFAIL)
				return False
			return True

	def finish(self):
		self.job.done()
	
	def getpid (self):
		"""
		Get the job id
		"""
		if self.helper:
			self.job.pid(self.helper.pid)

	def run(self):
		"""
		@returns:
			True: success/fail
			False: needs retry
		"""
		# cached jobs
		if self.job.index not in self.job.proc.ncjobids:
			self.finish()
			return True

		# stdout, stderr haven't been generated, wait
		while not path.isfile(self.job.errfile) or not path.isfile(self.job.outfile):
			sleep(self.INTERVAL)

		ferr = open(self.job.errfile)
		fout = open(self.job.outfile)
		lastout = ''
		lasterr = ''

		while self.job.rc() == self.job.RC_NOTGENERATE: # rc not generated yet
			sleep (self.INTERVAL)
			lastout, lasterr = self._flush(fout, ferr, lastout, lasterr)

		self._flush(fout, ferr, lastout, lasterr, True)
		ferr.close()
		fout.close()
		self.finish()
		
		return self.job.succeed()

	def retry(self):
		if self.job.proc.errhow == 'retry' and self.ntry.value < self.job.proc.errntry:
			self.ntry.value += 1
			self.job.proc.log ("%s Retrying job (%s/%s) ..." % (self.job._indexIndicator(), self.ntry.value, self.job.proc.errntry), 'RETRY')
			return True
		else:
			return False

	def isRunning (self):
		"""
		Try to tell whether the job is still running.
		@returns:
			`True` if yes, otherwise `False`
		"""
		if self.helper:
			return self.helper.alive()
		return False
		
	def _flush (self, fout, ferr, lastout, lasterr, end = False):
		"""
		Flush stdout/stderr
		@params:
			`fout`: The stdout file handler
			`ferr`: The stderr file handler
			`lastout`: The leftovers of previously readlines of stdout
			`lasterr`: The leftovers of previously readlines of stderr
			`end`: Whether this is the last time to flush
		"""
		if self.job.index not in self.job.proc.echo['jobs']:
			return None, None

		if 'stdout' in self.job.proc.echo['type']:
			lines, lastout = safefs.SafeFs.flush(fout, lastout, end)
			outfilter      = self.job.proc.echo['type']['stdout']
			
			for line in lines:
				if not outfilter or re.search(outfilter, line):
					with flushlock:
						sys.stdout.write(line)

		lines, lasterr = safefs.SafeFs.flush(ferr, lasterr, end)		
		for line in lines:
			if line.startswith('pyppl.log'):
				line = line.rstrip('\n')
				logstrs  = line[9:].lstrip().split(':', 1)
				if len(logstrs) == 1:
					logstrs.append('')
				(loglevel, logmsg) = logstrs
				
				loglevel = loglevel[1:] if loglevel else 'log'
				
				# '_' makes sure it's not filtered by log levels
				self.job.proc.log (self.job._indexIndicator() + ' ' + logmsg.lstrip(), '_' + loglevel)
			elif 'stderr' in self.job.proc.echo['type']:
				errfilter = self.job.proc.echo['type']['stderr']
				if not errfilter or re.search(errfilter, line):
					with flushlock:
						sys.stderr.write(line)
		
		return (lastout, lasterr)