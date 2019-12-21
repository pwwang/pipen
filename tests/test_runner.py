import pytest
import types
import cmdy
from pyppl.runner import register_runner, use_runner, current_runner, hookimpl, RUNNERS, runnermgr, _runner_name
from pyppl.exception import RunnerNoSuchRunner, RunnerMorethanOneRunnerEnabled, RunnerTypeError

class PyPPLRunnerTest1:

	@hookimpl
	def kill(self, job):
		pass

	@hookimpl
	def submit(self, job):
		pass

	@hookimpl
	def isrunning(self, job):
		pass

class PyPPLRunnerTest2(PyPPLRunnerTest1):
	pass

class PyPPLRunnerModule(types.ModuleType, PyPPLRunnerTest1):
	pass

class pyppl_runner_xrunner(PyPPLRunnerTest1):
	pass

@pytest.mark.parametrize('obj,name', [
	(PyPPLRunnerTest1, 'test1'),
	(PyPPLRunnerModule, 'module'),
	(pyppl_runner_xrunner, 'xrunner'),
])
def test_runner_name(obj, name):
	assert _runner_name(obj) == name

def test_x_runner():
	assert current_runner() == 'local'
	with pytest.raises(RunnerNoSuchRunner):
		use_runner('test1')
	test1runner = PyPPLRunnerTest1()
	register_runner(test1runner)
	with pytest.raises(RunnerMorethanOneRunnerEnabled):
		current_runner()

	use_runner('test1')
	assert current_runner() == 'test1'

	with pytest.raises(RunnerNoSuchRunner):
		use_runner('test2')

	with pytest.raises(RunnerTypeError):
		register_runner(PyPPLRunnerTest1())

	register_runner(test1runner)

	register_runner(PyPPLRunnerTest2())
	with pytest.raises(RunnerMorethanOneRunnerEnabled):
		current_runner()
	use_runner('test2')
	assert current_runner() == 'test2'

	use_runner('local')
	assert current_runner() == 'local'

	runnermgr.unregister(list(runnermgr.get_plugins())[0])
	with pytest.raises(RunnerNoSuchRunner):
		current_runner()

	register_runner(test1runner)
	del RUNNERS['test1']
	with pytest.raises(RunnerNoSuchRunner):
		current_runner()
	register_runner(test1runner)

# start testing hooks

class Job:

	def __init__(self, pid = 0, script = ['ls']):
		self.pid = pid
		self.script = script

class Action:

	def __init__(self, job):
		self.job = job

	def isrunning(self):
		return runnermgr.hook.isrunning(job = self.job)

	def kill(self):
		return runnermgr.hook.kill(job = self.job)

	def submit(self):
		return runnermgr.hook.submit(job = self.job)

	def script_parts(self):
		return runnermgr.hook.script_parts(job = self.job)

def test_hook():
	use_runner('local')
	action = Action(Job())
	assert not action.isrunning()
	assert action.kill()
	assert action.submit().cmd == 'bash -c ls'
	assert action.script_parts() is None

def test_hook2():
	import os
	use_runner('local')
	action = Action(Job(pid = os.getpid()))

	assert action.isrunning()
	assert action.submit().cmd == 'bash -c ls'
	assert action.script_parts() is None

def test_hook_kill():
	from psutil import pid_exists
	p = cmdy.sleep(100, _bg = True)
	assert pid_exists(p.pid)

	job = Job(pid = p.pid)
	action = Action(job)

	assert action.isrunning()
	assert job.pid == p.pid
	assert action.submit().cmd == 'bash -c ls'
	job.pid = p.pid
	assert action.script_parts() is None
	assert action.kill()
	assert not pid_exists(p.pid)

