
"""
jobmgr module for PyPPL
"""
import random
from time import sleep
from contextlib import contextmanager
from threading import Lock
from .utils import config, Queue, PQueue, ThreadPool
from .job import Job
from .logger import logger
from .exceptions import JobFailException, JobSubmissionException, JobBuildingException

class Jobmgr(object):
	"""
	A job manager for PyPPL

	@static variables
		`PBAR_SIZE`:  The length of the progressbar
		`PBAR_MARKS`: The marks for different job status
		`PBAR_LEVEL`: The log levels for different job status
		`SMBLOCK`   : The lock used to relatively safely to tell whether jobs can be submitted.
	"""
	PBAR_SIZE  = int(config._log.pbar or 50)
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

	def __init__(self, jobs, conf):
		"""
		Initialize the job manager
		@params:
			`jobs`: All the jobs
			`conf`: The configurations for the job manager
		"""
		if not jobs:  # no jobs
			return
		self.jobs    = jobs
		self.config  = conf
		self.stop    = False

		queue  = PQueue(batch_len = len(jobs))
		nslots = min(queue.batchLen, int(conf['nthread']))

		for job in self.jobs:
			queue.putToBuild(job.index)

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
			index, batch = queue.get()
			self._workonBuilding(index, batch, queue)
			self._workonSubmitting(index, batch, queue)
			self._workonRunning(index, batch, queue)
			queue.task_done()

	def _workonBuilding(self, index, batch, queue):
		job = self.jobs[index]
		if job.status != Job.STATUS_INITIATED:
			return
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
			queue.putToFirstSubmit(index)
	
	def _workonSubmitting(self, index, batch, queue):
		job = self.jobs[index]
		if not job.status == Job.STATUS_BUILT and not job.status == Job.STATUS_RETRYING:
			return
		with self.canSubmit() as can:
			if can:
				job.status = Job.STATUS_SUBMITTING
				self.progressbar(index)
		if job.status == Job.STATUS_SUBMITTING:
			submitted = job.submit()
			# in case other thread is check canSubmit
			with Jobmgr.SBMLOCK:
				job.status = Job.STATUS_SUBMITTED if submitted else Job.STATUS_SUBMITFAILED

			if job.status == Job.STATUS_SUBMITFAILED:
				self.progressbar(index)
				raise JobSubmissionException()
		elif batch == 1:
			queue.putToFirstRun(index)
		else:
			sleep(.5)
			queue.put(index, batch - 1)

	def _workonRunning(self, index, batch, queue):
		job = self.jobs[index]
		if not job.status == Job.STATUS_SUBMITTED and not job.status == Job.STATUS_RUNNING:
			return

		if batch % 3 == 0: # previously running
			# Just don't query it too frequently
			sleep(.5)
		else:
			self.progressbar(index)

		# check if job finishes, or any logs to output
		job.poll()
		# status then could be:
		# STATUS_RUNNING, STATUS_DONEFAILED, STATUS_DONE
		if job.status == Job.STATUS_RUNNING:
			if batch % 3 != 0:
				self.progressbar(index)
			queue.put(index, batch)

		elif job.status == Job.STATUS_DONEFAILED:
			rrr = job.retry()
			if rrr == 'halt':
				# status:
				# STATUS_ENDFAILED, STATUS_RETRYING
				raise JobFailException()
			if job.status == Job.STATUS_RETRYING:
				job.logger[Jobmgr.PBAR_LEVEL[job.status]](
					"Retrying %s/%s ...", job.ntry, job.config['errntry'])
				# retry as soon as possible
				queue.put(index, 1)
			else: # STATUS_ENDFAILED
				self.progressbar(index)
		else:
			self.progressbar(index)
		
		
	# pylint: disable=too-many-locals,too-many-statements
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
		# cache status
		status = [job.status for job in self.jobs]
		# distribute the jobs to bars
		if joblen <= Jobmgr.PBAR_SIZE:
			div, mod = divmod(Jobmgr.PBAR_SIZE, joblen)
			for j in range(joblen):
				step = div + 1 if j < mod else div
				for _ in range(step):
					barjobs.append([j])
		else:
			jobx = 0
			div, mod = divmod(joblen, Jobmgr.PBAR_SIZE)
			for i in range(Jobmgr.PBAR_SIZE):
				step = div + 1 if i < mod else div
				barjobs.append([jobx + jobstep for jobstep in range(step)])
				jobx += step

		ncompleted = nrunning = 0
		for stat in status:
			ncompleted += int(bool(stat & 0b1000000))
			nrunning   += int(stat in (Job.STATUS_RUNNING, Job.STATUS_SUBMITTED))

		for barjob in barjobs:
			if jobidx in barjob:
				pbar += Jobmgr.PBAR_MARKS[status[jobidx]]
			else:
				bjstatus  = [status[i] for i in barjob]
				if Job.STATUS_BUILTFAILED in bjstatus:
					stat = Job.STATUS_BUILTFAILED
				elif Job.STATUS_SUBMITFAILED in bjstatus:
					stat = Job.STATUS_SUBMITFAILED
				elif Job.STATUS_ENDFAILED in bjstatus:
					stat = Job.STATUS_ENDFAILED
				elif Job.STATUS_DONEFAILED in bjstatus:
					stat = Job.STATUS_DONEFAILED
				elif Job.STATUS_BUILDING in bjstatus:
					stat = Job.STATUS_BUILDING
				elif Job.STATUS_BUILT in bjstatus:
					stat = Job.STATUS_BUILT
				elif Job.STATUS_SUBMITTING in bjstatus:
					stat = Job.STATUS_SUBMITTING
				elif Job.STATUS_SUBMITTED in bjstatus:
					stat = Job.STATUS_SUBMITTED
				elif Job.STATUS_RETRYING in bjstatus:
					stat = Job.STATUS_RETRYING
				elif Job.STATUS_RUNNING in bjstatus:
					stat = Job.STATUS_RUNNING
				elif Job.STATUS_DONE in bjstatus:
					stat = Job.STATUS_DONE
				elif Job.STATUS_DONECACHED in bjstatus:
					stat = Job.STATUS_DONECACHED
				elif Job.STATUS_KILLING in bjstatus:
					stat = Job.STATUS_KILLING
				elif Job.STATUS_KILLED in bjstatus:
					stat = Job.STATUS_KILLED
				else:
					stat = Job.STATUS_INITIATED
				pbar += Jobmgr.PBAR_MARKS[stat]

		pbar += '] Done: {:5.1f}% | Running: {}'.format(
			100.0 * float(ncompleted) / float(joblen),
			str(nrunning).ljust(len(str(joblen)))
		)

		self.jobs[jobidx].logger.pbar[Jobmgr.PBAR_LEVEL[status[jobidx]]](
			pbar, done = ncompleted == joblen)

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
			logger.warning(message, proc = self.config['proc'])

		# kill running jobs
		rjobs = [
			job.index for job in self.jobs
			if job.status in (Job.STATUS_RUNNING, Job.STATUS_SUBMITTED, Job.STATUS_SUBMITTING)
		]
		killq = Queue()
		for rjob in rjobs:
			killq.put(rjob)

		ThreadPool(
			min(len(rjobs), self.config['nthread']),
			initializer = self.killWorker,
			initargs    = killq
		).join()

		failedjobs = [job for job in self.jobs if job.status & 0b1]
		if not failedjobs:
			failedjobs = [random.choice(self.jobs)]
		failedjobs[0].showError(len(failedjobs))

		if isinstance(ex, Exception) and not isinstance(ex, (JobFailException,
			JobBuildingException, JobSubmissionException, KeyboardInterrupt)):
			raise ex
		exit(1)

	def killWorker(self, runq):
		"""
		The worker to kill the jobs.
		@params:
			`runq`: The queue that has running jobs.
		"""
		while not runq.empty():
			i = runq.get()
			job = self.jobs[i]
			job.status = Job.STATUS_KILLING
			self.progressbar(i)
			job.kill()
			job.status = Job.STATUS_KILLED
			self.progressbar(i)
			runq.task_done()

	@contextmanager
	def canSubmit(self):
		"""
		Tell if jobs can be submitted.
		@return:
			`True` if they can else `False`
		"""
		with Jobmgr.SBMLOCK:
			yield sum(
				1 for job in self.jobs
				if job.status in (Job.STATUS_RUNNING, Job.STATUS_SUBMITTED, Job.STATUS_SUBMITTING)
			) < self.config['forks']
