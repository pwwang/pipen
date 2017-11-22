"""
The base runner class
"""
import sys
import re
from time import sleep
from multiprocessing import Lock
from subprocess import Popen, list2cmdline

from .. import utils

lock = Lock()

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
		self.ntry      = 0
		self.p         = None
		self.ferrw     = None
		self.foutw     = None
		
	def __del__(self):
		if self.ferrw:
			self.ferrw.close()
		if self.foutw:
			self.foutw.close()

	def submit (self):
		"""
		Try to submit the job use Popen
		"""
		self.job.reset(None if self.ntry == 0 else self.ntry)
		
		try:
			self.job.proc.log ('Submitting job #%-3s ...' % self.job.index, 'submit')
			# retry may open the files again
			self.ferrw = open(self.job.errfile, 'w')
			self.foutw = open(self.job.outfile, 'w')
			self.p = Popen (self.script, stderr=self.ferrw, stdout=self.foutw, close_fds=True)
		except Exception as ex:
			self.job.proc.log ('Failed to run job #%s: %s' % (self.job.index, str(ex)), 'error')
			with open (self.job.errfile, 'a') as f:
				f.write(str(ex))
			self.job.rc(99)
			#self.finish()
			
	
	def getpid (self):
		"""
		Get the job id
		"""
		self.job.pid (str(self.p.pid))

	def wait(self, rc = True, infout = None, inferr = None):
		"""
		Wait for the job to finish
		@params:
			`rc`: Whether to write return code in rcfile
			`infout`: The file handler for stdout file
			`inferr`: The file handler for stderr file
			- If infout or inferr is None, will open the file and close it before function returns.
		"""
		if self.job.rc() == 99:
			return
		
		fout = open (self.job.outfile) if infout is None else infout
		ferr = open (self.job.errfile) if inferr is None else inferr

		if self.p:
			self.getpid()
			lastout = ''
			lasterr = ''
			while self.p.poll() is None:
				(lastout, lasterr) = self._flushOut(fout, ferr, lastout, lasterr)
				sleep (2)
			
			self._flushOut(fout, ferr, lastout, lasterr, True)
			retcode = self.p.returncode
			if rc or retcode != 0:
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
		if self.job.succeed() or self.job.proc.errhow != 'retry' or self.ntry > self.job.proc.errntry:
			return
		self.job.proc.log ("Retrying job #%s ... (%s)" % (self.job.index, self.ntry), 'RETRY')
		sleep (1)
		self.__del__()
		self.submit()
		self.wait()
		self.finish()

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