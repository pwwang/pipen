from runner_local import runner_local
from time import sleep
from subprocess import Popen, list2cmdline 
import os, shlex, random, logging


class runner_ssh (runner_local):

	serverid = 0

	def __init__ (self, script, config = {}):
		super(runner_ssh, self).__init__(script, config)
		# construct an ssh cmd
		sshfile = script + '.ssh'

		servers  = self._config('sshRunner.servers')
		if not servers:
			raise Exception ("No servers found.")
		serverid = runner_ssh.serverid % len (servers)
		sshsrc  = [
			'#!/usr/bin/env bash',
			''
			'trap "status=\$?; echo \$status > %s; exit \$status" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT' % self.rcfile,
			'ssh %s "cd %s; %s"' % (servers[serverid], os.getcwd(), list2cmdline(self.script))
		]
		runner_ssh.serverid += 1
		
		with open (sshfile, 'w') as f:
			f.write ('\n'.join(sshsrc) + '\n')
		
		self.script = self.chmod_x(sshfile)

	def run (self):

		if os.path.exists(self.rcfile):
			os.remove(self.rcfile)

		try:
			p  = Popen (self.script)
			rc = p.wait()
			if rc != 0:
				raise RuntimeError ('Failed to submit job %s' % self.script)
			
			outp = errp = 0
			while self.rc() == -99:
				if self._config('echo', False):
					if os.path.exists (self.outfile):
						outs = ['- ' + l.strip() for l in open(self.outfile)][outp:]
						outp += len (outs)
						for line in outs:
							sys.stdout.write (line + '\n')
					if os.path.exists (self.errfile):
						errs = ['! ' + l.strip() for l in open(self.errfile)][errp:]
						errp += len (errs)
						for line in errs:
							sys.stderr.write (line + '\n')
				sleep (5)
			

		except Exception as ex:
			with open (self.rcfile, 'w') as f:
				f.write('1')
			self._config('logger', logging).debug ('[   ERROR] %s.%s#%s: %s' % (self._config('id'), self._config('tag'), self.index, ex))
			
		self.ntry += 1
		if not self.isValid() and self._config('errorhow') == 'retry' and self.ntry <= self._config('errorntry'):
			self._config('logger', logging).info ('[RETRY %s] %s.%s#%s: %s' % (self.ntry, self._config('id'), self._config('tag'), self.index, self._config('workdir')))
			self.run()
		


