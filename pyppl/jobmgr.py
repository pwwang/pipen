"""Job manager for PyPPL"""
import sys
import random
from time import sleep
from threading import Lock
from queue import Queue
from .utils import Box, StateMachine, PQueue, ThreadPool
from .logger import logger
from .exception import JobBuildingException, JobFailException
from .plugin import pluginmgr

STATES = Box(
	INIT         = '00_init',
	BUILDING     = '99_building',
	BUILT        = '97_built',
	BUILTFAILED  = '98_builtfailed',
	SUBMITTING   = '89_submitting',
	SUBMITTED    = '88_submitted',
	SUBMITFAILED = '87_submitfailed',
	RUNNING      = '78_running',
	RETRYING     = '79_retrying',
	DONE         = '67_done',
	DONECACHED   = '66_donecached',
	DONEFAILED   = '68_donefailed',
	ENDFAILED    = '69_endfailed',
	KILLING      = '59_killing',
	KILLED       = '57_killed',
	KILLFAILED   = '58_killfailed',
)
PBAR_MARKS = {
	STATES.INIT         : ' ',
	STATES.BUILDING     : '~',
	STATES.BUILT        : '-',
	STATES.BUILTFAILED  : '!',
	STATES.SUBMITTING   : '+',
	STATES.SUBMITTED    : '>',
	STATES.SUBMITFAILED : '$',
	STATES.RUNNING      : '>',
	STATES.RETRYING     : '-',
	STATES.DONE         : '=',
	STATES.DONECACHED   : 'z',
	STATES.DONEFAILED   : 'x',
	STATES.ENDFAILED    : 'X',
	STATES.KILLING      : '<',
	STATES.KILLED       : '*',
	STATES.KILLFAILED   : '*',
}
PBAR_LEVEL = {
	STATES.INIT         : 'BLDING',
	STATES.BUILDING     : 'BLDING',
	STATES.BUILT        : 'BLDING',
	STATES.BUILTFAILED  : 'BLDING',
	STATES.SUBMITTING   : 'SBMTING',
	STATES.SUBMITTED    : 'SBMTING',
	STATES.SUBMITFAILED : 'SBMTING',
	STATES.RUNNING      : 'RUNNING',
	STATES.RETRYING     : 'RTRYING',
	STATES.DONE         : 'JOBDONE',
	STATES.DONECACHED   : 'JOBDONE',
	STATES.DONEFAILED   : 'JOBDONE',
	STATES.ENDFAILED    : 'JOBDONE',
	STATES.KILLING      : 'KILLING',
	STATES.KILLED       : 'KILLING',
	STATES.KILLFAILED   : 'KILLING',
}

class Jobmgr(object):
	"""@API
	Job manager"""

	def __init__(self, jobs):
		"""@API
		Job manager constructor
		@params:
			jobs (list): All jobs of a process
		"""
		if not jobs:  # no jobs
			return

		self.lock = Lock()

		machine = StateMachine(
			model              = jobs,
			states             = STATES.values(),
			initial            = STATES.INIT,
			send_event         = True,
			after_state_change = self.progressbar)

		self.jobs = jobs
		self.proc = jobs[0].proc
		self.stop = False
		#self.pool = None

		self.queue  = PQueue(batch_len = len(jobs))
		self.nslots = min(self.queue.batchLen, int(self.proc.nthread))

		for job in jobs:
			self.queue.put(job.index)

		self.pbar_size = self.proc.config._log.get('pbar', 50)

		# switch state from init to building
		machine.add_transition(
			trigger = 'triggerStartBuild',
			source  = STATES.INIT,
			dest    = STATES.BUILDING)

		# do the real building
		machine.add_transition(
			trigger    = 'triggerBuild',
			source     = STATES.BUILDING,
			dest       = {
				'cached': STATES.DONECACHED,
				True    : STATES.BUILT,
				False   : STATES.BUILTFAILED},
			depends_on = 'build',
			after      = self._afterBuild)

		# switch state from built to submitting
		machine.add_transition(
			trigger = 'triggerStartSubmit',
			source  = STATES.BUILT,
			dest    = STATES.SUBMITTING)

		# do the real submit
		machine.add_transition(
			trigger    = 'triggerSubmit',
			source     = STATES.SUBMITTING,
			dest       = {
				True   : STATES.SUBMITTED,
				False  : STATES.SUBMITFAILED},
			depends_on = 'submit',
			after      = self._afterSubmit)

		# try to retry if submission failed or job itself failed
		machine.add_transition(
			trigger = 'triggerRetry',
			source  = [STATES.SUBMITFAILED, STATES.DONEFAILED],
			dest    = {
				True     : STATES.BUILT,       # ready to re-submit
				'ignored': STATES.DONE,
				False    : STATES.ENDFAILED },
			depends_on = 'retry',
			before  = lambda event: sleep(.5),
			after   = self._afterRetry)

		# switch from submitted to running
		machine.add_transition(
			trigger = 'triggerStartPoll',
			source  = STATES.SUBMITTED,
			dest    = STATES.RUNNING)

		# do the poll for the results
		machine.add_transition(
			trigger = 'triggerPoll',
			source  = STATES.RUNNING,
			dest    = {
				'running': STATES.RUNNING,
				True     : STATES.DONE,
				False    : STATES.DONEFAILED},
			depends_on = 'poll',
			after      = self._afterPoll)

		# start to kill the job
		machine.add_transition(
			trigger = 'triggerStartKill',
			source  = '*',
			dest    = STATES.KILLING)

		# killed/failed to kill
		machine.add_transition(
			trigger    = 'triggerKill',
			# STATES.KILLING not guareteed, as this will be running in a separate queue
			source     = '*',
			dest       = {
				True : STATES.KILLED,
				False: STATES.KILLFAILED},
			depends_on = 'kill')

	def start(self):
		"""@API
		Start the queue.
		"""
		# no jobs
		if not hasattr(self, 'lock'):
			return
		pool = ThreadPool(self.nslots, initializer = self.worker)
		pool.join(cleanup = self.cleanup)
		self.progressbar(Box(model = self.jobs[-1]))

	def _getJobs(self, *states):
		return [job for job in self.jobs if job.state in states]

	def _distributeJobsToPbar(self):
		joblen      = len(self.jobs)
		index_bjobs = []
		if joblen <= self.pbar_size:
			div, mod = divmod(self.pbar_size, joblen)
			for j in range(joblen):
				step = div + 1 if j < mod else div
				for _ in range(step):
					index_bjobs.append([j])
		else:
			jobx = 0
			div, mod = divmod(joblen, self.pbar_size)
			for i in range(self.pbar_size):
				step = div + 1 if i < mod else div
				index_bjobs.append([jobx + jobstep for jobstep in range(step)])
				jobx += step
		return index_bjobs

	def progressbar(self, event):
		"""@API
		Generate the progress bar.
		@params:
			event (StateMachine event): The event including job as model.
		"""
		job         = event.model
		index_bjobs = self._distributeJobsToPbar()

		# get all states in this moment
		#with self.lock:
		states = [job.state for job in self.jobs]
		ncompleted = nrunning = 0
		for state in states:
			ncompleted += int(state in (
				STATES.DONE, STATES.DONECACHED, STATES.ENDFAILED))
			nrunning   += int(state in (STATES.RUNNING, STATES.SUBMITTING, STATES.SUBMITTED))

		pbar  = '['
		pbar += ''.join(
			PBAR_MARKS[states[job.index]] if job.index in indexes \
			else PBAR_MARKS[max(states[index] for index in indexes)]
			for indexes in index_bjobs)
		pbar += '] Done: {:5.1f}% | Running: {}'.format(
			100.0*float(ncompleted)/float(len(self.jobs)),
			str(nrunning).ljust(len(str(self.proc.forks))))

		job.logger(pbar, pbar = True,
			done = ncompleted == len(self.jobs), level = PBAR_LEVEL[states[job.index]])

	def cleanup(self, ex = None):
		"""@API
		Cleanup the pipeline when
		- Ctrl-c hit
		- error encountered and `proc.errhow` = 'terminate'
		@params:
			ex (Exception): The exception raised by workers
		"""
		self.stop = True
		message = None
		if isinstance(ex, JobBuildingException):
			message = 'Job building failed, quitting pipeline ' + \
				'(Ctrl-c to skip killing jobs) ...'
		elif isinstance(ex, JobFailException):
			message = 'Error encountered (errhow = halt), quitting pipeline ' + \
				'(Ctrl-c to skip killing jobs) ...'
		elif isinstance(ex, KeyboardInterrupt):
			message = '[Ctrl-c] detected, quitting pipeline ' + \
				'(Ctrl-c again to skip killing jobs) ...'

		if message:
			logger.warning(message, proc = self.proc.name())

		# kill running jobs
		with self.lock:

			failed_jobs = self._getJobs(STATES.ENDFAILED)
			if not failed_jobs:
				failed_jobs = self._getJobs(STATES.DONEFAILED)
			if not failed_jobs:
				failed_jobs = self._getJobs(STATES.SUBMITFAILED)
			if not failed_jobs:
				failed_jobs = self._getJobs(STATES.BUILTFAILED)

			running_jobs = self._getJobs(
				STATES.BUILT, STATES.SUBMITTING, STATES.SUBMITTED,
				STATES.RUNNING, STATES.RETRYING, STATES.DONEFAILED,
			)
			killq = Queue()
			for rjob in running_jobs:
				killq.put(rjob)

			ThreadPool(
				min(len(running_jobs), self.proc.nthread),
				initializer = self.killWorker,
				initargs    = killq
			).join()

			random.choice(failed_jobs or running_jobs or self.jobs).showError(len(failed_jobs))

			if isinstance(ex, Exception) and not isinstance(ex, (
				JobFailException, JobBuildingException, KeyboardInterrupt)):
				raise ex from None

			pluginmgr.hook.procFail(proc = self.jobs[0].proc)
			sys.exit(1)


	@classmethod
	def killWorker(self, killq):
		"""@API
		The killing worker to kill the jobs"""
		while not killq.empty():
			job = killq.get()
			# Since this queue may be running at the same time as main queue is
			# So this is not thread-safe
			job.triggerStartKill()
			# we need to change state to *
			# as killing is not guareteed
			job.triggerKill()
			killq.task_done()

	def _afterBuild(self, event):
		job = event.model
		if job.state == STATES.DONECACHED:
			job.done(cached = True)
		elif job.state == STATES.BUILT:
			self.queue.putNext(job.index, event.kwargs['batch'])
		else: # BUILTFAILED, if any job failed to build, halt the pipeline
			raise JobBuildingException()

	def _afterSubmit(self, event):
		job = event.model
		if job.state == STATES.SUBMITTED:
			self.queue.put(job.index, event.kwargs['batch'])
		else: # SUBMITFAILED
			job.triggerRetry(batch = event.kwargs['batch'])

	def _afterRetry(self, event):
		job = event.model
		if job.state == STATES.BUILT:
			self.queue.putNext(job.index, event.kwargs['batch'])
		elif job.state == STATES.DONE:
			job.done()
		elif self.proc.errhow == 'halt': # ENDFAILED
			raise JobFailException()
		# else: endfailed but ignored

	def _afterPoll(self, event):
		job = event.model
		if job.state == STATES.DONE:
			job.done()
		elif job.state == STATES.RUNNING:
			self.queue.putNext(job.index, event.kwargs['batch'])
		else: # DONEFAILED
			job.triggerRetry(batch = event.kwargs['batch'])

	def worker(self):
		"""@API
		The worker to build, submit and poll the jobs"""
		while not self.queue.empty() and not self.stop:
			index, batch = self.queue.get()
			job = self.jobs[index]
			# make sure quit me for killWorker
			# and don't use a GIL, as it blocks regular jobs
			if self.stop: # pragma: no cover
				break

			if job.state == STATES.INIT:
				job.triggerStartBuild()
				job.triggerBuild(batch = batch)
			elif job.state == STATES.BUILT:
				with self.lock:
					if len(self._getJobs(
						STATES.RUNNING, STATES.SUBMITTING, STATES.SUBMITTED)) < self.proc.forks:
						job.triggerStartSubmit()
				if job.state == STATES.SUBMITTING:
					job.triggerSubmit(batch = batch)
				else:
					sleep(.5)
					# put the job back to the queue
					self.queue.putNext(index, batch)
			elif job.state == STATES.SUBMITTED:
				job.triggerStartPoll()
				job.triggerPoll(batch = batch)
			elif job.state == STATES.RUNNING:
				# have to be longer than ThreadPool.join's interval
				sleep(job.__class__.POLL_INTERVAL)
				job.triggerPoll(batch = batch)
			elif job.state == STATES.KILLING: # pragma: no cover
				break
			#else: # endfailed but ignored, after retry
			#	pass

			self.queue.task_done()
