"""
Make runners as plugins for PyPPL
"""
# pylint: disable=unused-argument,invalid-name
import sys
import pluggy
import psutil
from .exception import RunnerNoSuchRunner, RunnerMorethanOneRunnerEnabled, RunnerTypeError

PMNAME = "pyppl-runner"
# save all runners ever registered
RUNNERS = {}
# poll interval to check job status
DEFAULT_POLL_INTERVAL = 1

hookimpl = pluggy.HookimplMarker(PMNAME)
hookspec = pluggy.HookspecMarker(PMNAME)

@hookspec(firstresult = True)
def isrunning(job):
	"""Tell if the job is running"""

@hookspec(firstresult = True)
def submit(job):
	"""Submit the job"""

@hookspec(firstresult = True)
def kill(job):
	"""Try to kill the job"""

@hookspec(firstresult = True)
def script_parts(job):
	"""Overwrite script parts"""

runnermgr = pluggy.PluginManager(PMNAME)
runnermgr.add_hookspecs(sys.modules[__name__])
runnermgr.load_setuptools_entrypoints(PMNAME)

def _runner_name(runner):
	if hasattr(runner, '__name__'):
		name = runner.__name__
	else:
		name = runner.__class__.__name__

	if name[:13] in ('pyppl_runner_', 'pyppl-runner-'):
		name = name[13:]
	elif name[:11] == 'PyPPLRunner':
		name = name[11:].lower()
	return name

def use_runner(runner):
	"""
	runner should be a module or the name of a module, with or without "pyppl_runner_" prefix
	To enable a runner, we need to disable other runners
	"""
	if runner not in RUNNERS:
		raise RunnerNoSuchRunner(runner)
	for plugin in RUNNERS.values():
		if _runner_name(plugin) == runner:
			if not runnermgr.is_registered(plugin):
				runnermgr.register(plugin)
		elif runnermgr.is_registered(plugin):
			runnermgr.unregister(plugin)
	assert len(runnermgr.get_plugins()) == 1, \
		'One runner is allow at a time. We have {}'.format(runnermgr.get_plugins())

def current_runner():
	all_runners = list(runnermgr.get_plugins())
	if len(all_runners) > 1:
		raise RunnerMorethanOneRunnerEnabled(str(all_runners))
	if not all_runners:
		raise RunnerNoSuchRunner('No runners registered.')

	for name, plugin in RUNNERS.items():
		if plugin is all_runners[0]:
			return name
	raise RunnerNoSuchRunner('No runners registered.')

def poll_interval():
	runner = RUNNERS[current_runner()]
	if hasattr(runner, 'POLL_INTERVAL'):
		return int(runner.POLL_INTERVAL)
	return DEFAULT_POLL_INTERVAL

def register_runner(runner, name = None):
	name = name or _runner_name(runner)
	if not runnermgr.is_registered(runner):
		# we only allow an object from one class to be registered once
		for plugin in runnermgr.get_plugins():
			if _runner_name(plugin) == name:
				raise RunnerTypeError('Runner %r has already been registered.' % (name))
		else:
			runnermgr.register(runner, name = name)
	RUNNERS[name] = runner

class PyPPLRunnerLocal:

	@hookimpl
	def kill(self, job):
		"""
		Try to kill the running jobs if I am exiting
		"""
		if int(job.pid) > 0:
			myself = psutil.Process(int(job.pid))
			children = myself.children(recursive=True)
			children.append(myself)
			for proc in children:
				proc.send_signal(9)

			return psutil.wait_procs(children)
		return True

	@hookimpl
	def submit(self, job):
		"""
		Try to submit the job
		"""
		import cmdy
		cmd = cmdy.bash(c = job.script, _raise = False, _bg = True)
		cmd.rc = 0
		job.pid = cmd.pid
		return cmd

	@hookimpl
	def isrunning(self, job):
		"""
		Try to tell whether the job is still running.
		@returns:
			`True` if yes, otherwise `False`
		"""
		if not job.pid or int(job.pid) < 0:
			return False
		return psutil.pid_exists(int(job.pid))

register_runner(PyPPLRunnerLocal())
