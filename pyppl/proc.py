from functools import partial
from pathlib import Path
import sys
import traceback
import attr
import toml
import filelock
from diot import Diot
from attr_property import attr_property, attr_property_class
from varname import varname
from ._proc import proc_depends_setter, proc_input, proc_output, proc_script, \
	proc_suffix, proc_lang, proc_name, proc_shortname, proc_jobs, proc_size, \
	proc_runner, proc_template, proc_workdir, proc_input_setter, \
	proc_runtime_config_setter, proc_id_setter, proc_tag_setter, \
	proc_channel, proc_procset, proc_setter_count
from .utils import try_deepcopy, brief_list
from .channel import Channel
from .config import config
from .logger import logger
from .jobmgr import STATES, Jobmgr
from .plugin import pluginmgr, PluginConfig
from .pyppl import register_proc

@attr_property_class
@attr.s(eq = False, slots = True)
class Proc:
	"""Process of a pipeline"""
	# Remember the attr being set, they have the highest priority
	_setcounter = attr.ib(default = attr.Factory(dict), init = False, repr = False)
	# The id of the process
	id = attr_property(default = attr.Factory(lambda: varname(caller = 2)), repr = False, setter = proc_id_setter)
	# The tag of the process
	tag = attr_property(default = config.tag, setter = proc_tag_setter, kw_only = True,repr = False)
	# The description of the process
	desc = attr.ib(default = 'No description.', kw_only = True,repr = False)
	# The args of the process
	args = attr.ib(default = attr.Factory(Diot), kw_only = True, repr = False)
	# caching
	cache = attr_property(default = config.cache, kw_only = True, repr = False,
		setter = partial(proc_setter_count, name = 'cache'))
	# The output channel
	channel = attr_property(default = None, init = False, repr = False, getter = proc_channel)
	# Save the definitions to indicate you when you have 2
	# processes with the same id and tag defined
	_defs = attr.ib(default = attr.Factory(lambda: traceback.format_stack()[-3]), init = False, repr = False)
	# the dependencies of the process
	depends = attr_property(default = attr.Factory(list), kw_only = True, repr = False, setter = proc_depends_setter, raw = '_')
	# dirsig
	dirsig = attr_property(default = config.dirsig, kw_only = True, repr = False,
		setter = partial(proc_setter_count, name = 'dirsig'))
	# envs used to render templates
	envs = attr.ib(default = try_deepcopy(config.envs), kw_only = True, repr = False)
	# how to deal with errors
	errhow = attr_property(default = config.errhow, kw_only = True, repr = False,
		setter = partial(proc_setter_count, name = 'errhow'))
	# how many times to retry if errored
	errntry = attr_property(default = config.errntry, kw_only = True, repr = False,
		setter = partial(proc_setter_count, name = 'errntry'))
	# forks
	forks = attr_property(default = config.forks, converter = int, converter_runtime = True,
		kw_only = True, repr = False, setter = partial(proc_setter_count, name = 'forks'))
	# input of the process
	input = attr_property(default = None, kw_only = True, getter = proc_input, setter = proc_input_setter, repr = False, raw = '_')
	# jobs
	jobs = attr_property(default = attr.Factory(list), init = False, repr = False, getter = proc_jobs)
	# language
	lang = attr_property(default = config.lang, kw_only = True, repr = False,
		setter = partial(proc_setter_count, name = 'lang'), getter = proc_lang)
	# The full name, with procset
	name = attr_property(init = False, getter = proc_name, setter = False, repr = True)
	# Non-cached job indexes
	_ncjobids = attr.ib(default = attr.Factory(list), init = False, repr = False)
	# who depends on me?
	nexts = attr_property(init = False, setter = False, repr = False, getter = lambda this, value: [])
	# nthread
	nthread = attr.ib(default = config.nthread, converter = int, kw_only = True, repr = False)
	# original job id that I copied from
	origin = attr.ib(default = None, init = False, repr = False)
	# output of the process
	output = attr_property(default = '', kw_only = True, getter = proc_output, raw = '_', repr = False)
	# plugin configs
	plugin_config = attr_property(init = False, getter = lambda this, value: PluginConfig(config.plugin_config), kw_only = True, setter = False, repr = False)
	# pipeline directory
	ppldir = attr_property(default = config.ppldir, converter = Path, kw_only = True, repr = False, converter_runtime = True)
	# name of the procset
	procset = attr_property(setter = False, init = False, repr = False,
		getter = proc_procset)
	# runner
	runner = attr_property(default = config.runner, kw_only = True, repr = False,
		setter = partial(proc_setter_count, name = 'runner'), getter = proc_runner, raw = '_')
	# runtime configuration, used to override all possible configurations
	runtime_config = attr_property(default =None, init = False, repr = False, setter = proc_runtime_config_setter)
	# script
	script = attr_property(default = None, kw_only = True, repr = False, getter = proc_script)
	# Short name without procset
	shortname = attr_property(setter = False, init = False, repr = False, getter = proc_shortname)
	# size of the process
	size = attr_property(init = False, repr = False, getter = proc_size, setter = False)
	# suffix
	suffix = attr_property(init = False, repr = False, getter = proc_suffix, setter = False)
	# template
	template = attr_property(default = config.template, kw_only = True, repr = False,
		setter = partial(proc_setter_count, name = 'template'), getter = proc_template)
	# working directory
	workdir = attr_property(default = '', kw_only = True, getter = proc_workdir, repr = False)

	def __attrs_post_init__(self):
		register_proc(self)
		pluginmgr.hook.proc_init(proc = self)

	def run(self, runtime_config):
		self.runtime_config = runtime_config
		ret = pluginmgr.hook.proc_prerun(proc = self)
		# plugins can stop process from running
		if ret is not False:
			logger.workdir(self.workdir, proc = self.id)
			self._save_settings()
			self._run_jobs()

		self._post_run()

	def _post_run(self):
		if self.jobs:
			jobs = {}

			for job in self.jobs:
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

		pluginmgr.hook.proc_postrun(proc = self, status = 'successful')
		del self.jobs[:]

	def _save_settings(self):
		with open(self.workdir / 'proc.settings.toml', 'w') as fsettings:
			toml.dump(self.__attrs_property_raw__, fsettings)

	def _run_jobs(self):
		logger.debug('Queue starts ...', proc = self.id)
		Jobmgr(self.jobs).start()

		if self.jobs:
			self.channel.attach(*self.jobs[0].output.keys())

	def copy(self, *args, **kwargs):
		newid = varname() if not args else args[0]
		newproc = Proc(newid, **kwargs)
		newproc.__attrs_property_raw__ = self.__attrs_property_raw__.copy()
		del newproc.depends
		newproc.depends = []
		del newproc.nexts
		newproc.origin = self.origin if self.origin else self.id
		return newproc

	def add_config(self, name, default = None, converter = None, runtime = 'update'):
		"""
		runtime: override, update, ignore
		"""
		self.plugin_config.add(name, default, converter, runtime)
