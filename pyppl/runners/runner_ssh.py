import os

from .runner import Runner
from .helpers import SshHelper
from ..utils import cmd
from ..exception import RunnerSshError
from multiprocessing import Value

class RunnerSsh(Runner):
	"""
	The ssh runner

	@static variables:
		`SERVERID`: The incremental number used to calculate which server should be used.
		- Don't touch unless you know what's going on!

	"""
	SERVERID = Value('i', 0)
	
	@staticmethod
	def isServerAlive(server, key = None):
		cmdlist = ['ssh', server]
		if key:
			cmdlist.append('-i')
			cmdlist.append(key)
		cmdlist.append('-o')
		cmdlist.append('BatchMode=yes')
		cmdlist.append('-o')
		cmdlist.append('ConnectionAttempts=1')
		cmdlist.append('true')
		try:
			return cmd.run(cmdlist, timeout = 3).rc == 0
		except cmd.Timeout:
			return False

	def __init__ (self, job):
		"""
		Constructor
		@params:
			`job`:    The job object
		"""
		
		super(RunnerSsh, self).__init__(job)
		# construct an ssh cmd
		sshfile      = self.job.script + '.ssh'

		conf         = {}
		if 'sshRunner' in self.job.proc.props or 'sshRunner' in self.job.proc.config:
			conf     = self.job.proc.sshRunner
		
		if not 'servers' in conf:
			raise RunnerSshError('No server found for ssh runner.')
		
		servers    = conf['servers']
		checkAlive = conf.get('checkAlive', False)
		sid        = RunnerSsh.SERVERID.value % len (servers)
		server     = servers[sid]
		key        = conf['keys'][sid] if 'keys' in conf   \
			and isinstance(conf['keys'], list)     \
			and sid < len(conf['keys']) else None
		
		if checkAlive:
			n = 0
			while not RunnerSsh.isServerAlive(server, key):
				RunnerSsh.SERVERID.value += 1
				sid    = RunnerSsh.SERVERID.value % len (servers)
				server = servers[sid]
				key    = conf['keys'][sid] if 'keys' in conf   \
					and isinstance(conf['keys'], list) \
					and sid < len(conf['keys']) else None
				n += 1
				if n >= len(servers):
					raise RunnerSshError('No server is alive.')
		RunnerSsh.SERVERID.value += 1
		
		self.cmd2run = "cd %s; %s" % (os.getcwd(), self.cmd2run)
		sshsrc       = [
			'#!/usr/bin/env bash',
			'',
		]
		
		if 'preScript' in conf:
			sshsrc.append (conf['preScript'])
		
		sshsrc.append(self.cmd2run)
		
		if 'postScript' in conf:
			sshsrc.append (conf['postScript'])

		with open (sshfile, 'w') as f:
			f.write ('\n'.join(sshsrc) + '\n')

		sshcmd = ['ssh', '-t', server]
		if key:
			sshcmd.append('-i')
			sshcmd.append(key)

		self.helper = SshHelper(sshfile, sshcmd)


