import os

from .runner import Runner
from .. import utils
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
	def isServerAlive(server, key):
		cmd = ['ssh', server]
		if key:
			cmd.append('-i')
			cmd.append(key)
		cmd.append('-o')
		cmd.append('BatchMode=yes')
		cmd.append('-o')
		cmd.append('StrictHostKeyChecking=no')
		cmd.append('-o')
		cmd.append('ConnectionAttempts=1')
		cmd.append('true')
		return utils.dumbPopen(cmd, shell = False).wait() == 0

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
		checkAlive = False if 'checkAlive' not in conf else conf['checkAlive']
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
			"echo $$ > '%s'" % self.job.pidfile,
			'trap "status=\\$?; echo \\$status >\'%s\'; exit \\$status" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT' % self.job.rcfile
		]
		
		if 'preScript' in conf:
			sshsrc.append (conf['preScript'])
		
		sshsrc.append ('ssh %s %s %s' % (server, ('-i %s' % key) if key else '', self.cmd2run))
		
		if 'postScript' in conf:
			sshsrc.append (conf['postScript'])

		with open (sshfile, 'w') as f:
			f.write ('\n'.join(sshsrc) + '\n')

		utils.chmodX(sshfile)
		submitfile = self.job.script + '.submit'
		with open(submitfile, 'w') as f:
			f.write('#!/usr/bin/env bash\n')
			f.write("exec '%s' &\n" % sshfile)
		self.script = utils.chmodX(submitfile)


