"""
The base runner class
"""
import sys
import re
import atexit
from os import path
from time import sleep
from subprocess import list2cmdline
from multiprocessing import Lock

from pyppl.utils import safefs, cmd, ps
from pyppl.logger import logger

class Runner (object):
	"""
	The base runner class
	"""
	
	INTERVAL  = .1
	FLUSHLOCK = Lock()
	
	def __init__ (self, job):
		"""
		Constructor
		@params:
			`job`:    The job object
		"""
		self.script  = safefs.SafeFs(job.script).chmodX()
		self.job     = job
		self.cmd2run = list2cmdline(self.script)

	def kill(self):
		"""
		Try to kill the running jobs if I am exiting
		"""
		if self.job.pid:
			ps.killtree(int(self.job.pid), killme = True, sig = 9)

	def submit (self):
		"""
		Try to submit the job
		"""
		c = cmd.run([
			sys.executable, 
			path.realpath(__file__), 
			self.script[-1] if isinstance(self.script, list) else self.script
		], bg = True)
		c.rc = 0
		return c

	def run(self):
		"""
		@returns:
			True: success/fail
			False: needs retry
		"""
		# stdout, stderr haven't been generated, wait
		while not path.isfile(self.job.errfile) or not path.isfile(self.job.outfile):
			sleep(self.INTERVAL) # pragma: no cover
		
		ferr = open(self.job.errfile)
		fout = open(self.job.outfile)
		lastout = ''
		lasterr = ''
		
		while self.job.rc == self.job.RC_NOTGENERATE: # rc not generated yet
			sleep (self.INTERVAL)
			lastout, lasterr = self._flush(fout, ferr, lastout, lasterr)

		self._flush(fout, ferr, lastout, lasterr, True)
		ferr.close()
		fout.close()

	def isRunning (self):
		"""
		Try to tell whether the job is still running.
		@returns:
			`True` if yes, otherwise `False`
		"""
		if not self.job.pid:
			return False
		return ps.exists(int(self.job.pid))
		
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
		if self.job.index not in self.job.config['echo']['jobs']:
			return None, None

		if 'stdout' in self.job.config['echo']['type']:
			lines, lastout = safefs.SafeFs.flush(fout, lastout, end)
			outfilter      = self.job.config['echo']['type']['stdout']
			
			for line in lines:
				if not outfilter or re.search(outfilter, line):
					with Runner.FLUSHLOCK:
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
				logger.info(logmsg.lstrip(), extra = {
					'loglevel': '_' + loglevel,
					'pbar'    : False,
					'jobidx'  : self.job.index,
					'joblen'  : self.job.config['procsize'],
					'proc'    : self.job.config['proc']
				})
			elif 'stderr' in self.job.config['echo']['type']:
				errfilter = self.job.config['echo']['type']['stderr']
				if not errfilter or re.search(errfilter, line):
					with Runner.FLUSHLOCK:
						sys.stderr.write(line)
		
		return (lastout, lasterr)

class _LocalSubmitter(object):
	
	def __init__(self, script):
		scriptdir    = path.dirname(script)
		self.script  = script
		self.rcfile  = path.join(scriptdir, 'job.rc')
		self.pidfile = path.join(scriptdir, 'job.pid')
		self.outfile = path.join(scriptdir, 'job.stdout')
		self.errfile = path.join(scriptdir, 'job.stderr')
		self.outfd   = None
		self.errfd   = None

	def submit(self):
		"""
		Submit the real job.
		"""
		self.outfd = open(self.outfile, 'w')
		self.errfd = open(self.errfile, 'w')
		self.proc  = cmd.Cmd(safefs.SafeFs(self.script).chmodX(), stdout = self.outfd, stderr = self.errfd)
		with open(self.pidfile, 'w') as fpid:
			fpid.write(str(self.proc.pid))
		try:
			self.proc.run()
		except KeyboardInterrupt: # pragma: no cover
			self.proc.rc = 1

	def quit(self):
		"""
		Clean up.
		"""
		if self.outfd:
			self.outfd.close()
		if self.errfd:
			self.errfd.close()
		# write rc
		with open(self.rcfile, 'w') as frc:
			frc.write(str(self.proc.rc))	

if __name__ == '__main__': # pragma: no cover
	# work as local submitter
	submitter = _LocalSubmitter(sys.argv[1])
	atexit.register(submitter.quit)
	submitter.submit()
