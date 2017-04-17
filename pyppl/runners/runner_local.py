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

	def __init__ (self, job, config = {}):
		self.job       = job
		self.script    = utils.chmodX(self.job.script)
		self.ntry      = 0
		self.config    = config
		self.p         = None
		self.outp      = 0
		self.errp      = 0
	
	def _config (self, key, default = None):
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
		try:
			self.p = Popen (self.script, stdin=PIPE, stderr=PIPE, stdout=PIPE, close_fds=True)
			# have to wait, otherwise it'll continue submitting jobs
			self.job.rc(self.p.wait())
		except Exception as ex:
			open (self.job.errfile, 'w').write(str(ex))
			self.job.rc(-1)
			
	def wait (self):
		if self.job.rc() == -1: return
		while self.p is None: sleep (1)

		with open (self.job.outfile, 'w') as fout, open(self.job.errfile, 'w') as ferr:
			for line in iter(self.p.stderr.readline, ''):
				ferr.write(line)
				if self._config('echo', False):
					sys.stderr.write('! ' + line)

			for line in iter(self.p.stdout.readline, ''):
				fout.write(line)
				if self._config('echo', False):
					sys.stdout.write('- ' + line)
		self.p = None
		self.retry ()
		
	def retry (self):
		self.ntry += 1
		if self.isValid(): return
		if self._config('errorhow') != 'retry': return
		if self.ntry > self._config('errorntry'): return
		logger = self._config('logger', logging)
		paggr  = self._config('aggr')
		ptag   = self._config('tar')
		pwd    = self._config('workdir')
		# retrying
		logger.info ('[RETRY%s] %s%s.%s#%s: retrying ...' % (str(self.ntry).rjust(2), (paggr + ' -> ' if paggr else ''), pid, ptag, pwd))
		
		self.submit()
		self.wait()

		
	def isValid (self):
		return self.job.rc () in self._config('retcodes', [0])


	def flushFile (self, fn = 'stdout'):
		fname = self.outfile if fn == 'stdout' else self.errfile
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

