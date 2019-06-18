from copy import copy
from time import sleep
import pytest
from pyppl import Proc as _Proc
from pyppl.jobmgr2 import Jobmgr, STATES
from pyppl.logger import logger
from pyppl.utils import Box

class Proc(dict):
	OUT_VARTYPE    = _Proc.OUT_VARTYPE
	OUT_FILETYPE   = _Proc.OUT_FILETYPE
	OUT_DIRTYPE    = _Proc.OUT_DIRTYPE
	OUT_STDOUTTYPE = _Proc.OUT_STDOUTTYPE
	OUT_STDERRTYPE = _Proc.OUT_STDERRTYPE

	IN_VARTYPE   = _Proc.IN_VARTYPE
	IN_FILETYPE  = _Proc.IN_FILETYPE
	IN_FILESTYPE = _Proc.IN_FILESTYPE

	EX_GZIP = _Proc.EX_GZIP
	EX_COPY = _Proc.EX_COPY
	EX_MOVE = _Proc.EX_MOVE
	EX_LINK = _Proc.EX_LINK

	def __init__(self, *args, **kwargs):
		kwargs['nthread'] = 10
		kwargs['name']    = lambda procset = True: 'pProc'
		kwargs['errhow']  = 'terminate'
		kwargs['errntry'] = 3
		kwargs['forks']   = 1
		kwargs['config']  = Box(
			_log = {}
		)
		super(Proc, self).__init__(*args, **kwargs)

	def __getattr__(self, item):
		return super().__getitem__(item)

# Mock job
class Job(object):
	def __init__(self, index, proc):
		self.index      = index
		self.proc       = proc
		self.orig_state = STATES.INIT
		self.logger     = logger
		self.state      = None
		self.ntry       = 0

	def restore_state(self):
		self.state = self.orig_state

	def showError(self, joblen):
		logger.error('%s/%s: Job error', self.index, joblen)

	def kill(self):
		return self.orig_state.endswith('ing')

	def done(self, cached = False):
		logger.info('%s: Job done with cached: %s', self.index, cached)

	def build(self):
		return 'cached' if 'cached' in self.orig_state else True

	def submit(self):
		#sleep (2)
		return 'done' in self.orig_state or 'submit' in self.orig_state

	def poll(self):
		if 'done' in self.orig_state:
			self.orig_state = 'running'
			return 'running' # only run once
		return True

	def retry(self):
		if 'retry' in self.orig_state:
			return 'ignored'
		#if self.orig_state.endswith('ing'):
		self.ntry += 1
		return self.ntry < self.proc.errntry

@pytest.fixture
def proc_default():
	return Proc()

def job_factory(index, state):
	@pytest.fixture
	def job_with_state(proc_default):
		job       = Job(index, proc_default)
		job.state = job.orig_state = state
		return job
	return job_with_state

def inject_job_fixture(name, index, state):
	globals()[name] = job_factory(index, state)

inject_job_fixture('job_init', 0, STATES.INIT)
inject_job_fixture('job_building', 0, STATES.BUILDING)
inject_job_fixture('job_built', 0, STATES.BUILT)
inject_job_fixture('job_builtfailed', 0, STATES.BUILTFAILED)
inject_job_fixture('job_submitting', 0, STATES.SUBMITTING)
inject_job_fixture('job_submitted', 0, STATES.SUBMITTED)
inject_job_fixture('job_submitfailed', 0, STATES.SUBMITFAILED)
inject_job_fixture('job_running', 0, STATES.RUNNING)
inject_job_fixture('job_retrying', 0, STATES.RETRYING)
inject_job_fixture('job_done', 0, STATES.DONE)
inject_job_fixture('job_donecached', 0, STATES.DONECACHED)
inject_job_fixture('job_donefailed', 0, STATES.DONEFAILED)
inject_job_fixture('job_endfailed', 0, STATES.ENDFAILED)
inject_job_fixture('job_killing', 0, STATES.KILLING)
inject_job_fixture('job_killed', 0, STATES.KILLED)
inject_job_fixture('job_killfailed', 0, STATES.KILLFAILED)

# The job indexes have to be 0, 1, ...
@pytest.fixture(scope = 'module')
def jobindex_reset():
	def func(jobs):
		for i, job in enumerate(jobs):
			job.index = i
			job.logger = logger.bake(
				proc   = 'pProc', jobidx = i,
				joblen =  len(jobs),
			)
	return func

@pytest.fixture(params = [
	10, # njobs
])
def jobs_default(request, job_init):
	ret = []
	for i in range(request.param):
		job = copy(job_init)
		job.index = i
		ret.append(job)
	return ret

@pytest.fixture
def jobs_all(jobindex_reset,
	job_init, job_building, job_built, job_builtfailed, job_done, job_donecached, \
	job_donefailed, job_endfailed):
	ret = [job_init, job_building, job_built, job_builtfailed, job_done, job_donecached, \
	job_donefailed, job_endfailed]
	jobindex_reset(ret)
	return ret