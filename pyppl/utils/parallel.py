from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
#from loky import ProcessPoolExecutor
from traceback import format_exc

class Parallel(object):
	"""
	A parallel runner
	"""

	def __init__(self, nthread = 1, backend = 'process', raiseExc = True):
		"""
		Constructor
		@params:
			`nthread` : Number of jobs to run simultaneously. Default: `1`
			`backend` : The backend, either `process` (default) or `thread`
			`raiseExc`: Whether raise exception or not. Default: `True`
		"""
		PoolExecutor   = ProcessPoolExecutor if backend.lower() in 'multiprocessing' else ThreadPoolExecutor
		self.executor  = PoolExecutor(max_workers = nthread)
		self.raiseExc  = raiseExc

	def run(self, func, args):
		"""
		Run parallel jobs
		@params:
			`func`    : The function to run
			`args`    : The arguments for the function, should be a `list` with `tuple`s
			`nthread` : Number of jobs to run simultaneously. Default: `1`
			`backend` : The backend, either `process` (default) or `thread`
			`raiseExc`: Whether raise exception or not. Default: `True`
		@returns:
			The merged results from each job.
		"""
		_func = lambda arg: func(*arg)

		submits   = []
		results   = []
		exception = None
		for arg in args:
			submits.append(self.executor.submit(_func, arg))
		
		for submit in submits:
			try:
				results.append(submit.result())
			except Exception as ex: # pragma: no cover
				#results.append(None)
				exception = type(ex)(format_exc())

		self.executor.shutdown(wait = True)
		
		if self.raiseExc and exception:
			raise exception

		return results

# shortcuts
def run(func, args, nthread = 1, backend = 'process', raiseExc = True):
	"""
	A shortcut of `Parallel.run`
	@params:
		`func`    : The function to run
		`args`    : The arguments for the function, should be a `list` with `tuple`s
		`nthread` : Number of jobs to run simultaneously. Default: `1`
		`backend` : The backend, either `process` (default) or `thread`
		`raiseExc`: Whether raise exception or not. Default: `True`
	@returns:
		The merged results from each job.
	"""
	return Parallel(nthread, backend, raiseExc).run(func, args)