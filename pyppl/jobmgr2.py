"""Job manager for PyPPL"""
import sys
import random
from time import sleep
from threading import RLock
from transitions import State, MachineError
from .utils import Box, StateMachine, PQueue, Queue, ThreadPool
from .logger import logger
from .exceptions import JobBuildingException, JobFailException

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

	def __init__(self, jobs):
		if not jobs:  # no jobs
			return

		self.lock = RLock()

		states = [
			# State(
			# 	STATES.RUNNING,
			# 	on_enter = lambda event: self.lock.acquire(),
			# 	on_exit  = self._tryReleaseLock) \
			# if state == STATES.RUNNING else state
			state
			for _, state in STATES.items()
		]

		machine = StateMachine(
			model              = jobs,
			states             = states,
			initial            = STATES.INIT,
			send_event         = True,
			after_state_change = self.progressbar)

		self.jobs = jobs
		self.proc = jobs[0].proc
		self.stop = False

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
			source     = STATES.KILLING,
			dest       = {
				True : STATES.KILLED,
				False: STATES.KILLFAILED},
			depends_on = 'kill')

	def start(self):
		ThreadPool(self.nslots, initializer = self.worker).join(cleanup = self.cleanup)
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
		job         = event.model
		index_bjobs = self._distributeJobsToPbar()

		# get all states in this moment
		with self.lock:
			states = [job.state for job in self.jobs]
		ncompleted = nrunning = 0
		for state in states:
			ncompleted += int(state in (
				STATES.DONE, STATES.DONECACHED, STATES.ENDFAILED))
			nrunning   += int(state in (STATES.RUNNING, STATES.SUBMITTED))

		pbar  = '['
		pbar += ''.join(
			PBAR_MARKS[states[job.index]] if job.index in indexes \
			else PBAR_MARKS[max(states[index] for index in indexes)]
			for indexes in index_bjobs)
		pbar += '] Done: {:5.1f}% | Running: {}'.format(
			100.0*float(ncompleted)/float(len(self.jobs)), nrunning)

		job.logger.pbar[PBAR_LEVEL[states[job.index]]](
			pbar, done = ncompleted == len(self.jobs))

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
		elif isinstance(ex, JobFailException):
			message = 'Error encountered (errhow = halt), quitting pipeline ...'
		elif isinstance(ex, KeyboardInterrupt):
			message = '[Ctrl-c] detected, quitting pipeline ...'
		else:
			message = None
		if message:
			logger.warning(message, proc = self.proc.name())

		# kill running jobs
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

		with self.lock:
			failed_jobs = self._getJobs(
				STATES.BUILTFAILED,
				STATES.SUBMITFAILED,
				STATES.ENDFAILED
			)
			failed_jobs = failed_jobs or self.jobs

			random.choice(failed_jobs).showError(len(failed_jobs))

			if isinstance(ex, Exception) and not isinstance(ex, (
				JobFailException, JobBuildingException, KeyboardInterrupt)):
				raise ex
			sys.exit(1)

	def killWorker(self, killq):
		while not killq.empty():
			job = killq.get()
			job.triggerStartKill()
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
		while not self.queue.empty() and not self.stop:
			index, batch = self.queue.get()
			job = self.jobs[index]
			if job.state == STATES.INIT:
				job.triggerStartBuild()
				job.triggerBuild(batch = batch)
			elif job.state == STATES.BUILT:
				with self.lock:
					if len(self._getJobs(STATES.RUNNING, STATES.SUBMITTED)) < self.proc.forks:
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
				sleep(1) # have to be longer than ThreadPool.join's interval
				job.triggerPoll(batch = batch)
			#else: # endfailed but ignored, after retry
			#	pass
			self.queue.task_done()
