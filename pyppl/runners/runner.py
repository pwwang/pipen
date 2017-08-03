"""
The base runner class
"""
import sys
import re
from os import devnull
from time import sleep
from multiprocessing import Lock
from subprocess import Popen, list2cmdline

from ..helpers import utils

lock = Lock()

class runner (object):
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
		self.ntry      = 0
		self.p         = None

	def submit (self):
		"""
		Try to submit the job use Popen
		"""
		self.job.reset()
		try:
			self.job.proc.log ('Submitting job #%-3s ...' % self.job.index)
			self.p = Popen (self.script, stderr=open(self.job.errfile, "w"), stdout=open(self.job.outfile, "w"), close_fds=True)
		except Exception as ex:
			self.job.proc.log ('Failed to run job #%s: %s' % (self.job.index, str(ex)), 'error')
			with open (self.job.errfile, 'a') as f:
				f.write(str(ex))
			self.job.rc(self.job.FAILED_RC)
			self.finish()
			
	
	def getpid (self):
		"""
		Get the job id
		"""
		self.job.id (str(self.p.pid))

	def wait(self, rc = True, infout = None, inferr = None):
		"""
		Wait for the job to finish
		@params:
			`rc`: Whether to write return code in rcfile
			`infout`: The file handler for stdout file
			`inferr`: The file handler for stderr file
			- If infout or inferr is None, will open the file and close it before function returns.
		"""
		if self.job.rc() == self.job.FAILED_RC: 
			return
		
		fout = open (self.job.outfile) if infout is None else infout
		ferr = open (self.job.errfile) if inferr is None else inferr

		if self.p:
			self.getpid()
			lastout = ''
			lasterr = ''
			while self.p.poll() is None:
				(lastout, lasterr) = self._flushOut(fout, ferr, lastout, lasterr)
				sleep (3)
			
			self._flushOut(fout, ferr, lastout, lasterr)
			if rc:
				retcode = self.p.returncode
				self.job.rc(retcode)
		
		if infout is None:
			fout.close()
		if inferr is None:
			ferr.close()

	def finish (self):
		"""
		Do some cleanup work when jobs finish
		"""
		self.job.done ()
		self.p = None
		self.retry ()

	def retry (self):
		"""
		Retry to submit and run the job if failed
		"""
		self.ntry += 1
		if self.job.succeed() or self.job.proc.errorhow != 'retry' or self.ntry > self.job.proc.errorntry:
			return

		self.job.proc.log ("Retrying job #%s ... (%s)" % (self.job.index, self.ntry))
		sleep (3)
		self.submit()
		self.wait()
		self.finish()

	def isRunning (self):
		"""
		Try to tell whether the job is still running.
		@returns:
			`True` if yes, otherwise `False`
		"""
		jobid = self.job.id()
		if not jobid:
			return False
		return Popen (['kill', '-s', '0', jobid], stderr=open(devnull, 'w'), stdout=open(devnull, 'w')).wait() == 0
		
	def _flushOut (self, fout, ferr, lastout, lasterr):
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
					
					for line in lines:
						if not self.job.proc.echo['filter'] or (self.job.proc.echo['filter'] and re.search (self.job.proc.echo['filter'], line)):
							lock.acquire()
							sys.stdout.write (line)
							lock.release()
			
			lines = ferr.readlines()
			if lines: 
				lines[0] = lasterr + lines[0]
				if not lines[-1].endswith('\n'):
					lasterr = lines.pop(-1)
				
				for line in lines:
					if 'stderr' in self.job.proc.echo['type'] and (not self.job.proc.echo['filter'] or (self.job.proc.echo['filter'] and re.search (self.job.proc.echo['filter'], line))):
						lock.acquire()
						sys.stderr.write (line)
						lock.release()
					
					line = line.strip()
					if line.startswith('pyppl.log'):
						logstrs  = line.split(':', 1)
						if len(logstrs) == 1:
							logflags = logstrs[0]
							logmsgs  = ''
						else:
							(logflags, logmsgs) = logstrs
						
						loglevel = 'info'
						logflag  = 'info'
						logflags = logflags.split('.')
						if len(logflags) > 2:
							loglevel = logflags[2]
						if len(logflags) > 3:
							logflag  = logflags[3]
						self.job.proc.log (logmsgs.strip(), loglevel, logflag)
		return (lastout, lasterr)