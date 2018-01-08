"""
The base runner class
"""
import sys
import re
from time import sleep
from multiprocessing import Value, Lock, cpu_count
from subprocess import Popen, list2cmdline

from .. import utils

flushlock = Lock()

class Runner (object):
	"""
	The base runner class
	"""

	STATUS_INITIATED    = 0
	STATUS_SUBMITTED    = 1
	STATUS_SUBMITFAILED = 2
	STATUS_DONE         = 3

	MAXSUBMIT = int (cpu_count()/2)

	def __init__ (self, job):
		"""
		Constructor
		@params:
			`job`:    The job object
		"""
		self.job       = job
		self.script    = utils.chmodX(self.job.script)
		self.cmd2run   = list2cmdline (self.script)
		self.ntry      = 0
		self.lock      = Lock()
		self.st        = Value('i', Runner.STATUS_INITIATED)

	def status(self, s = None):
		with self.lock:
			if s is None:
				return self.st.value
			else:
				self.st.value = s

	def submit (self, isQ = False):
		"""
		Try to submit the job use Popen
		"""
		#assert self.status() in [Runner.STATUS_INITIATED, Runner.STATUS_SUBMITFAILED, Runner.STATUS_RUNFAILED]
		assert self.status() == Runner.STATUS_INITIATED
		if self.job.index not in self.job.proc.ncjobids:
			self.status(Runner.STATUS_SUBMITTED)
		elif self.isRunning():
			self.job.proc.log ("Job #%-3s is already running, skip submitting." % self.job.index, 'submit')
			self.status(Runner.STATUS_SUBMITTED)
		else:
			self.job.reset(None if self.ntry == 0 else self.ntry)
			
			ferrw = open(self.job.errfile, 'w')
			foutw = open(self.job.outfile, 'w')
			succ  = True

			try:
				self.job.proc.log ('Submitting job #%-3s ...' % self.job.index, 'submit')
				# retry may open the files again
				p  = Popen (self.script, stderr=ferrw, stdout=foutw, close_fds=True)
				
				rc = p.wait()
				if rc != 0:
					self.job.proc.log ('Failed to submit job #%s' % self.job.index, 'error')
					succ = False
					
			except Exception as ex:
				self.job.proc.log ('Failed to submit job #%s: %s' % (self.job.index, str(ex)), 'error')
				ferrw.write(str(ex))
				succ = False
			finally:
				ferrw.close()
				foutw.close()
				
			if not succ:
				self.job.rc(self.job.RC_SUBMITFAIL)
				self.status(Runner.STATUS_SUBMITFAILED)
			else:
				self.getpid()
				self.status(Runner.STATUS_SUBMITTED)

	def finish(self):
		self.job.done()
	
	def getpid (self):
		"""
		Get the job id
		"""
		pass

	def run(self, submitQ):
		while self.status() not in [Runner.STATUS_SUBMITTED, Runner.STATUS_SUBMITFAILED]:
			sleep(1)

		# cached jobs
		if self.job.index not in self.job.proc.ncjobids:
			self.finish()
			self.status(Runner.STATUS_DONE)
		else:
			ferr = open(self.job.errfile)
			fout = open(self.job.outfile)
			lastout = ''
			lasterr = ''
			while self.job.rc() == self.job.RC_NOTGENERATE: # rc not generated yet
				sleep (5)
				lastout, lasterr = self._flush(fout, ferr, lastout, lasterr)
			self._flush(fout, ferr, lastout, lasterr, True)
			ferr.close()
			fout.close()
			self.finish()
			
			if self.job.succeed():
				self.status(Runner.STATUS_DONE)
			else:
				if self.job.proc.errhow == 'retry' and self.ntry < self.job.proc.errntry:
					submitQ.put(self.job.index)
					self.ntry += 1
					self.job.proc.log ("Retrying job #%s ... (%s)" % (self.job.index, self.ntry), 'RETRY')
					self.status(Runner.STATUS_INITIATED)
					self.run(submitQ, test = test)
				else:
					self.status(Runner.STATUS_DONE)


	def isRunning (self):
		"""
		Try to tell whether the job is still running.
		@returns:
			`True` if yes, otherwise `False`
		"""
		jobpid = self.job.pid()
		if not jobpid:
			return False
		return utils.dumbPopen (['kill', '-s', '0', jobpid]).wait() == 0
		
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
			lines, lastout = utils.flushFile(fout, lastout, end)
			outfilter      = self.job.proc.echo['type']['stdout']
			
			for line in lines:
				if not outfilter or re.search(outfilter, line):
					with flushlock:
						sys.stdout.write(line)
		
		lines, lasterr = utils.flushFile(ferr, lasterr, end)
		for line in lines:
			if line.startswith('pyppl.log'):
				line = line.rstrip('\n')
				logstrs  = line[9:].lstrip().split(':', 1)
				if len(logstrs) == 1:
					logstrs.append('')
				(loglevel, logmsg) = logstrs
				
				loglevel = loglevel[1:] if loglevel else 'log'
				
				# '_' makes sure it's not filtered by log levels
				self.job.proc.log (logmsg.lstrip(), '_' + loglevel)
			elif 'stderr' in self.job.proc.echo['type']:
				errfilter = self.job.proc.echo['type']['stderr']
				if not errfilter or re.search(errfilter, line):
					with flushlock:
						sys.stderr.write(line)
		
		return (lastout, lasterr)