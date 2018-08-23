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
			# return True
			# This means I didn't submit the process
			return False
		else: # pragma: no cover
			# According to "man 2 kill" possible error values are
			# (EINVAL, EPERM, ESRCH) therefore we should never get
			# here. If we do let's be explicit in considering this
			# an error.
			raise err
	else: # pragma: no cover
		return True

def kill(pids, sig = signal.SIGKILL):
	if not isinstance(pids, list):
		pids = [pids]
	try:
		for pid in pids:
			os.kill(int(pid), sig)
	except OSError: # pragma: no cover
		Cmd(['kill', '-' + str(sig)] + [str(pid) for pid in pids]).run()

def child(pid, pidlist = None):
	"""
	Direct children
	"""
	ret = []
	if pidlist:
		for pidline in pidlist:
			if pidline[1] != str(pid):
				continue
			ret.append(pidline[0])
		return ret

	try:
		# --no-heading, --ppid not supported in osx
		# cids = Cmd(['ps', '--no-heading', '-o', 'pid', '--ppid', pid]).run()
		pidlist = Cmd(['ps', '-o', 'pid,ppid']).run().stdout.splitlines()
		pidlist = [line.strip().split() for line in pidlist]
		pidlist = [p for p in pidlist if len(p) == 2 and p[0].isdigit() and p[1].isdigit()]
		return child(pid, pidlist)
	except subprocess.CalledProcessError: # pragma: no cover
		return []

def children(pid):
	pidlist = Cmd(['ps', '-o', 'pid,ppid']).run().stdout.splitlines()
	pidlist = [line.strip().split() for line in pidlist]
	pidlist = [p for p in pidlist if len(p) == 2 and p[0].isdigit() and p[1].isdigit()]
	cids = child(pid, pidlist)
	ret  = cids
	while cids:
		cids2 = sum([child(c, pidlist) for c in cids], [])
		ret.extend(cids2)
		cids = cids2
	return ret

def killtree(ppid, killme = True, sig = signal.SIGKILL):
	cids = list(reversed(children(ppid)))
	if killme:
		cids.append(ppid)
	kill(cids, sig)