"""
cmd utility for PyPPL
"""
import subprocess
import shlex
from os import environ
from time import time, sleep
import warnings
# I am intended to run in background.
try:
	ResourceWarning
except NameError:
	class ResourceWarning(Warning):
		"""ResourceWarning for python2"""
		pass

class Timeout(Exception):
	"""Command Timeout Exception"""
	pass

class Cmd(object):
	"""
	A command (subprocess) wapper
	"""
	def __init__(self, cmd, raiseExc = True, timeout = None, **kwargs):
		"""
		Constructor
		@params:
			`cmd`     : The command, could be a string or a list
			`raiseExc`: raise the expcetion or not
			`**kwargs`: other arguments for `Popen`
		"""
		# process is intended to run in background
		warnings.simplefilter("ignore", ResourceWarning)
		self.cmd        = cmd
		self.timeout    = timeout
		self.p          = None
		self.stdout     = None
		self.stderr     = None
		self.rc         = 1
		self.pid        = 0
		popenargs = {
			'env'               : environ.copy(),
			'stdin'             : subprocess.PIPE,
			'stdout'            : subprocess.PIPE,
			'stderr'            : subprocess.PIPE,
			'shell'             : False,
			'universal_newlines': True
		}
		if 'envs' in kwargs:
			popenargs['env'].update({k:str(v) for k, v in kwargs['envs'].items()})
			del kwargs['envs']
		if 'env' in kwargs:
			popenargs['env'].update({k:str(v) for k, v in kwargs['env'].items()})
			del kwargs['env']
		popenargs.update(kwargs)

		cmd = self.cmd
		if popenargs['shell']:
			if isinstance(cmd, list):
				#cmd = ' '.join([str(c) for c in cmd])
				cmd = subprocess.list2cmdline([str(c) for c in cmd])
			# else: assume string
		else:
			if isinstance(cmd, (list, type)):
				cmd = [str(c) for c in cmd]
			else: 
				cmd = shlex.split(self.cmd)
		
		self.cmd = cmd if not isinstance(cmd, list) else subprocess.list2cmdline(cmd)

		try:
			self.p   = subprocess.Popen(cmd, **popenargs)
			self.pid = self.p.pid
		except (OSError, subprocess.CalledProcessError):
			if raiseExc:
				raise

	def __repr__(self):
		return '<Cmd {!r}>'.format(self.cmd)

	def run(self, bg = False):
		"""
		Wait for the command to run
		@params:
			`bg`: Run in background or not. Default: `False`
				- If it is `True`, `rc` and `stdout/stderr` will be default (no value retrieved).
		@returns:
			`self` 
		"""
		if not bg and self.p:
			if not self.timeout:
				self.rc     = self.p.wait()
			else:
				t0 = time()
				while self.p.poll() is None:
					sleep (.01)
					if time() - t0 > self.timeout:
						self.p.terminate()
						raise Timeout
				self.rc = self.p.wait()
			self.stdout = self.p.stdout and self.p.stdout.read()
			self.stderr = self.p.stderr and self.p.stderr.read()
		return self

	def readline(self, stream = 'stderr', save = None, interval = .01):
		"""
		Stream out the stderr or stdout
		@params:
			`stream`: Which stream to stream out, stdout or stderr. Default: `stderr`
			`save`  : Save the stream to self.stdout and/or self.stderr. Default: `None`
				- `None` : don't save
				- `other`: Save the other stream, other than `stream`
				- `same` : Save the same stream,  as `stream`
				- `both` : Save both streams
		@yield:
			Generator of lines from stderr or stdout
		"""
		if self.p:
			t0 = time()
			while self.p.poll() is None:
				if interval > 0:
					sleep (interval)
				if self.timeout and time() - t0 > self.timeout:
					self.p.terminate()
					raise Timeout
				line = getattr(self.p, stream).readline()
				yield line
				if save in ['same', 'both']:
					setattr(self, stream, (getattr(self, stream) or '') + line)
			for line in getattr(self.p, stream):
				yield line
				if save in ['same', 'both']:
					setattr(self, stream, (getattr(self, stream) or '') + line)
			self.rc = self.p.wait()
			if not self.stdout and (save == 'stdout' or (save == 'other' and stream == 'stderr')):
				self.stdout = self.p.stdout and self.p.stdout.read()
			elif not self.stderr and (save == 'stderr' or (save == 'other' and stream == 'stdout')):
				self.stderr = self.p.stderr and self.p.stderr.read()

	def pipe(self, cmd, **kwargs):
		"""
		Pipe another command
		@examples:
			```python
			c = Command('seq 1 3').pipe('grep 1').run()
			c.stdout == '1\\n'
			```
		@params:
			`cmd`: The other command
			`**kwargs`: Other arguments for `Popen` for the other command
		@returns:
			`Command` instance of the other command
		"""
		kwargs['stdin'] = self.p.stdout
		c = Cmd(cmd, **kwargs)
		c.cmd = '{} | {}'.format(self.cmd, c.cmd)
		return c

# shortcuts
def run(cmd, bg = False, raiseExc = True, timeout = None, **kwargs):
	"""
	A shortcut of `Command.run`  
	To chain another command, you can do:  
	`run('seq 1 3', bg = True).pipe('grep 1')`
	@params:
		`cmd`     : The command, could be a string or a list
		`bg`      : Run in background or not. Default: `False`
			- If it is `True`, `rc` and `stdout/stderr` will be default (no value retrieved).
		`raiseExc`: raise the expcetion or not
		`**kwargs`: other arguments for `Popen`
	@returns:
		The `Command` instance
	"""
	return Cmd(cmd, raiseExc = raiseExc, timeout = timeout, **kwargs).run(bg = bg)
