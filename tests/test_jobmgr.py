import logging
from copy import copy

import pytest
from transitions.core import MachineError
from pyppl.utils import PQueue
from pyppl.jobmgr2 import Jobmgr, STATES
from pyppl.exceptions import JobBuildingException, JobFailException

pytest_plugins = ["tests.fixt_jobmgr"]
logging.getLogger('transitions').setLevel(logging.INFO)

def test_init(jobs_default):
	jm = Jobmgr([])
	assert not hasattr(jm, 'lock')
	assert not hasattr(jm, 'machine')
	assert not hasattr(jm, 'jobs')

	jm = Jobmgr(jobs_default)
	assert jm.jobs is jobs_default
	assert jm.proc is jm.jobs[0].proc
	assert not jm.stop
	assert jm.nslots == len(jobs_default)
	assert isinstance(jm.queue, PQueue)
	queue_index = []
	while not jm.queue.empty():
		queue_index.append(jm.queue.get())
	assert queue_index == [(job.index, 2) for job in jobs_default]

@pytest.mark.parametrize('exc, expect_msg', [
	(None, ['Job error']),
	(OSError, ['ERROR']),
	(JobBuildingException, ['Job building failed, quitting pipeline ...']),
	(JobFailException, ['Error encountered (errhow = halt), quitting pipeline ...']),
	(KeyboardInterrupt, ['[Ctrl-c] detected, quitting pipeline ...']),
])
def test_cleanup(jobs_default, caplog, exc, expect_msg):
	jm = Jobmgr(jobs_default)
	if exc and exc not in (JobBuildingException, JobFailException, KeyboardInterrupt):
		with pytest.raises(exc):
			jm.cleanup(exc())
	else:
		with pytest.raises(SystemExit):
			jm.cleanup(exc and exc())
	assert jm.stop
	for msg in expect_msg:
		assert msg in caplog.text

def test_cleanup_with_running_jobs(jobs_all):
	jm = Jobmgr(jobs_all)
	for job in jobs_all:
		job.restore_state()
	with pytest.raises(SystemExit):
		jm.cleanup()
	for job in jm.jobs:
		if job.orig_state in (
			STATES.SUBMITTING, STATES.RUNNING, STATES.RETRYING):
			assert job.state == STATES.KILLED
		elif job.orig_state in (
			STATES.BUILT, STATES.DONEFAILED):
			assert job.state == STATES.KILLFAILED
		else:
			assert job.state not in (STATES.KILLED, STATES.KILLFAILED)

def test_trigger_startbuild(job_init):
	jm = Jobmgr([job_init])
	job_init.restore_state()
	job_init.triggerStartBuild()
	assert job_init.state == STATES.BUILDING
	with pytest.raises(MachineError):
		job_init.triggerStartBuild()

@pytest.mark.parametrize('buildfunc, expt_state', [
	((lambda: 'cached'), STATES.DONECACHED),
	((lambda: True), STATES.BUILT),
	((lambda: False), STATES.BUILTFAILED),
])
def test_trigger_build(job_building, buildfunc, expt_state):
	assert job_building.state == STATES.BUILDING
	job_building.build = buildfunc
	jm = Jobmgr([job_building])
	job_building.restore_state()
	if expt_state == STATES.BUILTFAILED:
		with pytest.raises(JobBuildingException):
			job_building.triggerBuild()
	else:
		job_building.triggerBuild()
	assert job_building.state == expt_state

def test_trigger_startsubmit(job_built):
	jm = Jobmgr([job_built])
	job_built.restore_state()
	job_built.triggerStartSubmit()
	assert job_built.state == STATES.SUBMITTING

@pytest.mark.parametrize('submitfunc, batch, retryfunc, expt_state', [
	((lambda: True), 1, (lambda: True), STATES.SUBMITTED),
	((lambda: True), 4, (lambda: False), STATES.SUBMITTED),
	((lambda: False), 1, (lambda: True), STATES.BUILT),
	((lambda: False), 1, (lambda: False), STATES.ENDFAILED), # not SUBMITFAILED, as it goes to retry
])
def test_trigger_submit(job_submitting, submitfunc, batch, retryfunc, expt_state):
	jm = Jobmgr([job_submitting])
	job_submitting.submit = submitfunc
	job_submitting.retry = retryfunc
	job_submitting.restore_state()
	job_submitting.triggerSubmit(batch = batch)
	assert job_submitting.state == expt_state

@pytest.mark.parametrize('retryfunc, errhow, expt_state', [
	((lambda: True), 'terminate', STATES.BUILT),
	((lambda: True), 'halt', STATES.BUILT),
	((lambda: False), 'terminate', STATES.ENDFAILED),
	((lambda: False), 'halt', STATES.ENDFAILED),
	((lambda: 'ignored'), 'halt', STATES.DONE),
])
def test_trigger_retry(job_submitfailed, retryfunc, errhow, expt_state):
	job_submitfailed.retry = retryfunc
	jm = Jobmgr([job_submitfailed])
	job_submitfailed.restore_state()
	jm.proc.errhow = errhow
	if expt_state == STATES.ENDFAILED and jm.proc.errhow == 'halt':
		with pytest.raises(JobFailException):
			job_submitfailed.triggerRetry()
	else:
		job_submitfailed.triggerRetry()
	assert job_submitfailed.state == expt_state

def test_trigger_startpoll(job_submitted):
	jm = Jobmgr([job_submitted])
	job_submitted.restore_state()
	job_submitted.triggerStartPoll()
	assert job_submitted.state == STATES.RUNNING

@pytest.mark.parametrize('pollfunc, retryfunc, expt_state', [
	((lambda: 'running'), (lambda: True), STATES.RUNNING),
	((lambda: True), (lambda: False), STATES.DONE),
	((lambda: False), (lambda: True), STATES.BUILT),
	((lambda: False), (lambda: False), STATES.ENDFAILED), # not DONEFAILED, as it goes to retry
])
def test_trigger_poll(job_running, pollfunc, retryfunc, expt_state):
	jm = Jobmgr([job_running])
	job_running.poll = pollfunc
	job_running.retry  = retryfunc
	job_running.restore_state()
	job_running.triggerPoll(batch = 1)
	assert job_running.state == expt_state

def test_trigger_startkill(job_submitted):
	jm = Jobmgr([job_submitted])
	job_submitted.restore_state()
	job_submitted.triggerStartKill()
	assert job_submitted.state == STATES.KILLING

@pytest.mark.parametrize('killfunc, expt_state', [
	((lambda: True), STATES.KILLED),
	((lambda: False), STATES.KILLFAILED),
])
def test_trigger_kill(job_killing, killfunc, expt_state):
	jm = Jobmgr([job_killing])
	job_killing.kill = killfunc
	job_killing.restore_state()
	job_killing.triggerKill()
	assert job_killing.state == expt_state

def test_start_1(job_done):
	jm = Jobmgr([job_done])
	jm.start()

def test_start_all(jobs_all):
	jm = Jobmgr(jobs_all)
	jm.start()

def test_start_all_running(job_done, jobindex_reset):
	jobs = [copy(job_done) for _ in range(20)]
	jobindex_reset(jobs)
	jm = Jobmgr(jobs)
	jm.start()

@pytest.mark.parametrize('pbarsize, expect', [
	(8, [[0],[1],[2],[3],[4],[5],[6],[7]]),
	(4, [[0,1],[2,3],[4,5],[6,7]]),
	(10, [[0],[0],[1],[1],[2],[3],[4],[5],[6],[7]]),
]) # len(jobs_all) == 8
def test_distributejobstopbar(jobs_all, pbarsize, expect):
	jm = Jobmgr(jobs_all)
	jm.pbar_size = pbarsize
	assert jm._distributeJobsToPbar() == expect

