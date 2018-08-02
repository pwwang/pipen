import errno, signal, os, subprocess
from . import cmd

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
        else:
            # According to "man 2 kill" possible error values are
            # (EINVAL, EPERM, ESRCH) therefore we should never get
            # here. If we do let's be explicit in considering this
            # an error.
            raise err
    else:
        return True

def kill(pid, sig = signal.SIGKILL):
	try:
		os.kill(int(pid), sig)
	except OSError:
		cmd.run(['kill', '-' + str(sig), str(pid)])

def child(pid):
	"""
	Direct children
	"""
	try:
		cids = cmd.run(['ps', '--no-heading', '-o', 'pid', '--ppid', str(pid)])
		return [p.strip() for p in cids.stdout.splitlines()]
	except subprocess.CalledProcessError:
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
	cids = children(ppid)
	if killme:
		cids.insert(0, ppid)
	for cid in cids:
		kill(cid, sig)