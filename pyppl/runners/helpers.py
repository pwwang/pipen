import sys, re, subprocess, atexit
from os import path
from pyppl.utils import chmodX, ps, cmd, Box

class Helper(object):

	def __init__(self, script, cmds = None):
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
		if pid is None:
			spid = ''
			self._pid = None
		else:
			spid = str(pid)
			self._pid = pid
		with open(self.pidfile, 'w') as fpid:
			fpid.write(spid)

	def submit(self):
		pass

	def run(self):
		pass

	def kill(self):
		pass

	def alive(self):
		pass

class LocalHelper(Helper):

	def submit(self):
		# run self as a script
		return cmd.run([sys.executable, path.realpath(__file__), self.script], bg = True)
		
	def run(self):
		self.outfd = open(self.outfile, 'w')
		self.errfd = open(self.errfile, 'w')
		self.proc  = cmd.run(chmodX(self.script), outfd = self.outfd, errfd = self.errfd, bg = True)
		self.pid   = self.proc.pid
		self.proc.p.wait()
		self.proc.rc = self.proc.p.returncode

	def kill(self):
		if self.pid is not None:
			ps.killtree(int(self.pid), killme = True, sig = 9)

	def alive(self):
		if self.pid is None:
			return False
		return ps.exists(int(self.pid))

	def quit(self):
		# close outfd and errfd
		if self.outfd:
			self.outfd.close()
		if self.errfd:
			self.errfd.close()
		# write rc
		with open(self.rcfile, 'w') as frc:
			frc.write(str(self.proc.rc))

class SgeHelper(Helper):

	def __init__(self, script, cmds = None):
		cmds = cmds or {
			'qsub' : 'qsub',
			'qstat': 'qstat',
			'qdel' : 'qdel'
		}
		super(SgeHelper, self).__init__(script, cmds)

	def submit(self):
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
		except subprocess.CalledProcessError as ex:
			r = Box()
			r.stderr = str(ex)
			r.rc = 1
			return r

	def kill(self):
		cmdlist = [self.cmds['qdel'], '-j', str(self.pid)]
		cmd.run(cmdlist)

	def alive(self):
		if self.pid is None:
			return False
		cmdlist = [self.cmds['qstat'], '-j', str(self.pid)]
		try:
			r = cmd.run(cmdlist)
			return r.rc == 0
		except subprocess.CalledProcessError:
			return False


if __name__ == '__main__':
	helper = LocalHelper(sys.argv[1])
	atexit.register(helper.quit)
	helper.run()