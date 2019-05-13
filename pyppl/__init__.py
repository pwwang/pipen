"""The main module of PyPPL"""

# give random tips in the log
import random
# access sys.argv
import sys
# any2proc
import fnmatch

from os import path
from time import time
from multiprocessing import cpu_count

from .utils import config, Box, OBox

__version__ = "2019.2.20"

DEFAULT_CFGFILES = (
	'~/.PyPPL.yaml', '~/.PyPPL.toml', './.PyPPL.yaml', './.PyPPL.toml', 'PYPPL.osenv')
def loadConfiguratiaons():
	"""
	Load default configurations.
	"""
	config.clear()
	config._load(dict(default = dict(
		_log = dict(
			file       = None,
			theme      = 'greenOnBlack',
			levels     = 'normal',
			leveldiffs = [],
			pbar       = 50,
			shortpath  = {'cutoff': 0},
		),
		_flowchart = dict(theme = 'default'),
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
		# Hide the process in flowchart
		hide       = False,
		# Default shell/language
		lang       = 'bash',
		# number of threads used to build jobs and to check job cache status
		nthread    = min(int(cpu_count() / 2), 16),
		# Where cache file and workdir located
		ppldir     = path.abspath('./workdir'),
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
	)), *DEFAULT_CFGFILES)

loadConfiguratiaons()

# load logger
# pylint: disable=wrong-import-position
from .logger import logger
from .aggr import Aggr, _Proxy
from .proc import Proc
from .job2 import Job
from .jobmgr2 import Jobmgr
from .channel import Channel
from .parameters import params, Parameters, commands
from .proctree import ProcTree
from .exceptions import PyPPLProcRelationError
from . import utils, runners2 as runners

class PyPPL (object):
	"""
	The PyPPL class

	@static variables:
		`TIPS`: The tips for users
		`RUNNERS`: Registered runners
		`DEFAULT_CFGFILES`: Default configuration file
		`COUNTER`: The counter for `PyPPL` instance
	"""

	TIPS = [
		"You can find the stdout in <workdir>/<job.index>/job.stdout",
		"You can find the stderr in <workdir>/<job.index>/job.stderr",
		"You can find the script in <workdir>/<job.index>/job.script",
		"Check documentation at: https://pwwang.github.io/PyPPL",
		"You cannot have two processes with the same id and tag",
		"beforeCmd and afterCmd only run locally",
		"If 'workdir' is not set for a process, "
		"it will be PyPPL.<proc-id>.<proc-tag>.<suffix> under default <ppldir>",
		"The default <ppldir> is './workdir'",
		]

	RUNNERS  = {}

	# counter
	COUNTER  = 0

	def __init__(self, conf = None, cfgfile = None):
		"""
		Constructor
		@params:
			`conf`: the configurations for the pipeline, default: {}
			`cfgfile`: the configuration file for the pipeline, default: None
		"""
		self.counter = PyPPL.COUNTER
		PyPPL.COUNTER += 1

		self.config = config.copy()
		if cfgfile and path.isfile(cfgfile):
			self.config._load(cfgfile)
		if isinstance(conf, dict):
			self.config.update(conf or {})

		if self.config._log.file is True:
			self.config._log.file = './%s%s.pyppl.log' % (
				path.splitext(path.basename(sys.argv[0]))[0],
				('_%s' % self.counter) if self.counter else ''
			)
		# reinitiate logger according to new config
		logger.init()
		logger.pyppl('Version: %s', __version__)
		logger.tips(random.choice(PyPPL.TIPS))

		for cfile in DEFAULT_CFGFILES + (str(cfgfile), ):
			if cfile.endswith('.osenv'):
				logger.config('Read from environment variables with prefix: %s',
					path.basename(cfile)[:-6])
			cfile = path.expanduser(cfile)
			if not path.isfile(cfile):
				continue
			if cfile.endswith('.yaml') or cfile.endswith('yml'):
				try:
					import yaml # pylint: disable=W0611
					logger.config('Read from %s', cfile)
				except ImportError:
					logger.warning('Module PyYAML not installed, config file ignored: %s', cfile)
			elif cfile.endswith('.toml'):
				try:

					import toml # pylint: disable=W0611
					logger.config('Read from %s', cfile)
				except ImportError:
					logger.warning('Module toml not installed, config file ignored: %s', cfile)
			else:
				logger.config('Read from %s', cfile)

		self.tree = ProcTree()

	def start (self, *args):
		"""
		Set the starting processes of the pipeline
		@params:
			`args`: the starting processes
		@returns:
			The pipeline object itself.
		"""
		starts  = set(PyPPL._any2procs(args))
		nostart = set()
		for start in starts:
			paths = self.tree.getPaths(start)
			pristarts = [pnode for sublist in paths for pnode in sublist if pnode in starts]
			if pristarts:
				nostart.add(start)
				names = [pnode.name(True) for pnode in pristarts]
				names = names[:3] + ['...'] if len(names) > 3 else names
				logger.warning('Start process %s ignored, depending on [%s]', start.name(True),
					', '.join(names))
		self.tree.setStarts(starts - nostart)
		return self

	def _resume(self, *args, **kwargs):
		"""
		Mark processes as to be resumed
		@params:
			`args`: the processes to be marked.
				The last element is the mark for processes to be skipped.
		"""

		sflag    = 'skip+' if kwargs.get('plus') else 'skip'
		rflag    = 'resume+' if kwargs.get('plus') else 'resume'
		resumes  = PyPPL._any2procs(args)

		ends     = self.tree.getEnds()
		#starts   = self.tree.getStarts()
		# check whether all ends can be reached
		for end in ends:
			if end in resumes:
				continue
			paths = self.tree.getPathsToStarts(end)
			failedpaths = [apath for apath in paths
				if not any([pnode in apath for pnode in resumes])]
			if not failedpaths:
				continue
			failedpath = failedpaths[0]
			raise PyPPLProcRelationError('%s <- [%s]' % (
				end.name(), ', '.join([pnode.name() for pnode in failedpath])),
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
		"""
		Mark processes as to be resumed
		@params:
			`args`: the processes to be marked
		@returns:
			The pipeline object itself.
		"""
		if not args or (len(args) == 1 and not args[0]):
			return self
		self._resume(*args)
		return self

	def resume2 (self, *args):
		"""
		Mark processes as to be resumed
		@params:
			`args`: the processes to be marked
		@returns:
			The pipeline object itself.
		"""
		if not args or (len(args) == 1 and not args[0]):
			return self
		self._resume(*args, plus = True)
		return self

	def showAllRoutes(self):
		"""
		Show all the routes in the log.
		"""
		logger.debug('ALL ROUTES:')
		#paths  = sorted([list(reversed(path)) for path in self.tree.getAllPaths()])
		paths  = sorted([[pnode.name() for pnode in reversed(apath)]
			for apath in self.tree.getAllPaths()])
		paths2 = [] # processes merged from the same aggr
		for apath in paths:
			prevaggr = None
			path2    = []
			for pnode in apath:
				if not '@' in pnode:
					path2.append(pnode)
				else:
					aggr = pnode.split('@')[-1]
					if not prevaggr or prevaggr != aggr:
						path2.append('[%s]' % aggr)
						prevaggr = aggr
					elif prevaggr == aggr:
						continue
			if path2 not in paths2:
				paths2.append(path2)
			# see details for aggregations
			#if path != path2:
			#	logger.logger.info('[  DEBUG] * %s' % (' -> '.join(path)))

		for path2 in paths2:
			logger.debug('* %s', ' -> '.join(path2))
		return self

	def run (self, profile = 'default'):
		"""
		Run the pipeline
		@params:
			`profile`: the profile used to run, if not found, it'll be used as runner name.
				- default: 'default'
		@returns:
			The pipeline object itself.
		"""
		timer     = time()

		#dftconfig = self._getProfile(profile)
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
				proc = proc.id
			)
			proc.run(profile, self.config)

			proc = self.tree.getNextToRun()

		unran = self.tree.unranProcs()
		if unran:
			klen  = max([len(key) for key, _ in unran.items()])
			for key, val in unran.items():
				fmtstr = "%-"+ str(klen) +"s won't run as path can't be reached: %s <- %s"
				logger.warning(fmtstr, key, key, ' <- '.join(val))

		logger.done (
			'Total time: %s',
			utils.formatSecs(time() - timer)
		)
		return self

	def flowchart (self, fcfile = None, dotfile = None):
		"""
		Generate graph in dot language and visualize it.
		@params:
			`dotfile`: Where to same the dot graph.
				- Default: `None` (`path.splitext(sys.argv[0])[0] + ".pyppl.dot"`)
			`fcfile`:  The flowchart file.
				- Default: `None` (`path.splitext(sys.argv[0])[0] + ".pyppl.svg"`)
				- For example: run `python pipeline.py` will save it to `pipeline.pyppl.svg`
		@returns:
			The pipeline object itself.
		"""
		from .flowchart import Flowchart
		self.showAllRoutes()
		fcfile  = fcfile or './%s%s.pyppl.svg' % (
			path.splitext(path.basename(sys.argv[0]))[0],
			('_%s' % self.counter) if self.counter else ''
		)
		dotfile = dotfile or '%s.dot' % (path.splitext(fcfile)[0])
		fchart  = Flowchart(fcfile = fcfile, dotfile = dotfile)
		fchart.setTheme(self.config._flowchart.theme)

		for start in self.tree.getStarts():
			fchart.addNode(start, 'start')

		for end in self.tree.getEnds():
			fchart.addNode(end, 'end')
			for apath in self.tree.getPathsToStarts(end):
				for pnode in apath:
					fchart.addNode(pnode)
					nextps = ProcTree.getNext(pnode)
					if not nextps:
						continue
					for nextp in nextps:
						fchart.addLink(pnode, nextp)

		fchart.generate()
		logger.info ('Flowchart file saved to: %s', fchart.fcfile)
		logger.info ('DOT file saved to: %s', fchart.dotfile)
		return self

	@staticmethod
	def _any2procs(anything):
		ret = _Proxy()
		if not isinstance(anything, (tuple, list)):
			if isinstance(anything, Proc):
				ret.add(anything)
			elif isinstance(anything, Aggr):
				ret.add(anything.starts)
			else:
				for node in ProcTree.NODES.values():
					if anything == node.proc.id:
						ret.add(node.proc)
					elif anything == node.proc.id + '.' + node.proc.tag:
						ret.add(node.proc)
						break
					elif fnmatch.fnmatch(anything, node.proc.id + '.' + node.proc.tag):
						ret.add(node.proc)
		else:
			for thing in anything:
				ret.add(PyPPL._any2procs(thing))
		return ret

	@staticmethod
	def _registerProc(proc):
		"""
		Register the process
		@params:
			`proc`: The process
		"""
		ProcTree.register(proc)

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
	def registerRunner(runner):
		"""
		Register a runner
		@params:
			`runner`: The runner to be registered.
		"""
		runner_name = runner.__name__
		if runner_name.startswith('Runner'):
			runner_name = runner_name[6:].lower()

		if not runner_name in PyPPL.RUNNERS:
			PyPPL.RUNNERS[runner_name] = runner

def registerDefaultRunners():
	"""
	Register builtin runners
	"""
	for runnername in dir(runners):
		if not runnername.startswith('Runner') or runnername in ['Runner', 'RunnerQueue']:
			continue
		runner = getattr(runners, runnername)
		PyPPL.registerRunner(runner)

registerDefaultRunners()
