"""The main module of PyPPL"""
# pylint: disable=protected-access,no-member

__version__ = "2.1.0"

# give random tips in the log
import random
# access sys.argv
import sys
# any2proc
import fnmatch

from pathlib import Path
from time import time
from multiprocessing import cpu_count
from simpleconf import Config
from .plugin import registerPlugins, pluginmgr
from .utils import config, loadConfigurations, Box, OBox

DEFAULT_CFGFILES = (
	'~/.PyPPL.yaml', '~/.PyPPL.toml', './.PyPPL.yaml', './.PyPPL.toml', 'PYPPL.osenv')

DEFAULT_CONFIG = dict(default = dict(
	# default plugins
	_plugins = ['pyppl-report', 'pyppl-flowchart'],
	# log options
	_log = dict(
		file       = None,
		theme      = 'greenOnBlack',
		levels     = 'normal',
		leveldiffs = [],
		pbar       = 50,
		shorten    = 0,
	),
	# The command to run after jobs start
	afterCmd   = '',
	# The extra arguments for the process
	args       = OBox(),
	# The command to run before jobs start
	beforeCmd  = '',
	# The cache option, True/False/export
	cache      = True,
	# Do cleanup for cached jobs?
	acache     = False,
	# The description of the job
	desc       = 'No description',
	# Whether expand directory to check signature
	dirsig     = True,
	# Whether to echo the stdout and stderr of the jobs to the screen
	# Could also be:
	# {
	#    # or [0, 1, 2], just echo output of those jobs.
	#   'jobs': 0
	#    # only echo stderr. (stdout: only echo stdout; [don't specify]: echo all)
	#   'type': 'stderr'
	# }
	# You can also specify a filter to the type
	# {
	#   'jobs':  0
	#   'type':  {'stderr': r'^Error'}	# only output lines starting with 'Error' in stderr
	# }
	# self.echo = True <=>
	#     self.echo = { 'jobs': [0], 'type': {'stderr': None, 'stdout': None} }
	# self.echo = False    <=> self.echo = { 'jobs': [] }
	# self.echo = 'stderr' <=> self.echo = { 'jobs': [0], 'type': {'stderr': None} }
	# self.echo = {'jobs': 0, 'type': 'stdout'} <=>
	#     self.echo = { 'jobs': [0], 'type': {'stdout': None} }
	# self.echo = {'type': {'all': r'^output'}} <=>
	#     self.echo = { 'jobs': [0], 'type': {'stdout': r'^output', 'stderr': r'^output'} }
	echo       = False,
	# How to deal with the errors
	# retry, ignore, halt
	# halt to halt the whole pipeline, no submitting new jobs
	# terminate to just terminate the job itself
	errhow     = 'terminate',
	# How many times to retry to jobs once error occurs
	errntry    = 3,
	# The directory to export the output files
	exdir      = '',
	# How to export # link, copy, gzip
	exhow      = 'move',
	# Whether to overwrite the existing files # overwrite
	exow       = True,
	# partial export, either the key of output file or the pattern
	expart     = '',
	# expect
	expect     = '',
	# How many jobs to run concurrently
	forks      = 1,
	# Default shell/language
	lang       = 'bash',
	# number of threads used to build jobs and to check job cache status
	nthread    = min(int(cpu_count() / 2), 16),
	# Where cache file and workdir located
	ppldir     = './workdir',
	# Valid return codes
	rc         = 0,
	# Select the runner
	runner     = 'local',
	# The script of the jobs
	script     = '',
	# The tag of the job
	tag        = 'notag',
	# The template engine (name)
	template   = '',
	# The template environment
	tplenvs    = Box(),
	# working directory for the process
	workdir    = ''
))

loadConfigurations(config, DEFAULT_CONFIG, *DEFAULT_CFGFILES)
registerPlugins(config['_plugins'], DEFAULT_CONFIG['default']['_plugins'])
pluginmgr.hook.setup(config = config)

# load logger
# pylint: disable=wrong-import-position
from .logger import logger
from .procset import ProcSet, Proxy
from .proc import Proc
from .job import Job
from .jobmgr import Jobmgr
from .channel import Channel
from .proctree import ProcTree
from .exception import PyPPLProcRelationError, RunnerClassNameError
from . import utils, runner

class PyPPL (object):
	"""@API
	The PyPPL class

	@static variables:
		TIPS (list): The tips for users
		RUNNERS (dict): Registered runners
		COUNTER (int): The counter for `PyPPL` instance
	"""

	TIPS = [
		"You can find the stdout in <workdir>/<job.index>/job.stdout",
		"You can find the stderr in <workdir>/<job.index>/job.stderr",
		"You can find the script in <workdir>/<job.index>/job.script",
		"Check documentation at: https://pyppl.readthedocs.io/en/latest/",
		"You cannot have two processes with the same id and tag",
		"beforeCmd and afterCmd only run locally",
		"Workdir defaults to PyPPL.<id>.<tag>.<suffix> under default <ppldir>",
		"The default <ppldir> is './workdir'"]

	RUNNERS  = {}

	# counter
	COUNTER  = 0

	def __init__(self, conf = None, cfgfile = None):
		"""@API
		PyPPL Constructor
		@params:
			conf (dict): the configurations for the pipeline, default: `None`
				- Remember the profile name should be included.
			cfgfile (file): the configuration file for the pipeline, default: `None`
		"""
		self.counter = PyPPL.COUNTER
		PyPPL.COUNTER += 1

		self.config = Config()
		# __noloading__ tells processes not load it as they have it initiated.
		self.config._load({'default': config, '__noloading__': None})
		if cfgfile:
			self.config._load(cfgfile)
		if conf and isinstance(conf, dict):
			self.config._load(conf)

		if self.config._log.file is True:
			self.config._log.file = (Path('./') / Path(sys.argv[0]).stem).with_suffix(
				'%s.pyppl.log' % ('.' + str(self.counter) if self.counter else ''))

		# reinitiate logger according to new config
		logger.init(self.config)
		logger.pyppl('Version: %s', __version__)
		logger.tips(random.choice(PyPPL.TIPS))

		for cfile in DEFAULT_CFGFILES + (str(cfgfile), ):
			if cfile.endswith('.osenv'):
				logger.config('Read from environment variables with prefix: "%s_"',
					Path(cfile).name[:-6])
			cfile = Path(cfile).expanduser()
			if not utils.fs.isfile(cfile):
				if cfile == cfgfile:
					logger.warning('Configuration file does not exist: %s', cfile)
				continue
			elif cfile.suffix in ('.yaml', 'yml'):
				try:
					import yaml # pylint: disable=W0611
				except ImportError: # pragma: no cover
					logger.warning('Module PyYAML not installed, config file ignored: %s', cfile)
			elif cfile.suffix == '.toml':
				try:
					import toml # pylint: disable=W0611
				except ImportError: # pragma: no cover
					logger.warning('Module toml not installed, config file ignored: %s', cfile)
			logger.config('Read from %s', cfile)

		for plgname, plugin in pluginmgr.list_name_plugin():
			logger.plugin('Loaded %s: %s', plgname, plugin)

		self.tree  = ProcTree()
		# save the procs in order for plugin use
		self.procs = []
		pluginmgr.hook.pypplInit(ppl = self)

	@staticmethod
	def _procsSelector(selector):
		ret = Proxy()
		if isinstance(selector, Proc):
			ret.add(selector)
		elif isinstance(selector, ProcSet):
			ret.add(selector.starts)
		elif isinstance(selector, (tuple, list)):
			for thing in selector:
				ret.add(PyPPL._procsSelector(thing))
		else:
			for proc in ProcTree.NODES:
				if selector == proc.id:
					ret.add(proc)
				elif selector == proc.id + '.' + proc.tag:
					ret.add(proc)
				elif fnmatch.fnmatch(proc.id + '.' + proc.tag, selector):
					ret.add(proc)
		return ret

	def start (self, *args):
		"""@API
		Set the starting processes of the pipeline
		@params:
			*args (Proc|str): process selectors
		@returns:
			(PyPPL): The pipeline object itself.
		"""
		starts  = set(PyPPL._procsSelector(args))
		PyPPL._registerProc(*starts)
		self.tree.init()

		nostart = set()
		for startproc in starts:
			# Let's check if we have any other procs on the path of start process
			paths = self.tree.getPaths(startproc)
			pristarts = [pnode for sublist in paths for pnode in sublist if pnode in starts]
			if pristarts:
				nostart.add(startproc)
				names = [pnode.name(True) for pnode in pristarts]
				names = names[:3] + ['...'] if len(names) > 3 else names
				logger.warning('Start process %s ignored, depending on [%s]', startproc.name(True),
					', '.join(names))
		self.tree.setStarts(starts - nostart)
		return self

	def _resume(self, *args, plus = False):
		"""
		Mark processes as to be resumed
		@params:
			`args`: the processes to be marked.
				The last element is the mark for processes to be skipped.
		"""

		sflag    = 'skip+' if plus else 'skip'
		rflag    = 'resume+' if plus else 'resume'
		resumes  = PyPPL._procsSelector(args)

		ends     = self.tree.getEnds()
		#starts   = self.tree.getStarts()
		# check whether all ends can be reached
		for end in ends:
			if end in resumes:
				continue
			paths = self.tree.getPathsToStarts(end)
			failedpaths = [apath for apath in paths
				if not any(pnode in apath for pnode in resumes)]
			if not failedpaths:
				continue
			failedpath = failedpaths[0]
			raise PyPPLProcRelationError('%s <- [%s]' % (
				end.name(), ', '.join(pnode.name() for pnode in failedpath)),
				'One of the routes cannot be achived from resumed processes')

		# set prior processes to skip
		for rsproc in resumes:
			rsproc.resume = rflag
			paths = self.tree.getPathsToStarts(rsproc)
			for apath in paths:
				for pnode in apath:
					if not pnode.resume:
						pnode.resume = sflag

	def resume (self, *args):
		"""@API
		Mark processes as to be resumed
		@params:
			*args (Proc|str): the processes to be marked
		@returns:
			(PyPPL): The pipeline object itself.
		"""
		if not args or (len(args) == 1 and not args[0]):
			return self
		self._resume(*args)
		return self

	def resume2 (self, *args):
		"""@API
		Mark processes as to be resumed
		@params:
			*args (Proc|str): the processes to be marked
		@returns:
			(PyPPL): The pipeline object itself.
		"""
		if not args or (len(args) == 1 and not args[0]):
			return self
		self._resume(*args, plus = True)
		return self

	def run(self, profile = 'default'):
		"""@API
		Run the pipeline
		@params:
			profile (str|dict): the profile used to run, if not found, it'll be used as runner name.
				- default: 'default'
		@returns:
			(PyPPL): The pipeline object itself.
		"""
		timer = time()

		pluginmgr.hook.pypplPreRun(ppl = self)
		proc = self.tree.getNextToRun()
		while proc:
			if proc.origin != proc.id:
				name = '{} ({}): {}'.format(proc.name(True), proc.origin, proc.desc)
			else:
				name = '{}: {}'.format(proc.name(True), proc.desc)
			#nlen = max(85, len(name) + 3)
			#logger.logger.info ('[PROCESS] +' + '-'*(nlen-3) + '+')
			#logger.logger.info ('[PROCESS] |%s%s|' % (name, ' '*(nlen - 3 - len(name))))
			decorlen = max(80, len(name))
			logger.process ('-' * decorlen)
			logger.process (name)
			logger.process ('-' * decorlen)
			logger.depends (
				'%s => %s => %s',
				ProcTree.getPrevStr(proc),
				proc.name(),
				ProcTree.getNextStr(proc),
				proc = proc.id)
			proc.run(profile, self.config)
			self.procs.append(proc)
			proc = self.tree.getNextToRun()

		# unran = self.tree.unranProcs()
		# if unran:
		# 	klen  = max([len(key) for key, _ in unran.items()])
		# 	for key, val in unran.items():
		# 		fmtstr = "%-"+ str(klen) +"s won't run as path can't be reached: %s <- %s"
		# 		logger.warning(fmtstr, key, key, ' <- '.join(val))

		pluginmgr.hook.pypplPostRun(ppl = self)
		logger.done('Total time: %s', utils.formatSecs(time() - timer))
		return self

	@staticmethod
	def _registerProc(*procs):
		"""
		Register the process
		@params:
			`*procs`: The process
		"""
		ProcTree.register(*procs)

	@staticmethod
	def _checkProc(proc):
		"""
		Check processes, whether 2 processes have the same id and tag
		@params:
			`proc`: The process
		@returns:
			If there are 2 processes with the same id and tag, raise `ValueError`.
		"""
		ProcTree.check(proc)

	@staticmethod
	def registerRunner(runner_to_reg):
		"""@API
		Register a runner
		@params:
			`runner_to_reg`: The runner to be registered.
		"""
		runner_name = runner_to_reg.__name__
		if not runner_name.startswith('Runner'):
			raise RunnerClassNameError('The class name of a runner should start with "Runner"')
		runner_name = runner_name[6:].lower()

		if runner_name not in PyPPL.RUNNERS:
			PyPPL.RUNNERS[runner_name] = runner_to_reg

def _registerDefaultRunners():
	"""
	Register builtin runners
	"""
	for runnername in dir(runner):
		if not runnername.startswith('Runner'):
			continue
		runner_to_reg = getattr(runner, runnername)
		PyPPL.registerRunner(runner_to_reg)

_registerDefaultRunners()
