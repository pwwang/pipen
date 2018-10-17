
from multiprocessing import Pool, Manger, Lock
from six.moves.queue import Empty as QueueEmpty
from .job import Job

class Jobmgr(object):

	def __init__(self, jobs, config):

		manager     = Manger()
		self.buldQ  = manager.Queue()
		self.sbmtQ  = manager.Queue()
		self.runnQ  = manager.Queue()
		self.killQ  = manager.Queue()
		self.status = manager.list([Job.STATUS_INITIATED for job in jobs])
		self.jobs   = jobs
		self.config = config
		for i in range(len(jobs)):
			self.buldQ.put(i)
		for i in range(len(jobs)):
			self.buldQ.put(None)

		pool = Pool(config['forks'], initializer = self.worker)
		pool.close()
		pool.join()
	
	@staticmethod
	def emptyQueue(q, length):
		while True:
			try:
				q.get_nowait()
			except QueueEmpty:
				for i in range(length):
					q.put(None)

	def _buildJobs(self):
		pass

	def _submitJobs(self):
		pass

	def _buildJob(self, i):
		self.jobs[i].build()

	def _killJob(self, i):
		self.jobs[i].kill()

	def halt(self):
		Jobmgr.emptyQueue(self.buldQ, self.config['forks'])
		Jobmgr.emptyQueue(self.sbmtQ, self.config['forks'])
		Jobmgr.emptyQueue(self.runnQ, self.config['forks'])
		runningJobs = [job.index for job in self.jobs if job.status.value in [Job.STATUS_RUNNING, Job.STATUS_SUBMITTED]]
		for i in runningJobs:
			self.killQ.put(i)
		for i in range(len(runningJobs)):
			self.killQ.put(None)

	def allJobsDone(self):
		return not self.jobs or bool(reduce(lambda x, y: x & y, self.status) & Job.STATUS_DONE)

	def worker(self):
		while True:
			self._runJobs()
			self._submitJobs()
			try:
				i = self.buldQ.get_nowait()
				if i is None:
					self.buldQ.task_done()
					break
				self._buildJobs(i)
			except QueueEmpty:
				pass

			if allJobsDone():
				Jobmgr.emptyQueue(self.runnQ, len(self.jobs))



			

				
