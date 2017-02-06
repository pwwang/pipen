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
		self.index   = script.split('.')[-1]
		self.script  = runner_local.chmod_x(script)
		self.outfile = script + '.stdout'
		self.errfile = script + '.stderr'
		self.rcfile  = script + '.rc'
		self.ntry    = 0
		self.config  = config

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

	def run (self):

		if os.path.exists(self.rcfile):
			os.remove(self.rcfile)
		
		try:
			sleep(.1) # not sleeping causes text file busy. Why?
			p      = Popen (self.script, stdin=PIPE, stderr=PIPE, stdout=PIPE)
			fout   = open (self.outfile, 'w')
			ferr   = open (self.errfile, 'w')
			#stdstr = ""
			for line in iter(p.stderr.readline, ''):
				ferr.write(line)
				sys.stderr.write(line)

			for line in iter(p.stdout.readline, ''):
				fout.write(line)
				if self._config('echo', False):
					sys.stdout.write(line)
			
			fout.close()
			ferr.close()

			with open (self.rcfile, 'w') as f:
				f.write(str(p.wait()))
		except Exception as ex:
			with open (self.errfile, 'w') as f:
				f.write (str(ex))
			with open (self.rcfile, 'w') as f:
				f.write('1')
			self._config('logger', logging).debug ('[  ERROR] %s.%s#%s: %s' % (self._config('id'), self._config('tag'), self.index, str(ex)))
		
		self.ntry += 1
		if not self.isValid() and self._config('errorhow') == 'retry' and self.ntry <= self._config('errorntry'):
			self._config('logger', logging).info ('[RETRY %s] %s.%s#%s: %s' % (self.ntry, self._config('id'), self._config('tag'), self.index, self._config('workdir')))
			sleep (.1)
			self.run()


	def rc (self):
		if not os.path.exists (self.rcfile):
			return -99 
		rccodestr  = ''
		with open (self.rcfile, 'r') as f:
			rccodestr = f.read().strip()
		
		return -99 if rccodestr == '' else int(rccodestr)
		
	def isValid (self):
		return self.rc () in self._config('retcodes', [0])



