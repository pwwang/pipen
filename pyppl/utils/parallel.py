from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
#from loky import ProcessPoolExecutor

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
		with self.executor:
			for arg in args:
				submits.append(self.executor.submit(_func, arg))

			for submit in as_completed(submits):
				if submit.exception() is not None:
					if self.raiseExc:
						raise submit.exception()
				else:
					results.append(submit.result())

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