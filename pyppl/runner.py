"""
Built-in runners for PyPPL
"""
import re
import sys
from os import getcwd
from multiprocessing import Lock
from psutil import pid_exists
from .job import Job, FILE_STDOUT, FILE_STDERR, DIR_OUTPUT, RC_ERROR_SUBMISSION
from .utils import killtree, chmodX, cmdy, Box
from .exception import RunnerSshError

class RunnerLocal(Job):
	"""@API
	The local runer
	"""
	@property
	def pid(self):
		"""
		Get the pid in integer format
		@returns:
			(int): The pid
		"""
		ret = super().pid or -1
		return int(ret)

	@pid.setter
	def pid(self, val):
		super(RunnerLocal, type(self)).pid.fset(self, val)

	def killImpl(self):
		"""
		Try to kill the running jobs if I am exiting
		"""
		if self.pid > 0:
			killtree(self.pid, killme = True)

	def submitImpl(self):
		"""
		Try to submit the job
		"""
		cmd = cmdy.bash(self.script, _raise = False, _bg = True)
		cmd.rc = 0
		self.pid = cmd.pid
		return cmd

	def isRunningImpl (self):
		"""
		Try to tell whether the job is still running.
		@returns:
			`True` if yes, otherwise `False`
		"""
		if self.pid < 0:
			return False
		return pid_exists(self.pid)

class RunnerDry(RunnerLocal):
	"""@API
	The dry runner
	"""
	@property
	def scriptParts(self):
		parts  = super().scriptParts
		procclass = self.proc.__class__

		parts.pre += '\n'
		parts.pre += '# Dry-run script to create empty output files and directories.\n'
		parts.pre += '\n'

		for vtype, value in self.output.values():
			if vtype in procclass.OUT_FILETYPE:
				parts.pre += "touch %s\n" % cmdy._shquote(str(self.dir / DIR_OUTPUT / value))
			elif vtype in procclass.OUT_DIRTYPE:
				parts.pre += "mkdir -p %s\n" % cmdy._shquote(str(self.dir / DIR_OUTPUT / value))
		# don't run the real script
		parts.command = ''
		parts.saveoe  = False
		return parts

class RunnerSsh(RunnerLocal):
	"""@API
	The ssh runner
	@static variables:
		LIVE_SERVERS (list): The live servers
	"""
	LIVE_SERVERS = None
	LOCK         = Lock()
	SSH          = cmdy.ssh.bake(_dupkey = True)

	@staticmethod
	def isServerAlive(server, key = None, timeout = 3, ssh = 'ssh'):
		"""@API
		Check if an ssh server is alive
		@params:
			server (str): The server to check
			key (str): The keyfile to login the server
			timeout (int|float): The timeout to check whether the server is alive.
		@returns:
			(bool): `True` if alive else `False`
		"""
		params = {'': server, '_timeout': timeout, '_': 'true'}
		if key:
			params['i'] = key
		params['o']    = ['BatchMode=yes', 'ConnectionAttempts=1']
		params['_exe'] = ssh
		try:
			cmd = RunnerSsh.SSH(**params)
			return cmd.rc == 0
		except cmdy.CmdyTimeoutException:
			return False

	def __init__ (self, index, proc):

		super().__init__(index, proc)

		ssh         = self.config.get('ssh', 'ssh')
		servers     = self.config.get('servers', [])
		keys        = self.config.get('keys', [])
		check_alive = self.config.get('checkAlive', False)
		if not servers:
			raise RunnerSshError('No server found for ssh runner.')

		with RunnerSsh.LOCK:
			if RunnerSsh.LIVE_SERVERS is None:
				self.logger('Checking status of servers ...', level = 'debug')
				if check_alive is True:
					RunnerSsh.LIVE_SERVERS = [i for i, server in enumerate(servers)
						if RunnerSsh.isServerAlive(server, keys and keys[i], ssh = ssh)]
				elif check_alive is False:
					RunnerSsh.LIVE_SERVERS = list(range(len(servers)))
				else:
					RunnerSsh.LIVE_SERVERS = [
						i for i, server in enumerate(servers)
						if RunnerSsh.isServerAlive(
							server, keys and keys[i], timeout = check_alive, ssh = ssh)]

		if not RunnerSsh.LIVE_SERVERS:
			raise RunnerSshError('No server is alive.')

		sid    = RunnerSsh.LIVE_SERVERS[self.index % len(RunnerSsh.LIVE_SERVERS)]
		server = servers[sid]

		self.ssh = RunnerSsh.SSH.bake(
			t = server, i = keys[sid] if keys else False, _exe = ssh)

	@property
	def scriptParts(self):
		parts = super().scriptParts
		parts.header  = '#\n# Running job on server: %s\n#' % self.ssh.keywords['t']
		parts.pre    += '\ncd %s' % cmdy._shquote(getcwd())
		return parts

	def submitImpl(self):
		"""
		Submit the job
		@returns:
			The `utils.cmd.Cmd` instance if succeed
			else a `Box` object with stderr as the exception and rc as 1
		"""
		cmd = self.ssh(_ = cmdy.ls(self.script, _hold = True).cmd)
		if cmd.rc != 0:
			dbox        = Box()
			dbox.rc     = RC_ERROR_SUBMISSION
			dbox.cmd    = cmd.cmd
			dbox.pid    = -1
			dbox.stderr = cmd.stderr
			dbox.stderr += '\nProbably the server ({})'.format(self.ssh.keywords['t'])
			dbox.stderr += ' is not using the same file system as the local machine.\n'
			return dbox

		cmd = self.ssh(_bg = True, _ = chmodX(self.script))
		cmd.rc = 0
		self.pid = cmd.pid
		return cmd

	def killImpl(self):
		"""
		Kill the job
		"""
		cmd = cmdy.python(
			_exe = sys.executable,
			c    = 'from pyppl.utils import killtree; killtree(%s, killme = True)' % self.pid,
			_hold = True).cmd
		self.ssh(_ = cmd)

	def isRunningImpl(self):
		"""
		Tell if the job is alive
		@returns:
			`True` if it is else `False`
		"""
		if self.pid < 0:
			return False

		cmd = cmdy.python(
			_exe  = sys.executable,
			c     = 'from psutil import pid_exists; ' + \
				'assert {pid} > 0 and pid_exists({pid})'.format(pid = self.pid),
			_hold = True).cmd
		return self.ssh(_ = cmd).rc == 0

class RunnerSge (Job):
	"""@API
	The sge runner
	@static variables:
		POLL_INTERVAL (int=5): The inteval between each job state polling.
	"""

	POLL_INTERVAL = 5

	def __init__ (self, index, proc):
		"""
		Constructor
		"""
		super().__init__(index, proc)

		self.qsub  = cmdy.qsub.bake(_exe  = self.config.get('qsub'))
		self.qstat = cmdy.qstat.bake(_exe = self.config.get('qstat'))
		self.qdel  = cmdy.qdel.bake(_exe  = self.config.get('qdel'))

	@property
	def scriptParts(self):
		parts = super().scriptParts

		sge_n = self.config.get('sge.N', '%s.%s.%s.%s' % (
			self.proc.id, self.proc.tag, self.proc.suffix, self.index + 1))
		parts.header += '#$ -N %s\n' % self.proc.template(
			sge_n, **self.proc.envs).render(self.data)
		parts.header += '#$ -cwd\n'
		parts.header += '#$ -o %s\n' % (self.dir / FILE_STDOUT)
		parts.header += '#$ -e %s\n' % (self.dir / FILE_STDERR)

		for key in sorted(self.config):
			if not key.startswith ('sge.') or key == 'sge.N':
				continue
			if key in ('sge.o', 'sge.e', 'sge.cwd'):
				raise ValueError('-o, -e and -cwd are not allowed to be configured.')
			val = self.config[key]
			key = key[4:]
			# {'notify': True} ==> -notify
			src = key if val is True else key + ' ' + str(val)
			parts.header += '#$ -%s\n' % src

		parts.saveoe = False
		return parts

	def submitImpl(self):
		"""
		Submit the job
		@returns:
			The `utils.cmd.Cmd` instance if succeed
			else a `Box` object with stderr as the exception and rc as 1
		"""
		cmd = self.qsub(self.script)
		if cmd.rc == 0:
			# Your job 6556149 ("pSort.notag.3omQ6NdZ.0") has been submitted
			match = re.search(r'\s(\d+)\s', cmd.stdout.strip())
			if not match:
				cmd.rc = RC_ERROR_SUBMISSION
			else:
				self.pid = match.group(1)
		return cmd

	def killImpl(self):
		"""
		Kill the job
		"""
		self.qdel(force = self.pid)

	def isRunningImpl(self):
		"""
		Tell if the job is alive
		@returns:
			`True` if it is else `False`
		"""
		if not self.pid:
			return False
		return self.qstat(j = self.pid).rc == 0

class RunnerSlurm (Job):
	"""@API
	The slurm runner
	@static variables:
		POLL_INTERVAL (int=5): The inteval between each job state polling.
	"""

	INTERVAL = 5

	def __init__ (self, index, proc):
		"""
		Constructor
		@params:
			`job`:    The job object
			`config`: The properties of the process
		"""
		super(RunnerSlurm, self).__init__(index, proc)

		self.sbatch  = cmdy.sbatch.bake(_exe = self.config.get('sbatch'))
		self.srun    = cmdy.srun.bake(_exe = self.config.get('srun'))
		self.squeue  = cmdy.squeue.bake(_exe = self.config.get('squeue'))
		self.scancel = cmdy.scancel.bake(_exe = self.config.get('scancel'))

	@property
	def scriptParts(self):
		parts = super().scriptParts

		slurm_j = self.config.get('slurm.J')
		slurm_j = slurm_j or self.config.get('slurm.job-name')
		slurm_j = slurm_j or '%s.%s.%s.%s' % (
			self.proc.id, self.proc.tag, self.proc.suffix, self.index + 1)
		parts.header += '#SBATCH -J %s\n' % self.proc.template(
			slurm_j, **self.proc.envs).render(self.data)
		parts.header += '#SBATCH -o %s\n' % (self.dir / FILE_STDOUT)
		parts.header += '#SBATCH -e %s\n' % (self.dir / FILE_STDERR)

		for key in sorted(self.config):
			if not key.startswith ('slurm.') or key in ('slurm.J', 'slurm.job-name'):
				continue
			if key in ('slurm.o', 'slurm.e'):
				raise ValueError('-o and -e are not allowed to be configured.')
			val = self.config[key]
			key = key[6:]
			# {'notify': True} ==> -notify
			if len(key) == 1:
				src = '-' + key if val is True else '-' + key + ' ' + str(val)
			else:
				src = '--' + key if val is True else '--' + key + '=' + str(val)
			parts.header += '#SBATCH %s\n' % src

		parts.saveoe  = False
		srunopts = self.config.get('srun.opts', '').split()
		srunopts.extend(parts.command)
		parts.command = self.srun(*srunopts, _hold = True).cmd

		return parts

	def submitImpl(self):
		"""
		Submit the job
		@returns:
			The `utils.cmd.Cmd` instance if succeed
			else a `Box` object with stderr as the exception and rc as 1
		"""
		cmd = self.sbatch(self.script)
		if cmd.rc == 0:
			# Submitted batch job 1823334668
			match = re.search(r'\s(\d+)$', cmd.stdout.strip())
			if not match:
				cmd.rc = RC_ERROR_SUBMISSION
			else:
				self.pid = match.group(1)
		return cmd

	def killImpl(self):
		"""
		Kill the job
		"""
		self.scancel(self.pid)

	def isRunningImpl(self):
		"""
		Tell if the job is alive
		@returns:
			`True` if it is else `False`
		"""
		if not self.pid:
			return False
		return self.squeue(j = self.pid).rc == 0
