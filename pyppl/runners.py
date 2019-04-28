"""
Built-in runners for PyPPL
"""
import sys
import cmdy
import atexit
from os import path, getcwd
from box import Box
from time import sleep
from subprocess import list2cmdline, CalledProcessError
from multiprocessing import Lock
from psutil import pid_exists

class _LocalSubmitter(object):
	
	def __init__(self, script):
		scriptdir    = path.dirname(script)
		self.script  = script
		self.rcfile  = path.join(scriptdir, 'job.rc')
		self.pidfile = path.join(scriptdir, 'job.pid')
		self.outfile = path.join(scriptdir, 'job.stdout')
		self.errfile = path.join(scriptdir, 'job.stderr')
		self.outfd   = None
		self.errfd   = None

	def submit(self):
		"""
		Submit the real job.
		"""
		from pyppl.utils.safefs import SafeFs
		self.outfd = open(self.outfile, 'w')
		self.errfd = open(self.errfile, 'w')
		try:
			self.proc = cmd.Cmd(SafeFs._chmodX(self.script), stdout = self.outfd, stderr = self.errfd)
			with open(self.pidfile, 'w') as fpid:
				fpid.write(str(self.proc.pid))
			try:
				self.proc.run()
			except KeyboardInterrupt: # pragma: no cover
				self.proc.rc = 88
		except Exception:
			from traceback import format_exc
			ex = format_exc()
			if 'Text file busy' in str(ex):
				sleep(.1)
				self.outfd.close()
				self.errfd.close()
				self.submit()
			else:
				with open(self.errfile, 'w') as f:
					f.write(str(ex))
				self.proc    = lambda: None
				self.proc.rc = 88

	def quit(self):
		"""
		Clean up.
		"""
		if self.outfd:
			self.outfd.close()
		if self.errfd:
			self.errfd.close()
		# write rc
		with open(self.rcfile, 'w') as frc:
			frc.write(str(self.proc.rc))

if __name__ == '__main__': # pragma: no cover
	# work as local submitter
	submitter = _LocalSubmitter(sys.argv[1])
	atexit.register(submitter.quit)
	submitter.submit()
	sys.exit(0)

import re
import copy
from .utils import safefs, cmd, killtree, ps
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
		self.script  = safefs.SafeFs._chmodX(job.script)
		self.job     = job
		self.cmd2run = list2cmdline(self.script)

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
		c = RunnerLocal.SUBMITTER(self.script[-1] if isinstance(self.script, list) else self.script)
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
	SUBMITTER = cmdy.python.bake(path.realpath(__file__), _exe = sys.executable)

	def __init__ (self, job):
		super(RunnerLocal, self).__init__(job)

		# construct an local script
		self.script = job.script + '.local'
		localsrc  = ['#!/usr/bin/env bash']

		conf = job.config.get('runnerOpts', {})
		conf = conf.get('localRunner', {})

		if 'preScript' in conf:
			localsrc.append (conf['preScript'])

		localsrc.append ('')
		localsrc.append (self.cmd2run)
		localsrc.append ('')

		if 'postScript' in conf:
			localsrc.append (conf['postScript'])
		
		with open (self.script, 'w') as f:
			f.write ('\n'.join(localsrc) + '\n')

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

		# construct an dry script
		self.script = self.job.script + '.dry'
		drysrc  = ['#!/usr/bin/env bash']
		
		drysrc.append ('')
		for val in job.output.values():
			if val['type'] in Proc.OUT_VARTYPE:
				continue
				
			if val['type'] in Proc.OUT_FILETYPE:
				drysrc.append("touch '{}'".format(val['data']))
			elif val['type'] in Proc.OUT_DIRTYPE:
				drysrc.append("mkdir -p '{}'".format(val['data']))

		with open (self.script, 'w') as f:
			f.write ('\n'.join(drysrc) + '\n')


class RunnerSsh(Runner):
	"""
	The ssh runner
	"""
	LIVE_SERVERS = None
	LOCK         = Lock()
	
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
		cmdlist = ['ssh', server]
		if key: # pragma: no cover
			cmdlist.append('-i')
			cmdlist.append(key)
		cmdlist.append('-o')
		cmdlist.append('BatchMode=yes')
		cmdlist.append('-o')
		cmdlist.append('ConnectionAttempts=1')
		cmdlist.append('true')
		try:
			return cmd.run(cmdlist, timeout = timeout).rc == 0
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
		self.script = self.job.script + '.ssh'

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
		key    = keys[sid] if keys else None

		self.cmd2run = "cd %s; %s" % (getcwd(), self.cmd2run)
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

		with open (self.script, 'w') as f:
			f.write ('\n'.join(sshsrc) + '\n')

		self.sshcmd = ['ssh', '-t', server]
		if key:
			self.sshcmd.append('-i')
			self.sshcmd.append(key)

	def submit(self):
		"""
		Submit the job
		@returns:
			The `utils.cmd.Cmd` instance if succeed 
			else a `Box` object with stderr as the exception and rc as 1
		"""
		cmdlist = ['ls', self.script]
		cmdlist = list2cmdline(cmdlist)
		c = cmd.run(self.sshcmd + [cmdlist])
		if c.rc != 0:
			c.stderr += 'Probably the server ({}) is not using the same file system as the local machine.\n'.format(self.sshcmd)
			return c
		
		# run self as a script
		submitter = path.join(path.realpath(path.dirname(__file__)), 'runner.py')
		cmdlist = [sys.executable, submitter, self.script]
		cmdlist = list2cmdline(cmdlist)
		c = cmd.run(self.sshcmd + [cmdlist], bg = True)
		c.rc = 0
		return c

	def kill(self):
		"""
		Kill the job
		"""
		cmdlist = 'ps -o pid,ppid'
		pidlist = cmd.run(self.sshcmd + [cmdlist]).stdout.splitlines()
		pidlist = [line.strip().split() for line in pidlist]
		pidlist = [pid for pid in pidlist if len(pid) == 2 and pid[0].isdigit() and pid[1].isdigit()]
		dchilds     = ps.child(self.job.pid, pidlist)
		allchildren = [str(self.job.pid)] + dchilds
		while dchilds: # pragma: no cover
			dchilds2 = sum([ps.child(p, pidlist) for p in dchilds], [])
			allchildren.extend(dchilds2)
			dchilds = dchilds2
		
		killcmd = ['kill', '-9'] + list(reversed(allchildren))
		killcmd = list2cmdline(killcmd)
		cmd.run(self.sshcmd + [killcmd])

	def isRunning(self):
		"""
		Tell if the job is alive
		@returns:
			`True` if it is else `False`
		"""
		if not self.job.pid:
			return False
		cmdlist = ['kill', '-0', str(self.job.pid)]
		cmdlist = list2cmdline(cmdlist)
		return cmd.run(self.sshcmd + [cmdlist]).rc == 0

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

		# construct an sge script
		self.script = self.job.script + '.sge'
		sgesrc  = ['#!/usr/bin/env bash']

		conf = self.job.config.get('runnerOpts', {})
		conf = copy.copy(conf.get('sgeRunner', {}))
		
		self.commands = {'qsub': 'qsub', 'qstat': 'qstat', 'qdel': 'qdel'}
		if 'qsub' in conf:
			self.commands['qsub'] = conf['qsub']
		if 'qstat' in conf:
			self.commands['qstat'] = conf['qstat']
		if 'qdel' in conf:
			self.commands['qdel'] = conf['qdel']
			
		if not 'sge.N' in conf:
			jobname = '.'.join([
				self.job.config['proc'],
				self.job.config['tag'],
				self.job.config['suffix'],
				str(self.job.index + 1)
			])
			sgesrc.append('#$ -N %s' % jobname)
		else:
			jobname = conf['sge.N']
			sgesrc.append('#$ -N %s' % jobname)
			del conf['sge.N']
		
		if 'sge.q' in conf:
			sgesrc.append('#$ -q %s' % conf['sge.q'])
			del conf['sge.q']
			
		if 'sge.j' in conf:
			sgesrc.append('#$ -j %s' % conf['sge.j'])
			del conf['sge.j']
		
		if 'sge.o' in conf:
			sgesrc.append('#$ -o %s' % conf['sge.o'])
			del conf['sge.o']
		else:
			sgesrc.append('#$ -o %s' % self.job.outfile)
			
		if 'sge.e' in conf:
			sgesrc.append('#$ -e %s' % conf['sge.e'])
			del conf['sge.e']
		else:
			sgesrc.append('#$ -e %s' % self.job.errfile)
			
		sgesrc.append('#$ -cwd')
		
		if 'sge.M' in conf:
			sgesrc.append('#$ -M %s' % conf['sge.M'])
			del conf['sge.M']
		
		if 'sge.m' in conf:
			sgesrc.append('#$ -m %s' % conf['sge.m'])
			del conf['sge.m']
		
		for k in sorted(conf.keys()):
			if not k.startswith ('sge.'): continue
			v = conf[k]
			k = k[4:].strip()
			src = '#$ -' + k
			if v != True: # {'notify': True} ==> -notify
				src += ' ' + str(v)
			sgesrc.append(src)

		sgesrc.append ('')
		sgesrc.append ('trap "status=\\$?; echo \\$status >\'%s\'; exit \\$status" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT' % self.job.rcfile)
		
		if 'preScript' in conf:
			sgesrc.append (conf['preScript'])

		sgesrc.append ('')
		sgesrc.append (self.cmd2run)

		if 'postScript' in conf:
			sgesrc.append (conf['postScript'])
		
		with open (self.script, 'w') as f:
			f.write ('\n'.join(sgesrc) + '\n')
		
	def submit(self):
		"""
		Submit the job
		@returns:
			The `utils.cmd.Cmd` instance if succeed 
			else a `Box` object with stderr as the exception and rc as 1
		"""
		cmdlist = [self.commands['qsub'], self.script]
		try:
			r = cmd.run(cmdlist)
			# Your job 6556149 ("pSort.notag.3omQ6NdZ.0") has been submitted
			m = re.search(r'\s(\d+)\s', r.stdout)
			if not m:
				r.rc = 1
			else:
				self.job.pid = m.group(1)
			return r

		except (OSError, CalledProcessError) as ex:
			r        = Box()
			r.stderr = str(ex)
			r.rc     = 1
			r.cmd    = list2cmdline(cmdlist)
			return r

	def kill(self):
		"""
		Kill the job
		"""
		cmdlist = [self.commands['qdel'], '--force', str(self.job.pid)]
		try:
			cmd.run(cmdlist)
		except (OSError, CalledProcessError): # pragma: no cover
			pass

	def isRunning(self):
		"""
		Tell if the job is alive
		@returns:
			`True` if it is else `False`
		"""
		if not self.job.pid:
			return False
		cmdlist = [self.commands['qstat'], '-j', str(self.job.pid)]
		try:
			r = cmd.run(cmdlist)
			return r.rc == 0
		except (OSError, CalledProcessError):
			return False


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

		# construct an slurm script
		self.script = self.job.script + '.slurm'
		slurmsrc    = ['#!/usr/bin/env bash']
	
		conf = self.job.config.get('runnerOpts', {})
		conf = copy.copy(conf.get('slurmRunner', {}))

		self.commands = {'sbatch': 'sbatch', 'srun': 'srun', 'squeue': 'squeue', 'scancel': 'scancel'}
		if 'sbatch' in conf:
			self.commands['sbatch']  = conf['sbatch']
		if 'srun' in conf:
			self.commands['srun']    = conf['srun']
		if 'squeue' in conf:
			self.commands['squeue']  = conf['squeue']
		if 'scancel' in conf:
			self.commands['scancel'] = conf['scancel']
		
		cmdPrefix = self.commands['srun']
		if 'cmdPrefix' in conf:
			cmdPrefix = conf['cmdPrefix']
		
		if not 'slurm.J' in conf:
			jobname = '.'.join([
				self.job.config['proc'],
				self.job.config['tag'],
				self.job.config['suffix'],
				str(self.job.index + 1)
			])
			slurmsrc.append('#SBATCH -J %s' % jobname)
		else:
			jobname = conf['slurm.J']
			slurmsrc.append('#SBATCH -J %s' % jobname)
			del conf['slurm.J']
		
		if 'slurm.o' in conf:
			slurmsrc.append('#SBATCH -o %s' % conf['slurm.o'])
			del conf['slurm.o']
		else:
			slurmsrc.append('#SBATCH -o %s' % self.job.outfile)
			
		if 'slurm.e' in conf:
			slurmsrc.append('#SBATCH -e %s' % conf['slurm.e'])
			del conf['slurm.e']
		else:
			slurmsrc.append('#SBATCH -e %s' % self.job.errfile)
		
		for k in sorted(conf.keys()):
			if not k.startswith ('slurm.'): continue
			v = conf[k]
			k = k[6:].strip()
			src = '#SBATCH -' + (k if len(k)==1 else '-' + k)
			if v != True: # {'notify': True} ==> -notify
				src += ' ' + str(v)
			slurmsrc.append(src)

		slurmsrc.append ('')
		slurmsrc.append ('trap "status=\\$?; echo \\$status >\'%s\'; exit \\$status" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT' % self.job.rcfile)
		
		if 'preScript' in conf:
			slurmsrc.append (conf['preScript'])

		slurmsrc.append ('')
		slurmsrc.append (cmdPrefix + ' ' + self.cmd2run)

		if 'postScript' in conf:
			slurmsrc.append (conf['postScript'])
		
		with open (self.script, 'w') as f:
			f.write ('\n'.join(slurmsrc) + '\n')
		
	def submit(self):
		"""
		Submit the job
		@returns:
			The `utils.cmd.Cmd` instance if succeed 
			else a `Box` object with stderr as the exception and rc as 1
		"""
		cmdlist = [self.commands['sbatch'], self.script]
		try:
			r = cmd.run(cmdlist)
			# Submitted batch job 1823334668
			m = re.search(r'\s(\d+)$', r.stdout.strip())
			if not m:
				r.rc = 1
			else:
				self.job.pid = m.group(1)
			return r

		except (OSError, CalledProcessError) as ex:
			r        = Box()
			r.stderr = str(ex)
			r.rc     = 1
			r.cmd    = list2cmdline(cmdlist)
			return r

	def kill(self):
		"""
		Kill the job
		"""
		cmdlist = [self.commands['scancel'], str(self.job.pid)]
		try:
			cmd.run(cmdlist)
		except (OSError, CalledProcessError): # pragma: no cover
			pass

	def isRunning(self):
		"""
		Tell if the job is alive
		@returns:
			`True` if it is else `False`
		"""
		if not self.job.pid:
			return False
		cmdlist = [self.commands['squeue'], '-j', str(self.job.pid)]
		try:
			r = cmd.run(cmdlist)
			return r.rc == 0
		except (OSError, CalledProcessError):
			return False
