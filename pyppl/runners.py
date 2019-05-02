"""
Built-in runners for PyPPL
"""
import re
import sys
from os import getcwd
from box import Box
from psutil import pid_exists
from multiprocessing import Lock
from .utils import killtree, chmodX, cmdy
from .exceptions import RunnerSshError

class Runner (object):
	"""
	The base runner class
	"""

	INTERVAL  = 1
	FLUSHLOCK = Lock()

	def __init__ (self, job):
		"""
		Constructor
		@params:
			`job`: The job object
		"""
		self.job = job

	def wrapScript(self, head = None, pre_script = None, post_script = None,
		real_script = None, suffix = None, save_oe = True):

		suffix      = suffix or '.' + self.__class__.__name__[6:].lower()
		self.script = self.job.script + suffix

		real_script = real_script or ' '.join(cmdy._shquote(x) for x in chmodX(self.job.script))
		# redirect stdout and stderr
		if save_oe:
			if isinstance(real_script, list):
				real_script[-1] += ' 1> %s 2> %s' % (cmdy._shquote(self.job.outfile), cmdy._shquote(self.job.errfile))
			else:
				real_script += ' 1> %s 2> %s' % (cmdy._shquote(self.job.outfile), cmdy._shquote(self.job.errfile))

		src       = ['#!/usr/bin/env bash']
		srcappend = src.append
		srcextend = src.extend
		addsrc    = lambda code: (srcextend if isinstance(code, list) else srcappend)(code) if code else None

		addsrc(head)
		addsrc('#')
		addsrc('# Collect return code on exit')
		addsrc('trap "status=\\$?; echo \\$status > %s; exit \\$status" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT' % cmdy._shquote(self.job.rcfile))
		addsrc('#')
		addsrc('# Run pre-script')
		addsrc(pre_script)
		addsrc('#')
		addsrc('# Run the real script')
		addsrc(real_script)
		addsrc('#')
		addsrc('# Run post-script')
		addsrc(post_script)
		addsrc('#')

		with open(self.script, 'w') as fscript:
			fscript.write('\n'.join(src))

	@property
	def runnercmd(self):
		return cmdy.bash(self.script, _hold = True).cmd

	def kill(self):
		"""
		Try to kill the running jobs if I am exiting
		"""
		if self.job.pid:
			killtree(int(self.job.pid), killme = True, sig = 9)

	def submit (self):
		"""
		Try to submit the job
		"""
		cmd = cmdy.bash(self.script, _bg = True)
		cmd.rc = 0
		self.job.pid = cmd.pid
		return cmd

	def isRunning (self):
		"""
		Try to tell whether the job is still running.
		@returns:
			`True` if yes, otherwise `False`
		"""
		if not self.job.pid:
			return False
		return pid_exists(int(self.job.pid))

class RunnerLocal (Runner):
	"""
	Constructor
	@params:
		`job`:    The job object
		`config`: The properties of the process
	"""

	def __init__ (self, job):
		super(RunnerLocal, self).__init__(job)

		conf = job.config.get('runnerOpts', {})
		conf = conf.get('localRunner', {})

		pre_script  = conf.get('preScript')
		post_script = conf.get('postScript')

		self.wrapScript(pre_script = pre_script, post_script = post_script)


class RunnerDry (Runner):
	"""
	The dry runner
	"""

	def __init__ (self, job):
		"""
		Constructor
		@params:
			`job`:    The job object
		"""
		super(RunnerDry, self).__init__(job)
		from .proc import Proc

		real_script = []

		for val in job.output.values():
			if val['type'] in Proc.OUT_VARTYPE:
				continue

			if val['type'] in Proc.OUT_FILETYPE:
				real_script.append("touch %s" % cmdy._shquote(val['data']))
			elif val['type'] in Proc.OUT_DIRTYPE:
				real_script.append("mkdir -p %s" % cmdy._shquote(val['data']))

		self.wrapScript(real_script = real_script)


class RunnerSsh(Runner):
	"""
	The ssh runner
	"""
	LIVE_SERVERS = None
	LOCK         = Lock()
	SSH          = cmdy.ssh.bake(_dupkey = True)

	@staticmethod
	def isServerAlive(server, key = None, timeout = 3, ssh = 'ssh'):
		"""
		Check if an ssh server is alive
		@params:
			`server`: The server to check
			`key`   : The keyfile to login the server
			`timeout`: The timeout to check whether the server is alive.
		@returns:
			`True` if alive else `False`
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

	def __init__ (self, job):
		"""
		Constructor
		@params:
			`job`:    The job object
		"""

		super(RunnerSsh, self).__init__(job)
		# construct an ssh cmd

		conf       = self.job.config.get('runnerOpts', {}).get('sshRunner', {})

		ssh         = conf.get('ssh', 'ssh')
		servers     = conf.get('servers', [])
		keys        = conf.get('keys', [])
		check_alive = conf.get('checkAlive', False)
		if not servers:
			raise RunnerSshError('No server found for ssh runner.')

		with RunnerSsh.LOCK:
			if RunnerSsh.LIVE_SERVERS is None:
				if check_alive is True:
					RunnerSsh.LIVE_SERVERS = [
						i for i, server in enumerate(servers)
						if RunnerSsh.isServerAlive(server, keys[i] if keys else None, ssh = ssh)
					]
				elif check_alive is False:
					RunnerSsh.LIVE_SERVERS = list(range(len(servers)))
				else:
					RunnerSsh.LIVE_SERVERS = [
						i for i, server in enumerate(servers)
						if RunnerSsh.isServerAlive(server, keys[i] if keys else None, check_alive, ssh = ssh)
					]

		if not RunnerSsh.LIVE_SERVERS:
			raise RunnerSshError('No server is alive.')

		sid    = RunnerSsh.LIVE_SERVERS[job.index % len(RunnerSsh.LIVE_SERVERS)]
		server = servers[sid]
		key    = keys[sid] if keys else False

		head       = '# run on server: {}'.format(server)
		pre_script  = conf.get('preScript')
		real_script = [
			'cd %s' % cmdy._shquote(getcwd()),
			' '.join(cmdy._shquote(x) for x in chmodX(self.job.script))
		]
		post_script = conf.get('postScript')
		self.wrapScript(head = head, pre_script = pre_script,
			real_script = real_script, post_script = post_script)

		baked = dict(t = server, i = key, _exe = ssh)
		self.ssh = RunnerSsh.SSH.bake(**baked)

	def submit(self):
		"""
		Submit the job
		@returns:
			The `utils.cmd.Cmd` instance if succeed
			else a `Box` object with stderr as the exception and rc as 1
		"""
		cmd = self.ssh(_ = cmdy.ls(self.script, _hold = True).cmd)
		if cmd.rc != 0:
			dbox        = Box()
			dbox.rc     = self.job.RC_SUBMITFAILED
			dbox.cmd    = cmd.cmd
			dbox.pid    = -1
			dbox.stderr = cmd.stderr + '\nProbably the server ({}) is not using the same file system as the local machine.\n'.format(self.ssh.keywords['t'])
			return dbox

		cmd = self.ssh(_bg = True, _ = self.runnercmd)
		cmd.rc = 0
		self.job.pid = cmd.pid
		return cmd

	def kill(self):
		"""
		Kill the job
		"""
		cmd = cmdy.python(
			_exe = sys.executable,
			c    = 'from pyppl.utils import killtree; killtree(%s, killme = True)' % self.job.pid,
			_hold = True).cmd
		self.ssh(_ = cmd)

	def isRunning(self):
		"""
		Tell if the job is alive
		@returns:
			`True` if it is else `False`
		"""
		if not self.job.pid:
			return False

		cmd = cmdy.python(
			_exe = sys.executable,
			c    = 'from psutil import pid_exists; assert {pid} > 0 and pid_exists({pid})'.format(pid = self.job.pid),
			_hold = True).cmd
		return self.ssh(_ = cmd).rc == 0

class RunnerSge (Runner):
	"""
	The sge runner
	"""

	INTERVAL = 5

	def __init__ (self, job):
		"""
		Constructor
		@params:
			`job`:    The job object
			`config`: The properties of the process
		"""
		super(RunnerSge, self).__init__(job)

		conf = self.job.config.get('runnerOpts', {})
		conf = conf.get('sgeRunner', {}).copy()

		self.qsub  = cmdy.qsub.bake(_exe  = conf.get('qsub'))
		self.qstat = cmdy.qstat.bake(_exe = conf.get('qstat'))
		self.qdel  = cmdy.qdel.bake(_exe  = conf.get('qdel'))

		head = []
		sge_bign = conf.pop('sge.N', '.'.join([
			self.job.config['proc'],
			self.job.config['tag'],
			self.job.config['suffix'],
			str(self.job.index + 1)
		]))
		head.append('#$ -N %s' % sge_bign)

		sge_q = conf.pop('sge.q', None)
		if sge_q:
			head.append('#$ -q %s' % sge_q)

		sge_j = conf.pop('sge.j', None)
		if sge_j:
			head.append('#$ -j %s' % sge_j)

		head.append('#$ -cwd')

		sge_bigm = conf.pop('sge.M', None)
		if sge_bigm:
			head.append('#$ -M %s' % sge_bigm)

		sge_m = conf.pop('sge.m', None)
		if sge_m:
			head.append('#$ -m %s' % sge_m)

		head.append('#$ -o %s' % self.job.outfile)
		head.append('#$ -e %s' % self.job.errfile)

		for k in sorted(conf.keys()):
			if not k.startswith ('sge.'): continue
			val = conf[k]
			k = k[4:].strip()
			src = '#$ -' + k
			if val != True: # {'notify': True} ==> -notify
				src += ' ' + str(val)
			head.append(src)

		pre_script = conf.get('preScript')
		post_script = conf.get('postScript')

		self.wrapScript(head = head, pre_script = pre_script,
			post_script = post_script, save_oe = False)

	def submit(self):
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
				cmd.rc = self.job.RC_SUBMITFAILED
			else:
				self.job.pid = match.group(1)
		return cmd

	def kill(self):
		"""
		Kill the job
		"""
		self.qdel(force = self.job.pid)

	def isRunning(self):
		"""
		Tell if the job is alive
		@returns:
			`True` if it is else `False`
		"""
		if not self.job.pid:
			return False
		return self.qstat(j = self.job.pid).rc == 0

class RunnerSlurm (Runner):
	"""
	The slurm runner
	"""

	INTERVAL = 5

	def __init__ (self, job):
		"""
		Constructor
		@params:
			`job`:    The job object
			`config`: The properties of the process
		"""
		super(RunnerSlurm, self).__init__(job)

		conf = self.job.config.get('runnerOpts', {})
		conf = conf.get('slurmRunner', {}).copy()

		self.sbatch  = cmdy.sbatch.bake(_exe = conf.get('sbatch'))
		self.srun    = cmdy.srun.bake(_exe = conf.get('srun'))
		self.squeue  = cmdy.squeue.bake(_exe = conf.get('squeue'))
		self.scancel = cmdy.scancel.bake(_exe = conf.get('scancel'))

		head = []
		slurm_bigj = conf.pop('slurm.J', '.'.join([
			self.job.config['proc'],
			self.job.config['tag'],
			self.job.config['suffix'],
			str(self.job.index + 1)
		]))
		head.append('#SBATCH -J %s' % slurm_bigj)
		head.append('#SBATCH -o %s' % self.job.outfile)
		head.append('#SBATCH -e %s' % self.job.errfile)

		for k in sorted(conf.keys()):
			if not k.startswith ('slurm.'): continue
			val = conf[k]
			k = k[6:].strip()
			src = '#SBATCH -' + (k if len(k)==1 else '-' + k)
			if val != True: # {'notify': True} ==> -notify
				src += ' ' + str(val)
			head.append(src)

		real_script = self.srun(*chmodX(self.job.script), _hold = True).cmd
		pre_script  = conf.get('preScript')
		post_script = conf.get('postScript')

		self.wrapScript(head = head, pre_script = pre_script, real_script = real_script,
			post_script = post_script, save_oe = False)

	def submit(self):
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
				cmd.rc = 1
			else:
				self.job.pid = match.group(1)
		return cmd

	def kill(self):
		"""
		Kill the job
		"""
		self.scancel(self.job.pid)

	def isRunning(self):
		"""
		Tell if the job is alive
		@returns:
			`True` if it is else `False`
		"""
		if not self.job.pid:
			return False
		return self.squeue(j = self.job.pid).rc == 0
