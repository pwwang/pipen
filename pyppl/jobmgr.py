
import signal
from multiprocessing import Pool, Process, Manager, Lock, current_process
from multiprocessing.pool import ThreadPool
from threading import Thread
from .utils import QueueEmpty
from .job import Job
from .logger import logger

class Jobmgr(object):

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

	def __init__(self, jobs, config):
		if not jobs:  # no jobs
			return
		manager       = Manager()
		self.buldQ    = manager.Queue()
		self.sbmtQ    = manager.Queue()
		self.runnQ    = manager.Queue()
		self.jobs     = jobs
		self.config   = config
		self.logger   = config.get('logger', logger)
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
			self.logger.info(
				'Ctrl-C detected, quitting pipeline ...'.ljust(Jobmgr.PBAR_SIZE + 50), 
				extra = {'loglevel': 'WARNING', 'pbar': 'next'}
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
		bar     = '['
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
				bar += Jobmgr.PBAR_MARKS[job.status.value]
			else:
				bjstatus  = [status[i] for i in bj]
				ss        = max(s & 0b0111111 for s in bjstatus)
				doneS     = ss | 0b1000000
				bar      += Jobmgr.PBAR_MARKS[doneS if doneS in bjstatus else ss]

		bar += '] Done: {:5.1f}% | Running: {}'.format(
			100.0 * float(ncompleted) / float(joblen), 
			str(nrunning).ljust(len(str(joblen))))
		self.logger.info(bar, extra = {
			'loglevel': Jobmgr.PBAR_LEVEL[job.status.value], 
			'jobidx'  : jobidx, 
			'joblen'  : joblen, 
			'pbar'    : True,
			'proc'    : self.config['proc']
		})

	def cleanup(self):
		#signal.signal(signal.SIGINT, signal.SIG_IGN)
		#self.locPool.join()
		self.locPool.terminate()
		self.remPool.terminate()

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
		exit(1)

	def buildWorker(self):
		signal.signal(signal.SIGINT, signal.SIG_IGN)
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
				except (QueueEmpty, IOError, EOFError):
					pass
				
	def runWorker(self):
		signal.signal(signal.SIGINT, signal.SIG_IGN)
		while not self.allJobsDone():
			try:
				i = self.runnQ.get(timeout = 1)
				if i is None:
					self.runnQ.task_done()
					break
				else:
					self.runJob(i)
					self.runnQ.task_done()

			except (QueueEmpty, IOError, EOFError):
				pass
		for _ in range(self.config['nsub']):
			self.sbmtQ.put(None)

	def allJobsDone(self):
		return not self.jobs or all(
			job.status.value & 0b1000000 
			for job in self.jobs
		)

	def buildJob(self, i):
		job = self.jobs[i]
		job.status.value = Job.STATUS_BUILDING
		self.progressbar(i)
		job.build()
		if job.status.value == Job.STATUS_BUILT:
			self.sbmtQ.put(i)
		self.progressbar(i)

	def submitJob(self, i):
		job = self.jobs[i]
		job.status.value = Job.STATUS_SUBMITTING
		self.progressbar(i)
		job.submit()
		if job.status.value == Job.STATUS_SUBMITTED:
			self.runnQ.put(i)
		self.progressbar(i)

	def runJob(self, i):
		job = self.jobs[i]
		job.status.value = Job.STATUS_RUNNING
		self.progressbar(i)
		job.run()
		retry = job.retry()
		if retry == 'halt':
			self.cleanup()
		elif retry is True:
			self.progressbar(i)
			self.sbmtQ.put(i)

	def killJob(self, i):
		job = self.jobs[i]
		job.status.value = Job.STATUS_KILLING
		self.progressbar(i)
		job.kill()