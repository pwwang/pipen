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

class TQueue(PriorityQueue):

	def __init__(self, maxsize = 0, init_batch_min = 100, init_batch_max = 100, batch_len = None):
		if not batch_len:
			raise ValueError('`batch_len` is required for TQueue.')
		PriorityQueue.__init__(self, maxsize)
		self.batch_min = init_batch_min
		self.batch_max = init_batch_max
		self.batch_len = batch_len
		self.lock      = Lock()

	def _item(self, item, where = 'max+1'):
		where = where.replace(' ', '')
		shift = 0
		place = where[:3]
		if place not in ['min', 'max']:
			raise ValueError('Invalid where parameter for TQueue.put')
		shift = int(where[3:] or 0)
		placedict = {'min': self.batch_min, 'max': self.batch_max}
		item2put = self.batch_len * (placedict[place] + shift) + item
		self.batch_min = min(placedict[place] + shift, self.batch_min)
		self.batch_max = max(placedict[place] + shift, self.batch_max)
		return item2put

	def put(self, item, block = True, timeout = None, where = 'max+1'):
		with self.lock:
			PriorityQueue.put(self, self._item(item, where), block, timeout)
	
	def put_nowait(self, item, where = 'max+1'):
		with self.lock:
			PriorityQueue.put_nowait(self, self._item(item, where))

	def get(self, block = True, timeout = None):
		item = PriorityQueue.get(self, block, timeout)
		ret  = divmod(item, self.batch_len)
		return (ret[1], ret[0])

	def get_nowait(self):
		item = PriorityQueue.get(self)
		ret  = divmod(item, self.batch_len)
		return (ret[1], ret[0])


