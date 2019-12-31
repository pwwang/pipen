from copy import copy
from time import sleep
import pytest
from diot import Diot
from pyppl._proc import OUT_DIRTYPE, OUT_FILETYPE, OUT_VARTYPE, OUT_STDOUTTYPE, OUT_STDERRTYPE, IN_VARTYPE, IN_FILETYPE, IN_FILESTYPE
from pyppl.template import TemplateLiquid
from pyppl.jobmgr import Jobmgr, STATES
from pyppl.logger import logger

class Proc(dict):

	def __init__(self, *args, **kwargs):
		kwargs['nthread'] = 10
		kwargs['name']    = lambda procset = True: 'pProc'
		kwargs['errhow']  = 'terminate'
		kwargs['errntry'] = 3
		kwargs['forks']   = 1
		kwargs['size']    = 1
		kwargs['id']    = 'pProc'
		super(Proc, self).__init__(*args, **kwargs)

	def __getattr__(self, item):
		return super().__getitem__(item)

# Mock job
class Job(object):
	POLL_INTERVAL = 1
	def __init__(self, index, proc, name = 'job'):
		self.index      = index
		self.proc       = proc
		self.orig_state = STATES.INIT
		self.state      = None
		self.ntry       = 0
		self.name = name

	def logger(self, *args, **kwargs):
		"""A logger wrapper to avoid instanize a logger object for each job"""
		level = kwargs.pop('level', 'info')
		kwargs['proc']   = self.proc.name(False)
		kwargs['jobidx'] = self.index
		kwargs['joblen'] = self.proc.size
		if kwargs.pop('pbar', False):
			logger.pbar[level](*args, **kwargs)
		else:
			logger[level](*args, **kwargs)

	def restore_state(self):
		self.state = self.orig_state

	def kill(self):
		return self.orig_state.endswith('ing')

	def done(self, cached = False, status = True):
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

def job_factory(index, state, name):
	@pytest.fixture
	def job_with_state(proc_default):
		job       = Job(index, proc_default, name)
		job.state = job.orig_state = state
		return job
	return job_with_state

def inject_job_fixture(name, index, state):
	globals()[name] = job_factory(index, state, name)

inject_job_fixture('job_init', 0, STATES.INIT)
inject_job_fixture('job_building', 0, STATES.BUILDING)
inject_job_fixture('job_built', 0, STATES.BUILT)
inject_job_fixture('job_builtfailed', 0, STATES.BUILTFAILED)
inject_job_fixture('job_submitting', 0, STATES.SUBMITTING)
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