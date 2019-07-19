"""
A set of utitities for PyPPL
"""
import re
import inspect
from queue import PriorityQueue
from os import path, walk, sep as pathsep
from hashlib import md5
from threading import Thread
import psutil
from transitions import Transition, Machine
from box import Box as _Box
import cmdy
from simpleconf import Config
from . import _fsutil as fs

cmdy   = cmdy(_raise = False) # pylint: disable=invalid-name,not-callable
config = Config() # pylint: disable=invalid-name

class Box(_Box):
	"""
	Subclass of box.Box to fix box_intact_types to [list] and
	rewrite __repr__ to make the string results back to object
	Requires python-box ^3.4.1
	"""

	def __init__(self, *args, **kwargs):
		kwargs['box_intact_types'] = kwargs.pop('box_intact_types', [list])
		super(Box, self).__init__(*args, **kwargs)

	def __repr__(self):
		"""Make sure repr can retrieve the object back"""
		ret = 'Box(%r, box_intact_types = (list,))' % self.items()
		return ret.replace('<BoxList: [', '[').replace(']>', ']')

	def __str__(self):
		return super(Box, self).__repr__()

class OBox(Box):
	"""Ordered Box"""
	def __init__(self, *args, **kwargs):
		kwargs['ordered_box'] = True
		super(OBox, self).__init__(*args, **kwargs)

	def __repr__(self):
		"""Make sure repr can retrieve the object back"""
		return 'Box(%r, box_intact_types = (list,), ordered_box = True)' % self.items()

OrderedBox = OBox # pylint: disable=invalid-name

def loadConfigurations(conf, *cfgfiles):
	conf.clear()
	conf._load(*cfgfiles)

# remove python2 support
# try:
# 	from Queue import Queue, PriorityQueue, Empty as QueueEmpty
# except ImportError: # pragma: no cover
# 	from queue import Queue, PriorityQueue, Empty as QueueEmpty


# try:
# 	string_types = basestring # pylint: disable=invalid-name
# except NameError: # pragma: no cover
# 	string_types = str # pylint: disable=invalid-name

def varname(context = 31):
	"""
	Get the variable name for ini
	@params:
		`maxline`: The max number of lines to retrive. Default: 20
		`incldot`: Whether include dot in the variable name. Default: False
	@returns:
		The variable name
	"""
	stacks   = inspect.stack(context)
	parent   = stacks[1]
	grandpar = stacks[2]
	keyword  = parent[3]
	# find the class name
	if keyword == '__init__':
		keyword = parent[0].f_locals['self'].__class__.__name__

	for i in range(grandpar[5], 0, -1):
		code = grandpar[4][i]
		if not keyword in code:
			continue
		match = re.search(r'([\w_]+)\s*=\s*[\w_.]*' + keyword, code)
		if not match:
			break
		return match.group(1)

	varname.index += 1
	return 'var_%s' % (varname.index - 1)

varname.index = 0

def split (string, delimter, trim = True):
	"""
	Split a string using a single-character delimter
	@params:
		`string`: the string
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
	special2 = ['\'', '"', '`']
	special3 = '\\'
	flags1   = [0, 0, 0]
	flags2   = [False, False, False]
	flags3   = False
	start = 0
	for i, char in enumerate(string):
		if char == special3:
			flags3 = not flags3
		elif not flags3:
			if char in special1:
				index = special1.index(char)
				if index % 2 == 0:
					flags1[int(index/2)] += 1
				else:
					flags1[int(index/2)] -= 1
			elif char in special2:
				index = special2.index(char)
				flags2[index] = not flags2[index]
			elif char == delimter and not any(flags1) and not any(flags2):
				rest = string[start:i]
				if trim:
					rest = rest.strip()
				ret.append(rest)
				start = i + 1
		else:
			flags3 = False
	rest = string[start:]
	if trim:
		rest = rest.strip()
	ret.append(rest)
	return ret

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
			sig = getsource(func).strip()
		except (TypeError, ValueError): # pragma: no cover
			sig = func.__name__
	else:
		sig = 'None'
	return sig

def uid(string, length = 8,
	alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'):
	"""
	Calculate a short uid based on a string.
	Safe enough, tested on 1000000 32-char strings, no repeated uid found.
	This is used to calcuate a uid for a process
	@params:
		`string`: the base string
		`length`: the length of the uid
		`alphabet`: the charset used to generate the uid
	@returns:
		The uid
	"""
	string = md5(str(string).encode('utf-8')).hexdigest()
	number = int (string, 16)
	base = ''

	while number != 0:
		number, i = divmod(number, len(alphabet))
		base = alphabet[i] + base

	return base[:length]

def formatSecs (seconds):
	"""
	Format a time duration
	@params:
		`seconds`: the time duration in seconds
	@returns:
		The formated string.
		For example: "01:01:01.001" stands for 1 hour 1 min 1 sec and 1 minisec.
	"""
	minute, sec  = divmod(seconds, 60)
	hour, minute = divmod(minute, 60)
	return "%02d:%02d:%02d.%03.0f" % (hour, minute, sec, 1000*(sec-int(sec)))

def alwaysList (data, trim = True):
	"""
	Convert a string or a list with element
	@params:
		`data`: the data to be converted
		`trim`: trim the whitespaces for each item or not. Default: True
	@examples:
		```python
		data = ["a, b, c", "d"]
		ret  = alwaysList (data)
		# ret == ["a", "b", "c", "d"]
		```
	@returns:
		The split list
	"""
	if isinstance(data, str):
		return split(data, ',', trim)
	if isinstance(data, list):
		return sum((alwaysList(dat, trim)
			if isinstance(dat, (str, list)) else [dat]
			for dat in data), [])
	raise ValueError('Expect str/list to convert to list, but got %r.' % type(data).__name__)

def expandNumbers(numbers):
	"""
	Expand a descriptive numbers like '0,3-5,7' into read numbers:
	[0,3,4,5,7]
	@params:
		numbers (str): The string of numbers to expand.
	@returns:
		list: The real numbers
	"""
	numberstrs = alwaysList(numbers)
	numbers = []
	for numberstr in numberstrs:
		if '-' not in numberstr:
			numbers.append(int(numberstr))
		else:
			numstart, numend = numberstr.split('-')
			numbers.extend(range(int(numstart), int(numend)+1))
	return numbers

def briefList(blist, base = 0):
	"""
	Briefly show an integer list, combine the continuous numbers.
	@params:
		`blist`: The list
	@returns:
		The string to show for the briefed list.
	"""
	if not blist:
		return "[]"
	blist = [b + base for b in blist]
	if len(blist) == 1:
		return str(blist[0])
	blist       = sorted(blist)
	groups  = [[]]
	ret     = []
	for i in range(0, len(blist) - 1):
		ele0 = blist[i]
		ele1 = blist[i + 1]
		if ele1 - ele0 > 1:
			groups[-1].append(ele0)
			groups.append([])
		else:
			groups[-1].append(ele0)
	groups[-1].append(blist[-1])
	for group in groups:
		if len(group) == 1:
			ret.append(str(group[0]))
		elif len(group) == 2:
			ret.append(str(group[0]))
			ret.append(str(group[1]))
		else:
			ret.append(str(group[0]) + '-' + str(group[-1]))
	return ', '.join(ret)

def briefPath(bpath, cutoff = 0):
	"""
	Show briefed path in logs
	/abcde/hijklm/opqrst/uvwxyz/123456 will be shorted as:
	/a/h/opqrst/uvwxyz/123456
	@params:
		`bpath` : The path
		`cutoff`: Shorten the whole path if it more than length of cutoff. Default: `0`
	@returns:
		The shorted path
	"""
	if not cutoff or not bpath or not str(bpath):
		return bpath

	bpath = path.normpath(bpath)
	lenp  = len(bpath)
	more  = lenp - cutoff

	if more <= 0:
		return bpath

	parts = bpath.split(pathsep)
	if len(parts) == 1:
		return bpath

	if not parts[0]:
		parts[0] = pathsep
	basename = parts.pop(-1)
	while more > 0:
		lens      = [len(part) for part in parts]
		maxlen    = max(lens)
		nextlen   = max([length for length in lens if length < maxlen] + [1])
		if nextlen == maxlen: # == 1, nothing to delete
			break
		maxidx    = [i for i, length in enumerate(lens) if length == maxlen]
		nmax      = len(maxidx)
		if more < nmax:
			for i in range(more):
				parts[maxidx[nmax-i-1]] = parts[maxidx[nmax-i-1]][:-1]
			more = 0
			continue
		lentodel = min(maxlen - nextlen, int(more/nmax))
		for i in maxidx:
			more -= lentodel
			parts[i] = parts[i][:-lentodel]

	return path.join(*(parts + [basename]))

def formatDict(val, keylen, alias = None):
	"""Format the dict values in log
	Value            | Alias | Formatted
	-----------------|-------|-------------
	"a"              |       | a
	"a"              | b     | [b] a
	{"a": 1}         | l     | [l] { a: 1 }
	{"a": 1, "b": 2} | x     | [x] { a: 1,
	                 |       |       b: 2 }
	Box(a=1)         |       | <Box> { a: 1 }
	Box(a=1,b=2)     | b     | [b] <Box>
	                 |       |     { a: 1,
	                 |       |       b: 2 }
	"""
	alias = '[%s] ' % alias if alias else ''
	if not isinstance(val, dict):
		ret = alias
		return ret + (repr(val) if val == '' else str(val))

	valtype = val.__class__.__name__
	valtype = '' if valtype == 'dict' else '<%s> ' % valtype

	if len(val) == 0:
		return alias + valtype + '{  }'
	if len(val) == 1:
		return formatDict(alias + valtype + '{ %s: %s }' % list(val.items())[0], 0)

	valkeylen = max(len(key) for key in val)
	ret = [alias + valtype]
	key0, val0 = list(val.items())[0]
	if not alias or not valtype:
		braceindt = len(alias + valtype)
		ret[0] += '{ %s: %s,' % (
			key0.ljust(valkeylen), repr(val0) if val0 == '' else val0)
	else:
		braceindt = len(alias)

	for keyi, vali in val.items():
		if keyi == key0 and (not alias or not valtype):
			continue
		fmt = '%s{ %s: %s,' if keyi == key0 else '%s  %s: %s,'
		ret.append(fmt % (' ' * (braceindt + keylen + 4),
			keyi.ljust(valkeylen), repr(vali) if vali == '' else vali))
	ret[-1] += ' }'
	return '\n'.join(ret)


def killtree(pid, killme = True, sig = 9, timeout = None): # signal.SIGKILL
	"""Kill a process and its childrent"""
	myself = psutil.Process(pid)
	children = myself.children(recursive=True)
	if killme:
		children.append(myself)
	for proc in children:
		proc.send_signal(sig)

	return psutil.wait_procs(children, timeout=timeout)

def chmodX(filepath):
	"""
	Convert file1 to executable or add extract shebang to cmd line
	@returns:
		A list with or without the path of the interpreter as the first element
		and the script file as the last element
	"""
	from stat import S_IEXEC
	from os import chmod, stat
	filepath = str(filepath)
	if not path.isfile(filepath):
		raise OSError('Unable to make {} as executable'.format(filepath))
	# in case it's a Path-like object
	ret = [filepath]
	try:
		chmod(filepath, stat(filepath).st_mode | S_IEXEC)
	except (OSError, PermissionError):
		shebang = None
		with open(filepath) as fsb:
			try:
				shebang = fsb.readline().strip()
			except (OSError, PermissionError, UnicodeDecodeError):
				# may raise UnicodeDecodeError for python3
				pass

		if not shebang or not shebang.startswith('#!'):
			raise OSError('Unable to make {} as executable by chmod '
				'and detect interpreter from shebang.'.format(filepath))
		ret = shebang[2:].strip().split() + [filepath]
	return ret

def filesig(filepath, dirsig = True):
	"""
	Generate a signature for a file
	@params:
		`dirsig`: Whether expand the directory? Default: True
	@returns:
		The signature
	"""
	if not filepath:
		return ['', 0]
	if not fs.exists(filepath):
		return False

	if dirsig and fs.isdir(filepath):
		mtime = path.getmtime(filepath)
		for root, dirs, files in walk(filepath):
			for directory in dirs:
				mtime2 = path.getmtime(path.join(root, directory))
				mtime  = max(mtime, mtime2)
			for filename in files:
				mtime2 = path.getmtime(path.join(root, filename))
				mtime  = max(mtime, mtime2)
	else:
		mtime = path.getmtime(filepath)
	return [str(filepath), int(mtime)]

def fileflush(filed, residue, end = False):
	"""
	Flush a file descriptor
	@params:
		`filed`  : The file handler
		`residue`: The remaining content of last flush
		`end`    : The file ends? Default: `False`
	"""
	filed.flush()
	# OSX cannot tell the pointer automatically
	filed.seek(filed.tell())
	lines = filed.readlines() or []
	if lines:
		lines[0] = residue + lines[0]
		residue  = '' if lines[-1].endswith('\n') else lines.pop(-1)
		if residue and end:
			lines.append(residue + '\n')
			residue = ''
	elif residue and end:
		lines.append(residue + '\n')
		residue = ''
	return lines, residue

class ThreadEx(Thread):
	"""
	A thread able to send exception to main thread
	thread.ex will hold the exception.
	"""

	def __init__(self, group=None, target=None, name=None, args=None, kwargs=None):
		Thread.__init__(self, group, target, name, args or (), kwargs or {})
		self.daemon = True
		self.ex     = None

	def run(self):
		try:
			Thread.run(self)
		except cmdy.CmdyReturnCodeException:
			#from traceback import format_exc
			self.ex = RuntimeError('cmdy.CmdyReturnCodeException')
		except Exception as ex: # pylint: disable=broad-except
			#from traceback import format_exc
			self.ex = ex

class ThreadPool(object):
	"""
	A thread manager for ThreadEx.
	"""

	def __init__(self, nthread, initializer = None, initargs = None):
		self.threads = []
		if not isinstance(initargs, list):
			initargs = [(initargs, ) if initargs else ()] * nthread
		for i in range(nthread):
			thread = ThreadEx(target = initializer, args = initargs[i])
			thread.start()
			self.threads.append(thread)

	def join(self, interval = 1, cleanup = None):
		"""
		Try to join the threads, able to respond to KeyboardInterrupt
		@params:
			`interval`: The interval/timeout to join every time.
			`cleanup` : The cleanup function
		"""
		try:
			while True:
				threads_alive = 0
				for thread in self.threads:
					# check if the thread is done
					thread.join(timeout = interval)
					if thread.ex:
						# exception raised, try to quit and cleanup
						if not callable(cleanup):
							raise thread.ex
						cleanup(thread.ex)
						threads_alive = 0
						break
					elif thread.is_alive():
						threads_alive += 1
				if threads_alive == 0:
					break
		except KeyboardInterrupt as ex: # pragma: no cover
			if callable(cleanup):
				cleanup(ex = ex)

class PQueue(PriorityQueue):
	"""
	A modified PriorityQueue, which allows jobs to be submitted in batch
	"""

	def __init__(self, maxsize = 0, batch_len = None):
		"""
		A Priority Queue for PyPPL jobs

			0                              0 done,             wait for 1
			  1        start 0    1        start 1             start 2
				2      ------>  0   2      ------>      2      --------->
				  3                   3               1   3                    3
					4                   4                   4                2   4
																		   1
		@params:
			`maxsize`  : The maxsize of the queue. Default: None
			`batch_len`: What's the length of a batch
		"""
		if not batch_len:
			raise ValueError('`batch_len` is required for PQueue.')
		PriorityQueue.__init__(self, maxsize)
		self.batchLen = batch_len

	def putNext(self, item, batch):
		"""Put item to next batch"""
		self.put(item, batch + 2)

	def put(self, item, batch = None): # pylint: disable=arguments-differ
		batch = batch or item
		PriorityQueue.put(self, item + batch * self.batchLen)

	def get(self): # pylint: disable=arguments-differ
		"""
		Get an item from the queue
		"""
		item = PriorityQueue.get(self)
		batch, index  = divmod(item, self.batchLen)
		return index, batch

class Hashable(object):
	"""
	A class for object that can be hashable
	"""
	def __hash__(self):
		"""
		Use id as identifier for hash
		"""
		return id(self)

	def __eq__(self, other):
		"""
		How to compare the hash keys
		"""
		return id(self) == id(other)

	def __ne__(self, other):
		"""
		Compare hash keys
		"""
		return not self.__eq__(other)

class MultiDestTransition(Transition):
	"""Transition with multiple destination"""
	def __init__(self, source, dest, conditions=None, unless=None,
		before=None, after=None, prepare=None, **kwargs):

		self._result = self._dest = None
		super(MultiDestTransition, self).__init__(
			source, dest, conditions, unless, before, after, prepare)
		if isinstance(dest, dict):
			self._func = kwargs.pop('depends_on', None)
			if not self._func:
				raise AttributeError("A multi-destination transition requires a 'depends_on'")
		else:
			# use base version in case transition does not need special handling
			self.execute = super(MultiDestTransition, self).execute

	def execute(self, event_data): # pylint: disable=method-hidden
		func = self._func if callable(self._func) else getattr(event_data.model, self._func)
		self._result = func()
		super(MultiDestTransition, self).execute(event_data)

	@property
	def dest(self):
		"""Get the destination"""
		return self._dest[self._result] if self._result is not None else self._dest

	@dest.setter
	def dest(self, value):
		self._dest = value

class StateMachine(Machine):
	"""StateMachine with multiple destination support"""
	transition_cls = MultiDestTransition
