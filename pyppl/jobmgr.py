"""Job manager for PyPPL
@variables:
	STATES (dict): Possible states for the job
	PBAR_MARKS (dict): The marks on progress bar for different states
	PBAR_LEVEL (dict): The levels for different states
	PBAR_SIZE (int): the size of the progress bar
"""
import sys
from time import sleep
from threading import Lock
from queue import Queue
from diot import Diot
from .utils import StateMachine, PQueue, ThreadPool
from .logger import logger
from .exception import JobBuildingError, JobFailError
from .runner import poll_interval

STATES = Diot(
	INIT         = '00_init',
	BUILDING     = '99_building',
	BUILT        = '97_built',
	BUILTFAILED  = '98_builtfailed',
	SUBMITTING   = '89_submitting',
	SUBMITFAILED = '87_submitfailed',
	RUNNING      = '78_running',
	DONE         = '67_done',
	RETRYING     = '80_retrying',
	DONECACHED   = '66_donecached',
	DONEFAILED   = '68_donefailed',
	ENDFAILED    = '69_endfailed',
	KILLING      = '59_killing',
	KILLED       = '57_killed',
	KILLFAILED   = '58_killfailed',
)
PBAR_MARKS = {
	STATES.INIT        : ' ',
	STATES.BUILDING    : '~',
	STATES.BUILT       : '-',
	STATES.BUILTFAILED : '!',
	STATES.SUBMITTING  : '>',
	STATES.SUBMITFAILED: '$',
	STATES.RUNNING     : '>',
	STATES.RETRYING    : '-',
	STATES.DONE        : '=',
	STATES.DONECACHED  : 'z',
	STATES.DONEFAILED  : 'x',
	STATES.ENDFAILED   : 'X',
	STATES.KILLING     : '<',
	STATES.KILLED      : '*',
	STATES.KILLFAILED  : '*',
}
PBAR_LEVEL = {
	STATES.INIT        : 'BLDING',
	STATES.BUILDING    : 'BLDING',
	STATES.BUILT       : 'BLDING',
	STATES.BUILTFAILED : 'BLDING',
	STATES.SUBMITTING  : 'SBMTING',
	STATES.SUBMITFAILED: 'SBMTING',
	STATES.RUNNING     : 'RUNNING',
	STATES.RETRYING    : 'RTRYING',
	STATES.DONE        : 'JOBDONE',
	STATES.DONECACHED  : 'JOBDONE',
	STATES.DONEFAILED  : 'JOBDONE',
	STATES.ENDFAILED   : 'JOBDONE',
	STATES.KILLING     : 'KILLING',
	STATES.KILLED      : 'KILLING',
	STATES.KILLFAILED  : 'KILLING',
}

PBAR_SIZE = 50

class Jobmgr:
	"""@API
	Job manager"""

	__slots__ = ('jobs', 'proc', 'stop', 'queue', 'nslots', 'lock')

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
			states             = list(STATES.values()),
			initial            = STATES.INIT,
			send_event         = True,
			after_state_change = self.progressbar)

		self.jobs = jobs
		self.proc = jobs[0].proc
		self.stop = False

		self.queue  = PQueue(batch_len = len(jobs))
		self.nslots = min(self.queue.batch_len, int(self.proc.nthread))

		for job in jobs:
			self.queue.put(job.index)

		# start building
		machine.add_transition(
			trigger    = 'trigger_build',
			source     = STATES.INIT,
			dest       = {
				'cached': STATES.DONECACHED,
				True    : STATES.BUILT,
				False   : STATES.BUILTFAILED},
			depends_on = 'build',
			before     = lambda event: setattr(event.model, 'state', STATES.BUILDING),
			after      = self._post_event)

		# do the real submit
		machine.add_transition(
			trigger    = 'trigger_submit',
			source     = [STATES.BUILT, STATES.RETRYING],
			dest       = {
				True   : STATES.RUNNING,
				False  : STATES.SUBMITFAILED},
			depends_on = 'submit',
			after      = self._post_event)

		# try to retry if submission failed or job itself failed
		machine.add_transition(
			trigger = 'trigger_retry',
			source  = [STATES.SUBMITFAILED, STATES.DONEFAILED],
			dest    = {
				True     : STATES.RETRYING, # ready to re-submit
				'ignored': STATES.DONE,
				False    : STATES.ENDFAILED },
			depends_on = 'retry',
			before  = lambda event: sleep(.5),
			after   = self._post_event)

		# do the poll for the results
		machine.add_transition(
			trigger = 'trigger_poll',
			source  = STATES.RUNNING,
			dest    = {
				'running': STATES.RUNNING,
				True     : STATES.DONE,
				False    : STATES.DONEFAILED},
			depends_on = 'poll',
			after      = self._post_event)

		# killed/failed to kill
		machine.add_transition(
			trigger    = 'trigger_kill',
			# STATES.KILLING not guareteed, as this will be running in a separate queue
			source     = '*',
			dest       = {
				True : STATES.KILLED,
				False: STATES.KILLFAILED},
			before     = lambda event: setattr(event.model, 'state', STATES.KILLING),
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
		self.progressbar(Diot(model = self.jobs[-1]))

	def _get_jobs_by_states(self, *states):
		return [job for job in self.jobs if job.state in states]

	def _distribute_jobs_to_pbar(self):
		joblen      = len(self.jobs)
		index_bjobs = []
		if joblen <= PBAR_SIZE:
			div, mod = divmod(PBAR_SIZE, joblen)
			for j in range(joblen):
				step = div + 1 if j < mod else div
				for _ in range(step):
					index_bjobs.append([j])
		else:
			jobx = 0
			div, mod = divmod(joblen, PBAR_SIZE)
			for i in range(PBAR_SIZE):
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
		index_bjobs = self._distribute_jobs_to_pbar()

		# get all states in this moment
		#with self.lock:
		states = [job.state for job in self.jobs]
		ncompleted = nrunning = 0
		for state in states:
			ncompleted += int(state in (
				STATES.DONE, STATES.DONECACHED, STATES.ENDFAILED))
			nrunning   += int(state in (STATES.RUNNING, STATES.SUBMITTING))

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
		- Ctrl-C hit
		- error encountered and `proc.errhow` = 'terminate'
		@params:
			ex (Exception): The exception raised by workers
		"""
		self.stop = True
		message = None
		if isinstance(ex, JobBuildingError):
			message = 'Job building failed, quitting pipeline ' + \
				'(Ctrl-C to skip killing jobs) ...'
		elif isinstance(ex, JobFailError):
			message = 'Error encountered (errhow = halt), quitting pipeline ' + \
				'(Ctrl-C to skip killing jobs) ...'
		elif isinstance(ex, KeyboardInterrupt):
			message = '[Ctrl-C] detected, quitting pipeline ' + \
				'(Ctrl-C again to skip killing jobs) ...'

		if message:
			logger.warning(message, proc = self.proc.id)

		# kill running jobs
		with self.lock:

			# failed_jobs =	self._get_jobs_by_states(STATES.ENDFAILED) or \
			# 				self._get_jobs_by_states(STATES.DONEFAILED) or \
			# 				self._get_jobs_by_states(STATES.SUBMITFAILED) or \
			# 				self._get_jobs_by_states(STATES.BUILTFAILED)

			running_jobs = self._get_jobs_by_states(
				# all possible states to go to next steps
				STATES.BUILT, STATES.SUBMITTING,
				STATES.RUNNING, STATES.RETRYING, STATES.DONEFAILED,
			)
			killq = Queue()
			for rjob in running_jobs:
				killq.put(rjob)

			ThreadPool(
				min(len(running_jobs), self.proc.nthread),
				initializer = self.kill_worker,
				initargs    = killq
			).join()

			#random.choice(failed_jobs or running_jobs or self.jobs).showError(len(failed_jobs))

			if isinstance(ex, Exception) and not isinstance(ex, (
				JobFailError, JobBuildingError, KeyboardInterrupt)):
				raise ex from None

			sys.exit(1)

	@classmethod
	def kill_worker(cls, killq):
		"""@API
		The killing worker to kill the jobs"""
		while not killq.empty():
			job = killq.get()
			job.trigger_kill()
			killq.task_done()

	def _post_event(self, event):
		job = event.model
		if job.state == STATES.DONECACHED:
			job.done(cached = True)
		elif job.state in (STATES.BUILT, STATES.RETRYING):
			self.queue.put_next(job.index, event.kwargs['batch'])
		elif job.state == STATES.BUILTFAILED:
			raise JobBuildingError()
		elif job.state == STATES.RUNNING:
			self.queue.put_next(job.index, event.kwargs['batch'])
		elif job.state in (STATES.SUBMITFAILED, STATES.DONEFAILED):
			job.trigger_retry(batch = event.kwargs['batch'])
		elif job.state == STATES.DONE:
			job.done(status = True)
		elif job.state == STATES.ENDFAILED:
			if self.proc.errhow == 'halt':
				raise JobFailError()
			# else: endfailed but ignored
			job.done(status = False)

	def worker(self):
		"""@API
		The worker to build, submit and poll the jobs"""
		while not self.queue.empty() and not self.stop:
			index, batch = self.queue.get()
			job = self.jobs[index]
			# make sure quit me for kill_worker
			# and don't use a GIL, as it blocks regular jobs
			if self.stop: # pragma: no cover
				break

			if job.state == STATES.INIT:
				job.trigger_build(batch = batch)
			elif job.state in (STATES.BUILT, STATES.RETRYING):
				with self.lock:
					if len(self._get_jobs_by_states(
						STATES.RUNNING, STATES.SUBMITTING)) < self.proc.forks:
						job.trigger_submit(batch = batch)
				# if we successfully submitted
				if job.state in (STATES.BUILT, STATES.RETRYING):
					sleep(.5)
					# put the job back to the queue
					self.queue.put_next(index, batch)
			elif job.state == STATES.RUNNING:
				# have to be longer than ThreadPool.join's interval
				sleep(poll_interval())
				job.trigger_poll(batch = batch)
			elif job.state == STATES.KILLING: # pragma: no cover
				break
			#else: # endfailed but ignored, after retry
			#	pass

			self.queue.task_done()
