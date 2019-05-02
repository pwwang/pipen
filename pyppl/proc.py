"""
proc module for PyPPL
"""
import sys
import yaml
import copy as pycopy
from time import time
from collections import OrderedDict
from os import path, makedirs, remove
from box import Box
import filelock
from simpleconf import NoSuchProfile
from .logger import logger
from .job import Job
from .jobmgr import Jobmgr
from .aggr import Aggr
from .channel import Channel
from .exceptions import ProcTagError, ProcAttributeError, ProcInputError, ProcOutputError, \
	ProcScriptError, ProcRunCmdError
from . import utils, template

class Proc (object):
	"""
	The Proc class defining a process

	@static variables:
		`ALIAS`:         The alias for the properties
		`DEPRECATED`:    Deprecated property names

		`OUT_VARTYPE`:    Variable types for output
		`OUT_FILETYPE`:   File types for output
		`OUT_DIRTYPE`:    Directory types for output
		`OUT_STDOUTTYPE`: Stdout types for output
		`OUT_STDERRTYPE`: Stderr types for output

		`IN_VARTYPE`:   Variable types for input
		`IN_FILETYPE`:  File types for input
		`IN_FILESTYPE`: Files types for input

		`EX_GZIP`: `exhow` value to gzip output files while exporting them
		`EX_COPY`: `exhow` value to copy output files while exporting them
		`EX_MOVE`: `exhow` value to move output files while exporting them
		`EX_LINK`: `exhow` value to link output files while exporting them
	"""

	# for future use, shortcuts
	ALIAS = {
		'envs'   : 'tplenvs',
		'preCmd' : 'beforeCmd',
		'postCmd': 'afterCmd'
	}
	# deprecated
	DEPRECATED = {}

	OUT_VARTYPE    = ['var']
	OUT_FILETYPE   = ['file', 'path']
	OUT_DIRTYPE    = ['dir', 'folder']
	OUT_STDOUTTYPE = ['stdout']
	OUT_STDERRTYPE = ['stderr']

	IN_VARTYPE   = ['var']
	IN_FILETYPE  = ['file', 'path', 'dir', 'folder']
	IN_FILESTYPE = ['files', 'paths', 'dirs', 'folders']

	EX_GZIP = ['gzip', 'gz']
	EX_COPY = ['copy', 'cp']
	EX_MOVE = ['move', 'mv']
	EX_LINK = ['link', 'symlink', 'symbol']

	# shorten paths in logs
	SHORTPATH = {'cutoff': 0, 'keep': 1}

	def __init__ (self, id = None, tag = 'notag', desc = 'No description.', **kwargs):
		"""
		Constructor
		@params:
			`tag`     : The tag of the process
			`desc`    : The description of the process
			`id`      : The identify of the process
			`**kwargs`: Other properties of the process, which can be set by `proc.xxx` later.
		@config:
			id, input, output, ppldir, forks, cache, acache, rc, echo, runner, script, depends, tag, desc, dirsig
			exdir, exhow, exow, errhow, errntry, lang, beforeCmd, afterCmd, workdir, args, aggr
			callfront, callback, expect, expart, template, tplenvs, resume, nthread
		@props
			input, output, rc, echo, script, depends, beforeCmd, afterCmd, workdir, expect
			expart, template, channel, jobs, ncjobids, size, sets, procvars, suffix
		"""
		# Do not go through __getattr__ and __setattr__
		# Get configuration from config
		self.__dict__['config']   = utils.config.copy()
		# computed props
		self.__dict__['props']    = Box(box_intact_types = [Channel])

		# The id (actually, it's the showing name) of the process
		self.config.id = id if id else utils.varname()

		if ' ' in tag:
			raise ProcTagError("No space is allowed in tag ('{}'). Do you mean 'desc' instead of 'tag'?".format(tag))

		# The aggregation name of the process, not configurable
		self.config.aggr       = None
		# The extra arguments for the process
		self.config.args       = utils.config.args.copy()
		# The callfront function of the process
		self.config.callfront  = None
		# The callback function of the process
		self.config.callback   = None
		# The output channel of the process
		self.props.channel     = Channel.create()
		# The dependencies specified
		self.config.depends    = []
		# The dependencies computed
		self.props.depends     = []
		# the computed echo option
		self.props.echo        = {}
		# computed expart
		self.props.expart      = []
		# computed expect
		self.props.expect      = None
		# The input that user specified
		self.config.input      = ''
		# The computed input
		self.props.input       = {}
		# The jobs
		self.props.jobs        = []
		# The locker for the process
		self.props.lock        = None
		# non-cached job ids
		self.props.ncjobids    = []
		# The original name of the process if it's copied
		self.props.origin      = self.config.id
		# The output that user specified
		self.config.output     = ''
		# The computed output
		self.props.output      = Box(ordered_box=True)
		# data for proc.xxx in template
		self.props.procvars    = {}
		# Valid return code
		self.props.rc          = [0]

		# which input file to use:
		# - indir:  The symbolic links in input directory
		# - origin: The original file specified by input channel
		# - real:   The realpath of the input file
		#self.config.iftype     = 'indir'

		# resume flag of the process
		# ''       : Normal, do not resume
		# 'skip+'  : Load data from previous run, pipeline resumes from future processes
		# 'resume+': Deduce input from 'skip+' processes
		# 'skip'   : Just skip, do not load data
		# 'resume' : Load data from previous run, resume pipeline
		self.config.resume     = ''
		# get the runner from the profile
		self.props.runner      = 'local'
		# The computed script. Template object
		self.props.script      = None
		# The size of the process (# jobs)
		self.props.size        = 0
		# The unique identify of the process
		self.props.suffix      = ''
		# The template class
		self.props.template    = None
		# timer for running time
		self.props.timer       = None
		# The template environment
		self.config.tplenvs    = utils.config.get('tplenvs', utils.config.get('envs', Box())).copy()
		# The computed workdir
		self.props.workdir     = ''

		# update the conf with kwargs
		self.config.update(dict(tag = tag, desc = desc, **kwargs))
		# remember which property is set, then it will not be overwritten by configurations, do not put any values here because we want
		# the kwargs to be overwritten by the configurations but keep the values set by:
		# p.xxx = xxx
		self.props.sets        = set()

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

		if name in self.props or name in self.config:
			return self.props.get(name, self.config.get(name))

		if name in Proc.ALIAS:
			name = Proc.ALIAS[name]

		return self.props.get(name, self.config.get(name))

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
			logger.warning(
				'Attribute "%s" is deprecated%s.',
				name,
				', use "{}" instead'.format(
					Proc.DEPRECATED[name]
				) if name in Proc.DEPRECATED and Proc.DEPRECATED[name] else '',
				proc = self.id
			)

		if name in Proc.ALIAS:
			name = Proc.ALIAS[name]

		self.sets.add(name)

		# depends have to be computed here, as it's used to infer the relation before run
		if name == 'depends':
			self.props.depends = []
			depends = list(value) if isinstance(value, tuple) else \
				value.ends if isinstance(value, Aggr) else \
				value if isinstance(value, list) else [value]

			for depend in depends:
				if isinstance(depend, Proc):
					if depend is self:
						raise ProcAttributeError(self.name(True), 'Process depends on itself')
					self.props.depends.append(depend)
				elif isinstance(depend, Aggr):
					self.props.depends.extend(depend.ends)
				elif isinstance(depend, list):
					self.props.depends.extend(depend)
				else:
					raise ProcAttributeError(type(value).__name__, "Process dependents should be 'Proc/Aggr', not")

		elif name == 'script' and value.startswith('file:'):
			scriptpath = value[5:]
			if not path.isabs(scriptpath):
				from inspect import getframeinfo, stack
				caller = getframeinfo(stack()[1][0])
				scriptdir = path.dirname(path.abspath(caller.filename))
				if not path.isfile(path.join(scriptdir, scriptpath)):
					scriptdir = path.dirname(path.realpath(caller.filename))
				scriptpath = path.join(scriptdir, scriptpath)
			self.config[name] = "file:%s" % scriptpath

		elif name == 'args' or name == 'tplenvs':
			self.config[name] = Box(value)

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
				logger.warning("Previous input is a dict with multiple keys. Now the key sequence is: %s", prevkey, proc = self.id)
		elif name == 'runner':
			self.config[name] = value
			self.props[name]  = value
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

	# pylint: disable=invalid-name
	def copy (self, id = None, tag = None, desc = None):
		"""
		Copy a process
		@params:
			`id`: The new id of the process, default: `None` (use the varname)
			`tag`:   The tag of the new process, default: `None` (used the old one)
			`desc`:  The desc of the new process, default: `None` (used the old one)
		@returns:
			The new process
		"""
		conf    = {}
		props   = {}
		newsets = set()
		if id:
			newsets.add('id')
		if tag:
			newsets.add('tag')
		if desc:
			newsets.add('desc')

		for key in self.config.keys():
			if key == 'id':
				conf[key]  = id if id else utils.varname()
			elif key == 'tag' and tag:
				conf[key] = tag
			elif key == 'desc' and desc:
				conf[key] = desc
			elif key == 'aggr':
				conf[key] = None
			elif key in ['workdir', 'resume']:
				conf[key] = ''
			elif isinstance(self.config[key], dict) and 'envs' not in key:
				conf[key] = pycopy.deepcopy(self.config[key])
			else:
				conf[key] = self.config[key]

		for key in self.props.keys():
			if key in ['depends', 'jobs', 'ncjobids']:
				props[key] = []
			elif key in ['procvars']:
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
				props[key] = self.props[key].copy() | newsets
			elif isinstance(self.props[key], dict):
				props[key] = pycopy.deepcopy(self.props[key])
			else:
				props[key] = self.props[key]

		newproc = Proc()
		newproc.config.update(conf)
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

		sigs = Box(ordered_box = True)
		sigs.argv0 = path.realpath(sys.argv[0])
		sigs.id    = self.id
		sigs.tag   = self.tag

		# lambda is not pickable
		if isinstance(self.config.input, dict):
			sigs.input = pycopy.copy(self.config.input)
			for key, val in self.config.input.items():
				sigs.input[key] = utils.funcsig(val) if callable(val) else val
		else:
			sigs.input = str(self.config.input)

		# Add depends to avoid the same suffix for processes with the same depends but different input files
		# They could have the same suffix because they are using input callbacks
		# callbacks could be the same though even if the input files are different
		if self.depends:
			sigs.depends = [p.name(True) + '#' + p._suffix() for p in self.depends]

		signature = sigs.to_json()
		logger.debug('Suffix decided by: %s', signature, proc = self.id)
		# suffix is only depending on where it comes from (sys.argv[0]) and it's name (id and tag) to avoid too many different workdirs being generated
		self.props.suffix = utils.uid(signature)
		#self.props.suffix = utils.uid(path.realpath(sys.argv[0]) + ':' + self.id)
		return self.suffix

	# self.resume != 'skip'
	def _tidyBeforeRun (self):
		"""
		Do some preparation before running jobs
		"""
		self._buildProps()
		try:
			if callable (self.callfront):
				logger.debug("Calling callfront ...", proc = self.id)
				self.callfront (self)
			self._buildInput()
			self._buildProcVars()
			self._buildOutput()
			self._buildScript()
			if self.resume not in ['skip+', 'resume']:
				self._saveSettings()
			self._buildJobs ()
			self.props.timer = time()
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
				logger.debug('Calling callback ...', proc = self.id)
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

			(logger.P_DONE if len(cachedjobs) < self.size else logger.CACHED)(
				'Time: %s. Jobs (Cached: %s, Succ: %s, B.Fail: %s, S.Fail: %s, R.Fail: %s)',
				utils.formatSecs(time() - self.timer),
				len(cachedjobs),
				len(successjobs),
				len(bfailedjobs),
				len(sfailedjobs),
				len(efailedjobs),
				proc = self.id)

			logger.debug('Cached           : %s', utils.briefList(cachedjobs), proc = self.id)
			logger.debug('Successful       : %s', utils.briefList(successjobs), proc = self.id)
			logger.debug('Building failed  : %s', utils.briefList(bfailedjobs), proc = self.id)
			logger.debug('Submission failed: %s', utils.briefList(sfailedjobs), proc = self.id)
			logger.debug('Running failed   : %s', utils.briefList(efailedjobs), proc = self.id)

			donejobs = successjobs + cachedjobs
			failjobs = bfailedjobs + sfailedjobs + efailedjobs
			showjob  = failjobs[0] if failjobs else 0

			if len(donejobs) == self.size or self.errhow == 'ignore':
				if callable(self.callback):
					logger.debug('Calling callback ...', proc = self.id)
					self.callback (self)
				if self.errhow == 'ignore':
					logger.warning('Jobs failed but ignored.', proc = self.id)
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
		ret = '%s.%s' % (self.id, self.tag)
		ret = ''.join(ret.split('.notag', 1))
		return ret if aggr else ret.split('@', 1)[0]

	def run (self, profile = None, config = None):
		"""
		Run the jobs with a configuration
		@params:
			`config`: The configuration
		"""
		self._readConfig (profile, config)
		if self.runner == 'dry':
			self.config.cache = False

		if self.resume == 'skip':
			logger.skipped("Pipeline will resume from future processes.")
		elif self.resume == 'skip+':
			self._tidyBeforeRun()
			logger.skipped("Data loaded, pipeline will resume from future processes.")
			try:
				self._tidyAfterRun ()
			finally:
				self.lock.release()
		else: # '', resume, resume+
			self._tidyBeforeRun ()
			try:
				self._runCmd('preCmd')
				if self.resume: # resume or resume+
					logger.resumed("Previous processes skipped.")
				self._runJobs()
				self._runCmd('postCmd')
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
		if callable(self.config.template):
			self.props.template = self.config.template
		elif not self.config.template:
			self.props.template = getattr(template, 'TemplateLiquid')
		else:
			self.props.template = getattr(template, 'Template' + self.config.template.capitalize())

		# build rc
		if isinstance(self.config.rc, utils.string_types):
			self.props.rc = [int(i) for i in utils.split(self.config.rc, ',') if i]
		elif isinstance(self.config.rc, int):
			self.props.rc = [self.config.rc]
		else:
			self.props.rc = self.config.rc

		# workdir
		if 'workdir' in self.sets:
			self.props.workdir = self.config.workdir
		elif not self.props.workdir:
			self.props.workdir = path.join(self.ppldir, "PyPPL.%s.%s.%s" % (self.id, self.tag, self._suffix()))
		logger.workdir(utils.briefPath(self.workdir, **Proc.SHORTPATH), proc = self.id)

		if not path.exists (self.workdir):
			if self.resume in ['skip+', 'resume'] and self.cache != 'export':
				raise ProcAttributeError(self.workdir, 'Cannot skip process, as workdir not exists')
			makedirs (self.workdir)

		self.props.lock = filelock.FileLock(path.join(self.workdir, 'proc.lock'))

		try:
			self.lock.acquire(timeout = 3)
		except filelock.Timeout: # pragma: no cover
			proclock = path.join(self.workdir, 'proc.lock')
			logger.warning('Another instance of this process is running, waiting ...', proc = self.id)
			logger.warning('If not, remove the process lock file (or hit Ctrl-c) and try again:', proc = self.id)
			logger.warning('- %s', proclock, proc = self.id)
			try:
				self.lock.acquire()
			except KeyboardInterrupt:
				remove(path.join(proclock))
				self.lock.acquire()

		try:
			# exdir
			if self.exdir:
				self.config.exdir = path.abspath(self.exdir)
				if not path.exists (self.exdir):
					makedirs (self.exdir)

			# echo
			if self.config.echo in [True, False, 'stderr', 'stdout']:
				if self.config.echo is True:
					self.props.echo = { 'jobs': 0 }
				elif self.config.echo is False:
					self.props.echo = { 'jobs': [], 'type': 'all' }
				else:
					self.props.echo = { 'jobs': 0, 'type': {self.config.echo: None} }
			else:
				self.props.echo = self.config.echo

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

			# do not cache for dry runner
			# runner is decided when run (in config)
			#if self.runner == 'dry':
			#	self.props.cache = False

			# expect
			self.props.expect = self.template(self.config.expect, **self.tplenvs)

			# expart
			expart = utils.alwaysList(self.config.expart)
			self.props.expart = [self.template(e, **self.tplenvs) for e in expart]

			logger.debug('Properties set explictly: %s', self.sets, proc = self.id)

		except Exception: # pragma: no cover
			if self.lock.is_locked:
				self.lock.release()
			raise

	def _saveSettings (self):
		"""
		Save all settings in proc.settings, mostly for debug
		"""
		settingsfile = path.join(self.workdir, 'proc.settings.yaml')

		props           = self.props.copy()
		props.lock      = None
		props.template  = props.template.__name__
		props.expect    = str(props.expect)
		props.expart    = [str(ep) for ep in props.expart]
		props.depends   = [repr(p) for p in self.depends]
		props.script    = str(props.script)
		props.procvars  = {}
		props.output    = OrderedDict([(key, str(val)) for key, val in props.output.items()])
		props.to_yaml(filename = settingsfile)

		logger.debug('Settings saved to: %s', settingsfile, proc = self.id)

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
		self.props.input = OrderedDict()

		if self.resume in ['skip+', 'resume']:
			# read input from settings file
			settingsfile = path.join(self.workdir, 'proc.settings.yaml')
			if not path.isfile(settingsfile):
				raise ProcInputError(settingsfile, 'Cannot parse input for skip+/resume process, no such file')

			with open(settingsfile, 'r') as fset:
				cached_props = yaml.load(fset, Loader = yaml.Loader)

			self.props.size = int(cached_props.get('size', 0))
			self.props.input = cached_props.get('input', OrderedDict())
			self.props.jobs = [None] * self.size
		else:
			# parse self.config.input keys
			# even for skipped or resumed process
			# because we need to keep the order
			# however, yaml does not
			input_keys_and_types = []
			# string/list/tupl
			if not isinstance(self.config.input, dict):
				input_keys_and_types = utils.alwaysList(self.config.input) if self.config.input else []
			else: # either raw dict or OrderedDict
				input_keys_and_types = sum((
					utils.alwaysList(key)
					for key in self.config.input.keys()
				), [])

			input_keys  = []
			input_types = []
			for keytype in input_keys_and_types:
				if ':' not in keytype:
					input_keys.append(keytype)
					input_types.append(Proc.IN_VARTYPE[0])
				else:
					thekey, thetype = keytype.split(':', 1)
					if thetype not in Proc.IN_VARTYPE + Proc.IN_FILESTYPE + Proc.IN_FILETYPE:
						raise ProcInputError(thetype, 'Unknown input type')
					input_keys.append(thekey)
					input_types.append(thetype)
			del input_keys_and_types

			indata = self.config.input
			# no data specified, inherit from depends or argv
			if not isinstance(indata, dict):
				input_values = [Channel.fromChannels(
					*[d.channel for d in self.depends]
				) if self.depends else Channel.fromArgv()]
			else:
				input_values = list(indata.values())

			input_channel = Channel.create()
			for invalue in input_values:
				# a callback, on all channels
				if callable(invalue):
					input_channel = input_channel.cbind(
						invalue(*[d.channel for d in self.depends] if self.depends else Channel.fromArgv())
					)
				elif isinstance(invalue, Channel):
					input_channel = input_channel.cbind(invalue)
				else:
					input_channel = input_channel.cbind(Channel.create(invalue))

			self.props.size = input_channel.length()
			self.props.jobs = [None] * self.size

			# support empty input
			input_keys = list(filter(None, input_keys))

			data_width = input_channel.width()
			key_width  = len(input_keys)
			if key_width < data_width:
				logger.warning('Not all data are used as input, %s column(s) wasted.', (data_width - key_width), proc = self.id)
			# compose self.props.input
			for i, inkey in enumerate(input_keys):
				self.props.input[inkey] = {'type': input_types[i]}
				if i < data_width:
					self.props.input[inkey]['data'] = input_channel.flatten(i)
					continue
				logger.warning('No data found for input key "%s", use empty strings/lists instead.', inkey, proc = self.id)
				# initiate some data
				if input_types[i] in Proc.IN_FILESTYPE:
					self.props.input[inkey]['data'] = [[]] * self.size
				else:
					self.props.input[inkey]['data'] = [''] * self.size

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

		procvars = Box()
		procargs = Box()

		alias   = { val:key for key, val in Proc.ALIAS.items() }
		maxlen  = 0
		propout = {}
		for key in allkeys:
			val = getattr(self, key)
			if key == 'args':
				procvars['args'] = val
				procargs         = val
				if val:
					maxlen = max(maxlen, max([len(thekey) for thekey in val.keys()]))
			elif key == 'runner':
				procvars[key] = val
				maxlen        = max(maxlen, len(key))
				if val == self.config.runner:
					propout[key]  = val
				else:
					propout[key]  = val + ' [profile: %s]' % self.config.runner
			elif key == 'exdir':
				procvars[key] = val
				maxlen        = max(maxlen, len(key))
				propout[key]  = utils.briefPath(val, **Proc.SHORTPATH)
			elif key in pvkeys:
				procvars[key] = val
				maxlen        = max(maxlen, len(key))
				propout[key]  = (repr(val) + ' [%s]' % alias[key]) if key in alias else repr(val)
			elif key not in nokeys:
				procvars[key] = val
		for key in sorted(procargs.keys()):
			logger.p_args('%s => %r', key.ljust(maxlen), procargs[key], proc = self.id)
		for key in sorted(propout.keys()):
			logger.p_props('%s => %s', key.ljust(maxlen), propout[key], proc = self.id)
		self.props.procvars = {'proc': procvars, 'args': procargs}

	def _buildOutput(self):
		"""
		Build the output data templates waiting to be rendered.
		"""
		output = self.config.output
		if isinstance(output, utils.string_types):
			output = utils.split(output, ',')
		if isinstance(output, list):
			output = list(filter(None, utils.alwaysList(output)))

		outdict = OrderedDict()
		if isinstance(output, list):
			for out in output:
				ops = utils.split(out, ':')
				lenops = len(ops)
				if lenops < 2:
					raise ProcOutputError(out, 'One of <key>:<type>:<value> missed for process output in')
				elif lenops > 3:
					raise ProcOutputError(out, 'Too many parts for process output in')
				outdict[':'.join(ops[:-1])] = ops[-1]
		else:
			outdict = self.config.output

		if not isinstance(outdict, OrderedDict):
			raise ProcOutputError(type(outdict).__name__, 'Process output should be str/list/OrderedDict, not')

		for key, val in outdict.items():
			kparts = utils.split(key, ':')
			lparts = len(kparts)
			if lparts == 1:
				thekey, thetype = key, Proc.OUT_VARTYPE[0]
			elif lparts == 2:
				thekey, thetype = kparts
			else:
				raise ProcOutputError(key, 'Too many parts for process output key in')

			if thetype not in Proc.OUT_DIRTYPE + Proc.OUT_FILETYPE + Proc.OUT_VARTYPE + Proc.OUT_STDOUTTYPE + Proc.OUT_STDERRTYPE:
				raise ProcOutputError(thetype, 'Unknown output type')
			self.props.output[thekey] = (thetype, self.template(val, **self.tplenvs))

	def _buildScript(self):
		"""
		Build the script template waiting to be rendered.
		"""
		script = self.config.script.strip()
		if not script:
			logger.warning('No script specified', proc = self.id)

		if script.startswith ('file:'):
			tplfile = script[5:].strip()
			if not path.exists (tplfile):
				raise ProcScriptError (tplfile, 'No such template file')
			logger.debug("Using template file: %s", tplfile, proc = self.id)
			with open(tplfile) as ftpl:
				script = ftpl.read().strip()

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

		self.props.script = self.template(modeline + '\n'.join(nlines) + '\n', **self.tplenvs)

	def _buildJobs (self):
		"""
		Build the jobs.
		"""
		self.props.channel = Channel.create([None] * self.size)
		if self.size == 0:
			logger.warning('No data found for jobs, process will be skipped.', proc = self.id)
			return

		from . import PyPPL
		if self.runner not in PyPPL.RUNNERS:
			raise ProcAttributeError('No such runner: {}. If it is a profile, did you forget to specify a basic runner?'.format(self.runner))

		jobcfg = {
			'workdir'   : self.workdir,
			'runner'    : PyPPL.RUNNERS[self.runner],
			'runnerOpts': {key: val for key, val in self.config.items() if key.endswith('Runner')},
			'procvars'  : self.procvars,
			'procsize'  : self.size,
			'echo'      : self.echo,
			'input'     : self.input,
			'output'    : self.output,
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
			'proc'      : self.id,
			'tag'       : self.tag,
			'suffix'    : self.suffix
		}
		for i in range(self.size):
			self.jobs[i] = Job(i, jobcfg)

	def _readConfig (self, profile, config):
		"""
		Read the configuration
		@params:
			`config`: The configuration
		"""
		if not profile:
			return

		# configs have been set
		setconfigs = {key:self.config[key] for key in self.sets}
		self.config._load(config or {})
		if isinstance(profile, dict):
			profile['runner'] = profile.get('runner', self.config.runner)
			self.config._load(dict(
				__tmp__ = profile
			))
			self.config._use('__tmp__')
			self.config.update(setconfigs)
			# the real runner
			self.props.runner  = self.config.runner
			# the real profile
			self.config.runner = '__tmp__'
		else:
			try:
				self.config._use(profile, raise_exc = True)
				self.config.update(setconfigs)
				self.props.runner  = self.config.runner
				self.config.runner = profile
			except NoSuchProfile:
				self.config._load({
					profile: dict(runner = profile)
				})
				self.config._use(profile)
				self.config.update(setconfigs)
				self.props.runner  = self.config.runner
				self.config.runner = None

	def _runCmd (self, key):
		"""
		Run the `beforeCmd` or `afterCmd`
		@params:
			`key`: "beforeCmd" or "afterCmd"
		@returns:
			The return code of the command
		"""
		#if not self.config[key]: return
		cmdstr = self.template(getattr(self, key), **self.tplenvs).render(self.procvars).strip()

		if not cmdstr:
			return

		logger.info('Running <%s> ...', key, proc = self.id)

		cmd = utils.cmdy.bash(c = cmdstr, _iter = 'err')
		for err in cmd:
			logger.cmderr('  ' + err.rstrip("\n"), proc = self.id)
		for out in cmd.stdout.splitlines():
			logger.cmdout('  ' + out.rstrip("\n"), proc = self.id)

		if cmd.rc != 0:
			raise ProcRunCmdError(repr(cmdstr), key)

	def _runJobs (self):
		"""
		Submit and run the jobs
		"""
		Jobmgr(self.jobs, {
			'nthread': self.nthread,
			'forks'  : min(self.forks, self.size),
			'proc'   : self.id,
			'lock'   : self.lock._lock_file
		})

		self.props.channel = Channel.create([
			tuple(job.data.o.values())
			for job in self.jobs
		])
		if self.jobs:
			self.channel.attach(*self.jobs[0].data.o.keys())
