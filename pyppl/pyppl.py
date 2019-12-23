"""Pipeline for PyPPL"""
# give random tips in the log
import random
import time
import textwrap
import fnmatch
from simpleconf import Config
from .config import config as default_config, DEFAULT_CFGFILES
from .logger import logger
from .plugin import pluginmgr, config_plugins
from .runner import RUNNERS
from .exception import PyPPLInvalidConfigurationKey, PyPPLNameError, \
	ProcessAlreadyRegistered
from .utils import try_deepcopy, format_secs, name2filename, fs

# length of separators in log
SEPARATOR_LEN = 80
# Regiester processes
PROCESSES = set()
# tips
TIPS = [
	"You can find the stdout in <workdir>/<job.index>/job.stdout",
	"You can find the stderr in <workdir>/<job.index>/job.stderr",
	"You can find the script in <workdir>/<job.index>/job.script",
	"Check documentation at: https://pyppl.readthedocs.io/en/latest/",
	"You cannot have two processes with the same id and tag",
	"beforeCmd and afterCmd only run locally",
	"Workdir defaults to PyPPL.<id>.<tag>.<suffix> under default <ppldir>",
	"The default <ppldir> is './workdir'"]

# name of defined pipelines
PIPELINES = {}

def register_proc(proc):
	"""Register process into the pool"""
	for registered_proc in PROCESSES:
		if registered_proc.name == proc.name and registered_proc is not proc:
			raise ProcessAlreadyRegistered(proc1 = registered_proc, proc2 = proc)
	PROCESSES.add(proc)

def get_next_procs(procs):
	"""Get next possible processes to run"""
	nextprocs = [nextproc
		for proc in procs if proc.nexts
		for nextproc in proc.nexts
			if nextproc not in procs and all(depend in procs for depend in nextproc.depends)]
	ret = []
	for nproc in nextprocs:
		if nproc not in ret:
			ret.append(nproc)
	return ret

def anything2procs(*anything, procset = 'starts'):
	"""Translate anything to a list of processes
	It actually serves as a process selector.
	Keep in mind that the order of the processes is not guaranteed.
	"""
	from .proc import Proc
	from .procset import ProcSet, Proxy
	ret = Proxy()
	for anyth in anything:
		if isinstance(anyth, Proc):
			ret.add(anyth)
		elif isinstance(anyth, ProcSet):
			ret.add(anyth.starts if procset == 'starts' else anyth.ends)
		elif isinstance(anyth, (tuple, list)):
			for thing in anyth:
				ret.add(anything2procs(thing))
		else:
			for proc in PROCESSES:
				if anyth in (proc.id, proc.shortname, proc.name):
					ret.add(proc)
				elif fnmatch.fnmatch(proc.shortname, anyth):
					ret.add(proc)
	return ret

def _logo():
	from . import __version__
	logger.pyppl('+' + r'-' * (SEPARATOR_LEN-2) + '+')
	logger.pyppl('|' + r''.center(SEPARATOR_LEN-2) + '|')
	logger.pyppl('|' + r'________        ______________________ '.center(SEPARATOR_LEN-2) + '|')
	logger.pyppl('|' + r'___  __ \____  ____  __ \__  __ \__  / '.center(SEPARATOR_LEN-2) + '|')
	logger.pyppl('|' + r'__  /_/ /_  / / /_  /_/ /_  /_/ /_  /  '.center(SEPARATOR_LEN-2) + '|')
	logger.pyppl('|' + r'_  ____/_  /_/ /_  ____/_  ____/_  /___'.center(SEPARATOR_LEN-2) + '|')
	logger.pyppl('|' + r'/_/     _\__, / /_/     /_/     /_____/'.center(SEPARATOR_LEN-2) + '|')
	logger.pyppl('|' + r'        /____/                         '.center(SEPARATOR_LEN-2) + '|')
	logger.pyppl('|' + r'v{}'.format(__version__).center(SEPARATOR_LEN-2) + '|')
	logger.pyppl('|' + r''.center(SEPARATOR_LEN-2) + '|')
	logger.pyppl('+' + r'-' * (SEPARATOR_LEN-2) + '+')
	logger.tips(random.choice(TIPS))
	for cfgfile in DEFAULT_CFGFILES:
		if fs.exists(cfgfile) or str(cfgfile).endswith('.osenv'):
			logger.config('Read from %s', cfgfile)
	for plug, plugin in pluginmgr.list_name_plugin():
		logger.plugin('Loaded plugin: %s (v%s)',
			plug, plugin.__version__ if hasattr(plugin, '__version__') else 'Unknown')
	for rname, rplugin in RUNNERS.items():
		logger.plugin('Loaded runner: %s (v%s)',
			rname, rplugin.__version__ if hasattr(rplugin, '__version__') else 'Unknown')

class PyPPL:
	"""The class for the whole pipeline"""
	# allow adding methods
	__slots__ = 'name', 'runtime_config', 'procs', 'starts', 'ends', '__dict__'

	def __init__(self, config = None, name = None, config_files = None, **kwconfigs):
		# check if keys in kwconfigs are valid
		config = config or {}
		config.update(kwconfigs)
		for key in config:
			if key not in default_config:
				raise PyPPLInvalidConfigurationKey('No such configuration key: ' + key)

		self.name = name or 'PyPPL_{}'.format(len(PIPELINES) + 1)
		filename = name2filename(self.name)
		if filename in PIPELINES:
			raise PyPPLNameError(
				'Pipeline name {!r}({!r}) has been used.'.format(self.name, filename))
		PIPELINES[filename] = self

		self.runtime_config = Config()
		self.runtime_config._load(dict(default = config, *(config_files or ())))

		logger_config = try_deepcopy(default_config.logger.dict())
		logger_config.update(self.runtime_config.pop('logger', {}))
		if logger_config['file'] is True:
			logger_config['file'] = './{}.pyppl.log'.format(filename)
		logger.init(logger_config)
		del logger_config

		plugin_config = self.runtime_config.pop('plugins', [])
		config_plugins(*plugin_config)

		_logo()
		logger.pyppl('~' * SEPARATOR_LEN)
		logger.pyppl('PIPELINE: {}'.format(self.name))
		#logger.pyppl('+' * SEPARATOR_LEN)

		self.procs  = []
		self.starts = []
		self.ends   = []
		pluginmgr.hook.pyppl_init(ppl = self)

	def run(self, profile = 'default'):
		"""@API
		Run the pipeline with certain profile
		@params:
			profile (str): The profile name
		"""
		timer = time.time()
		ret = pluginmgr.hook.pyppl_prerun(ppl = self)

		# plugins can stop pipeling being running
		if ret is not False:
			with default_config._with(profile = profile, copy = True) as defconfig:
				defconfig._load(self.runtime_config)
				defconfig._use(profile, raise_exc = True)
				del defconfig.logger
				del defconfig.plugins
				for proc in self.procs:
					# print process name and description
					name = proc.shortname
					if proc.origin and proc.origin != proc.id:
						name += ' ({})'.format(proc.origin)
					name += ': '
					lines = textwrap.wrap(name + proc.desc, SEPARATOR_LEN,
						subsequent_indent = ' ' * len(name))
					decorlen = max(SEPARATOR_LEN, max(len(line) for line in lines))
					logger.process('-' * decorlen)
					for line in lines:
						logger.process(line)
					logger.process('-' * decorlen)

					# print dependencies
					logger.depends('%s => %s => %s',
						[dproc.shortname for dproc in proc.depends] if proc.depends else 'START',
						proc.name,
						[nproc.shortname for nproc in proc.nexts] if proc.nexts else 'END')
					proc.run(defconfig)

		pluginmgr.hook.pyppl_postrun(ppl = self)
		logger.done('Total time: %s', format_secs(time.time() - timer))
		return self

	def start(self, *anything):
		"""Set the start processes for the pipeline"""
		del self.procs[:]
		del self.starts[:]
		del self.ends[:]

		self.starts = anything2procs(*anything)
		# Let's check if start process depending on others
		for start in self.starts:
			if start.depends:
				logger.warning('Start process %r is depending on others: %r',
					start, start.depends)

		self.procs  = self.starts[:]
		# fetch all procs depending on starts in the order that they will be excuted.
		nexts = get_next_procs(self.procs)
		if not nexts:
			for proc in self.procs:
				self.ends.append(proc)
				if proc.nexts:
					logger.warning(
						"%r will not run, as they depend on non-start processes or themselves.",
						proc.nexts)
			return self

		while nexts:
			for nextproc in nexts:
				self.procs.append(nextproc)
				if not nextproc.nexts:
					self.ends.append(nextproc)
			nexts = get_next_procs(self.procs)
		return self

	def method(self, func):
		"""Add a method to PyPPL object"""
		def wrapper(*args, **kwargs):
			func(self, *args, **kwargs)
			return self
		self.__dict__[func.__name__] = wrapper
