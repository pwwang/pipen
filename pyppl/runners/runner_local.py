# A runner wrapper for a single script
# Version: 0.0.1
# Author: pwwang@pwwang.com
# Examples: 
#	@see runner.unittest.py
#
import os, stat, sys, logging
from subprocess import Popen, check_output, list2cmdline, PIPE
from time import sleep
from getpass import getuser
from ..helpers import utils
from random import randint

class runner_local (object):
	"""
	The local runner
	"""

	def __init__ (self, job, config = {}):
		"""
		Constructor
		@params:
			`job`:    The job object
			`config`: The properties of the process
		"""
		self.job       = job
		self.script    = utils.chmodX(self.job.script)
		self.cmd2run   = list2cmdline (self.job.script)
		self.ntry      = 0
		self.config    = config
		self.p         = None
		self.outp      = 0
		self.errp      = 0
		self.submitRun = True
	
	def log (self, msg, level="info", flag=None):
		"""
		The log function with aggregation name, process id and tag integrated.
		@params:
			`msg`:   The message to log
			`levle`: The log level
			`flag`:  The flag
		"""
		if flag is None: flag = level
		flag  = flag.upper().rjust(7)
		flag  = "[%s]" % flag
		aggr  = self._config('aggr', '')
		aggr  = "@%s" % aggr if aggr else ""
		pid   = self._config('id')
		tag   = self._config('tag')
		tag   = ".%s" % tag if tag != "notag" else ""
		title = "%s%s%s:" % (pid, tag, aggr)
		func  = getattr(self._config('logger', utils.getLogger(name = title)), level)
		func ("%s %s %s" % (flag, title, msg))
	
	def _config (self, key, default = None):
		"""
		Get the configuration value by a key
		@params:
			`key`:     The key
			`default`: The default value to be used if the key is not found.
		@returns:
			The configuration value
		"""
		if '.' in key:
			config = self.config
			keys   = key.split('.')
			while keys:
				k = keys.pop(0)
				if not config.has_key(k):
					return default
				config = config[k]
			return config
		else:
			if not self.config.has_key(key):
				return default
			return self.config[key]
	
	def submit (self):
		"""
		Try to submit the job use Popen
		"""
		self.job.clearOutput()
		try:
			self.log ('Submitting job #%s ...' % self.job.index)
			self.p = Popen (self.script, stderr=open(self.job.errfile, "w"), stdout=open(self.job.outfile, "w"), close_fds=True)
		except Exception as ex:
			#self.log ('Failed to submit job #%s' % self.job.index, 'error')
			open (self.job.errfile, 'w').write(str(ex))
			self.job.rc(-1)
			self.p = None
			
	def wait(self):
		"""
		Wait for the job to finish
		"""
		if self.job.rc() == -1: return
		if self.p:
			rc = self.p.wait()
			if self._config('echo', False):
				self.flushFile('stderr')
				self.flushFile('stdout')
			if self.submitRun: self.job.rc(rc)
		
		if not self.submitRun:
			if not self.isRunning(): return 		
			while self.job.rc() == -9999:
				sleep (randint(20, 40))
				if self._config('echo', False):
					self.flushFile('stderr')
					self.flushFile('stdout')
				if not self.isRunning():
					break
			
			
	def finish (self):
		"""
		Do some cleanup work when jobs finish
		"""
		# IMPORTANT:
		# flush the output files, otherwise will cause output files not generated
		# If the job is running via ssh, the stat will not be flushed!
		workdir   = os.path.dirname ( os.path.dirname ( self.job.script ) )
		outdir    = os.path.join    ( workdir, "output" )
		scriptdir = os.path.join    ( workdir, "scripts" )
		os.utime (outdir, None)
		os.utime (scriptdir, None)
		self.job.checkOutFiles ()
		self.p = None
		self.retry ()
		
	def retry (self):
		"""
		Retry to submit and run the job if failed
		"""
		self.ntry += 1
		rc = self.job.rc ()
		if rc in self._config('retcodes', [0]) or self._config('errorhow') != 'retry' or self.ntry > self._config('errorntry'):
			return
		
		logger = self._config('logger')
		paggr  = self._config('aggr')
		ptag   = self._config('tar')
		pwd    = self._config('workdir')
		# retrying
		#logger.info ('[RETRY%s] %s%s.%s#%s: retrying ...' % (str(self.ntry).rjust(2), (paggr + ' -> ' if paggr else ''), pid, ptag, pwd))
		self.log ("Retrying job #%s ... (%s)" % (self.job.index, self.ntry))
		
		self.submit()
		self.wait()
		self.finish()
	
	def isRunning (self):
		"""
		Try to tell whether the job is still running.
		@returns:
			`True` if yes, otherwise `False`
		"""
		
		# rcfile already generated
		if self.job.rc() != -9999: return False
		
		uname = getuser()
		psout = check_output (['ps', '-u%s' % uname, '-o', 'args'])
		psout = psout.split("\n")[1:]
		if self.cmd2run in psout:
			return True
		return False

	def flushFile (self, fn = 'stdout'):
		"""
		Flush the stdout/stderr file
		@params:
			`fn`:  `stdout` or `stderr`, default: `stdout`
		"""
		fname = self.job.outfile if fn == 'stdout' else self.job.errfile
		if not os.path.exists(fname): return
		point = self.outp if fn == 'stdout' else self.errp
		def wfunc (line):
			rit  = sys.stdout.write if fn == 'stdout' else sys.stderr.write
			sign = 'STDOUT: ' if fn == 'stdout' else 'STDERR: '
			rit ("%s%s" % (sign, line))
			
		def point2 (n):
			if fn == 'stdout': self.outp += n
			else: self.errp += n
		lines = open (fname).readlines()[point:]
		point2(len(lines))
		for line in lines:
			wfunc (line)

