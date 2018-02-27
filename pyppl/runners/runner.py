"""
The base runner class
"""
import sys
import re
from time import sleep
from multiprocessing import Value, Lock
from subprocess import Popen, list2cmdline

from .. import utils

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
		self.script    = utils.chmodX(self.job.script)
		self.cmd2run   = list2cmdline (self.script)
		self.ntry      = Value('i', 0, lock = Lock())

	def submit (self):
		"""
		Try to submit the job use Popen
		"""
		indexstr = self.job._indexIndicator()
		if self.job.index not in self.job.proc.ncjobids:
			return True
		elif self.isRunning():
			self.job.proc.log ("%s is already running, skip submission." % indexstr, 'submit')
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
					self.job.proc.log ('%s Submission failed with return code: %s.' % (indexstr, rc), 'error')
					succ = False
					
			except Exception as ex:
				self.job.proc.log ('%s Submission failed with exception: %s' % (indexstr, str(ex)), 'error')
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
				self.job.proc.log (self.job._indexIndicator() + ' ' + logmsg, '_' + loglevel)
			elif 'stderr' in self.job.proc.echo['type']:
				errfilter = self.job.proc.echo['type']['stderr']
				if not errfilter or re.search(errfilter, line):
					with flushlock:
						sys.stderr.write(line)
		
		return (lastout, lasterr)