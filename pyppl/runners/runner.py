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

	def __init__ (self, job):
		"""
		Constructor
		@params:
			`job`:    The job object
		"""
		self.job       = job
		self.script    = utils.chmodX(self.job.script)
		self.cmd2run   = list2cmdline (self.script)
		self.ntry      = Value('i', 0, lock = Lock())

	def submit (self, isQ = False):
		"""
		Try to submit the job use Popen
		"""
		if self.job.index not in self.job.proc.ncjobids:
			return True
		elif self.isRunning():
			self.job.proc.log ("Job #%-3s is already running, skip submitting." % self.job.index, 'submit')
			return True
		else:
			self.job.reset(self.ntry.value)
			
			ferrw = open(self.job.errfile, 'w')
			foutw = open(self.job.outfile, 'w')
			succ  = True

			try:
				#self.job.proc.log ('Submitting job #%-3s ...' % self.job.index, 'submit')
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
				return False
			else:
				self.getpid()
				return True

	def finish(self):
		self.job.done()
	
	def getpid (self):
		"""
		Get the job id
		"""
		pass

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
		
		return self.job.succeed()

	def retry(self):
		if self.job.proc.errhow == 'retry' and self.ntry.value < self.job.proc.errntry:
			self.ntry.value += 1
			self.job.proc.log ("Retrying job #%s ... (%s)" % (self.job.index, self.ntry.value), 'RETRY')
			return True
		else:
			return False

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