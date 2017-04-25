# A runner wrapper for a single script
# Version: 0.0.1
# Author: pwwang@pwwang.com
# Examples: 
#	@see runner.unittest.py
#
import os, stat, sys, logging
from subprocess import Popen, PIPE
from time import sleep
from ..helpers import utils

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
		self.ntry      = 0
		self.config    = config
		self.p         = None
		self.outp      = 0
		self.errp      = 0
	
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
		try:
			self.p = Popen (self.script, stdin=PIPE, stderr=PIPE, stdout=PIPE, close_fds=True)
			# have to wait, otherwise it'll continue submitting jobs
			self.job.rc(self.p.wait())
		except Exception as ex:
			open (self.job.errfile, 'w').write(str(ex))
			self.job.rc(-1)
			
	def wait (self, checkP = True):
		"""
		Wait for the job to finish
		@params:
			`checkP`:  Whether to check the Popen handler or not
		"""
		if self.job.rc() == -1: return
		while checkP and self.p is None: sleep (1)
		
		if checkP:
			with open (self.job.outfile, 'w') as fout, open(self.job.errfile, 'w') as ferr:
				for line in iter(self.p.stderr.readline, ''):
					ferr.write(line)
					if self._config('echo', False):
						sys.stderr.write('! ' + line)
	
				for line in iter(self.p.stdout.readline, ''):
					fout.write(line)
					if self._config('echo', False):
						sys.stdout.write('- ' + line)
		else:
			while self.job.rc() == -99:
				if self._config('echo', False):
					self.flushFile('stdout')
					self.flushFile('stderr')
				sleep (5)
		# IMPORTANT:
		# flush the output files, otherwise will cause output files not generated
		# If the job is running via ssh, the stat will not be flushed!
		os.utime (self._config('outdir', os.path.dirname(os.path.dirname(self.job.script))), None)
		self.p = None
		self.retry ()
		
	def retry (self):
		"""
		Retry to submit and run the job if failed
		"""
		self.ntry += 1
		if self.isValid(): return
		if self._config('errorhow') != 'retry': return
		if self.ntry > self._config('errorntry'): return
		logger = self._config('logger')
		paggr  = self._config('aggr')
		ptag   = self._config('tar')
		pwd    = self._config('workdir')
		# retrying
		logger.info ('[RETRY%s] %s%s.%s#%s: retrying ...' % (str(self.ntry).rjust(2), (paggr + ' -> ' if paggr else ''), pid, ptag, pwd))
		
		self.submit()
		self.wait()
	
	
	def isRunning (self):
		"""
		Try to tell whether the job is still running.
		For local runner, if you leave the main thread, the job will quite
		@returns:
			`True` if yes, otherwise `False`
		"""
		return False
		
	def isValid (self):
		"""
		Tell the return code is valid
		@returns:
			`True` if yes, otherwise `False`
		"""
		return self.job.rc () in self._config('retcodes', [0])


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
			sign = '- ' if fn == 'stdout' else '! '
			rit ("%s%s" % (sign, line))
			
		def point2 (n):
			if fn == 'stdout': self.outp += n
			else: self.errp += n
		lines = open (fname).readlines()[point:]
		point2(len(lines))
		for line in lines:
			wfunc (line)

