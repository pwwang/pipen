import os
from getpass import getuser
from subprocess import check_output, list2cmdline

from .runner import runner
from ..helpers import utils


class runner_ssh (runner):
	"""
	The sge runner

	@static variables:
		`serverid`: The incremental number used to calculate which server should be used.
		- Don't touch unless you know what's going on!

	"""
	serverid = 0

	def __init__ (self, job):
		"""
		Constructor
		@params:
			`job`:    The job object
			`config`: The properties of the process
		"""
		
		super(runner_ssh, self).__init__(job)
		# construct an ssh cmd
		sshfile      = self.job.script + '.ssh'

		conf         = {}
		if hasattr (self.job.proc, 'sshRunner'):
			conf     = self.job.proc.sshRunner
			
		if not conf.has_key('servers'):
			raise Exception ("%s: No servers found." % self.job.proc._name())
		
		servers      = conf['servers']

		serverid     = runner_ssh.serverid % len (servers)
		self.server  = servers[serverid]
		# TODO: check the server is alive?

		self.cmd2run = "cd %s; %s" % (os.getcwd(), self.cmd2run)
		sshsrc       = [
			'#!/usr/bin/env bash',
			''
			'trap "status=\\$?; echo \\$status > %s; exit \\$status" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT' % self.job.rcfile
		]

		if conf.has_key('preScript'):
			sshsrc.append (conf['preScript'])
		
		sshsrc.append ('ssh %s "%s"' % (self.server, self.cmd2run))
		
		if conf.has_key('postScript'):
			sshsrc.append (conf['postScript'])

		runner_ssh.serverid += 1
		
		open (sshfile, 'w').write ('\n'.join(sshsrc) + '\n')
		
		self.script = utils.chmodX(sshfile)

	def isRunning (self, suppose):
		"""
		Try to tell whether the job is still running using `ps`
		@params:
			`suppose`: Whether the job is supposed to be running in the context		
		@returns:
			`True` if yes, otherwise `False`
		"""
		if not self.job.proc.checkrun:
			return suppose
		# rcfile already generated
		if self.job.rc() != self.job.EMPTY_RC:
			return False
		
		uname = getuser()
		psout = check_output (['ssh', self.server, 'ps -u%s -o args' % uname])
		psout = psout.split("\n")[1:]
		return self.cmd2run in psout or "bash -c " + self.cmd2run in psout
