"""
proc module for PyPPL
"""
import sys
import json
import copy as pycopy
from time import time
from collections import OrderedDict
from os import path, makedirs, remove
from multiprocessing import cpu_count
import filelock
from . import logger, utils, template
from .job import Job
from .jobmgr import Jobmgr
from .aggr import Aggr
from .channel import Channel
from .exception import ProcTagError, ProcAttributeError, ProcInputError, ProcOutputError, ProcScriptError, ProcRunCmdError

class Proc (object):
	"""
	The Proc class defining a process

	@static variables:
		`RUNNERS`:       The regiested runners
		`ALIAS`:         The alias for the properties
		`LOG_NLINE`:     The limit of lines of logging information of same type of messages

	@magic methods:
		`__getattr__(self, name)`: get the value of a property in `self.props`
		`__setattr__(self, name, value)`: set the value of a property in `self.config`
	"""

	# for future use, shortcuts
	ALIAS        = {
		'envs'   : 'tplenvs',
		'profile': 'runner',
		#'nsub'   : 'maxsubmit'
	}
	# deprecated
	DEPRECATED   = {
		'profile': 'runner'
	}

	OUT_VARTYPE     = ['var']
	OUT_FILETYPE    = ['file', 'path']
	OUT_DIRTYPE     = ['dir', 'folder']
	OUT_STDOUTTYPE  = ['stdout']
	OUT_STDERRTYPE  = ['stderr']

	IN_VARTYPE   = ['var']
	IN_FILETYPE  = ['file', 'path', 'dir', 'folder']
	IN_FILESTYPE = ['files', 'paths', 'dirs', 'folders']

	EX_GZIP      = ['gzip', 'gz']
	EX_COPY      = ['copy', 'cp']
	EX_MOVE      = ['move', 'mv']
	EX_LINK      = ['link', 'symlink', 'symbol']

	def __init__ (self, tag = 'notag', desc = 'No description.', id = None, **kwargs):
		"""
		Constructor
		@params:
			`tag`:  The tag of the process
			`desc`: The description of the process
			`id`:   The identify of the process
		@config:
			id, input, output, ppldir, forks, cache, acache, rc, echo, runner, script, depends, tag, desc, dirsig
			exdir, exhow, exow, errhow, errntry, lang, beforeCmd, afterCmd, workdir, args, aggr
			callfront, callback, expect, expart, template, tplenvs, resume, nsub
		@props
			input, output, rc, echo, script, depends, beforeCmd, afterCmd, workdir, expect
			expart, template, channel, jobs, ncjobids, size, sets, procvars, suffix, logs
		"""
		# Don't go through __getattr__ and __setattr__
		# To get a prop  : proc.echo   --> proc.props['echo']
		# To get a config: proc.ppldir --> proc.config['ppldir']
		# To get a config that has a prop with the same name:
		#                  proc.config['echo'] = True
		# To set a prop  : proc.props['echo']  = {}
		# To set a config: proc.ppldir = '/path/to/workdir'
		# configs
		self.__dict__['config']   = {}
		# computed props
		self.__dict__['props']    = {}

		self.config['id']         = utils.varname() if id is None else id

		if ' ' in tag:
			raise ProcTagError("No space is allowed in tag ('{}'). Do you mean 'desc' instead of 'tag'?".format(tag))

		# The command to run after jobs start
		self.config['afterCmd']   = ""

		# The aggregation name of the process
		self.config['aggr']       = None
		# The extra arguments for the process
		self.config['args']       = utils.box.Box()

		# The command to run before jobs start
		self.config['beforeCmd']  = ""

		# The bring files that user specified
		# self.config['brings']     = {}
		# The computed brings
		# self.props['brings']      = {}

		# The cache option
		self.config['cache']      = True # False or 'export'

		# The callfront function of the process
		self.config['callfront']  = None
		# The callback function of the process
		self.config['callback']   = None

		# Do cleanup for cached jobs?
		self.config['acache']     = False

		# The output channel of the process
		self.props['channel']     = Channel.create()

		# The dependencies specified
		self.config['depends']    = []
		# The dependencies computed
		self.props['depends']     = []

		# The description of the job
		self.config['desc']       = desc

		# Whether expand directory to check signature
		self.config['dirsig']     = True

		# Whether to echo the stdout and stderr of the jobs to the screen
		# Could also be:
		# {
		#   'jobs':   0           # or [0, 1, 2], just echo output of those jobs.
		#   'type':   'stderr'    # only echo stderr. (stdout: only echo stdout; [don't specify]: echo all)
		# }
		# You can also specify a filter to the type
		# {
		#   'jobs':  0
		#   'type':  {'stderr': r'^Error'}	# only output lines starting with 'Error' in stderr
		# }
		# self.echo = True     <=> self.echo = { 'jobs': [0], 'type': {'stderr': None, 'stdout': None} }
		# self.echo = False    <=> self.echo = { 'jobs': [] }
		# self.echo = 'stderr' <=> self.echo = { 'jobs': [0], 'type': {'stderr': None} }
		# self.echo = {'jobs': 0, 'type': 'stdout'} <=> self.echo = { 'jobs': [0], 'type': {'stdout': None} }
		# self.echo = {'type': {'all': r'^output'}} <=> self.echo = { 'jobs': [0], 'type': {'stdout': r'^output', 'stderr': r'^output'} }
		self.config['echo']       = False
		# the computed echo option
		self.props['echo']        = {}

		# How to deal with the errors
		# retry, ignore, halt
		# halt to halt the whole pipeline, no submitting new jobs
		# terminate to just terminate the job itself
		self.config['errhow']     = "terminate" 
		# How many times to retry to jobs once error occurs
		self.config['errntry']    = 3
		# The directory to export the output files
		self.config['exdir']      = ''
		# How to export
		self.config['exhow']      = 'move' # link, copy, gzip
		# Whether to overwrite the existing files
		self.config['exow']       = True # overwrite

		# partial export, either the key of output file or the pattern
		self.config['expart']     = ''
		# computed expart
		self.props['expart']      = []

		# expect
		self.config['expect']     = ''
		# computed expect
		self.props['expect']      = None

		# How many jobs to run concurrently
		self.config['forks']      = 1

		# The input that user specified
		self.config['input']      = ''
		# The computed input
		self.props['input']       = {}

		# The jobs
		self.props['jobs']        = []

		# Default shell/language
		self.config['lang']       = 'bash'

		self.props['lock']        = None

		# max number of processes used to submit jobs
		#self.config['maxsubmit']  = int(cpu_count() / 2)

		# non-cached job ids
		self.props['ncjobids']    = []
		# number of threads used to build jobs and to check job cache status
		self.config['nsub']       = min(int(cpu_count() / 2), 16)

		self.props['origin']      = self.config['id']

		# The output that user specified
		self.config['output']     = ''
		# The computed output
		self.props['output']      = OrderedDict()

		# Where cache file and workdir located
		self.config['ppldir']     = path.abspath("./workdir")

		# data for proc.xxx in template
		self.props['procvars']    = {}

		# Valid return code
		self.config['rc']         = 0
		self.props['rc']          = [0]

		# which input file to use:
		# - indir:  The symbolic links in input directory
		# - origin: The original file specified by input channel
		# - real:   The realpath of the input file
		self.config['iftype']     = 'indir'

		# resume flag of the process
		# ''       : Normal, don't resume
		# 'skip+'  : Load data from previous run, pipeline resumes from future processes
		# 'resume+': Deduce input from 'skip+' processes
		# 'skip'   : Just skip, don't load data
		# 'resume' : Load data from previous run, resume pipeline
		self.config['resume']     = ''

		# Select the runner
		self.config['runner']     = 'local'
		# get the runner from the profile
		self.props['runner']      = 'local'

		# The script of the jobs
		self.config['script']     = ''
		# The computed script. Template object
		self.props['script']      = None

		# remember which property is set, then it won't be overwritten by configurations
		self.props['sets']        = []
		# The size of the process (# jobs)
		self.props['size']        = 0

		# The unique identify of the process
		self.props['suffix']      = ''

		# The tag of the job
		self.config['tag']        = tag

		# The template engine (name)
		self.config['template']   = ''
		# The template class
		self.props['template']    = None

		self.props['timer']       = None

		# The template environment
		self.config['tplenvs']    = utils.box.Box()

		# The workdir for the process
		self.config['workdir']    = ''
		# The computed workdir
		self.props['workdir']     = ''

		self.props['logs']        = {}

		for key, val in kwargs.items():
			self.__setattr__(key, val)

		from . import PyPPL
		PyPPL._registerProc(self)

	def __getattr__ (self, name):
		"""
		Get the value of a property in `self.props`
		It recognizes alias as well.
		@params:
			`name`: The name of the property
		@returns:
			The value of the property
		"""
		if not name in self.props \
			and not name in self.config \
			and not name in Proc.ALIAS \
			and not name.endswith ('Runner'):
			raise ProcAttributeError(name)

		if name in Proc.ALIAS:
			name = Proc.ALIAS[name]

		return self.props[name] if name in self.props else self.config[name]

	def __setattr__ (self, name, value):
		"""
		Set the value of a property in `self.config`
		@params:
			`name` : The name of the property.
			`value`: The new value of the property.
		"""
		if not name in self.config and not name in Proc.ALIAS and not name.endswith ('Runner'):
			raise ProcAttributeError(name, 'Cannot set attribute for process')
		
		# profile will be deprecated, use runner instead
		if name in Proc.DEPRECATED:
			logger.logger.warning(
				'Attribute "%s" is deprecated%s.', 
				name, 
				', use "{}" instead'.format(
					Proc.DEPRECATED[name]) if name in Proc.DEPRECATED and Proc.DEPRECATED[name] else '',
				extra = {'proc': self.name(False)}
			)

		if name in Proc.ALIAS:
			name = Proc.ALIAS[name]

		if name not in self.sets:
			self.sets.append(name)

		# depends have to be computed here, as it's used to infer the relation before run
		if name == 'depends':
			self.props['depends'] = []
			depends = list(value) if isinstance(value, tuple) else \
				value.ends if isinstance(value, Aggr) else \
				value if isinstance(value, list) else [value]

			for depend in depends:
				if isinstance(depend, Proc):
					if depend is self:
						raise ProcAttributeError(self.name(True), 'Process depends on itself')
					self.props['depends'].append(depend)
				elif isinstance(depend, Aggr):
					self.props['depends'].extend(depend.ends)
				else:
					raise ProcAttributeError(type(value).__name__, "Process dependents should be 'Proc/Aggr', not")

		elif name == 'script' and value.startswith('file:'):
			scriptpath = value[5:]
			if not path.isabs(scriptpath):
				from inspect import getframeinfo, stack
				caller = getframeinfo(stack()[1][0])
				scriptpath = path.join(path.dirname(path.realpath(caller.filename)), scriptpath)
			self.config[name] = "file:%s" % scriptpath

		elif name == 'args' or name == 'tplenvs':
			self.config[name] = utils.box.Box(value)

		elif name == 'input' \
			and self.config[name] \
			and not isinstance(value, utils.string_types) \
			and not isinstance(value, dict):
			# specify data
			previn  = self.config[name]
			prevkey = ', '.join(previn) if isinstance(previn, list) else \
					  ', '.join(previn.keys()) if isinstance(previn, dict) else previn
			self.config[name] = {prevkey: value}
			if isinstance(previn, dict) and len(previn) > 1:
				logger.logger.warning("Previous input is a dict with multiple keys. Now the key sequence is: %s", prevkey, extra = {'proc': self.name(False)})
		else:
			self.config[name] = value

	def __repr__(self):
		return '<Proc(%s) @ %s>' % (self.name(), hex(id(self)))

	# make Proc hashable
	def __hash__(self):
		return id(self)

	def __eq__(self, other):
		return id(self) == id(other)

	def __ne__(self, other):
		return not self.__eq__(other)

	def copy (self, tag=None, desc=None, id=None):
		"""
		Copy a process
		@params:
			`id`: The new id of the process, default: `None` (use the varname)
			`tag`:   The tag of the new process, default: `None` (used the old one)
			`desc`:  The desc of the new process, default: `None` (used the old one)
		@returns:
			The new process
		"""
		config = {}
		props  = {}

		for key in self.config.keys():
			if key == 'id':
				config[key]  = id if id else utils.varname()
			elif key == 'tag' and tag:
				config[key] = tag
			elif key == 'desc' and desc:
				config[key] = desc
			elif key == 'aggr':
				config[key] = None
			elif key in ['workdir', 'resume']:
				config[key] = ''
			#elif isinstance(config[key], Box):
			#	config[key] = Box()
			#	config[key].update(self.config[key])
			#elif isinstance(config[key], OrderedDict):
			#	config[key] = OrderedDict()
			#	config[key].update(self.config[key])
			elif isinstance(self.config[key], dict) and 'envs' not in key:
				config[key] = pycopy.deepcopy(self.config[key])
			else:
				config[key] = self.config[key]

		for key in self.props.keys():
			if key in ['depends', 'jobs', 'ncjobids']:
				props[key] = []
			elif key in ['procvars', 'logs']:
				props[key] = {}
			elif key == 'size':
				props[key] = 0
			elif key == 'origin':
				props['origin'] = self.origin
			elif key in ['workdir', 'suffix']:
				props[key] = ''
			elif key == 'channel':
				props[key] = Channel.create()
			elif key == 'sets':
				props[key] = self.props[key][:]
			#elif isinstance(props[key], Box):
			#	props[key] = Box()
			#	props[key].update(self.props[key])
			#elif isinstance(props[key], OrderedDict):
			#	props[key] = OrderedDict()
			#	props[key].update(self.props[key])
			elif isinstance(self.props[key], dict):
				props[key] = pycopy.deepcopy(self.props[key])
			else:
				props[key] = self.props[key]

		newproc = Proc()
		newproc.config.update(config)
		newproc.props.update(props)
		return newproc

	def _suffix (self):
		"""
		Calcuate a uid for the process according to the configuration
		The philosophy:
		1. procs from different script must have different suffix (sys.argv[0])
		2. procs from the same script:
			- procs with different id or tag have different suffix
			- procs with different input have different suffix (depends, input)
		@returns:
			The uniq id of the process
		"""
		if self.suffix: return self.suffix

		sigs = {}
		sigs['argv0'] = path.realpath(sys.argv[0])
		sigs['id']    = self.id
		sigs['tag']   = self.tag

		# lambda is not pickable
		if isinstance(self.config['input'], dict):
			sigs['input'] = pycopy.copy(self.config['input'])
			for key, val in self.config['input'].items():
				sigs['input'][key] = utils.funcsig(val) if callable(val) else val
		else:
			sigs['input'] = str(self.config['input'])

		# Add depends to avoid the same suffix for processes with the same depends but different input files
		# They could have the same suffix because they are using input callbacks
		# callbacks could be the same though even if the input files are different
		if self.depends:
			sigs['depends'] = [p.name(True) + '#' + p._suffix() for p in self.depends]

		signature = json.dumps(sigs, sort_keys = True)
		logger.logger.debug('Suffix decided by: %s', signature, extra = {'proc': self.name(False)})
		# suffix is only depending on where it comes from (sys.argv[0]) and it's name (id and tag) to avoid too many different workdirs being generated
		self.props['suffix'] = utils.uid(signature)
		#self.props['suffix'] = utils.uid(path.realpath(sys.argv[0]) + ':' + self.name(False))
		return self.suffix

	# self.resume != 'skip'
	def _tidyBeforeRun (self):
		"""
		Do some preparation before running jobs
		"""
		self._buildProps()
		try:
			if callable (self.callfront):
				logger.logger.debug("Calling callfront ...")
				self.callfront (self)
			self._buildInput()
			self._buildProcVars()
			self._buildOutput()
			self._buildScript()
			if self.resume not in ['skip+', 'resume']:
				self._saveSettings()
			self._buildJobs ()
			self.props['timer'] = time()
		except Exception: # pragma: no cover
			if self.lock.is_locked:
				self.lock.release()
			raise

	# self.resume != 'skip'
	def _tidyAfterRun (self):
		"""
		Do some cleaning after running jobs
		self.resume can only be:
		- '': normal process
		- skip+: skipped process but required workdir and data exists
		- resume: resume pipeline from this process, no requirement
		- resume+: get data from workdir/proc.settings, and resume
		"""
		if self.resume == 'skip+':
			if callable (self.callback):
				logger.logger.debug('Calling callback ...')
				self.callback (self)
		else: # '', resume, resume+
			# summarize jobs
			bfailedjobs = []
			sfailedjobs = []
			efailedjobs = []
			#killedjobs  = []
			successjobs = []
			cachedjobs  = []
			for job in self.jobs:
				if job.status == Job.STATUS_BUILTFAILED:
					bfailedjobs.append(job.index)
				elif job.status == Job.STATUS_SUBMITFAILED:
					sfailedjobs.append(job.index)
				elif job.status == Job.STATUS_DONE:
					successjobs.append(job.index)
				elif job.status == Job.STATUS_DONECACHED:
					cachedjobs.append(job.index)
				elif job.status == Job.STATUS_ENDFAILED:
					efailedjobs.append(job.index)
				#elif job.status == Job.STATUS_KILLING or job.status == Job.STATUS_KILLED:
				#	killedjobs.append(job.index)

			logger.logger.info(
				'Time: %s. Jobs (Cached: %s, Succ: %s, B.Fail: %s, S.Fail: %s, R.Fail: %s)',
				utils.formatSecs(time() - self.timer),
				len(cachedjobs),
				len(successjobs),
				len(bfailedjobs),
				len(sfailedjobs),
				len(efailedjobs),
				extra = {
					'loglevel': 'P.DONE' if len(cachedjobs) < self.size else 'CACHED',
					'proc'    : self.name(False),
					'pbar'    : 'next'
				})

			logger.logger.debug('Cached           : %s', utils.briefList(cachedjobs), extra = {'proc': self.name(False)})
			logger.logger.debug('Successful       : %s', utils.briefList(successjobs), extra = {'proc': self.name(False)})
			logger.logger.debug('Building failed  : %s', utils.briefList(bfailedjobs), extra = {'proc': self.name(False)})
			logger.logger.debug('Submission failed: %s', utils.briefList(sfailedjobs), extra = {'proc': self.name(False)})
			logger.logger.debug('Running failed   : %s', utils.briefList(efailedjobs), extra = {'proc': self.name(False)})

			donejobs = successjobs + cachedjobs
			failjobs = bfailedjobs + sfailedjobs + efailedjobs
			showjob  = failjobs[0] if failjobs else 0

			if len(donejobs) == self.size or self.errhow == 'ignore':
				if callable(self.callback):
					logger.logger.debug('Calling callback ...', extra = {'proc': self.name(False)})
					self.callback (self)
				if self.errhow == 'ignore':
					logger.logger.warning('Jobs failed but ignored.', extra = {'proc': self.name(False)})
					self.jobs[showjob].showError(len(failjobs))
			else:
				self.jobs[showjob].showError(len(failjobs))
				sys.exit(1)

	def name (self, aggr = True):
		"""
		Get my name include `aggr`, `id`, `tag`
		@returns:
			the name
		"""
		aggrName  = "@%s" % self.aggr if self.aggr and aggr else ""
		tag   = ".%s" % self.tag  if self.tag != "notag" else ""
		return "%s%s%s" % (self.id, tag, aggrName)

	def run (self, profile = None, profiles = None):
		"""
		Run the jobs with a configuration
		@params:
			`config`: The configuration
		"""
		self._readConfig (profile, profiles)

		if self.runner == 'dry':
			self.config['cache'] = False

		if self.resume == 'skip':
			logger.logger.info("Pipeline will resume from future processes.", extra = {
				'loglevel': 'skipped'
			})
		elif self.resume == 'skip+':
			self._tidyBeforeRun()
			logger.logger.info("Data loaded, pipeline will resume from future processes.", extra = {
				'loglevel': 'skipped'
			})
			try:
				self._tidyAfterRun ()
			finally:
				self.lock.release()
		else: # '', resume, resume+
			self._tidyBeforeRun ()

			try:
				self._runCmd('beforeCmd')
				if self.resume: # resume or resume+
					logger.logger.info("Previous processes skipped.", extra = {'loglevel': 'resumed'})
				self._runJobs()
				self._runCmd('afterCmd')
				self._tidyAfterRun ()
			finally:
				self.lock.release()

	def _buildProps (self):
		"""
		Compute some properties
		"""
		from . import PyPPL
		PyPPL._checkProc(self)

		# get Template
		if callable(self.config['template']):
			self.props['template'] = self.config['template']
		elif not self.config['template']:
			self.props['template'] = getattr(template, 'TemplateLiquid')
		else:
			self.props['template'] = getattr(template, 'Template' + self.config['template'].capitalize())

		# build rc
		if isinstance(self.config['rc'], utils.string_types):
			self.props['rc'] = [int(i) for i in utils.split(self.config['rc'], ',') if i]
		elif isinstance(self.config['rc'], int):
			self.props['rc'] = [self.config['rc']]
		else:
			self.props['rc'] = self.config['rc']

		# workdir
		if 'workdir' in self.sets:
			self.props['workdir'] = self.config['workdir']
		elif not self.props['workdir']:
			self.props['workdir'] = path.join(self.ppldir, "PyPPL.%s.%s.%s" % (self.id, self.tag, self._suffix()))
		logger.logger.info(self.workdir, extra = {'proc': self.name(False), 'loglevel': 'WORKDIR'})

		if not path.exists (self.workdir):
			if self.resume in ['skip+', 'resume'] and self.cache != 'export':
				raise ProcAttributeError(self.workdir, 'Cannot skip process, as workdir not exists')
			makedirs (self.workdir)

		self.props['lock'] = filelock.FileLock(path.join(self.workdir, 'proc.lock'))
		
		try:
			self.lock.acquire(timeout = 3)
		except filelock.Timeout: # pragma: no cover
			proclock = path.join(self.workdir, 'proc.lock')
			logger.logger.warning('Another instance of this process is running, waiting ...', extra = {'proc': self.name(False)})
			logger.logger.warning('If not, remove the process lock file (or hit Ctrl-c) and try again:', extra = {'proc': self.name(False)})
			logger.logger.warning('- %s', proclock, extra = {'proc': self.name(False)})
			try:
				self.lock.acquire()
			except KeyboardInterrupt:
				remove(path.join(proclock))
				self.lock.acquire()

		try:
			# exdir
			if self.exdir:
				self.config['exdir'] = path.abspath(self.exdir)
				if not path.exists (self.exdir):
					makedirs (self.exdir)

			# echo
			if self.config['echo'] in [True, False, 'stderr', 'stdout']:
				if self.config['echo'] is True:
					self.props['echo'] = { 'jobs': 0 }
				elif self.config['echo'] is False:
					self.props['echo'] = { 'jobs': [], 'type': 'all' }
				else:
					self.props['echo'] = { 'jobs': 0, 'type': {self.config['echo']: None} }
			else:
				self.props['echo'] = self.config['echo']

			if not 'jobs' in self.echo:
				self.echo['jobs'] = 0
			if isinstance(self.echo['jobs'], int):
				self.echo['jobs'] = [self.echo['jobs']]
			elif isinstance(self.echo['jobs'], utils.string_types):
				self.echo['jobs'] = [int(x.strip()) for x in self.echo['jobs'].split(',')]
			else:
				self.echo['jobs'] = list(self.echo['jobs'])

			if not 'type' in self.echo or self.echo['type'] == 'all':
				self.echo['type'] = {'stderr': None, 'stdout': None}
			if not isinstance(self.echo['type'], dict):
				# must be a string, either stderr or stdout
				self.echo['type'] = {self.echo['type']: None}
			if 'all' in self.echo['type']:
				self.echo['type'] = {'stderr': self.echo['type']['all'], 'stdout': self.echo['type']['all']}

			# don't cache for dry runner
			# runner is decided when run (in config)
			#if self.runner == 'dry':
			#	self.props['cache'] = False

			# expect
			self.props['expect'] = self.template(self.config['expect'], **self.tplenvs)

			# expart
			expart = utils.alwaysList(self.config['expart'])
			self.props['expart'] = [self.template(e, **self.tplenvs) for e in expart]

			logger.logger.debug('Properties set explictly: %s', self.sets, extra = {'proc': self.name(False)})
		except Exception: # pragma: no cover
			if self.lock.is_locked:
				self.lock.release()
			raise

	def _saveSettings (self):
		"""
		Save all settings in proc.settings, mostly for debug
		"""
		settingsfile = path.join(self.workdir, 'proc.settings')

		def pickKey(key):
			"""Pickle key"""
			return key if key else "''"

		def flatData(data):
			"""Flatten data"""
			if isinstance(data, dict):
				return {k:flatData(v) for k,v in data.items()}
			elif isinstance(data, list):
				return [flatData(v) for v in data]
			elif isinstance(data, tuple):
				return tuple(flatData(v) for v in data)
			elif isinstance(data, self.template):
				return str(data)
			elif callable(data):
				return utils.funcsig(data)
			return data

		def pickData(data, splitline = False, forcelist = False):
			"""Pickle data"""
			data = flatData(data)
			if isinstance(data, dict):
				ret = json.dumps(data, sort_keys = True)
			elif isinstance(data, list) and splitline:
				ret = ['\t' + json.dumps(d, sort_keys = True) for d in data]
			elif isinstance(data, list) and not splitline:
				ret = data
			elif forcelist:
				ret = pickData([data], splitline)
			else:
				ret = data
			return ret

		def dump(key, data):
			"""Dump data"""
			ret = ['[%s]' % key]
			if key in ['jobs', 'ncjobids', 'logs', 'lock']:
				return ''
			elif key == 'input':
				for k in sorted(data.keys()):
					v = val[k]
					ret.append('%s.type: %s' % (k, pickData(v['type'])))
					for j, ds in enumerate(v['data']):
						ret.append('%s.data#%s:' % (k, j))
						ret.extend(pickData(ds, splitline = True, forcelist = True))
			elif key == 'output':
				for k in sorted(data.keys()):
					t, ds = val[k]
					ret.append('%s.type: %s' % (k, pickData(t)))
					ret.append('%s.data: %s' % (k, pickData(ds)))
			elif key == 'depends':
				ret.append('procs: %s' % pickData([p.name() for p in data]))
			elif key == 'template':
				ret.append('name: %s' % pickData(data.__name__))
			elif key in ['args', 'procvars', 'echo'] or key.endswith('Runner'):
				for k in sorted(data.keys()):
					v = val[k]
					ret.append('%s: %s' % (pickKey(k), pickData(v)))
			#elif key == 'brings':
			#	for k in sorted(data.keys()):
			#		v = val[k]
			#		ret.append('%s: %s' % (pickKey(k), pickData(v)))
			elif key in ['script']:
				ret.append('value:')
				ret.extend(pickData(str(data).splitlines(), splitline = True))
			elif key == 'expart':
				for i,v in enumerate(data):
					ret.append('value_%s: %s' % (i, pickData((v))))
			else:
				ret.append('value: %s' % pickData(val))
			ret.append('\n')
			return '\n'.join([str(r) for r in ret])

		with open(settingsfile, 'w') as f:
			for key in sorted(self.props.keys()):
				val = self.props[key]
				f.write(dump(key, val))

		logger.logger.debug('Settings saved to: %s', settingsfile, extra = {'proc': self.name(False)})

	# self.resume != 'skip'
	def _buildInput (self):
		"""
		Build the input data
		Input could be:
		1. list: ['input', 'infile:file'] <=> ['input:var', 'infile:path']
		2. str : "input, infile:file" <=> input:var, infile:path
		3. dict: {"input": channel1, "infile:file": channel2}
		   or    {"input:var, input:file" : channel3}
		for 1,2 channels will be the combined channel from dependents, if there is not dependents, it will be sys.argv[1:]
		"""
		self.props['input'] = {}

		if self.resume in ['skip+', 'resume']:
			psfile = path.join(self.workdir, 'proc.settings')
			if not path.isfile(psfile):
				raise ProcInputError(psfile, 'Cannot parse input for skip+/resume process, no such file')

			cp = utils.ConfigParser()
			cp.optionxform = str
			cp.read(psfile)
			self.props['size'] = int(json.loads(cp.get('size', 'value')))

			indata = OrderedDict(cp.items('input'))
			intype = ''
			inname = ''
			for key in indata.keys():
				if key.endswith('.type'):
					intype = indata[key]
					inname = key[:-5]
					self.props['input'][inname] = {
						'type': intype,
						'data': []
					}
				elif key.startswith(inname + '.data#'):
					if intype in Proc.IN_FILESTYPE:
						data = [json.loads(s) for s in filter(None, indata[key].splitlines())]
					else:
						data = json.loads(indata[key].strip())
					self.props['input'][inname]['data'].append(data)
			self.props['jobs'] = [None] * self.size
		else:
			indata = self.config['input']
			if not isinstance (indata, dict):
				indata   = ','.join(utils.alwaysList(indata))
				indata   = {
					indata: Channel.fromChannels (*[d.channel for d in self.depends]) \
						if self.depends else Channel.fromArgv()
				}

			inkeys   = list(indata.keys())
			pinkeys  = []
			pintypes = []
			for key in utils.alwaysList(inkeys):
				if ':' not in key:
					pinkeys.append(key)
					pintypes.append(Proc.IN_VARTYPE[0])
				else:
					k, t = key.split(':')
					if t not in Proc.IN_VARTYPE + Proc.IN_FILESTYPE + Proc.IN_FILETYPE:
						raise ProcInputError(t, 'Unknown input type')
					pinkeys.append(k)
					pintypes.append(t)

			invals = Channel.create()
			for inkey in inkeys:
				inval = indata[inkey]
				if callable(inval):
					inval = inval (*[d.channel for d in self.depends] if self.depends else Channel.fromArgv())
					invals = invals.cbind(inval)
				elif isinstance(inval, Channel):
					invals = invals.cbind(inval)
				else:
					invals = invals.cbind(Channel.create(inval))
			self.props['size'] = invals.length()
			self.props['jobs'] = [None] * self.size

			# support empty input
			pinkeys = list(filter(None, pinkeys))

			wdata   = invals.width()
			if len(pinkeys) < wdata:
				logger.logger.warning('Not all data are used as input, %s column(s) wasted.', (wdata - len(pinkeys)))
			for i, inkey in enumerate(pinkeys):
				self.props['input'][inkey] = {}
				self.props['input'][inkey]['type'] = pintypes[i]
				if i < wdata:
					self.props['input'][inkey]['data'] = invals.flatten(i)
				else:
					logger.logger.warning('No data found for input key "%s", use empty strings/lists instead.', inkey)
					self.props['input'][inkey]['data'] = [[] if pintypes[i] in Proc.IN_FILESTYPE else ''] * self.size

	def _buildProcVars (self):
		"""
		Build proc attribute values for template rendering,
		and also echo some out.
		"""
		show    = ['size', 'args']
		if self.runner != 'local':
			show.append('runner')
		hide    = ['desc', 'id', 'sets', 'tag', 'suffix', 'workdir', 'aggr', 'input', 'output', 'depends', 'script']
		nokeys  = ['tplenvs', 'input', 'output', 'depends', 'lock', 'jobs']
		allkeys = [key for key in set(self.props.keys()) | set(self.config.keys())]
		pvkeys  = [
			key for key in allkeys \
			if key in show or (key in self.sets and key not in hide)
		]

		procvars = utils.box.Box()
		procargs = utils.box.Box()

		alias   = { val:key for key, val in Proc.ALIAS.items() }
		maxlen  = 0
		propout = {}
		for key in allkeys:
			val = getattr(self, key)
			if key == 'args':
				procvars['args'] = val
				procargs         = val
				if val: 
					maxlen = max(maxlen, max([len(k) for k in val.keys()]))
			elif key == 'runner':
				procvars[key] = val
				maxlen        = max(maxlen, len(key))
				if val == self.config['runner']:
					propout[key]  = val
				else:
					propout[key]  = val + ' [profile: %s]' % self.config['runner']
			elif key in pvkeys:
				procvars[key] = val
				maxlen        = max(maxlen, len(key))
				propout[key]  = (repr(val) + ' [%s]' % alias[key]) if key in alias else repr(val)
			elif key not in nokeys:
				procvars[key] = val
		for key in sorted(procargs.keys()):
			logger.logger.info('%s => %r', key.ljust(maxlen), procargs[key], extra = {
				'loglevel': 'p.args',
				'proc': self.name(False)
			})
		for key in sorted(propout.keys()):
			logger.logger.info('%s => %s', key.ljust(maxlen), propout[key], extra = {
				'loglevel': 'p.props',
				'proc': self.name(False)
			})
		self.props['procvars'] = {'proc': procvars, 'args': procargs}

	def _buildOutput(self):
		"""
		Build the output data templates waiting to be rendered.
		"""
		output = self.config['output']
		if isinstance(output, utils.string_types):
			output = utils.split(output, ',')
		if isinstance(output, list):
			output = list(filter(None, utils.alwaysList(output)))

		outdict = OrderedDict()
		if isinstance(output, list):
			for op in output:
				ops = utils.split(op, ':')
				lenops = len(ops)
				if lenops < 2:
					raise ProcOutputError(op, 'One of <key>:<type>:<value> missed for process output in')
				elif lenops > 3:
					raise ProcOutputError(op, 'Too many parts for process output in')
				outdict[':'.join(ops[:-1])] = ops[-1]
		else:
			outdict = self.config['output']

		if not isinstance(outdict, OrderedDict):
			raise ProcOutputError(type(outdict).__name__, 'Process output should be str/list/OrderedDict, not')

		for key, val in outdict.items():
			kparts = utils.split(key, ':')
			lparts = len(kparts)
			if lparts == 1:
				k, t = key, Proc.OUT_VARTYPE[0]
			elif lparts == 2:
				k, t = kparts
			else:
				raise ProcOutputError(key, 'Too many parts for process output key in')

			if t not in Proc.OUT_DIRTYPE + Proc.OUT_FILETYPE + Proc.OUT_VARTYPE + Proc.OUT_STDOUTTYPE + Proc.OUT_STDERRTYPE:
				raise ProcOutputError(t, 'Unknown output type')
			self.props['output'][k] = (t, self.template(val, **self.tplenvs))

	def _buildScript(self):
		"""
		Build the script template waiting to be rendered.
		"""
		script = self.config['script'].strip()

		if not script:
			logger.logger.warning('No script specified', extra = {'proc': self.name(False)})

		if script.startswith ('file:'):
			tplfile = script[5:].strip()
			if not path.exists (tplfile):
				raise ProcScriptError (tplfile, 'No such template file')
			logger.logger.debug("Using template file: %s", tplfile, extra = {'proc': self.name(False)})
			with open(tplfile) as f:
				script = f.read().strip()
		
		# original lines
		olines = script.splitlines()
		# new lines
		nlines   = []
		indent   = ''
		modeline = ''
		for i, line in enumerate(olines):
			if i == 0 and line.lstrip().startswith('{%') \
				and line.lstrip()[2:].lstrip().startswith('mode'):
				modeline = line + '\n'
				continue
			if '# PYPPL INDENT REMOVE' in line:
				indent = line[:-len(line.lstrip())]
			elif '# PYPPL INDENT KEEP' in line:
				indent = ''
			elif indent and line.startswith(indent):
				nlines.append(line[len(indent):])
			else:
				nlines.append(line)

		if not nlines or not nlines[0].startswith('#!'):
			nlines.insert(0, '#!/usr/bin/env ' + self.lang)

		self.props['script'] = self.template(modeline + '\n'.join(nlines) + '\n', **self.tplenvs)

	def _buildJobs (self):
		"""
		Build the jobs.
		"""
		self.props['channel'] = Channel.create([None] * self.size)
		if self.size == 0:
			logger.logger.warning('No data found for jobs, process will be skipped.', extra = {'proc': self.name(False)})
			return
		
		from . import PyPPL
		if self.runner not in PyPPL.RUNNERS:
			raise ProcAttributeError('No such runner: {}.'.format(self.runner))
		config = {
			'workdir'   : self.workdir,
			'runner'    : PyPPL.RUNNERS[self.runner],
			'runnerOpts': {key: val for key, val in self.config.items() if key.endswith('Runner')},
			'procvars'  : self.procvars,
			'procsize'  : self.size,
			'echo'      : self.echo,
			'input'     : self.input,
			'output'    : self.output,
			'iftype'    : self.iftype,
			'script'    : self.script,
			'errntry'   : self.errntry,
			'errhow'    : self.errhow,
			'expect'    : self.expect,
			'exhow'     : self.exhow,
			'exow'      : self.exow,
			'expart'    : self.expart,
			'exdir'     : self.exdir,
			'acache'    : self.acache,
			'rcs'       : self.rc,
			'cache'     : self.cache,
			'dirsig'    : self.dirsig,
			'proc'      : self.name(False),
			'tag'       : self.tag,
			'suffix'    : self.suffix
		}
		for i in range(self.size):
			self.jobs[i] = Job(i, config)

	def _readConfig (self, profile, profiles):
		"""
		Read the configuration
		@params:
			`config`: The configuration
		"""
		if 'runner' in self.sets:
			profile = self.config['runner']
		else:
			profile = profile or self.config['runner']

		profiles = profiles or {
			'default': {'runner': 'local'}
		}
		if 'default' not in profiles:
			profiles['default'] = {'runner': 'local'}
		
		config = profiles['default']

		if isinstance(profile, dict):
			utils.dictUpdate(config, profile)
			if 'runner' not in config:
				config['runner'] = 'local'
		else:
			if profile in profiles:
				utils.dictUpdate(config, profiles[profile])
				if 'runner' not in config:
					config['runner'] = 'local' if profile == 'default' else profile
			else:
				config['runner'] = profile

		self.config['runner'] = profile
		self.props['runner']  = config['runner']
		del config['runner']
		
		for key, val in config.items():
			if key in self.sets:
				continue
			
			if key in Proc.ALIAS:
				key = Proc.ALIAS[key]
			self.config[key] = val

	def _runCmd (self, key):
		"""
		Run the `beforeCmd` or `afterCmd`
		@params:
			`key`: "beforeCmd" or "afterCmd"
		@returns:
			The return code of the command
		"""
		if not self.config[key]: return
		cmdstr = self.template(self.config[key], **self.tplenvs).render(self.procvars)
		logger.logger.info('Running <%s> ...', key, extra = {'proc': self.name(False)})

		c = utils.cmd.run(cmdstr, bg = True, shell = True, executable = '/bin/bash')
		for line in iter(c.p.stdout.readline, ''):
			logger.logger.info ('[ CMDOUT] %s', line.rstrip("\n"), extra = {'proc': self.name(False)})
		for line in iter(c.p.stderr.readline, ''):
			logger.logger.info ('[ CMDERR] %s', line.rstrip("\n"), extra = {'proc': self.name(False)})
		c.run()
		if c.rc != 0:
			raise ProcRunCmdError(cmdstr, key)

	def _runJobs (self):
		"""
		Submit and run the jobs
		"""
		Jobmgr(self.jobs, {
			'nsub' : min(self.nsub, self.forks, self.size),
			'forks': min(self.forks, self.size),
			'proc' : self.name(False),
			'lock' : self.lock._lock_file
		})

		self.props['channel'] = Channel.create([
			tuple(job.data.o.values())
			for job in self.jobs
		])
		if self.jobs:
			self.channel.attach(*self.jobs[0].data.o.keys())
