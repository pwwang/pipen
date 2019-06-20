import pytest
from psutil import pid_exists
import cmdy
from pyppl import Proc, utils
from pyppl.runners2 import RunnerLocal, RunnerDry

@pytest.fixture
def proc(tmp_path):
	proc = Proc()
	proc.props.workdir = tmp_path / 'test_runner'
	proc.workdir.mkdir()
	return proc

def test_local_kill_isrunning_impl(proc):
	r = RunnerLocal(0, proc)
	assert not r.isRunningImpl()
	r.killImpl()
	assert not pid_exists(r.pid)

	c = cmdy.sleep(10, _bg = True, _raise = False)
	r._pid = c.pid
	assert r.isRunningImpl()
	r.killImpl()
	assert not r.isRunningImpl()

	r._pid = 0
	assert not r.isRunningImpl()

def test_local_submit_impl(proc):

	r = RunnerLocal(0, proc)
	r.dir.mkdir()
	r.script.write_text('sleep 3')

	cmd = r.submitImpl()
	assert r.isRunningImpl()
	assert cmd.rc == 0
	assert r.pid == cmd.pid
	r.killImpl()
	assert not r.isRunningImpl()

def test_dry(proc):
	r = RunnerDry(0, proc)
	r.dir.mkdir()
	(r.dir / 'job.script').write_text('')
	r.output.b = ('dir', 'b.dir') # make output directory first
	r.output.a = ('file', 'a.txt')
	r.wrapScript()

	assert r.script.read_text() == '''#!/usr/bin/env bash
#
# Collect return code on exit
trap "status=\\$?; echo \\$status > '{jobdir}/job.rc'; exit \\$status" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT
#
# Run pre-script

# Dry-run script to create empty output files and directories.

mkdir -p {jobdir}/output/b.dir
touch {jobdir}/output/a.txt

#
# Run the real script
#
# Run post-script
#'''.format(jobdir = r.dir)

	utils.fs.remove(r.dir / 'output' / 'b.dir')
	utils.fs.remove(r.dir / 'output' / 'a.txt')

	cmdy.bash(r.script, _fg = True)

	# check if output file and directory generated
	assert (r.dir / 'output' / 'b.dir').exists()
	assert (r.dir / 'output' / 'a.txt').exists()

