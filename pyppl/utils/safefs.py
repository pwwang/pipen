
import filelock
import tempfile

from stat import S_IEXEC
from os import path, remove as osremove, readlink, symlink, getcwd, makedirs, walk, stat, chmod, chdir
from shutil import rmtree, move as shmove, copyfileobj, copytree, copyfile

try:
	ChmodError = (OSError, PermissionError, UnicodeDecodeError)
except NameError:
	ChmodError = OSError

from multiprocessing import Lock

class SafeFs(object):
	"""
	A thread-safe file system
	
	@static variables:
		
		`TMPDIR`: The default temporary directory to store lock files

		# file types
		`FILETYPE_UNKNOWN`  : Unknown file type
		`FILETYPE_NOENT`    : File does not exist
		`FILETYPE_NOENTLINK`: A dead link (a link links to a non-existent file.
		`FILETYPE_FILE`     : A regular file
		`FILETYPE_FILELINK` : A link to a regular file
		`FILETYPE_DIR`      : A regular directory
		`FILETYPE_DIRLINK`  : A link to a regular directory

		# relation of two files
		`FILES_DIFF_BOTHNOENT` : Two files are different and none of them exists
		`FILES_DIFF_NOENT1`    : Two files are different but file1 does not exists
		`FILES_DIFF_NOENT2`    : Two files are different but file2 does not exists
		`FILES_DIFF_BOTHENT`   : Two files are different and both of them exist
		`FILES_SAME_STRNOENT`  : Two files are the same string and it does not exist
		`FILES_SAME_STRENT`    : Two files are the same string and it exists
		`FILES_SAME_BOTHLINKS` : Two files link to one file
		`FILES_SAME_BOTHLINKS1`: File1 links to file2, file2 links to a regular file
		`FILES_SAME_BOTHLINKS2`: File2 links to file1, file1 links to a regular file
		`FILES_SAME_REAL1`     : File2 links to file1, which a regular file
		`FILES_SAME_REAL2`     : File1 links to file2, which a regular file

		`LOCK`: A global lock ensures the locks are locked at the same time
	"""

	TMPDIR = tempfile.gettempdir()
	LOCK   = Lock()

	# file types
	FILETYPE_UNKNOWN   = -1
	FILETYPE_NOENT     = 0
	FILETYPE_NOENTLINK = 1
	FILETYPE_FILE      = 2
	FILETYPE_FILELINK  = 3
	FILETYPE_DIR       = 4
	FILETYPE_DIRLINK   = 5

	# relation of two files
	FILES_DIFF_BOTHNOENT  = 0
	FILES_DIFF_NOENT1     = 1
	FILES_DIFF_NOENT2     = 2
	FILES_DIFF_BOTHENT    = 3
	FILES_SAME_STRNOENT   = 4
	FILES_SAME_STRENT     = 5
	FILES_SAME_BOTHLINKS  = 6
	# file1 is the link to file2
	FILES_SAME_BOTHLINKS1 = 7
	# file2 is the link to file1
	FILES_SAME_BOTHLINKS2 = 8
	# file1 and file2 are the same file and file2 is the link to file1
	FILES_SAME_REAL1      = 9
	# file1 and file2 are the same file and file1 is the link to file2
	FILES_SAME_REAL2      = 10

	@staticmethod
	def _lockfile(filepath, real = True, filetype = None, tmpdir = None):
		"""
		Get the path of lockfile of a file
		@params:
			`filepath`: The file
			`real`    : Use the filepath itself or the realpath (if filepath is a link). Default: `True`
			`filetype`: The filetype, if not provided, will be fetched by `SafeFs._filetype`
			`tmpdir`  : The tmpdir storing the lock files.
		@returns:
			The path of the lock file
		"""
		if filepath is None:
			return None

		from . import uid
		filetype = filetype or SafeFs._filetype(filepath)
		tmpdir = tmpdir or SafeFs.TMPDIR
		filepath = path.realpath(filepath) if real and SafeFs._exists(filepath, filetype) else filepath
		return path.join(tmpdir, uid(filepath, 16) + '.lock')

	@staticmethod
	def _filetype(filepath):
		"""
		Get the file type
		@params:
			`filepath`: The file path
		@returns:
			The file type (one of `SafeFs.FILETYPE_*`)
		"""
		try:
			if path.islink(filepath):
				if path.isfile(filepath):
					return SafeFs.FILETYPE_FILELINK
				elif path.isdir(filepath):
					return SafeFs.FILETYPE_DIRLINK
				elif not path.exists(filepath):
					return SafeFs.FILETYPE_NOENTLINK
			elif not path.exists(filepath):
				return SafeFs.FILETYPE_NOENT
			elif path.isfile(filepath):
				return SafeFs.FILETYPE_FILE
			elif path.isdir(filepath):
				return SafeFs.FILETYPE_DIR
			else:
				return SafeFs.FILETYPE_UNKNOWN
		except Exception:
			return SafeFs.FILETYPE_UNKNOWN

	@staticmethod
	def _filerel(file1, file2, filetype1 = None, filetype2 = None):
		"""
		Check the relations between file1 and file2.
		@params:
			`file1`: The first file
			`file2`: The second file
			`filetype1`: The file type of file1
			`filetype2`: The file type of file2
		@returns:
			`SafeFs.FILES_DIFF_BOTHNOENT`: they are different for whatever reason.
			`SafeFs.FILES_DIFF_NOENT1`   : they are different for whatever reason.
			`SafeFs.FILES_DIFF_NOENT2`   : they are different for whatever reason.
			`SafeFs.FILES_DIFF_BOTHENT`  : they are different for whatever reason.
			`SafeFs.FILES_SAME_STRENT`   : they are the same string and the file exists.
			`SafeFs.FILES_SAME_STRNOENT` : they are the same string but the file doesn't exist.
			`SafeFs.FILES_SAME_BOTHLINKS`: both of them are links to the same file.
			`SafeFs.FILES_SAME_REAL1`    : file1 is the real file, file2 is a link to it.
			`SafeFs.FILES_SAME_REAL2`    : file2 is the real file, file1 is a link to it.
		"""
		filetype1 = filetype1 or SafeFs._filetype(file1)
		filetype2 = filetype2 or SafeFs._filetype(file2)

		if file1 == file2:
			if SafeFs._exists(file1, filetype1):
				return SafeFs.FILES_SAME_STRENT
			else:
				return SafeFs.FILES_SAME_STRNOENT
		else:
			if not SafeFs._exists(file1, filetype1) and not SafeFs._exists(file2, filetype2):
				return SafeFs.FILES_DIFF_BOTHNOENT
			elif not SafeFs._exists(file1, filetype1):
				return SafeFs.FILES_DIFF_NOENT1
			elif not SafeFs._exists(file2, filetype2):
				return SafeFs.FILES_DIFF_NOENT2

			if not path.samefile(file1, file2):
				return SafeFs.FILES_DIFF_BOTHENT
			else:
				if filetype1 in [SafeFs.FILETYPE_FILELINK, SafeFs.FILETYPE_DIRLINK] and \
					filetype2 in [SafeFs.FILETYPE_FILELINK, SafeFs.FILETYPE_DIRLINK]:
					if file1 == readlink(file2):
						return SafeFs.FILES_SAME_BOTHLINKS2
					elif file2 == readlink(file1):
						return SafeFs.FILES_SAME_BOTHLINKS1
					else:
						return SafeFs.FILES_SAME_BOTHLINKS
				elif filetype2 in [SafeFs.FILETYPE_FILELINK, SafeFs.FILETYPE_DIRLINK]:
					return SafeFs.FILES_SAME_REAL1
				else:
					return SafeFs.FILES_SAME_REAL2

	@staticmethod
	def _remove(filepath, filetype = None):
		"""
		Remove an entry
		@params:
			`filepath`: The path of the entry
			`filetype`: The file type
		@returns:
			`True` if succeed else `False`
		"""
		try:
			filetype = filetype or SafeFs._filetype(filepath)
			if not SafeFs._exists(filepath, filetype):
				return False
			if filetype == SafeFs.FILETYPE_DIR:
				rmtree(filepath)
			else:
				osremove(filepath)
			return True
		except OSError:
			return False

	@staticmethod
	def _copy(file1, file2, overwrite = True, filetype1 = None, filetype2 = None):
		"""
		Copy a file or a directory
		@params:
			`file1`    : The source
			`file2`    : The destination
			`overwrite`: Overwrite the destination? Default: `True`
			`filetype1`: The file type of file1
			`filetype2`: The file type of file2
		@returns:
			`True` if succeed else `False`
		"""
		try:
			filetype1 = filetype1 or SafeFs._filetype(file1)
			filetype2 = filetype2 or SafeFs._filetype(file2)
			rel = SafeFs._filerel(file1, file2, filetype1, filetype2)
			
			if rel in [
				SafeFs.FILES_SAME_STRNOENT,
				SafeFs.FILES_DIFF_BOTHNOENT,
				# I can't copy the source link to itself
				SafeFs.FILES_SAME_BOTHLINKS1,
				SafeFs.FILES_DIFF_NOENT1
			]:
				return False
			elif rel in [
				# assume file copied from the same file path
				SafeFs.FILES_SAME_STRENT,
				SafeFs.FILES_SAME_REAL2
			]:
				return True
			else:
				if SafeFs._exists(file2):
					if not overwrite or not SafeFs._remove(file2, filetype2):
						return False
				if filetype1 == SafeFs.FILETYPE_DIR or filetype1 == SafeFs.FILETYPE_DIRLINK:
					copytree(file1, file2)
					return True
				else:
					copyfile(file1, file2)
					return True
		except OSError: # pragma: no cover
			return False

	@staticmethod
	def _link(file1, file2, overwrite = True, filetype1 = None, filetype2 = None):
		"""
		Create a symbolic link for the given file
		@params:
			`file1`    : The source
			`file2`    : The destination
			`overwrite`: Overwrite the destination? Default: `True`
			`filetype1`: The file type of file1
			`filetype2`: The file type of file2
		@returns:
			`True` if succeed else `False`
		"""
		try:
			filetype1 = filetype1 or SafeFs._filetype(file1)
			filetype2 = filetype2 or SafeFs._filetype(file2)
			rel = SafeFs._filerel(file1, file2, filetype1, filetype2)

			if rel in [
				SafeFs.FILES_SAME_STRNOENT,
				SafeFs.FILES_DIFF_BOTHNOENT,
				# I can't copy the source link to itself
				SafeFs.FILES_SAME_BOTHLINKS1,
				SafeFs.FILES_DIFF_NOENT1,
				SafeFs.FILES_SAME_REAL2
			]:
				return False
			elif rel in [
				# assume file linked from the same file path
				SafeFs.FILES_SAME_STRENT,
				SafeFs.FILES_SAME_REAL1,
				SafeFs.FILES_SAME_BOTHLINKS2
			]:
				return True
			else:
				if SafeFs._exists(file2):
					if not overwrite or not SafeFs._remove(file2, filetype2):
						return False
				symlink(file1, file2)
				return True
		except OSError: # pragma: no cover
			return False

	@staticmethod
	def _exists(filepath, filetype = None):
		"""
		Tell if a file exists
		@params:
			`filepath`: The source
			`filetype`: The file type of file2
		@returns:
			`True` if exists else `False`
		"""
		filetype = filetype or SafeFs._filetype(filepath)
		if filetype == SafeFs.FILETYPE_NOENTLINK:
			osremove(filepath)
			return False
		return filetype in [
			SafeFs.FILETYPE_FILE,
			SafeFs.FILETYPE_FILELINK,
			SafeFs.FILETYPE_DIR,
			SafeFs.FILETYPE_DIRLINK
		]

	@staticmethod
	def _move(file1, file2, overwrite = True, filetype1 = None, filetype2 = None):
		"""
		Move a file
		@params:
			`file1`    : The source
			`file2`    : The destination
			`overwrite`: Overwrite the destination? Default: `True`
			`filetype1`: The file type of file1
			`filetype2`: The file type of file2
		@returns:
			`True` if succeed else `False`
		"""
		try:
			filetype1 = filetype1 or SafeFs._filetype(file1)
			filetype2 = filetype2 or SafeFs._filetype(file2)
			rel = SafeFs._filerel(file1, file2, filetype1, filetype2)

			if rel in [
				SafeFs.FILES_DIFF_BOTHNOENT,
				SafeFs.FILES_DIFF_NOENT1,
				SafeFs.FILES_SAME_STRNOENT,
				# I can't copy the source link to itself
				SafeFs.FILES_SAME_BOTHLINKS1,
				SafeFs.FILES_SAME_REAL2
			]:
				return False
			elif rel in [
				# assume file linked from the same file path
				SafeFs.FILES_SAME_STRENT
			]:
				return True
			else:
				# NOENTLINK may be removed somewhere else
				# if SafeFs._exists(file2, filetype2):
				if SafeFs._exists(file2):
					if not overwrite or not SafeFs._remove(file2, filetype2):
						return False
				shmove(file1, file2)
				return True
		except OSError: # pragma: no cover
			return False

	@staticmethod
	def _gz(file1, file2, overwrite = True, filetype1 = None, filetype2 = None):
		"""
		Gzip a file or tar gzip a directory
		@params:
			`file1`    : The source
			`file2`    : The destination
			`overwrite`: Overwrite the destination? Default: `True`
			`filetype1`: The file type of file1
			`filetype2`: The file type of file2
		@returns:
			`True` if succeed else `False`
		"""
		try:
			filetype1 = filetype1 or SafeFs._filetype(file1)
			filetype2 = filetype2 or SafeFs._filetype(file2)
			rel = SafeFs._filerel(file1, file2, filetype1, filetype2)

			if rel in [
				SafeFs.FILES_DIFF_BOTHNOENT,
				SafeFs.FILES_DIFF_NOENT1,
				SafeFs.FILES_SAME_STRNOENT,
				SafeFs.FILES_SAME_REAL2,
				SafeFs.FILES_SAME_BOTHLINKS1
			]:
				return False
			else:
				if SafeFs._exists(file2):
					if not overwrite or not SafeFs._remove(file2, filetype2):
						return False
				if filetype1 in [SafeFs.FILETYPE_DIR, SafeFs.FILETYPE_DIRLINK]:
					import tarfile, glob
					tar = tarfile.open(file2, 'w:gz')
					cwd = getcwd()
					chdir(file1)
					for name in glob.glob('./*'):
						tar.add(name)
					tar.close()
					chdir(cwd)
					return True
				else:
					import gzip
					with open(file1, 'rb') as fin, gzip.open(file2, 'wb') as fout:
						copyfileobj(fin, fout)
					return True

		except OSError: # pragma: no cover
			return False

	@staticmethod
	def _ungz(file1, file2, overwrite = True, filetype1 = None, filetype2 = None):
		"""
		Decompress a gzip file or tar-gzip file
		@params:
			`file1`    : The source
			`file2`    : The destination
			`overwrite`: Overwrite the destination? Default: `True`
			`filetype1`: The file type of file1
			`filetype2`: The file type of file2
		@returns:
			`True` if succeed else `False`
		"""
		try:
			filetype1 = filetype1 or SafeFs._filetype(file1)
			filetype2 = filetype2 or SafeFs._filetype(file2)
			rel = SafeFs._filerel(file1, file2, filetype1, filetype2)

			if rel in [
				SafeFs.FILES_DIFF_BOTHNOENT,
				SafeFs.FILES_DIFF_NOENT1,
				SafeFs.FILES_SAME_STRNOENT,
				SafeFs.FILES_SAME_REAL2,
				SafeFs.FILES_SAME_BOTHLINKS1
			] or filetype1 not in [
				SafeFs.FILETYPE_FILE,
				SafeFs.FILETYPE_FILELINK
			]:
				return False
			else:
				if SafeFs._exists(file2):
					if not overwrite or not SafeFs._remove(file2, filetype2):
						return False
				if file1.endswith('.tgz') or file1.endswith('.tar.gz'):
					import tarfile
					tar = tarfile.open(file1, 'r:gz')
					makedirs(file2)
					tar.extractall(file2)
					tar.close()
					return True
				else:
					import gzip
					with gzip.open(file1, 'rb') as fin, open(file2, 'wb') as fout:
						copyfileobj(fin, fout)
					return True

		except OSError: # pragma: no cover
			return False

	@staticmethod
	def _dirmtime(filepath):
		"""
		Get the modified time of a directory recursively
		@params:
			`filepath`: The file path
		@return`:
			The most recent modified time
		"""
		# assert self.filetype1 in [SafeFs.FILETYPE_DIR, SafeFs.FILETYPE_DIRLINK]:
		mtime = 0
		for root, dirs, files in walk(filepath):
			m = path.getmtime (root) if path.exists(root) else 0
			mtime = max(m, mtime)
			for dr in dirs:
				m = SafeFs._dirmtime (path.join (root, dr))
				mtime = max(m, mtime)
			for f in files:
				m = path.getmtime (path.join (root, f)) if path.exists(path.join(root, f)) else 0
				mtime = max(m, mtime)
		return mtime

	def __init__(self, file1, file2 = None, tmpdir = None):
		"""
		Constructor
		@params:
			`file1`:  File 1
			`file2`:  File 2. Default: `None`
			`tmpdir`: The temporary directory used to store lock files. Default: `None` (`SafeFs.TMPDIR`)
		"""
		self.file1     = file1
		self.file2     = file2
		self.filetype1 = SafeFs._filetype(file1)
		self.filetype2 = SafeFs._filetype(file2)
		self.tmpdir    = tmpdir
		
		self.locks     = []

	def _lock(self, lock1 = 'both', lock2 = 'both'):
		"""
		Lock the file slots
		@params:
			`lock1`: Which slots to lock for file1
				- `both`: Both the file itself and the realpath of it (if it is a link)
				- `real`: Only the realpath of it
				- `self`: Just the file itself
			`lock2`: Which slots to lock for file2
		"""
		lockfiles = []
		if self.file1:
			if lock1 == 'self':
				lockfiles.append(SafeFs._lockfile(self.file1, False, self.filetype1, self.tmpdir))
			elif lock1 == 'real':
				lockfiles.append(SafeFs._lockfile(self.file1, True, self.filetype1, self.tmpdir))
			else:
				lockfiles.append(SafeFs._lockfile(self.file1, False, self.filetype1, self.tmpdir))
				lockfiles.append(SafeFs._lockfile(self.file1, True, self.filetype1, self.tmpdir))
		if self.file2:
			if lock2 == 'self':
				lockfiles.append(SafeFs._lockfile(self.file2, False, self.filetype2, self.tmpdir))
			elif lock2 == 'real': # pragma: no cover
				# in most cases, we don't need to lock realpath of lock2
				lockfiles.append(SafeFs._lockfile(self.file2, True, self.filetype2, self.tmpdir))
			else:
				lockfiles.append(SafeFs._lockfile(self.file2, False, self.filetype2, self.tmpdir))
				lockfiles.append(SafeFs._lockfile(self.file2, True, self.filetype2, self.tmpdir))

		for lfile in set(lockfiles):
			lock = filelock.FileLock(lfile)
			self.locks.append(lock)
		
		# have to lock it at the same time!
		# otherwise it will be a deadlock if locks acquired by different instances
		with SafeFs.LOCK:
			for lock in self.locks:
				lock.acquire()
	
	def _unlock(self):
		"""
		Unlock the slots
		"""
		for lock in self.locks:
			lock.release()

	def exists(self, callback = None):
		"""
		Tell if file1 exists thread-safely
		@params:
			`callback`: The callback. arguments: 
				- `r` : Whether the file exists
				- `fs`: This instance
		@returns:
			`True` if exists else `False`
		"""
		self._lock()
		#r = SafeFs._exists(self.file1, self.filetype1)
		# cannot rely on filetype1, file1 may be removed by other threads
		r = SafeFs._exists(self.file1)
		if callable(callback):
			callback(r, self)
		self._unlock()
		return r

	def samefile(self, callback = None):
		"""
		Tell if file1 and file2 are the same file in a thread-safe way
		@params:
			`callback`: The callback. arguments: 
				- `r` : Whether the file exists
				- `fs`: This instance
		@returns:
			`True` if they are the same file else `False`
		"""
		self._lock()
		rel = SafeFs._filerel(self.file1, self.file2)
		r = rel in [
			SafeFs.FILES_SAME_BOTHLINKS,
			SafeFs.FILES_SAME_BOTHLINKS1,
			SafeFs.FILES_SAME_BOTHLINKS2,
			SafeFs.FILES_SAME_REAL1,
			SafeFs.FILES_SAME_REAL2,
			SafeFs.FILES_SAME_STRENT,
			SafeFs.FILES_SAME_STRNOENT
		]
		if callable(callback):
			callback(r, self)
		self._unlock()
		return r

	def remove(self, callback = None):
		"""
		Remove file1 thread-safely
		@params:
			`callback`: The callback. arguments: 
				- `r` : Whether the file exists
				- `fs`: This instance
		@returns:
			`True` if succeed else `False`
		"""
		self._lock(lock1 = 'self')
		r = SafeFs._remove(self.file1, self.filetype1)
		if callable(callback):
			callback(r, self)
		self._unlock()
		return r

	def move(self, overwrite = True, callback = None):
		"""
		Move file1 to file2 thread-safely
		@params:
			`overwrite`: Allow overwrting file2? Default: `True`
			`callback`:  The callback. arguments: 
				- `r` :  Whether the file exists
				- `fs`:  This instance
		@returns:
			`True` if succeed else `False`
		"""
		self._lock(lock1 = 'self', lock2 = 'self')
		r = SafeFs._move(self.file1, self.file2, overwrite)
		if callable(callback):
			callback(r, self)
		self._unlock()
		return r
	
	def copy(self, overwrite = True, callback = None):
		"""
		Copy file1 to file2 thread-safely
		@params:
			`overwrite`: Allow overwrting file2? Default: `True`
			`callback`:  The callback. arguments: 
				- `r` :  Whether the file exists
				- `fs`:  This instance
		@returns:
			`True` if succeed else `False`
		"""
		self._lock(lock1 = 'both', lock2 = 'self')
		r = SafeFs._copy(self.file1, self.file2, overwrite)
		if callable(callback):
			callback(r, self)
		self._unlock()
		return r

	def link(self, overwrite = True, callback = None):
		"""
		Link file1 to file2 thread-safely
		@params:
			`overwrite`: Allow overwrting file2? Default: `True`
			`callback`:  The callback. arguments: 
				- `r` :  Whether the file exists
				- `fs`:  This instance
		@returns:
			`True` if succeed else `False`
		"""
		self._lock(lock1 = 'self', lock2 = 'self')
		r = SafeFs._link(self.file1, self.file2, overwrite)
		if callable(callback):
			callback(r, self)
		self._unlock()
		return r

	def moveWithLink(self, overwrite = True, callback = None):
		"""
		Move file1 to file2 and link file2 to file1 in a thread-safe way
		@params:
			`overwrite`: Allow overwrting file2? Default: `True`
			`callback`:  The callback. arguments: 
				- `r` :  Whether the file exists
				- `fs`:  This instance
		@returns:
			`True` if succeed else `False`
		"""
		self._lock(lock1 = 'self', lock2 = 'self')
		r = SafeFs._move(self.file1, self.file2, overwrite)
		if r:
			r = SafeFs._link(self.file2, self.file1, overwrite = False)
		if callable(callback):
			callback(r, self)
		self._unlock()
		return r

	def gz(self, overwrite = True, callback = None):
		"""
		Gzip file1 (tar-gzip if file1 is a directory) to file2 in a thread-safe way
		@params:
			`overwrite`: Allow overwrting file2? Default: `True`
			`callback`:  The callback. arguments: 
				- `r` :  Whether the file exists
				- `fs`:  This instance
		@returns:
			`True` if succeed else `False`
		"""
		self._lock(lock1 = 'real', lock2 = 'self')
		r = SafeFs._gz(self.file1, self.file2, overwrite)

		if callable(callback):
			callback(r, self)
		self._unlock()
		return r

	def ungz(self, overwrite = True, callback = None):
		"""
		Ungzip file1 (tar-ungzip if file1 tar-gzipped to file2 in a thread-safe way
		@params:
			`overwrite`: Allow overwrting file2? Default: `True`
			`callback`:  The callback. arguments: 
				- `r` :  Whether the file exists
				- `fs`:  This instance
		@returns:
			`True` if succeed else `False`
		"""
		self._lock(lock1 = 'real', lock2 = 'self')
		r = SafeFs._ungz(self.file1, self.file2, overwrite)
		if callable(callback):
			callback(r, self)
		self._unlock()
		return r

	def filesig(self, dirsig = True):
		"""
		Generate a signature for a file
		@params:
			`dirsig`: Whether expand the directory? Default: True
		@returns:
			The signature
		"""
		self._lock(lock1 = 'real')
		if not self.file1:
			self._unlock()
			return ['', 0]
		if not SafeFs._exists(self.file1):
			self._unlock()
			return False

		if dirsig and self.filetype1 in [SafeFs.FILETYPE_DIR, SafeFs.FILETYPE_DIRLINK]:
			mtime = SafeFs._dirmtime(self.file1)
		else:
			mtime = path.getmtime(self.file1)
		self._unlock()
		return [self.file1, int(mtime)]

	def chmodX(self):
		"""
		Convert file1 to executable or add extract shebang to cmd line
		@returns:
			A list with or without the path of the interpreter as the first element and the script file as the last element
		"""
		if not self.filetype1 in [SafeFs.FILETYPE_FILE, SafeFs.FILETYPE_FILELINK]:
			raise OSError('Unable to make {} as executable'.format(self.file1))
		
		ret = [self.file1]
		self._lock(lock1 = 'real')
		try:
			chmod(self.file1, stat(self.file1).st_mode | S_IEXEC)
		except ChmodError:
			shebang = None
			with open(self.file1) as fsb:
				try:
					shebang = fsb.readline().strip()
				except ChmodError: # pragma: no cover
					# may raise UnicodeDecodeError for python3
					pass
			if not shebang or not shebang.startswith('#!'):
				raise OSError('Unable to make {} as executable by chmod and detect interpreter from shebang.'.format(self.file1))
			ret = shebang[2:].strip().split() + [self.file1]
		finally:
			self._unlock()
		return ret

	@staticmethod
	def flush(fd, lastmsg, end = False):
		"""
		Flush a file descriptor
		@params:
			`fd`     : The file handler
			`lastmsg`: The remaining content of last flush
			`end`    : The file ends? Default: `False`
		"""
		fd.flush()
		# OSX cannot tell the pointer automatically
		fd.seek(fd.tell())
		lines = fd.readlines() or []
		if lines:
			lines[0] = lastmsg + lines[0]
			lastmsg  = '' if lines[-1].endswith('\n') else lines.pop(-1)
			if lastmsg and end:
				lines.append(lastmsg + '\n')
				lastmsg = ''
		elif lastmsg and end:
			lines.append(lastmsg + '\n')
			lastmsg = ''
		return lines, lastmsg

	@staticmethod
	def basename(filepath):
		"""
		Get the basename of a file
		If it is a directory like '/a/b/c/', return `c`
		@params:
			`filepath`: The file path
		@returns:
			The basename
		"""
		bname = path.basename(filepath)
		if not bname and path.isdir(filepath):
			bname = path.basename(path.dirname(filepath))
		return bname

# shortcuts
def exists(filepath, callback = None):
	"""
	A shortcut of `SafeFs.exists`
	@params:
		`filepath`: The filepath
		`callback`: The callback. arguments: 
			- `r` : Whether the file exists
			- `fs`: This instance
	@returns:
		`True` if the file exists else `False`
	"""
	return SafeFs(filepath).exists(callback)

def remove(filepath, callback = None):
	"""
	A shortcut of `SafeFs.remove`
	@params:
		`filepath`: The filepath
		`callback`: The callback. arguments: 
			- `r` : Whether the file exists
			- `fs`: This instance
	@returns:
		`True` if succeed else `False`
	"""
	return SafeFs(filepath).remove(callback)

def move(file1, file2, overwrite = True, callback = None):
	"""
	A shortcut of `SafeFs.move`
	@params:
		`file1`    : File 1
		`file2`    : File 2
		`overwrite`: Whether overwrite file 2. Default: `True`
		`callback` : The callback. arguments: 
			- `r` : Whether the file exists
			- `fs`: This instance
	@returns:
		`True` if succeed else `False`
	"""
	return SafeFs(file1, file2).move(overwrite, callback)

def copy(file1, file2, overwrite = True, callback = None):
	"""
	A shortcut of `SafeFs.copy`
	@params:
		`file1`    : File 1
		`file2`    : File 2
		`overwrite`: Whether overwrite file 2. Default: `True`
		`callback` : The callback. arguments: 
			- `r` : Whether the file exists
			- `fs`: This instance
	@returns:
		`True` if succeed else `False`
	"""
	return SafeFs(file1, file2).copy(overwrite, callback)

def link(file1, file2, overwrite = True, callback = None):
	"""
	A shortcut of `SafeFs.link`
	@params:
		`file1`    : File 1
		`file2`    : File 2
		`overwrite`: Whether overwrite file 2. Default: `True`
		`callback` : The callback. arguments: 
			- `r` : Whether the file exists
			- `fs`: This instance
	@returns:
		`True` if succeed else `False`
	"""
	return SafeFs(file1, file2).link(overwrite, callback)

def moveWithLink(file1, file2, overwrite = True, callback = None):
	"""
	A shortcut of `SafeFs.moveWithLink`
	@params:
		`file1`    : File 1
		`file2`    : File 2
		`overwrite`: Whether overwrite file 2. Default: `True`
		`callback` : The callback. arguments: 
			- `r` : Whether the file exists
			- `fs`: This instance
	@returns:
		`True` if succeed else `False`
	"""
	return SafeFs(file1, file2).moveWithLink(overwrite, callback)

def gz(file1, file2, overwrite = True, callback = None):
	"""
	A shortcut of `SafeFs.gz`
	@params:
		`file1`    : File 1
		`file2`    : File 2
		`overwrite`: Whether overwrite file 2. Default: `True`
		`callback` : The callback. arguments: 
			- `r` : Whether the file exists
			- `fs`: This instance
	@returns:
		`True` if succeed else `False`
	"""
	return SafeFs(file1, file2).gz(overwrite, callback)

def ungz(file1, file2, overwrite = True, callback = None):
	"""
	A shortcut of `SafeFs.ungz`
	@params:
		`file1`    : File 1
		`file2`    : File 2
		`overwrite`: Whether overwrite file 2. Default: `True`
		`callback` : The callback. arguments: 
			- `r` : Whether the file exists
			- `fs`: This instance
	@returns:
		`True` if succeed else `False`
	"""
	return SafeFs(file1, file2).ungz(overwrite, callback)


