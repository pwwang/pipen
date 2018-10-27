
"""
jobmgr module for PyPPL
"""
import signal
import os
from multiprocessing import Pool, Manager, Lock
from multiprocessing.pool import ThreadPool
from multiprocessing.managers import SyncManager
from .utils import QueueEmpty, ps
from .job import Job
from .logger import logger

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
		Job.STATUS_SUBMITTING  : '>',
		Job.STATUS_SUBMITTED   : '>',
		Job.STATUS_SUBMITFAILED: '*',
		Job.STATUS_RUNNING     : '>',
		Job.STATUS_RETRYING    : '>',
		Job.STATUS_DONE        : '=',
		Job.STATUS_DONECACHED  : '=',
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

	MANAGER = Manager()
	PIDS    = None
	LOCK    = Lock()
	PID     = os.getpid()

	def __init__(self, jobs, config):
		if not jobs:  # no jobs
			return
		self.buldQ    = Jobmgr.MANAGER.Queue()
		self.sbmtQ    = Jobmgr.MANAGER.Queue()
		self.runnQ    = Jobmgr.MANAGER.Queue()
		self.jobs     = jobs
		self.config   = config
		self.logger   = config.get('logger', logger)
		if not Jobmgr.PIDS:
			man = SyncManager()
			man.start(signal.signal, (signal.SIGINT, signal.SIG_IGN))
			Jobmgr.PIDS = man.list()

		for i in range(len(jobs)):
			self.buldQ.put(i)
		for i in range(len(jobs)):
			self.buldQ.put(None)

		self.locPool = Pool(config['nsub'], initializer = self.buildWorker)
		self.remPool = Pool(config['forks'], initializer = self.runWorker)
		self.locPool.close()
		self.remPool.close()
		try:
			self.locPool.join()
			self.remPool.join()
		except KeyboardInterrupt: # pragma: no cover
			self.logger.warning(
				'Ctrl-C detected, quitting pipeline ...'.ljust(Jobmgr.PBAR_SIZE + 50), 
				extra = {'pbar': 'next'}
			)
			self.cleanup()

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
		status = [job.status.value for job in self.jobs]
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
				pbar += Jobmgr.PBAR_MARKS[job.status.value]
			else:
				bjstatus  = [status[i] for i in bj]
				ss        = max(s & 0b0111111 for s in bjstatus)
				doneS     = ss | 0b1000000
				pbar     += Jobmgr.PBAR_MARKS[doneS if doneS in bjstatus else ss]

		pbar += '] Done: {:5.1f}% | Running: {}'.format(
			100.0 * float(ncompleted) / float(joblen), 
			str(nrunning).ljust(len(str(joblen))))
		self.logger.info(pbar, extra = {
			'loglevel': Jobmgr.PBAR_LEVEL[job.status.value], 
			'jobidx'  : jobidx, 
			'joblen'  : joblen, 
			'pbar'    : True,
			'proc'    : self.config['proc']
		})

	def cleanup(self, pid = 0):
		"""
		Cleanup the pipeline when
		- Ctrl-c hit
		- error encountered and `proc.errhow` = 'terminate'
		@params:
			`pid`: The pid of the process where this is running 
				- Don't try to kill me.
		"""
		#signal.signal(signal.SIGINT, signal.SIG_IGN)
		#self.locPool.join()
		self.logger.debug('Clearning up queues ...'.ljust(Jobmgr.PBAR_SIZE + 50))
		if hasattr(self, 'locPool'):
			self.locPool.terminate()
		# if I am in subprocess:
		if hasattr(self, 'remPool'): # pragma: no cover
			self.remPool.terminate()

		pids = [p for p in Jobmgr.PIDS if p != pid]
		Jobmgr.PIDS = None
		ps.kill(pids)

		runjobs  = [
			job.index for job in self.jobs 
			if job.status.value in (Job.STATUS_RUNNING, Job.STATUS_SUBMITTED)]

		killPool = ThreadPool(self.config['nsub'])
		killPool.map(self.killJob, runjobs)
		killPool.close()
		killPool.join()

		failedjobs = [job for job in self.jobs if job.status.value & 0b1000000]
		if not failedjobs:
			failedjobs = [self.jobs[0]]
		failedjobs[0].showError(len(failedjobs))
		
		# in case main process not quit
		ps.killtree(Jobmgr.PID, True)
		exit(1)

	def buildWorker(self):
		"""
		The build and submit worker
		"""
		signal.signal(signal.SIGINT, signal.SIG_IGN)
		Jobmgr.PIDS.append(os.getpid())
		maybeBreak = [False, False]
		while not all(maybeBreak):
			if not maybeBreak[0]:
				try:
					i = self.sbmtQ.get_nowait()
					if i is None:
						maybeBreak[0] = True
					else:
						self.submitJob(i)
				except (QueueEmpty, IOError, EOFError):
					pass

			if not maybeBreak[1]:
				try:
					i = self.buldQ.get_nowait()
					if i is None:
						maybeBreak[1] = True
						#self.sbmtQ.put(None)
					else:
						self.buildJob(i)
				except (QueueEmpty, IOError, EOFError): # pragma: no cover
					pass

	def runWorker(self):
		"""
		The job running worker
		"""
		signal.signal(signal.SIGINT, signal.SIG_IGN)
		Jobmgr.PIDS.append(os.getpid())
		while not self.allJobsDone():
			try:
				i = self.runnQ.get(timeout = 1)
				if i is None:
					self.runnQ.task_done()
					break
				else:
					self.runJob(i)
					self.runnQ.task_done()

			except (QueueEmpty, IOError, EOFError): # pragma: no cover
				pass
		for _ in range(self.config['nsub']):
			self.sbmtQ.put(None)
			self.runnQ.put(None)

	def allJobsDone(self):
		"""
		Tell if all jobs are done.
		@return:
			`True` if they are else `False`
		"""
		return not self.jobs or all(
			job.status.value & 0b1000000 
			for job in self.jobs
		)

	def buildJob(self, i):
		"""
		Build job
		@params:
			`i`: The job index
		"""
		job = self.jobs[i]
		job.status.value = Job.STATUS_BUILDING
		self.progressbar(i)
		job.build()
		if job.status.value == Job.STATUS_BUILT:
			self.sbmtQ.put(i)
		self.progressbar(i)

	def submitJob(self, i):
		"""
		Submit job
		@params:
			`i`: The job index
		"""
		job = self.jobs[i]
		job.status.value = Job.STATUS_SUBMITTING
		self.progressbar(i)
		job.submit()
		if job.status.value == Job.STATUS_SUBMITTED:
			self.runnQ.put(i)
		self.progressbar(i)

	def runJob(self, i):
		"""
		Wait for the job to run
		@params:
			`i`: The job index
		"""
		job = self.jobs[i]
		job.status.value = Job.STATUS_RUNNING
		self.progressbar(i)
		job.run()
		self.progressbar(i)
		retry = job.retry()
		if retry == 'halt':
			with Jobmgr.LOCK:
				self.logger.warning(
					'Error encountered (errhow = halt), quitting pipeline ...'.ljust(Jobmgr.PBAR_SIZE + 50), 
					extra = {'pbar': 'next'}
				)
				self.cleanup(os.getpid())
		elif retry is True:
			self.progressbar(i)
			self.sbmtQ.put(i)

	# process killed, so coverage not included
	def killJob(self, i): # pragma: no cover
		"""
		Kill job
		@params:
			`i`: The job index
		"""
		job = self.jobs[i]
		job.status.value = Job.STATUS_KILLING
		self.progressbar(i)
		job.kill()
