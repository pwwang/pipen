"""
Built-in runners for PyPPL
"""
import re
import sys
import cmdy
from os import getcwd
from psutil import pid_exists
from multiprocessing import Lock
from .utils import killtree, chmodX
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
			`job`:    The job object
		"""
		self.job        = job

	def wrapScript(self, head = None, preScript = None, 
		postScript = None, realScript = None, suffix = None):
		suffix      = suffix or '.' + self.__class__.__name__[6:].lower()
		self.script = self.job.script + suffix

		realScript = realScript or ' '.join(cmdy._shquote(x) for x in chmodX(self.job.script))
		# redirect stdout and stderr
		if isinstance(realScript, list):
			realScript[-1] += ' 1> %s 2> %s' % (cmdy._shquote(self.job.outfile), cmdy._shquote(self.job.errfile))
		else:
			realScript += ' 1> %s 2> %s' % (cmdy._shquote(self.job.outfile), cmdy._shquote(self.job.errfile))

		src       = ['#!/usr/bin/env bash']
		srcappend = src.append
		srcextend = src.extend
		addsrc    = lambda code: (srcextend if isinstance(code, list) else srcappend)(code) if code else None

		addsrc(head)
		addsrc('#')
		addsrc('# Collect return code on exit')
		addsrc('trap "status=\\$?; echo \\$status > %s; exit \\$status" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT' % cmdy._shquote(self.job.rcfile))
		addsrc('#')
		addsrc('# Save pid')
		addsrc('echo $$ > %s' % cmdy._shquote(self.job.pidfile))
		addsrc('#')
		addsrc('# Run pre-script')
		addsrc(preScript)
		addsrc('#')
		addsrc('# Run the real script')
		addsrc(realScript)
		addsrc('#')
		addsrc('# Run post-script')
		addsrc(postScript)
		addsrc('#')

		with open(self.script, 'w') as f:
			f.write('\n'.join(src))

	@property
	def runnercmd(self):
		return cmdy.bash(self.script, _dry = True).cmd

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
		c = cmdy.bash(self.script)
		c.rc = 0
		return c

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

		preScript  = conf.get('preScript')
		postScript = conf.get('postScript')

		self.wrapScript(preScript = preScript, postScript = postScript)


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

		realScript = []

		for val in job.output.values():
			if val['type'] in Proc.OUT_VARTYPE:
				continue
				
			if val['type'] in Proc.OUT_FILETYPE:
				realScript.append("touch '{}'".format(val['data']))
			elif val['type'] in Proc.OUT_DIRTYPE:
				realScript.append("mkdir -p '{}'".format(val['data']))

		self.wrapScript(realScript = realScript)


class RunnerSsh(Runner):
	"""
	The ssh runner
	"""
	LIVE_SERVERS = None
	LOCK         = Lock()
	SSH          = cmdy.ssh.bake(_dupkey = True, _okcode = '0~256')
	
	@staticmethod
	def isServerAlive(server, key = None, timeout = 3):
		"""
		Check if an ssh server is alive
		@params:
			`server`: The server to check
			`key`   : The keyfile to login the server 
			`timeout`: The timeout to check whether the server is alive.
		@returns:
			`True` if alive else `False`
		"""
		params = {'': server, '_timout': timeout, '_': 'true'}
		if key:
			params['i'] = key
		params['o'] = ['BatchMode=yes', 'ConnectionAttempts=1']
		try:
			c = RunnerSsh.SSH(**params)
			return c.rc == 0
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

		conf         = {}
		if 'sshRunner' in self.job.config.get('runnerOpts', {}):
			conf = self.job.config['runnerOpts']['sshRunner']
		
		servers    = conf.get('servers', [])
		keys       = conf.get('keys', [])
		checkAlive = conf.get('checkAlive', False)
		if not servers:
			raise RunnerSshError('No server found for ssh runner.')

		with RunnerSsh.LOCK:
			if RunnerSsh.LIVE_SERVERS is None:
				if checkAlive is True:
					RunnerSsh.LIVE_SERVERS = [
						i for i, server in enumerate(servers)
						if RunnerSsh.isServerAlive(server, keys[i] if keys else None)
					]
				elif checkAlive is False:
					RunnerSsh.LIVE_SERVERS = list(range(len(servers)))
				else:
					RunnerSsh.LIVE_SERVERS = [
						i for i, server in enumerate(servers)
						if RunnerSsh.isServerAlive(server, keys[i] if keys else None, checkAlive)
					]

		if not RunnerSsh.LIVE_SERVERS:
			raise RunnerSshError('No server is alive.')

		sid    = RunnerSsh.LIVE_SERVERS[job.index % len(RunnerSsh.LIVE_SERVERS)]
		server = servers[sid]
		key    = keys[sid] if keys else False
		
		head       = '# run on server: {}'.format(server)
		preScript  = conf.get('preScript')
		realScript = [
			'cd %s' % cmdy._shquote(getcwd()),
			' '.join(cmdy._shquote(x) for x in chmodX(self.job.script))
		]
		postScript = conf.get('postScript')
		self.wrapScript(head = head, preScript = preScript, 
			realScript = realScript, postScript = postScript)
		
		baked = dict(t = server, i = key)		
		self.ssh = RunnerSsh.SSH.bake(**baked)

	def submit(self):
		"""
		Submit the job
		@returns:
			The `utils.cmd.Cmd` instance if succeed 
			else a `Box` object with stderr as the exception and rc as 1
		"""
		c = self.ssh(_ = cmdy.ls(self.script, _dry = True).cmd)
		if c.rc != 0:
			c.stderr += 'Probably the server ({}) is not using the same file system as the local machine.\n'.format(self.sshcmd)
			return c

		c = self.ssh(_bg = True, _ = self.runnercmd)
		c.rc = 0
		return c

	def kill(self):
		"""
		Kill the job
		"""
		cmd = cmdy.python(
			_exe = sys.executable,
			c    = 'from pyppl.utils import killtree; killtree(%s, killme = True)' % self.job.pid,
			_dry = True).cmd
		self.ssh(cmd)

	def isRunning(self):
		"""
		Tell if the job is alive
		@returns:
			`True` if it is else `False`
		"""
		if not self.job.pid:
			return False
		cmd = cmdy.kill(s = 0, _ = self.job.pid, _dry = True).cmd
		return self.ssh(cmd).rc == 0

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
		sge_N = conf.pop('sge.N', '.'.join([
			self.job.config['proc'],
			self.job.config['tag'],
			self.job.config['suffix'],
			str(self.job.index + 1)
		]))
		head.append('#$ -N %s' % sge_N)

		sge_q = conf.pop('sge.q')
		if sge_q: 
			head.append('#$ -q %s' % sge_q)

		sge_j = conf.pop('sge.j')
		if sge_j: 
			head.append('#$ -j %s' % sge_j)
		
		head.append('#$ -cwd')

		sge_M = conf.pop('sge.M')
		if sge_M:
			head.append('#$ -M %s' % sge_M)

		sge_m = conf.pop('sge.m')
		if sge_m:
			head.append('#$ -m %s' % sge_m)
		
		for k in sorted(conf.keys()):
			if not k.startswith ('sge.'): continue
			v = conf[k]
			k = k[4:].strip()
			src = '#$ -' + k
			if v != True: # {'notify': True} ==> -notify
				src += ' ' + str(v)
			head.append(src)

		preScript = conf.get('preScript')
		postScript = conf.get('postScript')

		self.wrapScript(head = head, preScript = preScript, postScript = postScript)
		
	def submit(self):
		"""
		Submit the job
		@returns:
			The `utils.cmd.Cmd` instance if succeed 
			else a `Box` object with stderr as the exception and rc as 1
		"""
		c = self.qsub(self.script, _okcode = '0~256')
		if c.rc == 0:
			# Your job 6556149 ("pSort.notag.3omQ6NdZ.0") has been submitted
			m = re.search(r'\s(\d+)\s', c.stdout.strip())
			if not m:
				c.rc = 5
			else:
				self.job.pid = m.group(1)
		return c

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
		return self.qstat(j = self.job.pid, _okcode = '0~256').rc == 0

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
		conf = copy.copy(conf.get('slurmRunner', {}))

		self.sbatch  = cmdy.sbatch.bake(_exe = conf.get('sbatch'))
		self.srun    = cmdy.srun.bake(_exe = conf.get('srun'))
		self.squeue  = cmdy.squeue.bake(_exe = conf.get('squeue'))
		self.scancel = cmdy.scancel.bake(_exe = conf.get('scancel'))

		head = []
		slurm_J = conf.pop('slurm.J', '.'.join([
			self.job.config['proc'],
			self.job.config['tag'],
			self.job.config['suffix'],
			str(self.job.index + 1)
		]))
		head.append('#SBATCH -J %s' % slurm_J)

		for k in sorted(conf.keys()):
			if not k.startswith ('slurm.'): continue
			v = conf[k]
			k = k[6:].strip()
			src = '#SBATCH -' + (k if len(k)==1 else '-' + k)
			if v != True: # {'notify': True} ==> -notify
				src += ' ' + str(v)
			head.append(src)

		realScript = self.srun(chmodX(self.job.script), _dry = True).cmd
		preScript  = conf.get('preScript')
		postScript = conf.get('postScript')

		self.wrapScript(head = head, preScript = preScript, 
			realScript = realScript, postScript = postScript)
		
	def submit(self):
		"""
		Submit the job
		@returns:
			The `utils.cmd.Cmd` instance if succeed 
			else a `Box` object with stderr as the exception and rc as 1
		"""
		c = self.sbatch(self.script, _okcode = '0~256')
		if c.rc == 0:
			# Submitted batch job 1823334668
			m = re.search(r'\s(\d+)$', c.stdout.strip())
			if not m:
				c.rc = 1
			else:
				self.job.pid = m.group(1)
		return c

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
		return self.squeue(j = self.job.pid, _okcode = '0~256').rc == 0
