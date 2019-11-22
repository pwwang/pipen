"""
Plugin system for PyPPL
"""
# pylint: disable=unused-argument
import sys
import pluggy
from .exception import PyPPLFuncWrongPositionError

PMNAME = "pyppl"

# pylint: disable=invalid-name
hookimpl = pluggy.HookimplMarker(PMNAME)
hookspec = pluggy.HookspecMarker(PMNAME)

def prerun(func):
	"""@API
	Wrap up method that called before .run()
	"""
	def wrapper(ppl, *args, **kwargs):
		if ppl.procs: # processes has run
			raise PyPPLFuncWrongPositionError(
				'Function %r should be called before .run()' % func.__name__)
		func(ppl, *args, **kwargs)
		return ppl
	return wrapper

def postrun(func):
	"""@API
	Wrap up method that called after .run()
	"""
	def wrapper(ppl, *args, **kwargs):
		if not ppl.procs: # processes has run
			raise PyPPLFuncWrongPositionError(
				'Function %r should be called after .run()' % func.__name__)
		func(ppl, *args, **kwargs)
		return ppl
	return wrapper

def addmethod(ppl, name, method):
	"""@API
	Add method to PyPPL object
	@params:
		ppl (PyPPL): The pipeline object
		name (str): The name of the method
		method (callable): The method
	"""
	def func(*args, **kwargs):
		method(ppl, *args, **kwargs)
		return ppl
	setattr(ppl, name, func)

@hookspec
def setup(config):
	"""Add default configs"""

@hookspec
def procSetAttr(proc, name, value):
	"""Pre-calculate the attribute"""

@hookspec(firstresult=True)
def procGetAttr(proc, name):
	"""Pre-calculate the attribute"""

@hookspec
def procPreRun(proc):
	"""Before a process starts"""

@hookspec
def procPostRun(proc):
	"""After a process has done"""

@hookspec
def procFail(proc):
	"""When a process fails"""

@hookspec
def pypplInit(ppl):
	"""Right after a pipeline initiates"""

@hookspec
def pypplPreRun(ppl):
	"""A set of functions run when pipeline starts"""

@hookspec
def pypplPostRun(ppl):
	"""A set of functions run when pipeline ends"""

@hookspec
def jobPreRun(job):
	"""A set of functions run when job starts"""

@hookspec
def jobPostRun(job):
	"""A set of functions run when job ends"""

@hookspec
def jobFail(job):
	"""A set of function run when job fails"""

@hookspec
def cliAddCommand(commands):
	"""Add command and options to CLI"""

@hookspec
def cliExecCommand(command, opts):
	"""Execute the command being added to CLI"""

pluginmgr = pluggy.PluginManager(PMNAME)
pluginmgr.add_hookspecs(sys.modules[__name__])
pluginmgr.load_setuptools_entrypoints(PMNAME)

def registerPlugins(plugins, default_plugins = None):
	"""
	Register plugins.
	"""
	if plugins is None:
		return
	default_plugins = default_plugins or []
	# register 3rd-party plugins first, so that 3rd-party plugins have higher priorty
	# Queue is FIFO
	for plugin in default_plugins:
		pluginmgr.register(__import__(plugin))
	for plugin in plugins:
		if plugin not in default_plugins:
			pluginmgr.register(__import__(plugin))
