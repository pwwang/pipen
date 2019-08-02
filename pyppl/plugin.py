import sys
import pluggy
from .exception import PyPPLFuncWrongPositionError

PMNAME = "pyppl"

hookimpl = pluggy.HookimplMarker(PMNAME)
hookspec = pluggy.HookspecMarker(PMNAME)

def prerun(func):
	def wrapper(ppl, *args, **kwargs):
		if ppl.procs: # processes has run
			raise PyPPLFuncWrongPositionError(
				'Function %r should be called before .run()' % func.__name__)
		func(ppl, *args, **kwargs)
		return ppl
	return wrapper

def postrun(func):
	def wrapper(ppl, *args, **kwargs):
		if not ppl.procs: # processes has run
			raise PyPPLFuncWrongPositionError(
				'Function %r should be called after .run()' % func.__name__)
		func(ppl, *args, **kwargs)
		return ppl
	return wrapper

def addmethod(ppl, name, method):
	def func(*args, **kwargs):
		method(ppl, *args, **kwargs)
	setattr(ppl, name, func)

@hookspec
def setup(config):
	"""Add default configs"""

@hookspec
def procSetAttr(proc, name, value):
	"""Pre-calculate the attribute"""
	proc.config[name] = value
	return True

@hookspec(firstresult=True)
def procGetAttr(proc, name):
	"""Pre-calculate the attribute"""
	return proc.props.get(name, proc.config.get(name))

@hookspec
def procPreRun(proc):
	"""After a process starts"""

@hookspec
def procPostRun(proc):
	"""After a process has done"""

@hookspec
def procFail(proc):
	"""When a process fails"""

@hookspec
def pypplInit(ppl):
	"""A set of functions run before all processes start"""

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

pluginmgr = pluggy.PluginManager(PMNAME)
pluginmgr.add_hookspecs(sys.modules[__name__])
pluginmgr.load_setuptools_entrypoints(PMNAME)

def registerPlugins(plugins, default_plugins):
	# register 3rd-party plugins first, so that 3rd-party plugins have higher priorty
	# Queue is LIFO
	for plugin in reversed(plugins):
		if plugin not in default_plugins:
			pluginmgr.register(__import__(plugin))
	for plugin in reversed(default_plugins):
		pluginmgr.register(__import__(plugin))
