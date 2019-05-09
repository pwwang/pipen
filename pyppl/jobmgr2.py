
from threading import RLock
from transitions import State
from transitions.extensions import LockedMachine as Machine
from .utils import Box

class Jobmgr(object):

	STATE = Box(
		INIT         = 'init',
		BUILDING     = State(name = 'building', on_enter = ''),
		BUILT        = 'built',
		BUILTFAILED  = 'builtfailed',
		SUBMITTING   = 'submitting',
		SUBMITTED    = 'submitted',
		SUBMITFAILED = 'submitfailed',
		RUNNING      = 'running',
		RETRYING     = 'retrying',
		DONE         = 'done',
		DONECACHED   = 'donecached',
		DONEFAILED   = 'donefailed',
		ENDFAILED    = 'endfailed',
		KILLING      = 'killing',
		KILLED       = 'killed',
		KILLFAILED   = 'killfailed',
	)

	def __init__(self, jobs, conf):
		if not jobs:  # no jobs
			return

		self.machine = Machine(
			model              = jobs,
			states             = Jobmgr.STATE.values(),
			initial            = Jobmgr.STATE.INIT,
			send_event         = True,
			after_state_change = self.progressbar
			machine_context    = RLock())

		self.machine.add_transition(
			trigger = 'init',
			source  = Jobmgr.STATE.INIT,
			dest    = Jobmgr.STATE.BUILDING,
			before  = self.progressbar)

		self.machine.add_transition(
			trigger    = 'build',
			source     = Jobmgr.STATE.BUILDING,
			dest       = Jobmgr.STATE.BUILT,
			conditions = 'building')

		self.machine.add_transition(
			trigger = 'build',
			source  = Jobmgr.STATE.BUILDING,
			dest    = Jobmgr.STATE.BUILTFAILED,
			unless  = 'building')

		self.machine.add_transition(
			trigger = 'start',
			source  = Jobmgr.STATE.BUILT,
			dest    = Jobmgr.STATE.SUBMITTING
		)

		self.machine.add_transition(
			trigger    = 'submit',
			source     = [Jobmgr.STATE.SUBMITTING, Jobmgr.STATE.RETRYING],
			dest       = Jobmgr.STATE.SUBMITTED,
			conditions = 'submitting'
		)

		self.machine.add_transition(
			trigger = 'submit',
			source  = [Jobmgr.STATE.SUBMITTING, Jobmgr.STATE.RETRYING],
			dest    = Jobmgr.STATE.SUBMITFAILED,
			unless  = 'submitting'
		)

		self.machine.add_transition(
			trigger = 'run',
			source  = Jobmgr.STATE.SUBMITTED,
			dest    = Jobmgr.STATE.RUNNING
		)

		self.machine.add_transition(
			trigger    = 'complete',
			source     = Jobmgr.STATE.RUNNING,
			dest       = Jobmgr.STATE.DONE,
			conditions = 'completing'
		)

		self.machine.add_transition(
			trigger = 'complete',
			source  = Jobmgr.STATE.RUNNING,
			dest    = Jobmgr.STATE.DONEFAILED,
			unless  = 'completing'
		)

		self.machine.add_transition(
			trigger = 'retry',
			source  = Jobmgr.STATE.DONEFAILED,
			dest    = Jobmgr.STATE.RETRYING,
			conditions  = 'retrying'
		)

		self.machine.add_transition(
			trigger = 'retry',
			source  = Jobmgr.STATE.DONEFAILED,
			dest    = Jobmgr.STATE.ENDFAILED,
			unless  = 'retrying'
		)

		self.machine.add_transition(
			trigger = 'sharpen',
			source  = '*',
			dest    = Jobmgr.STATE.KILLING
		)

		self.machine.add_transition(
			trigger    = 'kill',
			source     = Jobmgr.STATE.KILLING,
			dest       = Jobmgr.STATE.KILLED,
			conditions = 'killing'
		)

		self.machine.add_transition(
			trigger = 'kill',
			source  = Jobmgr.STATE.KILLING,
			dest    = Jobmgr.STATE.KILLFAILED,
			unless  = 'killing'
		)

		self.jobs    = jobs
		self.config  = conf
		self.stop    = False

		self.queue  = PQueue(batch_len = len(jobs))
		self.nslots = min(queue.batchLen, int(conf['nthread']))

		for job in jobs:
			self.queue.putToBuild(job.index)

	def run(self):
		pool = ThreadPool(
			self.nslots,
			initializer = self.worker,
			initargs    = self.queue
		)
		pool.join(cleanup = self.cleanup)

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
			nrunning   += int(stat in (Jobmgr.STATE.RUNNING, Jobmgr.STATE.SUBMITTED))

		for barjob in barjobs:
			if jobidx in barjob:
				pbar += Jobmgr.PBAR_MARKS[status[jobidx]]
			else:
				bjstatus  = [status[i] for i in barjob]
				if Jobmgr.STATE.BUILTFAILED in bjstatus:
					stat = Jobmgr.STATE.BUILTFAILED
				elif Jobmgr.STATE.SUBMITFAILED in bjstatus:
					stat = Jobmgr.STATE.SUBMITFAILED
				elif Jobmgr.STATE.ENDFAILED in bjstatus:
					stat = Jobmgr.STATE.ENDFAILED
				elif Jobmgr.STATE.DONEFAILED in bjstatus:
					stat = Jobmgr.STATE.DONEFAILED
				elif Jobmgr.STATE.BUILDING in bjstatus:
					stat = Jobmgr.STATE.BUILDING
				elif Jobmgr.STATE.BUILT in bjstatus:
					stat = Jobmgr.STATE.BUILT
				elif Jobmgr.STATE.SUBMITTING in bjstatus:
					stat = Jobmgr.STATE.SUBMITTING
				elif Jobmgr.STATE.SUBMITTED in bjstatus:
					stat = Jobmgr.STATE.SUBMITTED
				elif Jobmgr.STATE.RETRYING in bjstatus:
					stat = Jobmgr.STATE.RETRYING
				elif Jobmgr.STATE.RUNNING in bjstatus:
					stat = Jobmgr.STATE.RUNNING
				elif Jobmgr.STATE.DONE in bjstatus:
					stat = Jobmgr.STATE.DONE
				elif Jobmgr.STATE.DONECACHED in bjstatus:
					stat = Jobmgr.STATE.DONECACHED
				elif Jobmgr.STATE.KILLING in bjstatus:
					stat = Jobmgr.STATE.KILLING
				elif Jobmgr.STATE.KILLED in bjstatus:
					stat = Jobmgr.STATE.KILLED
				else:
					stat = Jobmgr.STATE.INITIATED
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
		rjobs = [job for job in self.jobs if job.state in (
			Jobmgr.STATE.BUILT,
			Jobmgr.STATE.SUBMITTING,
			Jobmgr.STATE.SUBMITTED,
			Jobmgr.STATE.RUNNING,
			Jobmgr.STATE.RETRYING,
			Jobmgr.STATE.DONEFAILED,
		)]
		killq = Queue()
		for rjob in rjobs:
			killq.put(rjob)

		ThreadPool(
			min(len(rjobs), self.config['nthread']),
			initializer = self.killWorker,
			initargs    = killq
		).join()

		failedjobs = [job for job in self.jobs if job.state in (
			Jobmgr.STATE.BUILTFAILED,
			Jobmgr.STATE.SUBMITFAILED,
			Jobmgr.STATE.ENDFAILED,
		)] or self.jobs

		random.choice(failedjobs).showError(len(failedjobs))

		if isinstance(ex, Exception) and not isinstance(ex, (JobFailException,
			JobBuildingException, JobSubmissionException, KeyboardInterrupt)):
			raise ex
		exit(1)

	def killWorker(self, killq):
		while not killq.empty():
			job = killq.get()
			job.sharpen()
			job.kill()
			killq.task_done()

	def worker(self):
		pass
