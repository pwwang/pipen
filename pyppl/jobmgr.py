
"""
jobmgr module for PyPPL
"""
import random
from threading import Lock
from .utils import Queue, QueueEmpty, threadpool
from .job import Job
from .logger import logger
from .exception import JobFailException, JobSubmissionException, JobBuildingException

class Jobmgr(object):
	"""
	A job manager for PyPPL
	"""
	PBAR_SIZE  = 50
	PBAR_MARKS = {
		Job.STATUS_INITIATED   : ' ',
		Job.STATUS_BUILDING    : '~',
		Job.STATUS_BUILT       : '-',
		Job.STATUS_BUILTFAILED : '!',
		Job.STATUS_SUBMITTING  : '-',
		Job.STATUS_SUBMITTED   : '-',
		Job.STATUS_SUBMITFAILED: '*',
		Job.STATUS_RUNNING     : '>',
		Job.STATUS_RETRYING    : '-',
		Job.STATUS_DONE        : '=',
		Job.STATUS_DONECACHED  : 'z',
		Job.STATUS_DONEFAILED  : 'x',
		Job.STATUS_ENDFAILED   : 'X',
		Job.STATUS_KILLING     : '<',
		Job.STATUS_KILLED      : '-',
	}
	PBAR_LEVEL = {
		Job.STATUS_INITIATED   : 'BLDING',
		Job.STATUS_BUILDING    : 'BLDING',
		Job.STATUS_BUILT       : 'BLDING',
		Job.STATUS_BUILTFAILED : 'BLDING',
		Job.STATUS_SUBMITTING  : 'SUBMIT',
		Job.STATUS_SUBMITTED   : 'SUBMIT',
		Job.STATUS_SUBMITFAILED: 'SUBMIT',
		Job.STATUS_RUNNING     : 'RUNNING',
		Job.STATUS_RETRYING    : 'RETRY',
		Job.STATUS_DONE        : 'JOBDONE',
		Job.STATUS_DONECACHED  : 'JOBDONE',
		Job.STATUS_DONEFAILED  : 'JOBDONE',
		Job.STATUS_ENDFAILED   : 'JOBDONE',
		Job.STATUS_KILLING     : 'KILLING',
		Job.STATUS_KILLED      : 'KILLING',
	}

	LOCK    = Lock()

	def __init__(self, jobs, config):
		if not jobs:  # no jobs
			return
		self.buldQ  = Queue()
		self.sbmtQ  = Queue()
		self.runnQ  = Queue()
		self.jobs   = jobs
		self.config = config
		self.logger = config.get('logger', logger)
		self.stop   = False

		for i in range(len(jobs)):
			self.buldQ.put(i)
		for i in range(len(jobs)):
			self.buldQ.put(None)

		self.pool = threadpool.ThreadPool(
			config['nsub'] + config['forks'],  
			initializer = self.worker,
			initargs = [(i, ) for i in range(config['nsub'] + config['forks'])]
		)
		self.pool.join(cleanup = self.cleanup)

	def worker(self, index):
		"""
		Worker for threads, use first `nsub` workers to build and submit jobs,
		and the rest of them to run (wait for) the jobs.
		"""
		if index < self.config['nsub']:
			self.buildWorker()
		else:
			self.runWorker()

	def progressbar(self, jobidx):
		"""
		Generate progressbar.
		@params:
			`jobidx`: The job index.
			`loglevel`: The log level in PyPPL log system
		@returns:
			The string representing the progressbar
		"""
		pbar    = '['
		barjobs = []
		joblen  = len(self.jobs)
		status = [job.status for job in self.jobs]
		# distribute the jobs to bars
		if joblen <= Jobmgr.PBAR_SIZE:
			n, m = divmod(Jobmgr.PBAR_SIZE, joblen)
			for j in range(joblen):
				step = n + 1 if j < m else n
				for _ in range(step):
					barjobs.append([j])
		else:
			jobx = 0
			n, m = divmod(joblen, Jobmgr.PBAR_SIZE)
			for i in range(Jobmgr.PBAR_SIZE):
				step = n + 1 if i < m else n
				barjobs.append([jobx + s for s in range(step)])
				jobx += step

		ncompleted = sum(1 for s in status if s & 0b1000000)
		nrunning   = sum(1 for s in status if s == Job.STATUS_RUNNING)

		job = self.jobs[jobidx]
		for bj in barjobs:
			if jobidx in bj:
				pbar += Jobmgr.PBAR_MARKS[job.status]
			else:
				bjstatus  = [status[i] for i in bj]
				if Job.STATUS_BUILTFAILED in bjstatus:
					s = Job.STATUS_BUILTFAILED
				elif Job.STATUS_SUBMITFAILED in bjstatus:
					s = Job.STATUS_SUBMITFAILED
				elif Job.STATUS_ENDFAILED in bjstatus:
					s = Job.STATUS_ENDFAILED
				elif Job.STATUS_DONEFAILED in bjstatus:
					s = Job.STATUS_DONEFAILED
				elif Job.STATUS_BUILDING in bjstatus:
					s = Job.STATUS_BUILDING
				elif Job.STATUS_BUILT in bjstatus:
					s = Job.STATUS_BUILT
				elif Job.STATUS_SUBMITTING in bjstatus:
					s = Job.STATUS_SUBMITTING
				elif Job.STATUS_SUBMITTED in bjstatus:
					s = Job.STATUS_SUBMITTED
				elif Job.STATUS_RETRYING in bjstatus:
					s = Job.STATUS_RETRYING
				elif Job.STATUS_RUNNING in bjstatus:
					s = Job.STATUS_RUNNING
				elif Job.STATUS_DONE in bjstatus:
					s = Job.STATUS_DONE
				elif Job.STATUS_DONECACHED in bjstatus:
					s = Job.STATUS_DONECACHED
				elif Job.STATUS_KILLING in bjstatus:
					s = Job.STATUS_KILLING
				elif Job.STATUS_KILLED in bjstatus:
					s = Job.STATUS_KILLED
				else:
					s = Job.STATUS_INITIATED
				pbar += Jobmgr.PBAR_MARKS[s]

		pbar += '] Done: {:5.1f}% | Running: {}'.format(
			100.0 * float(ncompleted) / float(joblen), 
			str(nrunning).ljust(len(str(joblen))))
		self.logger.info(pbar, extra = {
			'loglevel': Jobmgr.PBAR_LEVEL[job.status], 
			'jobidx'  : jobidx, 
			'joblen'  : joblen, 
			'pbar'    : True,
			'proc'    : self.config['proc']
		})

	def cleanup(self, ex = None):
		"""
		Cleanup the pipeline when
		- Ctrl-c hit
		- error encountered and `proc.errhow` = 'terminate'
		@params:
			`ex`: The exception raised by workers
		"""
		self.stop = True
		if isinstance(ex, JobBuildingException):
			self.logger.warning(
				'Job building failed, quitting pipeline ...',
				extra = {'pbar': 'next', 'proc': self.config['proc']}
			)
		elif isinstance(ex, JobSubmissionException):
			self.logger.warning(
				'Job submission failed, quitting pipeline ...',
				extra = {'pbar': 'next', 'proc': self.config['proc']}
			)
		elif isinstance(ex, JobFailException):
			self.logger.warning(
				'Error encountered (errhow = halt), quitting pipeline ...',
				extra = {'pbar': 'next', 'proc': self.config['proc']}
			)
		elif isinstance(ex, KeyboardInterrupt):
			self.logger.warning(
				'Ctrl-C detected, quitting pipeline ...'.ljust(Jobmgr.PBAR_SIZE + 50), 
				extra = {'pbar': 'next', 'proc': self.config['proc']}
			)

		runningQ = Queue()
		for job in self.jobs:
			if job.status in (Job.STATUS_RUNNING, Job.STATUS_SUBMITTED, Job.STATUS_SUBMITTING):
				runningQ.put(job.index)

		killPool = threadpool.ThreadPool(self.config['nsub'], initializer = self.killWorker, initargs = runningQ)
		killPool.join()
			
		failedjobs = [job for job in self.jobs if job.status & 0b1000000]
		if not failedjobs:
			failedjobs = [random.choice(self.jobs)]
		failedjobs[0].showError(len(failedjobs))

		if ex and not isinstance(ex, (JobFailException, JobBuildingException, JobSubmissionException, KeyboardInterrupt)):
			raise ex
		exit(1)

	def killWorker(self, rq):
		"""
		The worker to kill the jobs.
		@params:
			`rq`: The queue that has running jobs.
		"""
		while not rq.empty():
			i = rq.get()
			self.killJob(i)
			rq.task_done()

	def buildWorker(self):
		"""
		The build and submit worker
		"""
		maybeBreak = [False, False]
		while not all(maybeBreak) and not self.stop:
			if not maybeBreak[0]:
				try:
					#with Jobmgr.LOCK:
					if self.canSubmit():
						i = self.sbmtQ.get_nowait()
						if i is None:
							maybeBreak[0] = True
						else:
							self.submitJob(i)
				except QueueEmpty:
					pass
				except KeyboardInterrupt:
					break

			if not maybeBreak[1]:
				try:
					i = self.buldQ.get_nowait()
					if i is None:
						maybeBreak[1] = True
					else:
						self.buildJob(i)
				except QueueEmpty:
					pass
				except KeyboardInterrupt:
					break

	def runWorker(self):
		"""
		The job running worker
		"""
		while not self.allJobsDone() and not self.stop:
			try:
				i = self.runnQ.get(timeout = 1)
				if i is None:
					self.runnQ.task_done()
					break
				else:
					self.runJob(i)
					self.runnQ.task_done()

			except QueueEmpty:
				pass
			except KeyboardInterrupt:
				break
		self.sbmtQ.put(None)
		self.runnQ.put(None)

	def canSubmit(self):
		"""
		Tell if jobs can be submitted.
		@return:
			`True` if they can else `False`
		"""
		return sum(
			job.status in (Job.STATUS_RUNNING, Job.STATUS_SUBMITTED)
			for job in self.jobs
		) < self.config['forks']
		
	def allJobsDone(self):
		"""
		Tell if all jobs are done.
		@return:
			`True` if they are else `False`
		"""
		return all(job.status & 0b1000000 for job in self.jobs)

	def buildJob(self, i):
		"""
		Build job
		@params:
			`i`: The job index
		"""
		job = self.jobs[i]
		job.status = Job.STATUS_BUILDING
		self.progressbar(i)
		job.build()
		if job.status == Job.STATUS_BUILT:
			self.sbmtQ.put(i)
		elif job.status == Job.STATUS_BUILTFAILED:
			raise JobBuildingException()
		self.progressbar(i)

	def submitJob(self, i):
		"""
		Submit job
		@params:
			`i`: The job index
		"""
		job = self.jobs[i]
		job.status = Job.STATUS_SUBMITTING
		self.progressbar(i)
		job.submit()
		if job.status == Job.STATUS_SUBMITTED:
			self.runnQ.put(i)
		elif job.status == Job.STATUS_SUBMITFAILED:
			raise JobSubmissionException()
		self.progressbar(i)

	def runJob(self, i):
		"""
		Wait for the job to run
		@params:
			`i`: The job index
		"""
		job = self.jobs[i]
		job.status = Job.STATUS_RUNNING
		self.progressbar(i)
		job.run()
		self.progressbar(i)
		retry = job.retry()
		if retry == 'halt':
			raise JobFailException()
		elif retry is True:
			self.logger.warning("Retrying %s/%s ...", job.ntry, job.config['errntry'], extra = {
				'loglevel': Jobmgr.PBAR_LEVEL[job.status], 
				'jobidx'  : job.index, 
				'joblen'  : len(self.jobs), 
				'pbar'    : False,
				'proc'    : self.config['proc']
			})
			self.sbmtQ.put(i)

	# process killed, so coverage not included
	def killJob(self, i): # pragma: no cover
		"""
		Kill job
		@params:
			`i`: The job index
		"""
		job = self.jobs[i]
		job.status = Job.STATUS_KILLING
		self.progressbar(i)
		job.kill()
