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
	
	INTERVAL  = 1
	FLUSHLOCK = Lock()
	
	def __init__ (self, job):
		"""
		Constructor
		@params:
			`job`:    The job object
		"""
		self.script  = safefs.SafeFs._chmodX(job.script)
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

	def isRunning (self):
		"""
		Try to tell whether the job is still running.
		@returns:
			`True` if yes, otherwise `False`
		"""
		if not self.job.pid:
			return False
		return ps.exists(int(self.job.pid))

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
		try:
			self.proc = cmd.Cmd(safefs.SafeFs._chmodX(self.script), stdout = self.outfd, stderr = self.errfd)
			with open(self.pidfile, 'w') as fpid:
				fpid.write(str(self.proc.pid))
			try:
				self.proc.run()
			except KeyboardInterrupt: # pragma: no cover
				self.proc.rc = 88
		except Exception:
			from traceback import format_exc
			ex = format_exc()
			if 'Text file busy' in str(ex):
				sleep(.1)
				self.outfd.close()
				self.errfd.close()
				self.submit()
			else:
				with open(self.errfile, 'w') as f:
					f.write(str(ex))
				self.proc    = lambda: None
				self.proc.rc = 88

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
