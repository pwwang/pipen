
"""
jobmgr module for PyPPL
"""
import random
from time import sleep
from .utils.taskmgr import PQueue, ThreadPool, Lock
from .job import Job
from .logger import logger
from .exception import JobFailException, JobSubmissionException, JobBuildingException

class Jobmgr(object):
	"""
	A job manager for PyPPL

	@static variables
		`PBAR_SIZE`:  The length of the progressbar
		`PBAR_MARKS`: The marks for different job status
		`PBAR_LEVEL`: The log levels for different job status
		`SMBLOCK`   : The lock used to relatively safely to tell whether jobs can be submitted.
	"""
	PBAR_SIZE  = 50
	PBAR_MARKS = {
		Job.STATUS_INITIATED   : ' ',
		Job.STATUS_BUILDING    : '~',
		Job.STATUS_BUILT       : '-',
		Job.STATUS_BUILTFAILED : '!',
		Job.STATUS_SUBMITTING  : '-',
		Job.STATUS_SUBMITTED   : '>',
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
	# submission lock
	SBMLOCK = Lock()

	def __init__(self, jobs, config):
		"""
		Initialize the job manager
		@params:
			`jobs`: All the jobs
			`config`: The configurations for the job manager
		"""
		if not jobs:  # no jobs
			return
		self.jobs    = jobs
		self.config  = config
		self.logger  = config.get('logger', logger)
		self.stop    = False

		queue  = PQueue(batch_len = len(jobs))
		nslots = min(queue.batch_len, config['nthread'])

		for job in self.jobs:
			# say nslots = 40
			# where = 0 if job.index = [0, 19]
			# where = 1 if job.index = [20, 39]
			# ...
			queue.put(job.index, where = int(2*job.index/nslots))
		
		ThreadPool(
			nslots,
			initializer = self.worker,
			initargs = queue
		).join(cleanup = self.cleanup)

	def worker(self, queue):
		"""
		Worker for the queue
		@params:
			`queue`: The priority queue
		"""
		while not queue.empty() and not self.stop:
			self.workon(queue.get(), queue)
			queue.task_done()

	def workon(self, index, queue):
		"""
		Work on a queue item
		@params:
			`index`: The job index and batch number, got from the queue
			`queue`: The priority queue
		"""
		index, batch = index
		job = self.jobs[index]
		if job.status == Job.STATUS_INITIATED:
			self.progressbar(index)
			job.status = Job.STATUS_BUILDING
			job.build()
			# status then could be: 
			# STATUS_DONECACHED, STATUS_BUILT, STATUS_BUILTFAILED
			if job.status == Job.STATUS_DONECACHED:
				self.progressbar(index)
			elif job.status == Job.STATUS_BUILTFAILED:
				self.progressbar(index)
				raise JobBuildingException()
			else: 
				queue.put(index, where = batch+3)
		elif job.status == Job.STATUS_BUILT or job.status == Job.STATUS_RETRYING:
			# when slots are available
			if self.canSubmit():
				with Jobmgr.SBMLOCK:
					job.status = Job.STATUS_SUBMITTING
				self.progressbar(index)
				s = job.submit()
				with Jobmgr.SBMLOCK:
					job.status = Job.STATUS_SUBMITTED if s else Job.STATUS_SUBMITFAILED
				if job.status == Job.STATUS_SUBMITFAILED:
					self.progressbar(index)
					raise JobSubmissionException()
			queue.put(index, where = batch+3)
		elif job.status == Job.STATUS_SUBMITTED or job.status == Job.STATUS_RUNNING:
			oldstatus = job.status
			if oldstatus == Job.STATUS_RUNNING:
				# Just don't run it too frequently
				sleep(.5)
			else:
				self.progressbar(index)

			# check if job finishes, or any logs to output
			job.poll()
			# status then could be:
			# STATUS_RUNNING, STATUS_DONEFAILED, STATUS_DONE
			if job.status == Job.STATUS_RUNNING:
				if oldstatus != job.status:
					self.progressbar(index)
				queue.put(index, where = batch+3)

			elif job.status == Job.STATUS_DONEFAILED:
				if job.retry() == 'halt':
					# status:
					# STATUS_ENDFAILED, STATUS_RETRYING
					raise JobFailException()
				if job.status == Job.STATUS_RETRYING:
					self.logger.warning("Retrying %s/%s ...", job.ntry, job.config['errntry'], extra = {
						'loglevel': Jobmgr.PBAR_LEVEL[job.status], 
						'jobidx'  : index, 
						'joblen'  : queue.batch_len, 
						'pbar'    : False,
						'proc'    : self.config['proc']
					})
					# retry as soon as possible
					queue.put(index, where = batch+3)
				else: # STATUS_ENDFAILED
					self.progressbar(index)
			else:
				self.progressbar(index)


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
		nrunning   = sum(1 for s in status if s == Job.STATUS_RUNNING or s == Job.STATUS_SUBMITTED)

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
			str(nrunning).ljust(len(str(joblen)))
		)
		
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
			message = 'Job building failed, quitting pipeline ...'
		elif isinstance(ex, JobSubmissionException):
			message = 'Job submission failed, quitting pipeline ...'
		elif isinstance(ex, JobFailException):
			message = 'Error encountered (errhow = halt), quitting pipeline ...'
		elif isinstance(ex, KeyboardInterrupt):
			message = 'Ctrl-C detected, quitting pipeline ...'
		else:
			message = None
		if message:
			self.logger.warning(message, extra = {'pbar': 'next', 'proc': self.config['proc']})
		
		# kill running jobs
		rjobs = [
			job.index for job in self.jobs 
			if job.status in (Job.STATUS_RUNNING, Job.STATUS_SUBMITTED, Job.STATUS_SUBMITTING)
		]
		killQ = PQueue(batch_len = len(self.jobs))
		for rjob in rjobs:
			killQ.put(rjob)

		ThreadPool(
			min(len(rjobs), self.config['nthread']), 
			initializer = self.killWorker,
			initargs    = killQ
		).join()
			
		failedjobs = [job for job in self.jobs if job.status & 0b1]
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
			i = rq.get()[0]
			job = self.jobs[i]
			job.status = Job.STATUS_KILLING
			self.progressbar(i)
			job.kill()
			self.progressbar(i)
			rq.task_done()

	def canSubmit(self):
		"""
		Tell if jobs can be submitted.
		@return:
			`True` if they can else `False`
		"""
		with Jobmgr.SBMLOCK:
			return sum(
				1 for job in self.jobs
				if job.status in (Job.STATUS_RUNNING, Job.STATUS_SUBMITTED, Job.STATUS_SUBMITTING)
			) < self.config['forks']

