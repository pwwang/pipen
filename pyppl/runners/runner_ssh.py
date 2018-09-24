import os

from .runner import Runner
from .helpers import SshHelper
from ..utils import cmd
from ..exception import RunnerSshError
from multiprocessing import Value, Lock, Array

class RunnerSsh(Runner):
	"""
	The ssh runner

	@static variables:
		`SERVERID`: The incremental number used to calculate which server should be used.
		- Don't touch unless you know what's going on!

	"""
	SERVERID     = Value('i', 0)
	LIVE_SERVERS = None
	LOCK         = Lock()
	
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
		except cmd.Timeout: # pragma: no cover
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
		
		servers    = conf.get('servers', [])
		keys       = conf.get('keys', [])
		checkAlive = conf.get('checkAlive', False)
		if not servers:
			raise RunnerSshError('No server found for ssh runner.')

		if checkAlive:
			with RunnerSsh.LOCK:
				if not RunnerSsh.LIVE_SERVERS:
					live_server_ids = []
					for i, server in enumerate(servers):
						if RunnerSsh.isServerAlive(server, keys[i] if keys else None):
							live_server_ids.append(i)
					RunnerSsh.LIVE_SERVERS = Array('i', live_server_ids)
		else:
			RunnerSsh.LIVE_SERVERS = list(range(len(servers)))

		if len(RunnerSsh.LIVE_SERVERS) == 0:
			raise RunnerSshError('No server is alive.')

		sid    = RunnerSsh.LIVE_SERVERS[RunnerSsh.SERVERID.value % len (RunnerSsh.LIVE_SERVERS)]
		server = servers[sid]
		key    = keys[sid] if keys else None
		
		RunnerSsh.SERVERID.value += 1
		
		self.cmd2run = "cd %s; %s" % (os.getcwd(), self.cmd2run)
		sshsrc       = [
			'#!/usr/bin/env bash',
			'# run on server: {}'.format(server),
			''
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


