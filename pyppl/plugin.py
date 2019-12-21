"""
Plugin system for PyPPL
"""
# pylint: disable=unused-argument
import sys
import types
import pluggy
from .exception import PyPPLPluginWrongPositionFunction, PluginConfigKeyError, PluginNoSuchPlugin, PluginWrongPluginType

PMNAME = "pyppl"

# pylint: disable=invalid-name
hookimpl = pluggy.HookimplMarker(PMNAME)
hookspec = pluggy.HookspecMarker(PMNAME)

@hookspec
def setup(config):
	"""Add default configs"""

@hookspec
def proc_init(proc):
	"""At the end of __init__"""

@hookspec(firstresult = True)
def proc_prerun(proc):
	"""Before a process starts"""

@hookspec
def proc_postrun(proc):
	"""After a process has done"""

@hookspec
def proc_fail(proc):
	"""When a process fails"""

@hookspec
def pyppl_init(ppl):
	"""Right after a pipeline initiates"""

@hookspec(firstresult = True)
def pyppl_prerun(ppl):
	"""A set of functions run when pipeline starts"""

@hookspec
def pyppl_postrun(ppl):
	"""A set of functions run when pipeline ends"""

@hookspec
def job_init(job):
	"""Right after job initiates"""

@hookspec
def job_is_successed(job, status):
	"""Tell if job is successfully done or not
	One can add not rigorous check. By default, only
	if returncode is 0 checked.
	return False to tell if job is failed otherwise
	use the default status or results from other plugins
	"""

@hookspec
def job_build(job, status):
	"""A set of functions run when job starts"""

@hookspec
def job_submit(job, status):
	"""A set of functions run when job starts"""

@hookspec
def job_poll(job, status):
	"""A set of functions run when job ends"""

@hookspec
def job_kill(job, status):
	"""A set of function run when job fails"""

@hookspec
def job_done(job, status):
	"""A set of function run when job fails"""

@hookspec
def cli_addcmd(commands):
	"""Add command and options to CLI"""

@hookspec
def cli_execcmd(command, opts):
	"""Execute the command being added to CLI"""

pluginmgr = pluggy.PluginManager(PMNAME)
pluginmgr.add_hookspecs(sys.modules[__name__])
pluginmgr.load_setuptools_entrypoints(PMNAME)

def _get_plugin(name):
	"""
	Try to find the plugin by name with/without prefix.
	If the plugin is not found, try to treat it as a module and import it
	"""
	if isinstance(name, str):
		for plugin in pluginmgr.get_plugins():
			plname = pluginmgr.get_name(plugin)
			if	plname == 'pyppl-' + name or \
				plname == 'pyppl_' + name or \
				plname == 'PyPPL' + name.capitalize():
				return plugin
		if name[:6] not in ('pyppl-', 'pyppl_'):
			name = 'pyppl-' + name
		try:
			return __import__(name)
		except ImportError as exc:
			raise PluginNoSuchPlugin(name) from exc
	return name

def disable_plugin(plugin):
	plugin = _get_plugin(plugin)
	if pluginmgr.is_registered(plugin):
		pluginmgr.unregister(plugin)

def config_plugins(*plugins):
	for plugin in plugins:
		if isinstance(plugin, str) and plugin[:3] == 'no:':
			try:
				disable_plugin(_get_plugin(plugin[3:]))
			except PluginNoSuchPlugin:
				pass
		else:
			plugin = _get_plugin(plugin)
			if not isinstance(plugin, types.ModuleType) and isinstance(plugin, type):
				raise PluginWrongPluginType('Expect a module or an instance of a class as a plugin, not a type/class.')
			if not pluginmgr.is_registered(plugin):
				if isinstance(plugin, types.ModuleType):
					pluginmgr.register(plugin)
				else:
					pluginmgr.register(plugin, name = plugin.__class__.__name__)

class PluginConfig(dict):

	def __init__(self, pconfig = None):
		self.__dict__['__raw__'] = {}
		self.__dict__['__cache__'] = {}
		self.__dict__['__converter__'] = {}
		self.__dict__['__setcounter__'] = {}
		self.__dict__['__update__'] = {}
		pconfig = pconfig or {}
		for key, val in pconfig.items():
			self.add(key, val)

	def add(self, name, default = None, converter = None, update = 'update'):
		"""
		Add a config item
		@params:
			name (str): The name of the config item.
			default (any): The default value
			converter (callable): The converter to convert the value whenever the value is set.
			update (str): With setcounter > 1, should we update the value or ignore it in .update()?
				- if value is not a dictionary, update will just replace the value.
		"""
		self.__raw__[name] = default
		self.__converter__[name] = converter
		self.__setcounter__[name] = 0
		self.__update__[name] = update
		return self

	def update(self, pconfig):
		for key, value in pconfig.items():
			if key not in self.__raw__:
				raise PluginConfigKeyError('Plugin configuration {!r} does not exist.'.format(key))
			if self.__update__[key] == 'ignore' and self.__setcounter__[key] > 0:
				continue

			if key in self.__cache__:
				del self.__cache__[key]
			if isinstance(value, dict) and isinstance(self.__raw__[key], dict):
				self.__raw__[key].update(value)
			else:
				self.__raw__[key] = value

	def setcounter(self, name):
		return self.__setcounter__.get(name, 0)

	def __getattr__(self, name):
		if name in self.__cache__:
			return self.__cache__[name]
		if self.__converter__.get(name):
			value = self.__converter__[name](self.__raw__[name])
			self.__cache__[name] = value
			return value
		return self.__raw__[name]

	def __setattr__(self, name, value):
		if name in self.__cache__:
			del self.__cache__[name]
		self.__setcounter__[name] = self.__setcounter__.setdefault(name, 0) + 1
		self.__raw__[name] = value

	__getitem__ = __getattr__
	__setitem__ = __setattr__
