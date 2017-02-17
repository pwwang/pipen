from runner_local import runner_local
from time import sleep
from subprocess import Popen, list2cmdline 
import os, shlex, random


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
			'ssh %s cd %s; %s' % (servers[serverid], os.getcwd(), list2cmdline(self.script))
		]
		runner_ssh.serverid += 1
		
		with open (sshfile, 'w') as f:
			f.write ('\n'.join(sshsrc) + '\n')
		
		self.script = self.chmod_x(sshfile)


		


