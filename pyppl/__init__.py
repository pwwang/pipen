"""
The main module of PyPPL
"""
VERSION = "2019.2.20"

import json
import random
import sys
import copy as pycopy
# used to update logger according to new config

from os import path
from time import time

from simpleconf import config
from .logger2 import logger
from .aggr import Aggr
from .proc import Proc
from .job import Job
from .jobmgr import Jobmgr
from .channel import Channel
from .parameters import params, Parameters, commands
from .proctree import ProcTree
from .exception import PyPPLProcFindError, PyPPLProcRelationError
from .utils import Box, jsonLoads
from . import utils, runners

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
		"If 'workdir' is not set for a process, it will be PyPPL.<proc-id>.<proc-tag>.<suffix> under default <ppldir>",
		"The default <ppldir> is './workdir'",
	]

	RUNNERS  = {}
	# ~/.PyPPL.json has higher priority
	DEFAULT_CFGFILES = [
		'~/.PyPPL.yaml', 
		'~/.pyppl.yaml',
		'~/.PyPPL.toml'
		'~/.pyppl.toml',
	]
	# counter
	COUNTER  = 0

	def __init__(self, conf = None, cfgfile = None):
		"""
		Constructor
		@params:
			`conf`: the configurations for the pipeline, default: {}
			`cfgfile`:  the configuration file for the pipeline, default: `~/.PyPPL.json` or `./.PyPPL`
		"""
		self.counter = PyPPL.COUNTER
		PyPPL.COUNTER += 1

		config._load(*PyPPL.DEFAULT_CFGFILES)
		
		# reinitiate logger according to new config
		logger.init()
		logger.pyppl('Version: %s', VERSION)
		logger.tips(random.choice(PyPPL.TIPS))

		for cfile in PyPPL.DEFAULT_CFGFILES + [str(cfgfile)]:
			if not path.isfile(cfile): 
				continue
			if cfile.endswith('.yaml') or cfile.endswith('yml'):
				try:
					import yaml
					logger.config('Read from %s', cfile)
				except ImportError:
					logger.warning('Module PyYAML not installed, config file ignored: %s', cfile)
			elif cfile.endswith('.toml'):
				try: 
					import toml
					logger.config('Read from %s', cfile)
				except ImportError:
					logger.warning('Module toml not installed, config file ignored: %s', cfile)

		self.tree = ProcTree()

	def start (self, *args):
		"""
		Set the starting processes of the pipeline
		@params:
			`args`: the starting processes
		@returns:
			The pipeline object itself.
		"""
		starts  = set(PyPPL._any2procs(*args))
		nostart = set()
		for start in starts:
			paths = self.tree.getPaths(start)
			pristarts = [p for sublist in paths for p in sublist if p in starts]
			if pristarts:
				nostart.add(start)
				names = [p.name(True) for p in pristarts]
				names = names[:3] + ['...'] if len(names) > 3 else names
				logger.warning('Start process %s ignored, depending on [%s]', start.name(True), ', '.join(names))
		self.tree.setStarts(starts - nostart)
		return self

	def _resume(self, *args, **kwargs):
		"""
		Mark processes as to be resumed
		@params:
			`args`: the processes to be marked. The last element is the mark for processes to be skipped.
		"""

		sflag    = 'skip+' if kwargs['plus'] else 'skip'
		rflag    = 'resume+' if kwargs['plus'] else 'resume'
		resumes  = PyPPL._any2procs(*args)

		ends     = self.tree.getEnds()
		#starts   = self.tree.getStarts()
		# check whether all ends can be reached
		for end in ends:
			if end in resumes: 
				continue
			paths = self.tree.getPathsToStarts(end)
			failedpaths = [ps for ps in paths if not any([p in ps for p in resumes])]
			if not failedpaths: 
				continue
			failedpath = failedpaths[0]
			raise PyPPLProcRelationError('%s <- [%s]' % (end.name(), ', '.join([p.name() for p in failedpath])), 'One of the routes cannot be achived from resumed processes')

		# set prior processes to skip
		for rsproc in resumes:
			rsproc.resume = rflag
			paths = self.tree.getPathsToStarts(rsproc)
			for pt in paths:
				for p in pt:
					if not p.resume:
						p.resume = sflag

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
		self._resume(*args, plus = False)
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
		paths  = sorted([[p.name() for p in reversed(ps)] for ps in self.tree.getAllPaths()])
		paths2 = [] # processes merged from the same aggr
		for pt in paths:
			prevaggr = None
			path2    = []
			for p in pt:
				if not '@' in p: 
					path2.append(p)
				else:
					aggr = p.split('@')[-1]
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

		for pt in paths2:
			logger.debug('* %s', ' -> '.join(pt))
		return self

	def run (self, profile = 'default'):
		"""
		Run the pipeline
		@params:
			`profile`: the profile used to run, if not found, it'll be used as runner name. default: 'default'
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
			proc.run(profile, pycopy.deepcopy(self.config))

			proc = self.tree.getNextToRun()

		unran = self.tree.unranProcs()
		if unran:
			klen  = max([len(k) for k in unran.keys()])
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
			`dotfile`: Where to same the dot graph. Default: `None` (`path.splitext(sys.argv[0])[0] + ".pyppl.dot"`)
			`fcfile`:  The flowchart file. Default: `None` (`path.splitext(sys.argv[0])[0] + ".pyppl.svg"`)
			- For example: run `python pipeline.py` will save it to `pipeline.pyppl.svg`
			`dot`:     The dot visulizer. Default: "dot -Tsvg {{dotfile}} > {{fcfile}}"
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
		fc  = Flowchart(fcfile = fcfile, dotfile = dotfile)
		fc.setTheme(self.fcconfig['theme'])

		for start in self.tree.getStarts():
			fc.addNode(start, 'start')

		for end in self.tree.getEnds():
			fc.addNode(end, 'end')
			for ps in self.tree.getPathsToStarts(end):
				for p in ps:
					fc.addNode(p)
					nextps = ProcTree.getNext(p)
					if not nextps: 
						continue
					for np in nextps: 
						fc.addLink(p, np)

		fc.generate()
		logger.info ('Flowchart file saved to: %s', fc.fcfile)
		logger.info ('DOT file saved to: %s', fc.dotfile)
		return self

	@staticmethod
	def _any2procs (*args):
		"""
		Get procs from anything (aggr.starts, proc, procs, proc names)
		@params:
			`arg`: anything
		@returns:
			A set of procs
		"""
		# convert all to flat list
		procs = [a for a in args if not isinstance(a, list)]
		for a in args:
			if isinstance(a, list):
				procs.extend(a)

		ret = []

		for pany in set(procs):
			if isinstance(pany, Proc):
				ret.append(pany)
			elif isinstance(pany, Aggr):
				ret.extend([p for p in pany.starts])
			else:
				found = False
				for node in ProcTree.NODES.values():
					p = node.proc
					if p.id == pany:
						found = True
						ret.append(p)
					elif p.id + '.' + p.tag == pany:
						found = True
						ret.append(p)
				if not found:
					raise PyPPLProcFindError(pany)
		return list(set(ret))

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
	def registerRunner(r):
		"""
		Register a runner
		@params:
			`r`: The runner to be registered.
		"""
		runnerName = r.__name__
		if runnerName.startswith('Runner'):
			runnerName = runnerName[6:].lower()

		if not runnerName in PyPPL.RUNNERS:
			PyPPL.RUNNERS[runnerName] = r


for runnername in dir(runners):
	if not runnername.startswith('Runner') or runnername in ['Runner', 'RunnerQueue']:
		continue
	runner = getattr(runners, runnername)
	PyPPL.registerRunner(runner)
