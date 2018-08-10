import sys, re, subprocess, atexit, shlex
from os import path
from pyppl.utils import ps, cmd, Box
from pyppl.utils.safefs import SafeFs

class Helper(object):
	"""
	A helper class for runners
	"""
	def __init__(self, script, cmds = None):
		"""
		Constructor
		@params:
			`script`: The script of the job
			`cmds`  : The original runner commands
		"""
		self.script  = script
		self.pidfile = path.join(path.dirname(self.script), 'job.pid')
		self.rcfile  = path.join(path.dirname(self.script), 'job.rc')
		self.outfile = path.join(path.dirname(self.script), 'job.stdout')
		self.errfile = path.join(path.dirname(self.script), 'job.stderr')
		self.outfd   = None
		self.errfd   = None
		self.cmds    = cmds or {}
		self._pid    = None

	@property
	def pid(self):
		"""
		Property getter
		@returns:
			The pid
		"""
		if self._pid is not None:
			return self._pid
		if not path.isfile(self.pidfile):
			self._pid = None
			return None

		with open(self.pidfile, 'r') as fpid:
			spid = fpid.read().strip()
			if spid: 
				self._pid = spid
		return self._pid

	@pid.setter
	def pid(self, pid):
		"""
		Property setter
		@params:
			`pid`: The pid to be saved to pidfile
		"""
		if pid is None:
			spid = ''
			self._pid = None
		else:
			spid = str(pid)
			self._pid = pid
		with open(self.pidfile, 'w') as fpid:
			fpid.write(spid)

	def submit(self):
		"""
		Submit the job
		"""
		pass

	def run(self):
		"""
		Run the job, wait for the job to complete
		"""
		pass

	def kill(self):
		"""
		Kill the job
		"""
		pass

	def alive(self):
		"""
		Tell if the job is alive
		"""
		pass

class LocalHelper(Helper):

	def submit(self):
		"""
		Submit the job
		@returns:
			The `utils.cmd.Cmd` instance
		"""
		# run self as a script
		c = cmd.run([sys.executable, path.realpath(__file__), self.script], bg = True)
		c.rc = 0
		return c
		
	def run(self):
		"""
		Run the job, wait for the job to complete
		"""
		self.outfd = open(self.outfile, 'w')
		self.errfd = open(self.errfile, 'w')
		self.proc  = cmd.Cmd(SafeFs(self.script).chmodX(), stdout = self.outfd, stderr = self.errfd)
		self.pid   = self.proc.pid
		try:
			self.proc.run()
		except KeyboardInterrupt: # pragma: no cover
			self.proc.rc = 1

	def kill(self):
		"""
		Kill the job
		"""
		if self.pid is not None:
			ps.killtree(int(self.pid), killme = True, sig = 9)

	def alive(self):
		"""
		Tell if the job is alive
		@returns:
			`True` if it is else `False`
		"""
		if self.pid is None:
			return False
		return ps.exists(int(self.pid))

	def quit(self):
		"""
		Quit the program, when the job is complete
		"""
		# close outfd and errfd
		if self.outfd:
			self.outfd.close()
		if self.errfd:
			self.errfd.close()
		# write rc
		with open(self.rcfile, 'w') as frc:
			frc.write(str(self.proc.rc))

class SshHelper(Helper):

	def __init__(self, script, cmds = None):
		"""
		Constructor
		@params:
			`script`: The script of the job
			`cmds`  : The command used for ssh job submission
		"""
		if not isinstance(cmds, list):
			cmds = shlex.split(cmds)
		super(SshHelper, self).__init__(script, cmds)

	def submit(self):
		"""
		Submit the job
		@returns:
			The `utils.cmd.Cmd` instance
		"""
		# test if self.script exists on the ssh server  
		# make sure it is using the same file system as the local machine
		cmdlist = ['ls', self.script]
		cmdlist = subprocess.list2cmdline(cmdlist)
		c = cmd.run(self.cmds + [cmdlist])
		if c.rc != 0:
			c.stderr += 'Probably the server ({}) is not using the same file system as the local machine.\n'.format(self.cmds)
			return c
		
		# run self as a script
		cmdlist = [sys.executable, path.realpath(__file__), self.script]
		cmdlist = subprocess.list2cmdline(cmdlist)
		c = cmd.run(self.cmds + [cmdlist], bg = True)
		c.rc = 0
		return c

	def kill(self):
		"""
		Kill the job
		"""
		cmdlist = ['ps', '-o', 'pid,ppid']
		cmdlist = subprocess.list2cmdline(cmdlist)
		pidlist = cmd.run(self.cmds + [cmdlist]).stdout.splitlines()
		pidlist = [line.strip().split() for line in pidlist]
		pidlist = [pid for pid in pidlist if len(pid) == 2 and pid[0].isdigit() and pid[1].isdigit()]
		dchilds     = ps.child(self.pid, pidlist)
		allchildren = [str(self.pid)] + dchilds
		while dchilds:
			dchilds2 = sum([ps.child(p, pidlist) for p in dchilds], [])
			allchildren.extend(dchilds2)
			dchilds = dchilds2
		
		killcmd = ['kill', '-9'] + list(reversed(allchildren))
		killcmd = subprocess.list2cmdline(killcmd)
		cmd.run(self.cmds + [killcmd])
	
	def alive(self):
		"""
		Tell if the job is alive.  
		This just sends '-0 (Cancel)' signal to the process via ssh
		@returns:
			`True` if it is else `False`
		"""
		if self.pid is None:
			return False
		cmdlist = ['kill', '-0', str(self.pid)]
		cmdlist = subprocess.list2cmdline(cmdlist)
		return cmd.run(self.cmds + [cmdlist]).rc == 0

class SgeHelper(Helper):

	def __init__(self, script, cmds = None):
		"""
		Constructor
		@params:
			`script`: The script of the job
			`cmds`  : The original runner commands
				- `qsub`: The command to submit job
				- `qstat`: The command to check job status
				- `qdel`: The command to delete job
		"""
		cmds = cmds or {
			'qsub' : 'qsub',
			'qstat': 'qstat',
			'qdel' : 'qdel'
		}
		super(SgeHelper, self).__init__(script, cmds)

	def submit(self):
		"""
		Submit the job
		@returns:
			The `utils.cmd.Cmd` instance if succeed 
			else a `Box` object with stderr as the exception and rc as 1
		"""
		cmdlist = [self.cmds['qsub'], self.script]
		try:
			r = cmd.run(cmdlist)
			# Your job 6556149 ("pSort.notag.3omQ6NdZ.0") has been submitted
			m = re.search(r'\s(\d+)\s', r.stdout)
			if not m:
				r.rc = 1
			else:
				self.pid = m.group(1)

			return r
		except (OSError, subprocess.CalledProcessError) as ex:
			r = Box()
			r.stderr = str(ex)
			r.rc = 1
			return r

	def kill(self):
		"""
		Kill the job
		"""
		cmdlist = [self.cmds['qdel'], '-j', str(self.pid)]
		try:
			cmd.run(cmdlist)
		except (OSError, subprocess.CalledProcessError): # pragma: no cover
			pass

	def alive(self):
		"""
		Tell if the job is alive
		@returns:
			`True` if it is else `False`
		"""
		if self.pid is None:
			return False
		cmdlist = [self.cmds['qstat'], '-j', str(self.pid)]
		try:
			r = cmd.run(cmdlist)
			return r.rc == 0
		except (OSError, subprocess.CalledProcessError):
			return False

class SlurmHelper(Helper):

	def __init__(self, script, cmds = None):
		"""
		Constructor
		@params:
			`script`: The script of the job
			`cmds`  : The original runner commands
				- `sbatch`: The command to submit job
				- `squeue`: The command to check job status
				- `srun`: The command to run job
				- `scancel`: The command to cancel job
		"""
		cmds = cmds or {
			'sbatch' : 'sbatch',
			'squeue' : 'squeue',
			'srun'   : 'srun',
			'scancel': 'scancel'
		}
		super(SlurmHelper, self).__init__(script, cmds)

	def submit(self):
		"""
		Submit the job
		@returns:
			The `utils.cmd.Cmd` instance if succeed 
			else a `Box` object with stderr as the exception and rc as 1
		"""
		cmdlist = [self.cmds['sbatch'], self.script]
		try:
			r = cmd.run(cmdlist)
			# sbatch: Submitted batch job 99999999
			m = re.search(r'\s(\d+)$', r.stdout)
			if not m: # pragma: no cover
				r.rc = 1
			else:
				self.pid = m.group(1)

			return r
		except (OSError, subprocess.CalledProcessError) as ex: # pragma: no cover
			r = Box()
			r.stderr = str(ex)
			r.rc = 1
			return r

	def kill(self):
		"""
		Kill the job
		"""
		cmdlist = [self.cmds['scancel'], str(self.pid)]
		try:
			cmd.run(cmdlist)
		except (OSError, subprocess.CalledProcessError): # pragma: no cover
			pass

	def alive(self):
		"""
		Tell if the job is alive
		@returns:
			`True` if it is else `False`
		"""
		if self.pid is None:
			return False
		cmdlist = [self.cmds['squeue'], '-j', str(self.pid)]
		try:
			r = cmd.run(cmdlist)
			if r.rc != 0:
				return False
			return r.stdout.splitlines()[1].split()[0] == str(self.pid)
		except (OSError, subprocess.CalledProcessError):
			return False


if __name__ == '__main__': # pragma: no cover
	# work as local submitter
	helper = LocalHelper(sys.argv[1])
	atexit.register(helper.quit)
	helper.run()