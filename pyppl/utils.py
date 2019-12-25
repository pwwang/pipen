"""Utility functions for PyPPL"""
import re
from os import path, walk
from copy import deepcopy
from queue import PriorityQueue
from threading import Thread
import cmdy
from transitions import Transition, Machine
from liquid.stream import LiquidStream
from . import _fsutil as fs

def name2filename(name):
	"""@API
	Convert any name to a valid filename
	@params:
		name (str): The name to be converted
	@returns:
		(str): The converted name
	"""
	name = re.sub(r'[^\w_]+', '_', name)
	name = re.sub(r'_+', '_', name)
	return name.strip('_')

def format_secs (seconds):
	"""@API
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

def filesig(filepath, dirsig = True):
	"""@API
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

	getmtime = path.getmtime
	if dirsig and fs.isdir(filepath):
		mtime = getmtime(filepath)
		for root, dirs, files in walk(filepath):
			for directory in dirs:
				mtime2 = getmtime(path.join(root, directory))
				mtime  = max(mtime, mtime2)
			for filename in files:
				mtime2 = getmtime(path.join(root, filename))
				mtime  = max(mtime, mtime2)
	else:
		mtime = getmtime(filepath)
	return [str(filepath), int(mtime)]

def funcsig (func):
	"""@API
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

def always_list (data, trim = True):
	"""@API
	Convert a string or a list with element
	@params:
		`data`: the data to be converted
		`trim`: trim the whitespaces for each item or not. Default: True
	@examples:
		```python
		data = ["a, b, c", "d"]
		ret  = always_list (data)
		# ret == ["a", "b", "c", "d"]
		```
	@returns:
		The split list
	"""
	if isinstance(data, str):
		return LiquidStream.from_string(data).split(',', trim = trim)
	if isinstance(data, list):
		return sum((always_list(dat, trim)
			if isinstance(dat, (str, list)) else [dat]
			for dat in data), [])
	raise ValueError('Expect str/list to convert to list, but got %r.' % type(data).__name__)

def try_deepcopy(obj, _recurvise = True):
	"""@API
	Try do deepcopy an object. If fails, just do a shallow copy.
	@params:
		obj (any): The object
		_recurvise (bool): A flag to avoid deep recursion
	@returns:
		(any): The copied object
	"""
	if _recurvise and isinstance(obj, dict):
		# do a shallow copy first
		# we don't start with an empty dictionary, because obj may be
		# an object from a class extended from dict
		ret = obj.copy()
		for key, value in obj.items():
			ret[key] = try_deepcopy(value, False)
		return ret
	if _recurvise and isinstance(obj, list):
		ret = obj[:]
		for i, value in enumerate(obj):
			ret[i] = try_deepcopy(value, False)
		return ret
	try:
		return deepcopy(obj)
	except TypeError:
		return obj


def chmod_x(filepath):
	"""@API
	Convert file1 to executable or add extract shebang to cmd line
	@params:
		filepath (path): The file path
	@returns:
		(list): with or without the path of the interpreter as the first element
		and the script file as the last element
	"""
	from stat import S_IEXEC
	from os import chmod, stat
	filepath = str(filepath)
	if not fs.isfile(filepath):
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

def brief_list(blist, base = 0):
	"""@API
	Briefly show an integer list, combine the continuous numbers.
	@params:
		blist: The list
	@returns:
		(str): The string to show for the briefed list.
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

class ThreadEx(Thread):
	"""
	A thread able to send exception to main thread
	thread.ex will hold the exception.
	"""

	def __init__(self, group=None, target=None, name=None, args=None, kwargs=None):
		# pylint: disable=too-many-arguments
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

class ThreadPool: # pylint: disable=too-few-public-methods
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
					if thread.is_alive():
						threads_alive += 1
				if threads_alive == 0:
					break
		except KeyboardInterrupt as ex: # pragma: no cover
			if callable(cleanup):
				cleanup(ex = ex)

class PQueue(PriorityQueue):
	"""@API
	A modified PriorityQueue, which allows jobs to be submitted in batch
	"""
	# pylint: disable=arguments-differ
	def __init__(self, maxsize = 0, batch_len = None):
		"""@API
		A Priority Queue for PyPPL jobs
			0                              0 done,             wait for 1
			  1        start 0    1        start 1             start 2
				2      ------>  0   2      ------>      2      --------->
				  3                   3               1   3                    3
					4                   4                   4                2   4
																		   1
		@params:
			maxsize  : The maxsize of the queue. Default: None
			batch_len: What's the length of a batch
		"""
		if not batch_len:
			raise ValueError('`batch_len` is required for PQueue.')
		PriorityQueue.__init__(self, maxsize)
		self.batch_len = batch_len

	def put_next(self, item, batch):
		"""@API
		Put item to next batch
		@params:
			item (any): item to put
			batch (int): current batch
		"""
		self.put(item, batch + 2)

	def put(self, item, batch = None):
		"""@API
		Put item to any batch
		@params:
			item (any): item to put
			batch (int): target batch
		"""
		batch = batch or item
		PriorityQueue.put(self, item + batch * self.batch_len)

	def get(self):
		"""@API
		Get an item from the queue
		@returns:
			(int, int): The index of the item and the batch of it
		"""
		item = PriorityQueue.get(self)
		batch, index  = divmod(item, self.batch_len)
		return index, batch

class _MultiDestTransition(Transition):
	"""Transition with multiple destination"""
	# pylint: disable=too-many-arguments
	def __init__(self, source, dest, conditions=None, unless=None,
		before=None, after=None, prepare=None, **kwargs):
		self._result = self._dest = None
		super().__init__(
			source, dest, conditions, unless, before, after, prepare)
		if isinstance(dest, dict):
			self._func = kwargs.pop('depends_on', None)
			if not self._func:
				raise AttributeError("A multi-destination transition requires a 'depends_on'")
		else:
			# use base version in case transition does not need special handling
			self.execute = super().execute

	def execute(self, event_data): # pylint: disable=method-hidden
		"""Excute the function"""
		func = self._func if callable(self._func) else getattr(event_data.model, self._func)
		self._result = func()
		super().execute(event_data)

	@property
	def dest(self):
		"""Get the destination"""
		return self._dest[self._result] if self._result is not None else self._dest

	@dest.setter
	def dest(self, value):
		self._dest = value

class StateMachine(Machine): # pylint: disable=too-few-public-methods
	"""StateMachine with multiple destination support"""
	transition_cls = _MultiDestTransition
