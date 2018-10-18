
import signal
from multiprocessing import Pool, Manager, Lock, Value, current_process
from .utils import QueueEmpty
from .job import Job
from .logger import logger

class Jobmgr(object):

	PBAR_SIZE  = 50
	PBAR_MARKS = {
		Job.STATUS_INITIATED   : ' ',
		Job.STATUS_BUILDING    : '-',
		Job.STATUS_BUILT       : '~',
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
		Job.STATUS_KILLING     : '/',
		Job.STATUS_KILLED      : '+',
	}
	PBAR_LEVEL = {
		Job.STATUS_INITIATED   : 'BUILD',
		Job.STATUS_BUILDING    : 'BUILD',
		Job.STATUS_BUILT       : 'BUILD',
		Job.STATUS_BUILTFAILED : 'BUILD',
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

		manager       = Manager()
		self.buldQ    = manager.Queue()
		self.killQ    = manager.Queue()
		self.sbmtQ    = manager.Queue()
		self.runnQ    = manager.Queue()
		self.jobs     = jobs
		self.config   = config
		self.cleaning = Value('i', 0)
		for i in range(len(jobs)):
			self.buldQ.put(i)
		for i in range(len(jobs)):
			self.buldQ.put(None)

		self.locPool = Pool(config['nthread'], initializer = self.buildWorker)
		self.remPool = Pool(config['forks'], initializer = self.runWorker)
		self.remPool.close()
		self.locPool.close()
		try:
			self.remPool.join()
			self.locPool.join()
		except KeyboardInterrupt:
			logger.info('Ctrl-C detected, quitting pipeline ...', extra = {'loglevel': 'WARNING'})
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

		bar += '] Done: {:5.1f}% | Running: {}'.format(100.0 * float(ncompleted) / float(joblen), str(nrunning).ljust(len(str(joblen))))
		logger.info(bar, extra = {
			'loglevel': Jobmgr.PBAR_LEVEL[job.status.value], 
			'jobidx'  : jobidx, 
			'joblen'  : joblen, 
			'pbar'    : True
		})

	def cleanup(self):
		signal.signal(signal.SIGINT, signal.SIG_IGN)
		with self.cleaning.get_lock():
			print 'Terminating local pool ...'
			self.locPool.terminate()
			print 'Terminating remote pool ...'
			self.remPool.terminate()
			if self.cleaning.value:
				return
			self.cleaning.value = 1

			runningJobs = [
				job.index for job in self.jobs 
				if job.status.value in (Job.STATUS_RUNNING, Job.STATUS_SUBMITTED)
			]

			print 'Killing running jobs ...', len(runningJobs)
			from multiprocessing.pool import ThreadPool
			pool = ThreadPool(self.config['nthread'])
			pool.map(self.killJob, runningJobs)
			pool.close()
			pool.join()

	def buildWorker(self):
		signal.signal(signal.SIGINT, signal.SIG_IGN)
		maybeBreak = [False, False]
		while not all(maybeBreak):
			if not maybeBreak[0]:
				try:
					i = self.sbmtQ.get_nowait()
					if i is None:
						maybeBreak[0] = True
						#self.sbmtQ.task_done()
					else:
						self.submitJob(i)
				except QueueEmpty:
					pass

			if not maybeBreak[1]:
				try:
					i = self.buldQ.get_nowait()
					if i is None:
						maybeBreak[1] = True
						self.sbmtQ.put(None)
						#self.buldQ.task_done()
					else:
						self.buildJob(i)
				except QueueEmpty:
					pass
				
	def runWorker(self):
		signal.signal(signal.SIGINT, signal.SIG_IGN)
		while not self.allJobsDone():
			try:
				i = self.runnQ.get(timeout = 1)
				self.runJob(i)
				self.runnQ.task_done()
			
			except QueueEmpty:
				pass

	def allJobsDone(self):
		return not self.jobs or all(
			job.status.value & 0b1000000 
			for job in self.jobs
		)

	def buildJob(self, i):
		job = self.jobs[i]
		job.build()
		if job.status.value == Job.STATUS_BUILT:
			self.sbmtQ.put(i)
		self.progressbar(i)

	def submitJob(self, i):
		job = self.jobs[i]
		job.submit()
		if job.status.value == Job.STATUS_SUBMITTED:
			self.runnQ.put(i)
		self.progressbar(i)

	def runJob(self, i):
		job = self.jobs[i]
		job.run()
		self.progressbar(i)

	def killJob(self, i):
		job = self.jobs[i]
		job.kill()
		self.progressbar(i)