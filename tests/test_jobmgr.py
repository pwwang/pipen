import logging
from copy import copy

import pytest
from transitions.core import MachineError
from pyppl.utils import PQueue
from pyppl.jobmgr import Jobmgr, STATES
from pyppl.exception import JobBuildingError, JobFailError
from pyppl import runner
runner.DEFAULT_POLL_INTERVAL = .1

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
    assert queue_index == [(job.index, job.index) for job in jobs_default]


@pytest.mark.parametrize('exc, expect_msg', [
    (None, []),
    (OSError, []),
    (JobBuildingError, ['Job building failed, quitting pipeline']),
    (JobFailError, ['Error encountered (errhow = halt), quitting pipeline']),
    (KeyboardInterrupt, ['[Ctrl-C] detected, quitting pipeline']),
])
def test_cleanup(jobs_default, caplog, exc, expect_msg):
    jm = Jobmgr(jobs_default)
    if exc and exc not in (JobBuildingError, JobFailError, KeyboardInterrupt):
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
        if job.orig_state in (STATES.SUBMITTING, STATES.RUNNING,
                              STATES.RETRYING):
            assert job.state == STATES.KILLED
        elif job.orig_state in (STATES.BUILT, STATES.DONEFAILED):
            assert job.state == STATES.KILLFAILED
        else:
            assert job.state not in (STATES.KILLED, STATES.KILLFAILED)


@pytest.mark.parametrize('buildfunc, expt_state', [
    ((lambda: 'cached'), STATES.DONECACHED),
    ((lambda: True), STATES.BUILT),
    ((lambda: False), STATES.BUILTFAILED),
])
def test_trigger_build(job_init, buildfunc, expt_state):
    assert job_init.state == STATES.INIT
    job_init.build = buildfunc
    jm = Jobmgr([job_init])
    job_init.restore_state()
    if expt_state == STATES.BUILTFAILED:
        with pytest.raises(JobBuildingError):
            job_init.trigger_build(batch=1)
    else:
        job_init.trigger_build(batch=1)
    assert job_init.state == expt_state


@pytest.mark.parametrize(
    'submitfunc, batch, retryfunc, expt_state',
    [
        ((lambda: True), 1, (lambda: True), STATES.RUNNING),
        ((lambda: True), 4, (lambda: False), STATES.RUNNING),
        ((lambda: False), 1, (lambda: True), STATES.RETRYING),
        ((lambda: False), 1, (lambda: False),
         STATES.ENDFAILED),  # not SUBMITFAILED, as it goes to retry
    ])
def test_trigger_submit(job_built, submitfunc, batch, retryfunc, expt_state):
    jm = Jobmgr([job_built])
    job_built.submit = submitfunc
    job_built.retry = retryfunc
    job_built.restore_state()
    job_built.trigger_submit(batch=batch)
    assert job_built.state == expt_state


@pytest.mark.parametrize('retryfunc, errhow, expt_state', [
    ((lambda: True), 'terminate', STATES.RETRYING),
    ((lambda: True), 'halt', STATES.RETRYING),
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
        with pytest.raises(JobFailError):
            job_submitfailed.trigger_retry(batch=1)
    else:
        job_submitfailed.trigger_retry(batch=1)
    assert job_submitfailed.state == expt_state


@pytest.mark.parametrize(
    'mark, pollfunc, retryfunc, expt_state',
    [
        ('t1', (lambda: True), (lambda: True), STATES.DONE),
        ('t2', (lambda: True), (lambda: False), STATES.DONE),
        ('t3', (lambda: 'running'), (lambda: True), STATES.RUNNING),
        ('t4', (lambda: False), (lambda: False),
         STATES.ENDFAILED),  # not DONEFAILED, as it goes to retry
    ])
def test_trigger_poll(mark, job_running, pollfunc, retryfunc, expt_state):
    jm = Jobmgr([job_running])
    job_running.poll = pollfunc
    job_running.retry = retryfunc
    job_running.restore_state()
    job_running.trigger_poll(batch=1)
    assert job_running.state == expt_state


@pytest.mark.parametrize('killfunc, expt_state', [
    ((lambda: True), STATES.KILLED),
    ((lambda: False), STATES.KILLFAILED),
])
def test_trigger_kill(job_killing, killfunc, expt_state):
    jm = Jobmgr([job_killing])
    job_killing.kill = killfunc
    job_killing.restore_state()
    job_killing.trigger_kill()
    assert job_killing.state == expt_state


def test_start_0():
    assert Jobmgr([]).start() is None


def test_start_1_done(job_done):
    jm = Jobmgr([job_done])
    jm.start()


def test_start_1_init(job_init):
    jm = Jobmgr([job_init])
    jm.start()


# def test_start_5(job_init, job_built, job_retrying, job_running, job_killing, caplog):
# 	jm = Jobmgr([job_init, job_built, job_retrying, job_running, job_killing])
# 	jm.start()
# 	assert '[XXXXXXXXXX                                        ]' in caplog.text


@pytest.mark.parametrize('forks', [1, 4, 10])  # len(jobs_all) == 8
def test_start_all_running(job_done, jobindex_reset, forks, caplog):
    jobs = [copy(job_done) for _ in range(10)]
    jobindex_reset(jobs)
    jobs[0].proc.forks = forks
    jm = Jobmgr(jobs)
    jm.barsize = 10
    jm.start()
    assert '[==========]' in caplog.text


@pytest.mark.parametrize('pbarsize, expect', [
    (8, [[0], [1], [2], [3], [4], [5], [6], [7]]),
    (4, [[0, 1], [2, 3], [4, 5], [6, 7]]),
    (10, [[0], [0], [1], [1], [2], [3], [4], [5], [6], [7]]),
])  # len(jobs_all) == 8
def test_distributejobstopbar(jobs_all, pbarsize, expect):
    from pyppl import jobmgr
    #jobmgr.PBAR_SIZE = pbarsize
    jm = Jobmgr(jobs_all)
    jm.barsize = pbarsize
    assert jm._distribute_jobs_to_pbar() == expect
