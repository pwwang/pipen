import subprocess
import shlex
import six
from . import Box

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
		p = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = subprocess.PIPE)

		(ret.stdout, ret.stderr) = p.communicate()
		ret.rc  = p.returncode
		ret.pid = p.pid
		ret.p   = p
		return ret
	else:
		kwargs = {}
		if outfd:
			kwargs['stdout'] = outfd
		if errfd:
			kwargs['stderr'] = errfd
		p = subprocess.Popen(cmd, **kwargs)
		ret.rc  = 0
		ret.p   = p
		ret.pid = p.pid
		return ret