"""
A thread module for PyPPL
"""
try:
	from Queue import PriorityQueue
except ImportError: # pragma: no cover
	from queue import PriorityQueue
from threading import Thread, Lock

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
		except Exception as ex:
			from traceback import format_exc
			self.ex = type(ex)(format_exc())

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
			while any(thread.isAlive() for thread in self.threads):
				for thread in self.threads:
					if thread.ex:
						if callable(cleanup):
							cleanup(ex = thread.ex)
						else:
							raise thread.ex
					thread.join(timeout = interval)
		except KeyboardInterrupt as ex:
			if callable(cleanup):
				cleanup(ex = ex)

class PQueue(PriorityQueue):

	def __init__(self, maxsize = 0, batch_len = None):
		if not batch_len:
			raise ValueError('`batch_len` is required for PQueue.')
		PriorityQueue.__init__(self, maxsize)
		self.batch_len = batch_len
		self.lock      = Lock()

	def put(self, item, block = True, timeout = None, where = 0):
		with self.lock:
			PriorityQueue.put(self, item + where * self.batch_len, block, timeout)
	
	def put_nowait(self, item, where = 0):
		with self.lock:
			PriorityQueue.put_nowait(self, item + where * self.batch_len)

	def get(self, block = True, timeout = None):
		item = PriorityQueue.get(self, block, timeout)
		ret  = divmod(item, self.batch_len)
		return (ret[1], ret[0])

	def get_nowait(self):
		item = PriorityQueue.get(self)
		ret  = divmod(item, self.batch_len)
		return (ret[1], ret[0])


