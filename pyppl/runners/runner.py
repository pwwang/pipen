"""
The base runner class
"""
import sys
import re
from time import sleep
from multiprocessing import Value, Lock, cpu_count
from subprocess import Popen, list2cmdline

from .. import utils

lock = Lock()

class Runner (object):
	"""
	The base runner class
	"""

	STATUS_INITIATED    = 0
	STATUS_SUBMITTING   = 1
	STATUS_SUBMITTED    = 2
	STATUS_SUBMITFAILED = 3
	STATUS_RUNFAILED    = 4
	STATUS_RUNNING      = 5
	STATUS_DONE         = 6

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
		assert self.status() in [Runner.STATUS_INITIATED, Runner.STATUS_SUBMITFAILED, Runner.STATUS_RUNFAILED]

		self.status(Runner.STATUS_SUBMITTING)
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
				if isQ:
					self.job.proc.log ('Failed to submit job #%s' % self.job.index, 'error')
				else:
					self.job.proc.log ('Failed to run job #%s' % self.job.index, 'error')
				succ = False
			if not isQ:
				self.job.rc(rc)
				
		except Exception as ex:
			if isQ:
				self.job.proc.log ('Failed to submit job #%s: %s' % (self.job.index, str(ex)), 'error')
			else:
				self.job.proc.log ('Failed to run job #%s: %s' % (self.job.index, str(ex)), 'error')
			ferrw.write(str(ex))
			succ = False
		finally:
			ferrw.close()
			foutw.close()
			
		if not succ:
			if isQ: self.job.rc(99)
			self.status(Runner.STATUS_SUBMITFAILED)
		else:
			if isQ: self.getpid()
			else:   self.getpid(p.pid)
			self.status(Runner.STATUS_SUBMITTED)

	def finish(self):
		self.job.done()
	
	def getpid (self, pid = None):
		"""
		Get the job id
		"""
		if pid is not None:
			self.job.pid (str(pid))

	def run(self, submitQ, test = False):
		
		# wait until the job is submitted
		allowed_status = [Runner.STATUS_SUBMITTED, Runner.STATUS_SUBMITFAILED]
		if test: allowed_status.append(Runner.STATUS_RUNFAILED)
		while self.status() not in allowed_status:
			sleep(1)

		self.status(Runner.STATUS_RUNNING)
		# cached jobs
		if self.job.index not in self.job.proc.ncjobids:
			self.finish()
			self.status(Runner.STATUS_DONE)
		else:
			ferr = open(self.job.errfile)
			fout = open(self.job.outfile)
			lastout = ''
			lasterr = ''
			while self.job.rc() == -1: # rc not generated yet
				sleep (5)
				lastout, lasterr = self._flushOut(fout, ferr, lastout, lasterr)
			self._flushOut(fout, ferr, lastout, lasterr, True)
			ferr.close()
			fout.close()
			self.finish()
			
			if self.job.succeed():
				self.status(Runner.STATUS_DONE)
			else:
				if self.job.proc.errhow == 'retry' and self.ntry < self.job.proc.errntry:
					self.status(Runner.STATUS_RUNFAILED)
					submitQ.put(self.job.index)
					self.ntry += 1
					self.job.proc.log ("Retrying job #%s ... (%s)" % (self.job.index, self.ntry), 'RETRY')
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
		
	def _flushOut (self, fout, ferr, lastout, lasterr, end = False):
		"""
		Flush stdout/stderr
		@params:
			`fout`: The stdout file handler
			`ferr`: The stderr file handler
			`lastout`: The leftovers of previously readlines of stdout
			`lasterr`: The leftovers of previously readlines of stderr
		"""
		if self.job.index in self.job.proc.echo['jobs']:
			if 'stdout' in self.job.proc.echo['type']:
				lines = fout.readlines()
				if lines:
					lines[0] = lastout + lines[0]
					if not lines[-1].endswith('\n'):
						lastout = lines.pop(-1)
					else:
						lastout = ''
					if lastout and end:
						lines.append(lastout + '\n')
					for line in lines:
						if not self.job.proc.echo['filter'] or (self.job.proc.echo['filter'] and re.search (self.job.proc.echo['filter'], line)):
							lock.acquire()
							sys.stdout.write (line)
							lock.release()
			
			lines = ferr.readlines()
			if lines:
				lines[0] = lasterr + lines[0]
				lastline = lines[-1]
				if end and not lastline.endswith('\n'):
					lines[-1] += '\n'
				elif not end and not lines[-1].endswith('\n'):
					lasterr = lines.pop(-1)
				
				for line in lines:
					if 'stderr' in self.job.proc.echo['type'] and (not self.job.proc.echo['filter'] or (self.job.proc.echo['filter'] and re.search (self.job.proc.echo['filter'], line))):
						lock.acquire()
						sys.stderr.write (line)
						lock.release()
					
					line = line.strip()
					if line.startswith('pyppl.log'):
						logstrs  = line[9:].lstrip().split(':', 1)
						if len(logstrs) == 1:
							loglevel = logstrs[0]
							logmsg   = ''
						else:
							(loglevel, logmsg) = logstrs
						
						if not loglevel:
							loglevel = 'log'
						else:
							loglevel = loglevel[1:] # remove leading dot
							
						# '_' makes sure it's not filtered by log levels
						self.job.proc.log (logmsg.lstrip(), '_' + loglevel)
		return (lastout, lasterr)