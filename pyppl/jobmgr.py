from collections import OrderedDict
from time import sleep
from os import getppid
from signal import SIGINT
from multiprocessing import Lock, JoinableQueue, Process, Array
from .utils import ps

class Jobmgr (object):
	"""
	Job Manager
	"""
	STATUS_INITIATED    = 0
	STATUS_SUBMITTING   = 1
	STATUS_SUBMITTED    = 2
	STATUS_SUBMITFAILED = 3
	STATUS_DONE         = 4
	STATUS_DONEFAILED   = 5

	PBAR_SIZE = 50

	def __init__(self, proc, runner):
		"""
		Job manager constructor
		@params:
			`proc`     : The process
			`runner`   : The runner class
		"""
		self.proc    = proc
		self.lock    = Lock()
		status       = []
		self.runners = OrderedDict()
		for job in proc.jobs:
			if not proc.cclean and job.index not in proc.ncjobids:
				status.append(Jobmgr.STATUS_DONE)
			else:
				status.append(Jobmgr.STATUS_INITIATED)
				self.runners[job.index] = runner(job)
		self.status  = Array('i', status, lock = Lock())
		# number of runner processes
		self.nprunner = min(proc.forks, len(self.runners))
		# number of submit processes
		self.npsubmit = min(self.nprunner, proc.forks, proc.nthread)
		self.subprocs = []

	def _exit(self):
		indexes = [i for i, s in enumerate(self.status) if s != Jobmgr.STATUS_DONE]
		lenidx  = len(indexes)
		if lenidx > 0:
			try:
				self.runners[indexes[0]].job.showError(lenidx)
			except KeyboardInterrupt: # pragma: no cover
				pass

			for idx in indexes:
				self.runners[idx].kill()

		for proc in self.subprocs:
			if proc._popen:
				proc.terminate()

	def allJobsDone(self):
		"""
		Tell whether all jobs are done.
		No need to lock as it only runs in one process (the watcher process)
		@returns:
			`True` if all jobs are done else `False`
		"""
		if not self.runners: return True
		return all(s in [Jobmgr.STATUS_DONE, Jobmgr.STATUS_DONEFAILED] for s in self.status)

	def halt(self, halt_anyway = False):
		"""
		Halt the pipeline if needed
		"""
		with self.lock: # only one thread can halt
			if self.proc.errhow == 'halt' or halt_anyway:
				ps.killtree(getppid(), killme = True, sig = SIGINT)
			
	def progressbar(self, jid, loglevel = 'info'):
		bar     = '%s [' % self.proc.jobs[jid]._indexIndicator()
		barjobs = []
		# distribute the jobs to bars
		if self.proc.size <= Jobmgr.PBAR_SIZE:
			n, m = divmod(Jobmgr.PBAR_SIZE, self.proc.size)
			for j in range(self.proc.size):
				step = n + 1 if j < m else n
				for _ in range(step):
					barjobs.append([j])
		else:
			jobx = 0
			n, m = divmod(self.proc.size, Jobmgr.PBAR_SIZE)
			for i in range(Jobmgr.PBAR_SIZE):
				step = n + 1 if i < m else n
				barjobs.append([jobx + s for s in range(step)])
				jobx += step

		# status can only be:
		# Jobmgr.STATUS_SUBMITTED
		# Jobmgr.STATUS_SUBMITFAILED
		# Jobmgr.STATUS_DONE
		# Jobmgr.STATUS_DONEFAILED
		# Jobmgr.STATUS_INITIATED
		ncompleted = sum(1 for s in self.status if s == Jobmgr.STATUS_DONE or s == Jobmgr.STATUS_DONEFAILED)
		nrunning   = sum(1 for s in self.status if s == Jobmgr.STATUS_SUBMITTED or s == Jobmgr.STATUS_SUBMITFAILED)

		for bj in barjobs:
			if jid in bj and self.status[jid] == Jobmgr.STATUS_INITIATED:
				bar += '-'
			elif jid in bj and self.status[jid] == Jobmgr.STATUS_SUBMITFAILED:
				bar += '!'
			elif jid in bj and (self.status[jid] in [Jobmgr.STATUS_SUBMITTING, Jobmgr.STATUS_SUBMITTED]):
				bar += '>'
			elif jid in bj and self.status[jid] == Jobmgr.STATUS_DONEFAILED:
				bar += 'X'
			elif jid in bj and self.status[jid] == Jobmgr.STATUS_DONE:
				bar += '='
			elif any(self.status[j] == Jobmgr.STATUS_INITIATED for j in bj):
				bar += '-'
			elif any(self.status[j] == Jobmgr.STATUS_SUBMITFAILED for j in bj):
				bar += '!'
			elif any(self.status[j] in [Jobmgr.STATUS_SUBMITTING, Jobmgr.STATUS_SUBMITTED] for j in bj):
				bar += '>'
			elif any(self.status[j] == Jobmgr.STATUS_DONEFAILED for j in bj):
				bar += 'X'
			else: # STATUS_DONE
				bar += '='

		bar += '] Done: %5.1f%% | Running: %d' % (100.0*float(ncompleted)/float(self.proc.size), nrunning)
		self.proc.log(bar, loglevel)

	def canSubmit(self):
		"""
		Tell whether we can submit jobs.
		@returns:
			`True` if we can, otherwise `False`
		"""
		with self.lock:
			if self.nprunner == 0: return True
			return sum(s in [
				Jobmgr.STATUS_SUBMITTING,
				Jobmgr.STATUS_SUBMITTED,
				Jobmgr.STATUS_SUBMITFAILED
			] for s in self.status) < self.nprunner

	def submitPool(self, sq):
		"""
		The pool to submit jobs
		@params:
			`sq`: The submit queue
		"""
		try:
			while True:
				# if we already have enough # jobs running, wait
				if not self.canSubmit():
					sleep(.2)
					continue

				jid = sq.get()
				if jid is None:
					sq.task_done()
					break

				self.status[jid] = Jobmgr.STATUS_SUBMITTING
				if self.runners[jid].submit():
					self.status[jid] = Jobmgr.STATUS_SUBMITTED
				else:
					self.status[jid] = Jobmgr.STATUS_SUBMITFAILED
					self.halt()
				self.progressbar(jid, 'submit')
				sq.task_done()
		except KeyboardInterrupt: # pragma: no cover
			pass

	def runPool(self, rq, sq):
		"""
		The pool to run jobs (wait jobs to be done)
		@params:
			`rq`: The run queue
			`sq`: The submit queue
		"""
		try:
			while True:
				jid = rq.get()
				if jid is None:
					rq.task_done()
					break
				else:
					r = self.runners[jid]
					while self.status[jid]!=Jobmgr.STATUS_SUBMITTED and self.status[jid]!=Jobmgr.STATUS_SUBMITFAILED:
						sleep(.2)
					if self.status[jid]==Jobmgr.STATUS_SUBMITTED and r.run():
						self.status[jid] = Jobmgr.STATUS_DONE
					else: # submission failed
						if r.retry():
							self.status[jid] = Jobmgr.STATUS_INITIATED
							sq.put(jid)
							rq.put(jid)
						else:
							self.status[jid] = Jobmgr.STATUS_DONEFAILED
							r.kill()
							self.halt()
					self.progressbar(jid, 'jobdone')
					rq.task_done()
		except KeyboardInterrupt: # pragma: no cover
			pass

	def watchPool(self, rq, sq):
		"""
		The watchdog, checking whether all jobs are done.
		"""
		try:
			while not self.allJobsDone():
				sleep(.1)

			for _ in range(self.npsubmit):
				sq.put(None)
			for _ in range(self.nprunner):
				rq.put(None)
		except KeyboardInterrupt: # pragma: no cover
			pass

	def run(self):
		"""
		Start to run the jobs
		"""
		submitQ = JoinableQueue()
		runQ    = JoinableQueue()

		for rid in self.runners.keys():
			submitQ.put(rid)
			runQ.put(rid)

		for _ in range(self.npsubmit):
			p = Process(target = self.submitPool, args = (submitQ, ))
			p.daemon = True
			self.subprocs.append(p)
			p.start()

		for _ in range(self.nprunner):
			p = Process(target = self.runPool, args = (runQ, submitQ))
			p.daemon = True
			self.subprocs.append(p)
			p.start()

		watchDog = Process(target = self.watchPool, args = (runQ, submitQ))
		watchDog.daemon = True
		self.subprocs.append(watchDog)
		watchDog.start()

		runQ.join()
		submitQ.join()
		watchDog.join()