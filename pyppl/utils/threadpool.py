"""
A thread module for PyPPL
"""
from threading import Thread

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

	def join(self, interval = .1, cleanup = None):
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
