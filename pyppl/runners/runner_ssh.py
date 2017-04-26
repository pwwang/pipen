from runner_local import runner_local
from getpass import getuser
from subprocess import check_output, list2cmdline 
import os, shlex
from ..helpers import utils

class runner_ssh (runner_local):
	"""
	The sge runner

	@static variables:
		`serverid`: The incremental number used to calculate which server should be used.
		- Don't touch unless you know what's going on!

	"""
	serverid = 0

	def __init__ (self, job, config = {}):
		"""
		Constructor
		@params:
			`job`:    The job object
			`config`: The properties of the process
		"""
		
		super(runner_ssh, self).__init__(job, config)
		# construct an ssh cmd
		sshfile      = os.path.realpath(self.job.script + '.ssh')

		servers      = self._config('sshRunner.servers')
		if not servers:
			raise Exception ("No servers found.")
		serverid     = runner_ssh.serverid % len (servers)
		self.server  = servers[serverid]
		self.cmd2run = "cd %s; %s" % (os.getcwd(), list2cmdline(self.script))
		sshsrc       = [
			'#!/usr/bin/env bash',
			''
			'trap "status=\$?; echo \$status > %s; exit \$status" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT' % self.job.rcfile,
			'ssh %s "%s"' % (self.server, self.cmd2run)
		]
		runner_ssh.serverid += 1
		
		open (sshfile, 'w').write ('\n'.join(sshsrc) + '\n')
		
		self.script = utils.chmodX(sshfile)

	def isRunning (self):
		"""
		Try to tell whether the job is still running using `ps`
		@returns:
			`True` if yes, otherwise `False`
		"""
		# rcfile already generated
		if self.job.rc() != -9999: return False
		
		uname = getuser()
		psout = check_output (['ssh', self.server, 'ps -u%s -o args' % uname])
		psout = psout.split("\n")[1:]
		if self.cmd2run in psout or "bash -c " + self.cmd2run in psout:
			return True
		return False

