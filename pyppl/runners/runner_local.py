# A runner wrapper for a single script
# Version: 0.0.1
# Author: pwwang@pwwang.com
# Examples: 
#	@see runner.unittest.py
#
import os, stat, sys, logging
from subprocess import Popen, PIPE
from time import sleep

class runner_local (object):

	def __init__ (self, script, config = {}):
		self.index     = script.split('.')[-1]
		self.script    = runner_local.chmod_x(script)
		self.outfile   = script + '.stdout'
		self.errfile   = script + '.stderr'
		self.rcfile    = script + '.rc'
		self.ntry      = 0
		self.config    = config
		self.p         = None
		self.outp      = 0
		self.errp      = 0

	@staticmethod
	def chmod_x (thefile):
		thefile = os.path.realpath(thefile)
		ret = [thefile]
		try:
			st = os.stat (thefile)
			os.chmod (thefile, st.st_mode | stat.S_IEXEC)
		except:
			try:
				shebang = ''
				with open (thefile, 'r') as f:
					shebang = f.read().strip().split("\n")[0]
				if not shebang.startswith("#!"):
					raise Exception()
				ret = shebang[2:].strip().split() + [thefile]
			except Exception as e:
				raise Exception("Cannot change %s as executable or read the shebang from it." % thefile)
		return ret
	
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
		if os.path.exists(self.rcfile):
			os.remove(self.rcfile)
			
		try:
			self.p = Popen (self.script, stdin=PIPE, stderr=PIPE, stdout=PIPE, close_fds=True)
		except Exception as ex:
			open (self.errfile, 'w').write(str(ex))
			open (self.rcfile, 'w').write('-1') # not able to submit
			# don't retry if failed to submit
		sleep (0.1)
			
	def wait (self):
		if self.rc() == -1: return
		while self.p is None: sleep (1)
		open (self.rcfile, 'w').write(str(self.p.wait()))
		with open (self.outfile, 'w') as fout, open(self.errfile, 'w') as ferr:
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

	def rc (self):
		if not os.path.exists (self.rcfile):
			return -99 
		rccodestr  = ''
		with open (self.rcfile, 'r') as f:
			rccodestr = f.read().strip()
		
		return -99 if rccodestr == '' else int(rccodestr)
		
	def isValid (self):
		return self.rc () in self._config('retcodes', [0])


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

