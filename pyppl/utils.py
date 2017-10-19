"""
A set of utitities for PyPPL
"""
import inspect
import filelock
import tempfile
import tarfile
import gzip
import re

from stat import S_IEXEC
from glob import glob
from traceback import format_exc
from os import path, remove, symlink, makedirs, chdir, getcwd, walk, stat, chmod, devnull
from shutil import rmtree, copyfile, copytree, move, copyfileobj
from subprocess import Popen
from multiprocessing import Process, Pipe
from hashlib import md5
from box import Box
from six import moves, string_types

class ProcessEx (Process):
	"""
	Try to capture process exceptions when join
	"""
	def __init__(self, *args, **kwargs):
		Process.__init__(self, *args, **kwargs)
		self._pconn, self._cconn = Pipe()
		
	def run(self):
		try:
			Process.run(self)
			self._cconn.send(None)
		except Exception as ex:
			message = format_exc()
			self._cconn.send(type(ex)(message))
	
	def join(self):
		Process.join(self)
		if self._pconn.poll():
			ex = self._pconn.recv()
			if ex:
				raise ex

def varname (maxline = 20, incldot = False):
	"""
	Get the variable name for ini
	@params:
		`maxline`: The max number of lines to retrive. Default: 20
		`incldot`: Whether include dot in the variable name. Default: False
	@returns:
		The variable name
	"""
	stack     = inspect.stack()
	
	if 'self' in stack[1][0].f_locals:
		theclass  = stack[1][0].f_locals["self"].__class__.__name__
		themethod = stack[1][0].f_code.co_name
	else:
		theclass  = stack[1][0].f_code.co_name
		themethod = ''

	srcfile   = stack[2][1]
	srclineno = stack[2][2]

	with open(srcfile) as f:
		srcs   = list(reversed(f.readlines()[max(0, srclineno-maxline): srclineno]))

	re_var = r'([A-Za-z_][\w.]*)' if incldot else r'([A-Za-z_]\w*)'
	if themethod and themethod != '__init__':
		#            var =     pp          .copy    (
		re_hit  = r'%s\s*=\s*([A-Za-z_]\w*\.)+%s\s*\(' % (re_var, themethod)
		#           pp.copy    (
		re_stop = r'([A-Za-z_]\w*\.)+%s\s*\(' % themethod
	else:
		#           var  =
		re_hit  = r'%s\s*=\s*([A-Za-z_]\w*\.)*%s\s*\(' % (re_var, theclass)
		re_stop = r'([A-Za-z_]\w*\.)*%s\s*\(' % theclass
	
	for src in srcs:
		hitgroup = re.search(re_hit, src)
		if hitgroup: return hitgroup.group(1)
		stopgroup = re.search(re_stop, src)
		if stopgroup: break

	varname.index += 1
	return 'var_%s' % (varname.index - 1)
		
varname.index = 0

def reduce(func, vec):
	"""
	Python2 and Python3 compatible reduce
	@params:
		`func`: The reduce function
		`vec`: The list to be reduced
	@returns:
		The reduced value
	"""
	return moves.reduce(func, vec)
	
def map(func, vec):
	"""
	Python2 and Python3 compatible map
	@params:
		`func`: The map function
		`vec`: The list to be maped
	@returns:
		The maped list
	"""
	return list(moves.map(func, vec))

def filter(func, vec):
	"""
	Python2 and Python3 compatible filter
	@params:
		`func`: The filter function
		`vec`:  The list to be filtered
	@returns:
		The filtered list
	"""
	return list(moves.filter(func, vec))

def split (s, delimter, trim = True):
	"""
	Split a string using a single-character delimter
	@params:
		`s`: the string
		`delimter`: the single-character delimter
		`trim`: whether to trim each part. Default: True
	@examples:
		```python
		ret = split("'a,b',c", ",")
		# ret == ["'a,b'", "c"]
		# ',' inside quotes will be recognized.
		```
	@returns:
		The list of substrings
	"""
	ret   = []
	special1 = ['(', ')', '[', ']', '{', '}']
	special2 = ['\'', '"']
	special3 = '\\'
	flags1   = [0, 0, 0]
	flags2   = [False, False]
	flags3   = False
	start = 0
	for i, c in enumerate(s):
		if c == special3:
			flags3 = not flags3
		elif not flags3:
			if c in special1:
				index = special1.index(c)
				if index % 2 == 0:
					flags1[int(index/2)] += 1
				else:
					flags1[int(index/2)] -= 1
			elif c in special2:
				index = special2.index(c)
				flags2[index] = not flags2[index]
			elif c == delimter and not any(flags1) and not any(flags2):
				r = s[start:i]
				if trim: r = r.strip()
				ret.append(r)
				start = i + 1
		else:
			flags3 = False
	r = s[start:]
	if trim: r = r.strip()
	ret.append(r)
	return ret

def dictUpdate(origDict, newDict):
	"""
	Update a dictionary recursively.
	@params:
		`origDict`: The original dictionary
		`newDict`:  The new dictionary
	@examples:
		```python
		od1 = {"a": {"b": {"c": 1, "d":1}}}
		od2 = {key:value for key:value in od1.items()}
		nd  = {"a": {"b": {"d": 2}}}
		od1.update(nd)
		# od1 == {"a": {"b": {"d": 2}}}, od1["a"]["b"] is lost
		dictUpdate(od2, nd)
		# od2 == {"a": {"b": {"c": 1, "d": 2}}}
		```
	"""
	for k, v in newDict.items():

		if isinstance(v, list):
			origDict[k] = [e for e in v]
		elif isinstance(v, dict):
			if k not in origDict:
				origDict[k] = Box() if isinstance(v, Box) else {}
			dictUpdate(origDict[k], newDict[k])
		else:
			origDict[k] = newDict[k]

			
def funcsig (func):
	"""
	Get the signature of a function
	Try to get the source first, if failed, try to get its name, otherwise return None
	@params:
		`func`: The function
	@returns:
		The signature
	"""
	if callable (func):
		try:
			from inspect import getsource
			sig = getsource(func)
		except Exception:
			sig = func.__name__
	else:
		sig = 'None'
	return sig

def uid(s, l = 8, alphabet='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'):
	"""
	Calculate a short uid based on a string.
	Safe enough, tested on 1000000 32-char strings, no repeated uid found.
	This is used to calcuate a uid for a process
	@params:
		`s`: the base string
		`l`: the length of the uid
		`alphabet`: the charset used to generate the uid
	@returns:
		The uid
	"""
	s = md5(str(s).encode('utf-8')).hexdigest()
	number = int (s, 16)
	base = ''

	while number != 0:
		number, i = divmod(number, len(alphabet))
		base = alphabet[i] + base

	return base[:l]

def formatSecs (seconds):
	"""
	Format a time duration
	@params:
		`seconds`: the time duration in seconds
	@returns:
		The formated string.
		For example: "01:01:01.001" stands for 1 hour 1 min 1 sec and 1 minisec.
	"""
	m, s = divmod(seconds, 60)
	h, m = divmod(m, 60)
	return "%02d:%02d:%02d.%03.0f" % (h, m, s, 1000*(s-int(s)))

def range (i, *args, **kwargs):
	"""
	Convert a range to list, because in python3, range is not a list
	@params:
		`r`: the range data
	@returns:
		The converted list
	"""
	return list(moves.range(i, *args, **kwargs))

def alwaysList (data):
	"""
	Convert a string or a list with element
	@params:
		`data`: the data to be converted
	@examples:
		```python
		data = ["a, b, c", "d"]
		ret  = alwaysList (data)
		# ret == ["a", "b", "c", "d"]
		```
	@returns:
		The split list
	"""
	if isinstance(data, string_types):
		ret = split (data, ',')
	elif isinstance(data, list):
		ret = []
		for d in data:
			if ',' in d:
				ret += split(d, ',')
			else:
				ret.append (d)
	else:
		raise ValueError('Expect string or list to convert to list.')
	return [x.strip() for x in ret]
	
def _lockfile(f):
	"""
	Get the path of lockfile of a file
	@params:
		`f`: The file
	@returns:
		The path of the lock file
	"""
	return path.join(tempfile.gettempdir(), uid(f, 16) + '.lock')
	
def _fileExists(f, callback = None):
	"""
	Tell whether a path exists
	@params:
		`f`: the path
		`callback`: the callback
	@returns:
		True if yes, otherwise False
		If any of the path does not exist, return False
	"""
	ret = path.exists(f)
	if not ret and path.islink(f): remove(f)
	if callback:
		callback(ret, f)
	return ret
		
def fileExists(f, callback = None):
	"""
	Tell whether a path exists under a lock
	@params:
		`f`: the path
		`callback`: the callback
	@returns:
		True if yes, otherwise False
		If any of the path does not exist, return False
	"""
	lfile = _lockfile(f)
	with filelock.FileLock(lfile):
		ret = _fileExists(f, callback)
	return ret

def _samefile(f1, f2, callback = None):
	"""
	Tell whether two paths pointing to the same file
	@params:
		`f1`: the first path
		`f2`: the second path
		`callback`: the callback
	@returns:
		True if yes, otherwise False
		If any of the path does not exist, return False
	"""
	if not path.exists (f1) or not path.exists(f2):
		ret = False
	else:
		ret = path.samefile (f1, f2)
	if callback:
		callback(ret, f1, f2)
	return ret
	
def samefile (f1, f2, callback = None):
	"""
	Tell whether two paths pointing to the same file under locks
	@params:
		`f1`: the first path
		`f2`: the second path
		`callback`: the callback
	@returns:
		True if yes, otherwise False
		If any of the path does not exist, return False
	"""
	if f1 == f2:
		callback(True, f1, f2)
		return
		
	f1lock = _lockfile(f1)
	f2lock = _lockfile(f2)
	with filelock.FileLock(f1lock), filelock.FileLock(f2lock):
		ret = _samefile(f1, f2, callback)
	return ret

def safeRemove(f):
	"""
	Safely remove a file/dir.
	@params:
		`f`: the file or dir.
	"""
	def callback (e, fn):
		if e:
			if path.isdir(fn) and not path.islink(fn):
				rmtree(fn)
			else:
				remove(fn)
	fileExists(f, callback)
	
def _safeMove(src, dst, overwrite = True):
	"""
	Move a file/dir
	@params:
		`src`: The source file
		`dst`: The destination
		`overwrite`: Whether overwrite the destination
	@return:
		True if succeed else False
	"""
	if not path.exists(src):
		return False
	
	if path.exists(dst) and not path.samefile(src, dst) and overwrite:
		if path.isdir(dst) and not path.islink(dst):
			rmtree(dst)
		else:
			remove(dst)
	elif not path.exists(dst) and path.islink(dst):
		remove(dst)
	
	if not path.exists(dst):
		move (src, dst)
	return True

def safeMove(src, dst, overwrite = True):
	"""
	Move a file/dir with locks
	@params:
		`src`: The source file
		`dst`: The destination
		`overwrite`: Whether overwrite the destination
	@return:
		True if succeed else False
	"""
	if src == dst:	return False
	
	srclock = _lockfile(src)
	dstlock = _lockfile(dst)
	with filelock.FileLock(srclock), filelock.FileLock(dstlock):
		ret = _safeMove(src, dst, overwrite)
	return ret
			
def _safeMoveWithLink(src, dst, overwrite = True):
	"""
	Move a file/dir and leave a link the source file
	@params:
		`src`: The source file
		`dst`: The destination
		`overwrite`: Whether overwrite the destination
	@return:
		True if succeed else False
	"""
	if not path.exists(src):
		return False

	# already point the dst
	if path.islink(src) and path.exists(dst) and path.samefile(path.realpath(src), dst):
		return False
	
	# remove dead link
	if not path.exists(dst) and path.islink(dst):
		remove(dst)
	
	# if dst is link, and overwrite, remove it
	if path.islink(dst):
		if overwrite: remove(dst)
		else: return False
		
	if path.exists(dst):
		if path.samefile(src, dst): return False
		if not overwrite: return False
		if path.isdir(dst): rmtree(dst)
		else: remove(dst)
	
	if not path.exists(dst):
		# if source is a link, copy the realfile
		if path.islink(src):
			ret = _safeCopy(path.realpath(src), dst)
			if not ret: return False
			return _safeLink(dst, src)
		else:
			move(src, dst)
			return _safeLink(dst, src)

	return False

def safeMoveWithLink(src, dst, overwrite = True):
	"""
	Move a file/dir and leave a link the source file with locks
	@params:
		`src`: The source file
		`dst`: The destination
		`overwrite`: Whether overwrite the destination
	@return:
		True if succeed else False
	"""
	if src == dst:	return False
	
	srclock = _lockfile(src)
	dstlock = _lockfile(dst)
	with filelock.FileLock(srclock), filelock.FileLock(dstlock):
		ret = _safeMoveWithLink(src, dst, overwrite)
	return ret
	
def _safeCopy(src, dst, overwrite = True):
	"""
	Copy a file/dir
	@params:
		`src`: The source file
		`dst`: The destination
		`overwrite`: Whether overwrite the destination
	@return:
		True if succeed else False
	"""
	if not path.exists(src):
		return False
	
	if path.exists(dst) and not path.samefile(src, dst) and overwrite:
		if path.isdir(dst) and not path.islink(dst):
			rmtree(dst)
		else:
			remove(dst)
			
	if not path.exists(dst):
		if path.isdir(src):
			copytree(src, dst)
		else:
			copyfile(src, dst)
	return True
	
def safeCopy(src, dst, overwrite = True):
	"""
	Copy a file/dir with locks
	@params:
		`src`: The source file
		`dst`: The destination
		`overwrite`: Whether overwrite the destination
	@return:
		True if succeed else False
	"""
	if src == dst:	return False
	
	srclock = _lockfile(src)
	dstlock = _lockfile(dst)
	with filelock.FileLock(srclock), filelock.FileLock(dstlock):
		ret = _safeCopy(src, dst, overwrite)
	return ret
	
def _safeLink(src, dst, overwrite = True):
	"""
	Symlink a file/dir
	@params:
		`src`: The source file
		`dst`: The destination
		`overwrite`: Whether overwrite the destination
	@return:
		True if succeed else False
	"""
	if not path.exists(src):
		return False
	
	if path.exists(dst) and not path.samefile(src, dst):
		if overwrite:
			if path.isdir(dst) and not path.islink(dst):
				rmtree(dst)
			else:
				remove(dst)
		else:
			return False		
	if not path.exists(dst):
		symlink(path.abspath(src), dst)
	else:
		return False
	return True
	
def safeLink(src, dst, overwrite = True):
	"""
	Symlink a file/dir with locks
	@params:
		`src`: The source file
		`dst`: The destination
		`overwrite`: Whether overwrite the destination
	@return:
		True if succeed else False
	"""
	if src == dst:	return False
	
	srclock = _lockfile(src)
	dstlock = _lockfile(dst)
	with filelock.FileLock(srclock), filelock.FileLock(dstlock):
		ret = _safeLink(src, dst, overwrite)
	return ret
	
def targz (srcdir, tgzfile, overwrite = True):
	"""
	Do a "tar zcf"-like for a directory
	@params:
		`tgzfile`: the final .tgz file
		`srcdir`:  the source directory
	"""
	if not path.isdir(srcdir):
		return False
		
	if overwrite:
		safeRemove(tgzfile)
	
	if not path.exists(tgzfile):
		cwd = getcwd()
		tar = tarfile.open(tgzfile, 'w:gz')
		chdir (srcdir)
		for name in glob ('./*'):
			tar.add(name)
		tar.close()
		chdir (cwd)
		return True
	else:
		return False
	
def untargz (tgzfile, dstdir, overwrite = True):
	"""
	Do a "tar zxf"-like for .tgz file
	@params:
		`tgzfile`:  the .tgz file
		`dstdir`: which directory to extract the file to
	"""
	if not path.isfile(tgzfile):
		return False
	if overwrite:
		safeRemove(dstdir)
	if not path.exists(dstdir):
		makedirs(dstdir)
		tar = tarfile.open (tgzfile, 'r:gz')
		tar.extractall (dstdir)
		tar.close()
		return True
	else:
		return False
	
def gz (srcfile, gzfile, overwrite = True):
	"""
	Do a "gzip"-like for a file
	@params:
		`gzfile`:  the final .gz file
		`srcfile`: the source file
	"""
	if not path.isfile(srcfile):
		return False
	if overwrite:
		safeRemove(gzfile)
	
	if not path.exists(gzfile):
		fin  = gzip.open (srcfile, 'rb')
		fout = gzip.open (gzfile, 'wb')
		copyfileobj (fin, fout)
		fin.close()
		fout.close()
		return True
	else:
		return False
		
def ungz (gzfile, dstfile, overwrite = True):
	"""
	Do a "gunzip"-like for a .gz file
	@params:
		`gzfile`:  the .gz file
		`dstfile`: the extracted file
	"""
	if not path.isfile(gzfile):
		return False
	if overwrite:
		safeRemove(dstfile)
	if not path.exists(dstfile):
		fin  = gzip.open (gzfile, 'rb')
		fout = open (dstfile, 'wb')
		copyfileobj (fin, fout)
		fin.close()
		fout.close()
		return True
	else:
		return False

def dirmtime (d):
	"""
	Calculate the mtime for a directory.
	Should be the max mtime of all files in it.
	@params:
		`d`:  the directory
	@returns:
		The mtime.
	"""
	mtime = 0
	for root, dirs, files in walk(d):
		m = path.getmtime (root) if path.exists(root) else 0
		if m > mtime:
			mtime = m
		for dr in dirs:
			m = dirmtime (path.join (root, dr))
			if m > mtime:
				mtime = m
		for f in files:
			m = path.getmtime (path.join (root, f)) if path.exists(path.join(root, f)) else 0
			if m > mtime:
				mtime = m
	return mtime

def filesig (fn):
	"""
	Calculate a signature for a file according to its path and mtime
	@params:
		`fn`: the file
	@returns:
		The md5 deigested signature.
	"""
	if fn == '': return ['', 0]
	fname = path.realpath(fn)
	if not path.exists (fname):
		return False
	mtime = dirmtime(fname) if path.isdir (fname) else path.getmtime(fname)
	# not using fname, because we intend to allow links to replace the original file
	# say in case of export using move
	if not mtime:
		return False
	return [fn, int(mtime)]

def chmodX (thefile):
	"""
	Convert script file to executable or add extract shebang to cmd line
	@params:
		`thefile`: the script file
	@returns:
		A list with or without the path of the interpreter as the first element and the script file as the last element
	"""
	thefile = path.realpath(thefile)
	ret = [thefile]
	try:
		st = stat (thefile)
		chmod (thefile, st.st_mode | S_IEXEC)
	except Exception as e1:
		try:
			shebang = open (thefile).read().strip().split("\n")[0]
			if not shebang.startswith("#!"):
				raise
			ret = shebang[2:].strip().split() + [thefile]
		except Exception as e2:
			raise Exception("Cannot change %s as executable or read the shebang from it:\n%s\n%s" % (thefile, e1, e2))
	return ret

def dumbPopen(cmd, shell = False):
	'''
	A dumb Popen (no stdout and stderr)
	@params:
		`cmd`: The command for `Popen`
		`shell`: The shell argument for `Popen`
	@returns:
		The process object
	'''
	with open(devnull, 'w') as f:
		ret = Popen(cmd, shell = shell, stdout = f, stderr = f)
	return ret
		