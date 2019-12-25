"""Process for PyPPL"""
from functools import partial
from pathlib import Path
import sys
import traceback
import attr
import toml
from diot import Diot
from attr_property import attr_property, attr_property_class
from varname import varname
from ._proc import proc_depends_setter, proc_input, proc_output, proc_script, \
	proc_suffix, proc_lang, proc_name, proc_shortname, proc_jobs, proc_size, \
	proc_runner, proc_template, proc_workdir, proc_input_setter, \
	proc_runtime_config_setter, proc_id_setter, proc_tag_setter, \
	proc_channel, proc_procset, proc_setter_count
from .utils import try_deepcopy, brief_list
from .config import config as default_config
from .logger import logger
from .jobmgr import STATES, Jobmgr
from .plugin import pluginmgr, PluginConfig
from .runner import runnermgr
from .pyppl import _register_proc

@attr_property_class
@attr.s(eq = False, slots = True)
class Proc:
	"""@API
	Process of a pipeline
	"""
	# pylint: disable=too-many-instance-attributes
	# Remember the attr being set, they have the highest priority
	_setcounter = attr.ib(
		default = attr.Factory(dict),
		init    = False,
		repr    = False)
	# The id of the process
	id = attr_property(
		default = attr.Factory(lambda: varname(caller = 2, context = 30)),
		repr    = False,
		setter  = proc_id_setter,
		doc     = "@API\nThe identity of the process")
	# The tag of the process
	tag = attr_property(
		default = default_config.tag,
		setter  = proc_tag_setter,
		kw_only = True,
		repr    = False,
		doc     = "@API\nThe tag of the process")
	# The description of the process
	desc = attr.ib(
		default = 'No description.',
		kw_only = True,
		repr    = False)
	# The args of the process
	args = attr.ib(
		default = attr.Factory(Diot),
		kw_only = True,
		repr    = False)
	# caching
	cache = attr_property(
		default = default_config.cache,
		kw_only = True,
		repr    = False,
		setter  = partial(proc_setter_count, name = 'cache'),
		doc     = '@API\nShould we cache the results or read results from cache?')
	# The output channel
	channel = attr_property(
		default = None,
		init    = False,
		repr    = False,
		getter  = proc_channel)
	# Save the definitions to indicate you when you have 2
	# processes with the same id and tag defined
	_defs = attr.ib(
		default = attr.Factory(lambda: traceback.format_stack()[-3]),
		init    = False,
		repr    = False)
	# the dependencies of the process
	depends = attr_property(
		default = attr.Factory(list),
		kw_only = True,
		repr    = False,
		setter  = proc_depends_setter, raw = '_')
	# dirsig
	dirsig = attr_property(
		default = default_config.dirsig,
		kw_only = True,
		repr    = False,
		setter  = partial(proc_setter_count, name = 'dirsig'))
	# envs used to render templates
	envs = attr.ib(
		default = try_deepcopy(default_config.envs),
		kw_only = True,
		repr    = False)
	# how to deal with errors
	errhow = attr_property(
		default = default_config.errhow,
		kw_only = True,
		repr    = False,
		setter  = partial(proc_setter_count, name = 'errhow'))
	# how many times to retry if errored
	errntry = attr_property(
		default = default_config.errntry,
		kw_only = True,
		repr    = False,
		setter  = partial(proc_setter_count, name = 'errntry'))
	# forks
	forks = attr_property(
		default           = default_config.forks,
		converter         = int,
		converter_runtime = True,
		kw_only           = True,
		repr              = False,
		setter            = partial(proc_setter_count, name = 'forks'))
	# input of the process
	input = attr_property(
		default = None,
		kw_only = True,
		getter  = proc_input,
		setter  = proc_input_setter,
		repr    = False,
		raw     = '_')
	# jobs
	jobs = attr_property(
		default = attr.Factory(list),
		init    = False,
		repr    = False,
		getter  = proc_jobs)
	# language
	lang = attr_property(
		default = default_config.lang,
		kw_only = True,
		repr    = False,
		setter  = partial(proc_setter_count, name = 'lang'),
		getter  = proc_lang)
	# The full name, with procset
	name = attr_property(
		init   = False,
		getter = proc_name,
		setter = False,
		repr   = True)
	# Non-cached job indexes
	_ncjobids = attr.ib(
		default = attr.Factory(list),
		init    = False,
		repr    = False)
	# who depends on me?
	nexts = attr_property(
		init   = False,
		# will be automatically deduced from depends, not allowed to set
		setter = False,
		repr   = False,
		getter = lambda this, value: [])
	# nthread
	nthread = attr.ib(
		default   = default_config.nthread,
		converter = int,
		kw_only   = True,
		repr      = False)
	# original job id that I copied from
	origin = attr.ib(
		default = None,
		init    = False,
		repr    = False)
	# output of the process
	output = attr_property(
		default = '',
		kw_only = True,
		getter  = proc_output,
		raw     = '_',
		repr    = False)
	# plugin configs
	config = attr_property(
		init    = False,
		getter  = lambda this, value: PluginConfig(default_config.config),
		kw_only = True,
		setter  = False,
		repr    = False)
	# pipeline directory
	ppldir = attr_property(
		default           = default_config.ppldir,
		converter         = Path,
		kw_only           = True,
		repr              = False,
		converter_runtime = True)
	# name of the procset
	procset = attr_property(
		setter = False,
		init   = False,
		repr   = False,
		getter = proc_procset)
	# runner
	runner = attr_property(
		default = default_config.runner,
		kw_only = True,
		repr    = False,
		setter  = partial(proc_setter_count, name = 'runner'),
		getter  = proc_runner,                                 raw = '_')
	# runtime configuration, used to override all possible configurations
	runtime_config = attr_property(
		default = None,
		init    = False,
		repr    = False,
		setter  = proc_runtime_config_setter)
	# script
	script = attr_property(
		default = None,
		kw_only = True,
		repr    = False,
		getter  = proc_script)
	# Short name without procset
	shortname = attr_property(
		setter = False,
		init   = False,
		repr   = False,
		getter = proc_shortname)
	# size of the process
	size = attr_property(
		init   = False,
		repr   = False,
		getter = proc_size,
		setter = False) # deduced from input
	# suffix
	suffix = attr_property(
		init   = False,
		repr   = False,
		getter = proc_suffix,
		setter = False)
	# template
	template = attr_property(
		default = default_config.template,
		kw_only = True,
		repr    = False,
		setter  = partial(proc_setter_count, name = 'template'),
		getter  = proc_template)
	# working directory
	workdir = attr_property(
		default = '',
		kw_only = True,
		getter  = proc_workdir,
		repr    = False)

	def __attrs_post_init__(self):
		_register_proc(self)
		pluginmgr.hook.proc_init(proc = self)

	def run(self, runtime_config):
		"""@API
		Run the process
		@params:
			runtime_config (simpleconf.Config): The runtime configuration
		"""
		self.runtime_config = runtime_config
		self.input
		self.output
		self.suffix
		logger.workdir(self.workdir, proc = self.id)
		ret = pluginmgr.hook.proc_prerun(proc = self)
		# plugins can stop process from running
		if ret is not False:
			self._save_settings()
			self._run_jobs()

		self._post_run()

	def _post_run(self):
		if self.jobs:
			jobs = {}

			for job in self.jobs: # pylint: disable=not-an-iterable
				jobs.setdefault(job.state, []).append(job.index)

			(logger.P_DONE, logger.CACHED)[int(
				len(jobs.get(STATES.DONECACHED, [])) == self.size and self.size > 0
			)]('Jobs [Cached: %s, Succ: %s, B.Fail: %s, S.Fail: %s, R.Fail: %s]',
				len(jobs.get(STATES.DONECACHED, [])),
				len(jobs.get(STATES.DONE, [])),
				len(jobs.get(STATES.BUILTFAILED, [])),
				len(jobs.get(STATES.SUBMITFAILED, [])),
				len(jobs.get(STATES.ENDFAILED, [])),
				proc = self.id)

			logger.debug('Cached: %s', brief_list(jobs.get(STATES.DONECACHED, []), 1),
				proc = self.id)
			logger.debug('Succeeded: %s', brief_list(jobs.get(STATES.DONE, []), 1),
				proc = self.id)
			if STATES.BUILTFAILED in jobs:
				logger.error('Building failed: %s', brief_list(jobs[STATES.BUILTFAILED], 1),
					proc = self.id)
			if STATES.SUBMITFAILED in jobs:
				logger.error('Submission failed: %s', brief_list(jobs[STATES.SUBMITFAILED], 1),
					proc = self.id)
			if STATES.ENDFAILED in jobs:
				logger.error('Running failed: %s', brief_list(jobs[STATES.ENDFAILED], 1),
					proc = self.id)

			donejobs = jobs.get(STATES.DONE, []) + jobs.get(STATES.DONECACHED, [])
			if len(donejobs) < self.size and self.errhow != 'ignore':
				pluginmgr.hook.proc_postrun(proc = self, status = 'failed')
				sys.exit(1)

		pluginmgr.hook.proc_postrun(proc = self, status = 'succeeded')
		del self.jobs[:] # pylint: disable=unsupported-delete-operation

	def _save_settings(self):
		def stringify(conf):
			"""Convert Path to str, even if it is buried deeply"""
			if isinstance(conf, Path):
				return str(conf)
			if isinstance(conf, Proc):
				return conf.name
			if isinstance(conf, dict):
				return {key: stringify(val) for key, val in conf.items()}
			if isinstance(conf, list):
				return [stringify(val) for val in conf]
			return conf

		with open(self.workdir / 'proc.settings.toml', 'w') as fsettings:
			toml.dump({key: stringify(val) \
				for key, val in self.__attrs_property_raw__.items()
				if key not in ('id', 'jobs', 'runtime_config')
			}, fsettings)

	def _run_jobs(self):
		logger.debug('Queue starts ...', proc = self.id)
		jobmgr = Jobmgr(self.jobs)
		# we need to jobs to be initialized, as during initialization
		# use_runner called, and we only initialize that runner
		runnermgr.hook.runner_init(proc = self)
		jobmgr.start()

		if self.jobs:
			# pylint: disable=unsubscriptable-object
			self.channel.attach(*self.jobs[0].output.keys())

	def copy(self, id = None, **kwargs):
		"""@API
		Copy a process to a new one
		Depends and nexts will be copied
		@params:
			id: The id of the new process
			kwargs: Other arguments for constructing a process
		"""
		newid = id or varname()
		raw_attrs = {key: try_deepcopy(value) \
			for key, value in self.__attrs_property_raw__.items()
			if key not in (
				'id', 'channel', 'jobs', 'runtime_config', 'depends', 'nexts')}
		raw_attrs.update(kwargs)
		newproc = Proc(newid, **raw_attrs)
		# pylint: disable=attribute-defined-outside-init
		newproc.origin = self.origin or self.id
		return newproc

	def add_config(self, name, default = None, converter = None, runtime = 'update'):
		"""@API
		Add a plugin configuration
		@params:
			name (str): The name of the plugin configuration
			default (any): The default value
			converter (callable): The converter function for the value
			runtime (str): How should we deal with it while \
				runtime_config is passed and its setcounter > 1
				- override: Override the value
				- update: Update the value if it's a dict otherwise override its
				- ignore: Ignore the value from runtime_config
		"""
		self.config.add(name, default, converter, runtime)
