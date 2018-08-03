import subprocess
import shlex
import six
from . import Box, asStr
import warnings
# I am intended to run in background.
try:
	ResourceWarning
except NameError:
	class ResourceWarning(Warning):
		pass

def run(cmd, bg = False, outfd = None, errfd = None):
	ret = Box(
		stdout = None,
		stderr = None,
		rc     = 1,
		pid    = 0,
		p      = None,
		cmd    = None
	)
	if isinstance(cmd, six.string_types):
		cmd = shlex.split(cmd)
	ret.cmd = cmd

	if not bg:
		kwargs = {
			'stdout': subprocess.PIPE,
			'stderr': subprocess.PIPE
		}
		if outfd:
			kwargs['stdout'] = outfd
		if errfd:
			kwargs['stderr'] = errfd
		try:
			p = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
			(stdout, stderr) = p.communicate()
			ret.stdout = asStr(stdout)
			ret.stderr = asStr(stderr)
		except OSError:
			raise subprocess.CalledProcessError(1, ' '.join(cmd))
		ret.rc  = p.returncode
		ret.pid = p.pid
		ret.p   = p
		return ret
	else:

		warnings.simplefilter("ignore", ResourceWarning)

		kwargs = {}
		if outfd:
			kwargs['stdout'] = outfd
		if errfd:
			kwargs['stderr'] = errfd
		try:
			p = subprocess.Popen(cmd, **kwargs)
		except OSError:
			raise subprocess.CalledProcessError(1, ' '.join(cmd))
		ret.rc  = 0
		ret.p   = p
		ret.pid = p.pid
		return ret