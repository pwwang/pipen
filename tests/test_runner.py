import os
import pytest
from pathlib import Path
from psutil import pid_exists
import cmdy
from pyppl import Proc, utils, Box
from pyppl.runner import RunnerLocal, RunnerDry, RunnerSsh, RunnerSge, RunnerSlurm, RC_ERROR_SUBMISSION
from pyppl.exception import RunnerSshError
from pyppl.template import TemplateLiquid

@pytest.fixture(scope='function')
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

@pytest.fixture
def ssh():
	return str(Path(__file__).parent / 'mocks' / 'ssh')

@pytest.fixture
def sge():
	return Box(
		qsub  = str(Path(__file__).parent / 'mocks' / 'qsub'),
		qstat = str(Path(__file__).parent / 'mocks' / 'qstat'),
		qdel  = str(Path(__file__).parent / 'mocks' / 'qdel'),
	)

@pytest.fixture
def slurm():
	return Box(
		sbatch  = str(Path(__file__).parent / 'mocks' / 'sbatch'),
		srun    = str(Path(__file__).parent / 'mocks' / 'srun'),
		squeue  = str(Path(__file__).parent / 'mocks' / 'squeue'),
		scancel = str(Path(__file__).parent / 'mocks' / 'scancel'),
	)

@pytest.fixture(autouse=True)
def resetliveservers():
	RunnerSsh.LIVE_SERVERS = None

@pytest.mark.parametrize('server,key,timeout,expt', [
	('host', 'host1', 0, False),
	('host', 'host', 0, True),
	('host', '', 0, True),
	('host', 'host+0', 0, True),
	('host', 'host+0.3', 0.1, False),
])
def test_ssh_isserveralive(server, key, timeout, expt, ssh):
	assert RunnerSsh.isServerAlive(server, key, timeout = timeout, ssh = ssh) == expt

def test_ssh_init(proc, ssh):
	proc.sshRunner = Box(
		ssh = ssh,
		servers = ['server1', 'server2', 'server3', 'server4'],
		keys = ['server1', 'server2', 'server3', 'wrongkey'],
		checkAlive = True)
	r = RunnerSsh(0, proc)
	assert RunnerSsh.LIVE_SERVERS == [0,1,2]
	assert r.ssh.keywords['t'] == 'server1'

def test_ssh_init_noserver(proc, ssh):
	proc.sshRunner = Box(
		ssh = ssh,
		servers = [],
		keys = ['server1', 'server2', 'server3', 'wrongkey'],
		checkAlive = True)
	with pytest.raises(RunnerSshError):
		RunnerSsh(0, proc)

def test_ssh_init_nolive(proc, ssh):
	proc.sshRunner = Box(
		ssh = ssh,
		servers = ['a', 'b', 'c', 'd'],
		keys = ['server1', 'server2', 'server3', 'wrongkey'],
		checkAlive = True)
	with pytest.raises(RunnerSshError):
		RunnerSsh(0, proc)

def test_ssh_init_nocheck(proc, ssh):
	proc.sshRunner = Box(
		ssh = ssh,
		servers = ['server1', 'server2', 'server3', 'server4'],
		keys = ['server1', 'server2', 'server3', 'wrongkey'],
		checkAlive = False)
	r = RunnerSsh(0, proc)
	assert RunnerSsh.LIVE_SERVERS == [0,1,2,3]
	assert r.ssh.keywords['t'] == 'server1'

def test_ssh_init_checktimeout(proc, ssh):
	proc.sshRunner = Box(
		ssh = ssh,
		servers = ['server1', 'server2', 'server3', 'server4'],
		keys = ['server1', 'server2', 'server3+1.5', 'wrongkey'],
		checkAlive = 1)
	r = RunnerSsh(0, proc)
	assert RunnerSsh.LIVE_SERVERS == [0,1]
	assert r.ssh.keywords['t'] == 'server1'

def test_ssh_scriptparts(proc):
	proc.sshRunner = Box(
		ssh = ssh,
		servers = ['server1'],
		checkAlive = False)
	r = RunnerSsh(0, proc)
	r.dir.mkdir()
	(r.dir / 'job.script').write_text('#!/usr/bin/env bash')
	r.script.write_text('#!/usr/bin/env bash')
	assert r.scriptParts.header == '#\n# Running job on server: server1\n#'
	assert r.scriptParts.pre == "\ncd %s" % cmdy._shquote(os.getcwd())
	assert r.scriptParts.post == ''
	assert r.scriptParts.saveoe == True
	assert r.scriptParts.command == [str(r.dir / 'job.script')]

def test_ssh_impl(proc, ssh):
	proc.sshRunner = Box(
		ssh = ssh,
		servers = ['server1'],
		checkAlive = False)
	r = RunnerSsh(0, proc)
	assert not r.isRunningImpl()
	dbox = r.submitImpl()
	assert dbox.rc == RC_ERROR_SUBMISSION
	assert dbox.pid == -1
	assert 'is not using the same file system as the local machine' in dbox.stderr

	r.dir.mkdir()
	r.script.write_text('#!/usr/bin/env bash\nsleep 3')
	cmd = r.submitImpl()
	assert cmd.rc == 0
	assert r.pid == cmd.pid
	assert r.isRunningImpl()
	r.killImpl()
	assert not r.isRunningImpl()

def test_sge_init(proc, sge):
	proc.sgeRunner = sge.copy()
	proc.sgeRunner.preScript = 'ls'
	proc.sgeRunner['sge.notify'] = True
	proc.sgeRunner['sge.N'] = 'Jobname{{job.index}}'
	proc.props.template = TemplateLiquid
	r = RunnerSge(0, proc)
	r.dir.mkdir()
	(r.dir / 'job.script').write_text('#!/usr/bin/env bash')
	parts = r.scriptParts
	assert parts.saveoe == False
	assert parts.header == '''#$ -N Jobname0
#$ -cwd
#$ -o {jobdir}/job.stdout
#$ -e {jobdir}/job.stderr
#$ -notify
'''.format(jobdir = r.dir)
	assert parts.pre == 'ls'
	assert parts.post == ''

def test_sge_init_error(proc, sge):
	proc.sgeRunner = sge.copy()
	proc.sgeRunner['sge.cwd'] = True
	proc.props.template = TemplateLiquid
	r = RunnerSge(0, proc)
	r.dir.mkdir()
	(r.dir / 'job.script').write_text('#!/usr/bin/env bash')
	with pytest.raises(ValueError):
		r.scriptParts

def test_sge_impl(proc, sge):
	proc.sgeRunner = sge.copy()
	r = RunnerSge(0, proc)
	assert not r.isRunningImpl()
	r.dir.mkdir()
	r.script.write_text('#!/usr/bin/env bash\n#$ -N Jobname1\nsleep 3')
	r.submitImpl()
	assert r.isRunningImpl()
	r.killImpl()
	assert not r.isRunningImpl()

	# fail
	r.script.write_text('#!/usr/bin/env bash\n# ShouldFail\n#$ -N Jobname1\nsleep 3')
	cmd = r.submitImpl()
	assert cmd.rc == RC_ERROR_SUBMISSION

def test_slurm_init(proc, slurm):
	proc.slurmRunner = slurm.copy()
	proc.slurmRunner.preScript = 'ls'
	# need a number, just testing the boolean options
	proc.slurmRunner['slurm.ntasks'] = True
	proc.slurmRunner['slurm.x'] = 1
	proc.slurmRunner['srun.opts'] = '-n8 --mpi=pmix_v1'
	proc.slurmRunner['slurm.J'] = 'Jobname{{job.index}}'
	proc.props.template = TemplateLiquid
	r = RunnerSlurm(0, proc)
	r.dir.mkdir()
	(r.dir / 'job.script').write_text('#!/usr/bin/env bash')
	parts = r.scriptParts
	assert parts.saveoe == False
	assert parts.header == '''#SBATCH -J Jobname0
#SBATCH -o {jobdir}/job.stdout
#SBATCH -e {jobdir}/job.stderr
#SBATCH --ntasks
#SBATCH -x 1
'''.format(jobdir = r.dir)
	assert parts.pre == 'ls'
	assert parts.post == ''
	assert parts.command == '%s -n8 --mpi=pmix_v1 %s' % (slurm.srun, (r.dir / 'job.script'))

def test_slurm_init_error(proc, slurm):
	proc.slurmRunner = slurm.copy()
	proc.slurmRunner['slurm.o'] = '/path/to/stdout'
	proc.props.template = TemplateLiquid
	r = RunnerSlurm(0, proc)
	r.dir.mkdir()
	(r.dir / 'job.script').write_text('#!/usr/bin/env bash')
	with pytest.raises(ValueError):
		r.scriptParts

def test_slurm_impl(proc, slurm):
	proc.slurmRunner = slurm.copy()
	r = RunnerSlurm(0, proc)
	assert not r.isRunningImpl()
	r.dir.mkdir()
	r.script.write_text('#!/usr/bin/env bash\n#SBATCH -J Jobname1\nsleep 3')
	r.submitImpl()
	assert r.isRunningImpl()
	r.killImpl()
	assert not r.isRunningImpl()

	# fail
	r.script.write_text('#!/usr/bin/env bash\n# ShouldFail\n#SBATCH -J Jobname1\nsleep 3')
	cmd = r.submitImpl()
	assert cmd.rc == RC_ERROR_SUBMISSION