import errno, signal, os, subprocess
from .cmd import Cmd

def exists(pid):
	"""
	Check whether pid exists in the current process table.
	From https://github.com/kennethreitz/delegator.py/blob/master/delegator.py
	"""
	if pid == 0:
		# According to "man 2 kill" PID 0 has a special meaning:
		# it refers to <<every process in the process group of the
		# calling process>> so we don't want to go any further.
		# If we get here it means this UNIX platform *does* have
		# a process with id 0.
		return True
	try:
		os.kill(pid, 0)
	except OSError as err:
		if err.errno == errno.ESRCH:
			# ESRCH == No such process
			return False
		elif err.errno == errno.EPERM:
			# EPERM clearly means there's a process to deny access to
			return True
		else: # pragma: no cover
			# According to "man 2 kill" possible error values are
			# (EINVAL, EPERM, ESRCH) therefore we should never get
			# here. If we do let's be explicit in considering this
			# an error.
			raise err
	else: # pragma: no cover
		return True

def kill(pid, sig = signal.SIGKILL):
	try:
		os.kill(int(pid), sig)
	except OSError: # pragma: no cover
		Cmd(['kill', '-' + str(sig), pid]).run()

def child(pid):
	"""
	Direct children
	"""
	try:
		# --no-heading, --pid not supported in osx
		# cids = Cmd(['ps', '--no-heading', '-o', 'pid', '--ppid', pid]).run()
		c = Cmd(['ps', '-o', 'pid,ppid']).run()
		cids = []
		for line in c.stdout.splitlines():
			parts = line.split()
			if len(parts) != 2 or parts[-1] != str(pid):
				continue
			cids.append(parts[0])
		return cids
	except subprocess.CalledProcessError: # pragma: no cover
		return []

def children(pid):
	cids = child(pid)
	ret  = cids
	while cids:
		cids2 = sum([child(c) for c in cids], [])
		ret.extend(cids2)
		cids = cids2
	return ret

def killtree(ppid, killme = True, sig = signal.SIGKILL):
	cids = list(reversed(children(ppid)))
	if killme:
		cids.append(ppid)
	for cid in cids:
		kill(cid, sig)