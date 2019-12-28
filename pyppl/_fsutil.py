"""A thread-safe file operation package for python"""
import os
import shutil
import tempfile
from hashlib import md5
from contextlib import contextmanager
from threading import Lock
from filelock import FileLock
import cmdy

MULTILOCK = Lock()
TMPDIR    = tempfile.gettempdir()
#TMPDIR   = os.path.join(tempfile.gettempdir(), 'fsutil.locks')
## not threading-safe!!
# if not os.path.exists(TMPDIR): # pragma: no cover
# 	os.makedirs(TMPDIR)

class TargetExistsError(OSError):
	"""Raise when target exists and not able to overwrite"""

class TargetNotExistsError(OSError):
	"""Raise when target does not exist and not able to ignore"""

def _get_lock_file(path):
	basename = md5(str(path).encode()).hexdigest()
	return os.path.join(TMPDIR, basename + '.lock')

@contextmanager
def lock(*files, resolve = False):
	"""Lock file context"""
	files = [os.path.realpath(path) if resolve else os.path.abspath(path) for path in files]
	locks = [FileLock(_get_lock_file(path)) for path in files]
	if len(files) == 1:
		with locks[0]:
			yield locks[0]
	else:
		with MULTILOCK:
			_ = [lock.acquire() for lock in locks]
			yield locks
		_ = [lock.release() for lock in locks]

def autolock(func, *filekws, resolve = False):
	"""Regiester function for auto locking operating files"""
	def realfunc(*args, **kwargs):
		files = [path for i, path in enumerate(args) if i in filekws]
		files.extend([path for kw, path in kwargs.items() if kw in filekws])
		files = set(files or [args[0]])
		with lock(*files, resolve = resolve) as locks:
			func.lock = locks
			return func(*args, **kwargs)
	return realfunc

exists = os.path.exists # pylint: disable=invalid-name
isfile = os.path.isfile # pylint: disable=invalid-name
isdir  = os.path.isdir  # pylint: disable=invalid-name
islink = os.path.islink # pylint: disable=invalid-name

# haven't figured out a way to mimic this
def _remove_busy_dir(path): # pragma: no cover
	"""Try to remove directory with files being ocupied by open process"""
	for root, _, files in os.walk(path):
		for fname in files:
			if not fname.startswith('.'):
				continue
			fpath = os.path.join(root, fname)
			lsof = cmdy.lsof(fpath, _raise = False) # pylint: disable=no-member
			if lsof.rc != 0:
				continue
			lsof = lsof.splitlines()
			if len(lsof) < 2:
				continue
			pid = lsof[-1].split()[1]
			cmdy.kill({'9': pid})  # pylint: disable=no-member
	shutil.rmtree(path)

def remove(path, ignore_nonexist = True):
	"""Remove anything. If ignore_nonexist is False and path does not exists,
	a TargetNotExistsError raises."""
	if os.path.islink(path):
		os.remove(path)
	if os.path.isdir(path):
		try:
			shutil.rmtree(path)
		except OSError as ex: # pragma: no cover
			if 'busy' not in str(ex):
				raise
			_remove_busy_dir(path)
	if not exists(path):
		if not ignore_nonexist:
			raise TargetNotExistsError(path)
		return
	os.remove(path)

def move(src, dst, overwrite = True):
	"""Move src to dst. If overwrite is False and dst exists, a TargetExistsError raises"""
	if not islink(dst) and samefile(src, dst):
		remove(src)
		return
	if overwrite:
		remove(dst)
	elif exists(dst):
		raise TargetExistsError(dst)
	shutil.move(src, dst)

def copy(src, dst, overwrite = True):
	"""Copy src to dst. If overwrite is False and dst exists, a TargetExistsError raises"""
	if not islink(dst) and samefile(src, dst):
		return
	if overwrite:
		remove(dst)
	elif exists(dst):
		raise TargetExistsError(dst)
	if isdir(src):
		shutil.copytree(src, dst)
	else:
		shutil.copy2(src, dst)

def link(src, dst, overwrite = True):
	"""Symbolically link src to dst.
	If overwrite is False and dst exists, a TargetExistsError raises"""
	if not islink(dst) and samefile(src, dst):
		move(dst, src)
		link(src, dst)
		return
	if overwrite:
		remove(dst)
	elif exists(dst):
		raise TargetExistsError(dst)
	os.symlink(src, dst)

def samefile(path1, path2):
	"""Tell if two paths are pointing to the same file
	If both of them don't exists, they have to be the same string.
	Otherwise, they have to point to the same file
	"""
	exist1 = exists(path1)
	exist2 = exists(path2)
	if not exist1 and not exist2:
		return path1 == path2
	if not exist1 or not exist2:
		return False
	return os.path.samefile(path1, path2)

def makedirs(path, overwrite = True):
	"""Create directory. If overwrite is False and path exists, a TargetExistsError raises.
	Important: if overwrite is True and path exists, content of the directory will lost!"""
	if overwrite:
		remove(path)
	elif exists(path):
		raise TargetExistsError(path)
	os.makedirs(path)
mkdir = makedirs # pylint: disable=invalid-name

def gzip(src, dst, overwrite = True):
	"""Gzip a file or a directory (using tar zip)"""
	if overwrite:
		remove(dst)
	elif exists(dst):
		raise TargetExistsError(dst)
	if os.path.isdir(src): # tar.gz
		import tarfile
		from glob import glob
		cwd = os.getcwd()
		os.chdir(src)
		with tarfile.open(dst, 'w:gz') as tar:
			for name in glob('./*'):
				tar.add(name)
		os.chdir(cwd)
	else:
		import gzip as _gzip
		with open(src, 'rb') as srcf, _gzip.open(dst, 'wb') as dstf:
			shutil.copyfileobj(srcf, dstf)


def gunzip(src, dst, overwrite = True):
	"""Gunzip a gzip file or a tar.gz file"""
	if overwrite:
		remove(dst)
	elif exists(dst):
		raise TargetExistsError(dst)
	if str(src).endswith('.tgz') or str(src).endswith('.tar.gz'):
		import tarfile
		makedirs(dst, overwrite)
		with tarfile.open(src, 'r:gz') as tar:
			tar.extractall(dst)
	else:
		import gzip as _gzip
		with _gzip.open(src, 'rb') as srcf, open(dst, 'wb') as dstf:
			shutil.copyfileobj(srcf, dstf)
