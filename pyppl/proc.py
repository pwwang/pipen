"""
proc module for PyPPL
"""
import sys
import copy as pycopy
from pathlib import Path
from time import time
from collections import OrderedDict
from os import path
import yaml
import filelock
from simpleconf import NoSuchProfile, Config
from .logger import logger
from .utils import Box, OBox, Hashable, fs
from .jobmgr import Jobmgr, STATES
from .procset import ProcSet
from .channel import Channel
from .exception import ProcTagError, ProcAttributeError, ProcInputError, ProcOutputError, \
	ProcScriptError, ProcRunCmdError
from . import utils, template
from .plugin import pluginmgr

class Proc(Hashable):
	"""@API
	The Proc class defining a process

	@static variables:
		ALIAS      (dict): The alias for the properties
		DEPRECATED (dict): Deprecated property names

		OUT_VARTYPE    (list): Variable types for output
		OUT_FILETYPE   (list): File types for output
		OUT_DIRTYPE    (list): Directory types for output
		OUT_STDOUTTYPE (list): Stdout types for output
		OUT_STDERRTYPE (list): Stderr types for output

		IN_VARTYPE   (list): Variable types for input
		IN_FILETYPE  (list): File types for input
		IN_FILESTYPE (list): Files types for input

		EX_GZIP (list): `exhow` value to gzip output files while exporting them
		EX_COPY (list): `exhow` value to copy output files while exporting them
		EX_MOVE (list): `exhow` value to move output files while exporting them
		EX_LINK (list): `exhow` value to link output files while exporting them
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

	# pylint: disable=redefined-builtin
	def __init__(self, id = None, tag = 'notag', desc = 'No description.', **kwargs):
		"""@API
		Proc constructor
		@params:
			tag  (str)   : The tag of the process
			desc (str)   : The description of the process
			id   (str)   : The identify of the process
			**kwargs: Other properties of the process, which can be set by `proc.xxx` later.
		"""
		# Do not go through __getattr__ and __setattr__
		# Get configuration from config
		self.__dict__['config'] = Config()
		# computed props
		self.__dict__['props'] = Box(box_intact_types = [list])

		defaultconfig = dict.copy(utils.config)
		# The id (actually, it's the showing name) of the process
		defaultconfig['id'] = id if id else utils.varname()
		if ' ' in tag:
			raise ProcTagError("No space allowed in tag.")
		if 'depends' in kwargs:
			raise ProcAttributeError("Attribute 'depends' has to be set using `__setattr__`")

		# The extra arguments for the process
		defaultconfig['args'] = dict.copy(defaultconfig['args'])
		# The callfront function of the process
		defaultconfig['callfront'] = None
		# The callback function of the process
		defaultconfig['callback'] = None
		# The dependencies specified
		defaultconfig['depends'] = []
		# The input that user specified
		defaultconfig['input'] = ''
		# The output that user specified
		defaultconfig['output'] = ''
		# resume flag of the process
		# ''       : Normal, do not resume
		# 'skip+'  : Load data from previous run, pipeline resumes from future processes
		# 'resume+': Deduce input from 'skip+' processes
		# 'skip'   : Just skip, do not load data
		# 'resume' : Load data from previous run, resume pipeline
		defaultconfig['resume'] = ''
		# The template environment, keep process indenpendent, even for the subconfigs
		defaultconfig['tplenvs'] = pycopy.deepcopy(
			defaultconfig.get('envs', defaultconfig['tplenvs']))

		# The output channel of the process
		self.props.channel = Channel.create()
		# The dependencies computed
		self.props.depends = []
		# the computed echo option
		self.props.echo = {}
		# computed expart
		self.props.expart = []
		# computed expect
		self.props.expect = None
		# The computed input
		self.props.input = {}
		# The jobs
		self.props.jobs = []
		# The locker for the process
		self.props.lock = None
		# non-cached job ids
		self.props.ncjobids = []
		# The original name of the process if it's copied
		self.props.origin = defaultconfig['id']
		# The computed output
		self.props.output = OBox()
		# data for proc.xxx in template
		self.props.procvars = {}
		# Valid return code
		self.props.rc = [0]
		# get the runner from the profile
		self.props.runner = 'local'
		# The computed script. Template object
		self.props.script = None
		# The unique identify of the process
		# cache the suffix
		self.props._suffix = ''
		# The template class
		self.props.template = None
		# timer for running time
		self.props.timer = None
		# The computed workdir
		self.props.workdir = ''
		# remember which property is set, then it will not be overwritten by configurations,
		# do not put any values here because we want
		# the kwargs to be overwritten by the configurations but keep the values set by:
		# p.xxx           = xxx
		self.props.sets = set()

		# update the conf with kwargs
		defaultconfig.update(dict(tag = tag, desc = desc, **kwargs))
		# collapse the loading trace, we don't need it anymore.
		self.config._load({'default': defaultconfig})

	def __getattr__(self, name):
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
			pass
		elif name in Proc.ALIAS:
			name = Proc.ALIAS[name]

		ret = pluginmgr.hook.procGetAttr(proc = self, name = name)
		if ret is None:
			return self.props.get(name, self.config.get(name))

		return ret

	def __setattr__(self, name, value):
		"""
		Set the value of a property in `self.config`
		@params:
			`name` : The name of the property.
			`value`: The new value of the property.
		"""
		if not name in self.config and not name in Proc.ALIAS and not name.endswith ('Runner'):
			raise ProcAttributeError(name, 'Cannot set attribute for process')

		# profile will be deprecated, use runner instead
		# currently nothing deprecated
		if name in Proc.DEPRECATED: # pragma: no cover
			logger.warning('Attribute "%s" is deprecated%s.', name,
				', use "{}" instead'.format(Proc.DEPRECATED[name]) \
					if name in Proc.DEPRECATED and Proc.DEPRECATED[name] else '',
				proc = self.id)

		if name in Proc.ALIAS:
			name = Proc.ALIAS[name]

		self.sets.add(name)

		# depends have to be computed here, as it's used to infer the relation before run
		if name == 'depends':

			self.props.depends = []
			depends = list(value) if isinstance(value, tuple) else \
				value.ends if isinstance(value, ProcSet) else \
				value if isinstance(value, list) else [value]

			for depend in depends:
				if isinstance(depend, Proc):
					if depend is self:
						raise ProcAttributeError(self.name(True), 'Process depends on itself')
					self.props.depends.append(depend)
				elif isinstance(depend, ProcSet):
					self.props.depends.extend(depend.ends)
				elif isinstance(depend, list):
					self.props.depends.extend(depend)
				else:
					raise ProcAttributeError(type(value).__name__,
						"Process dependents should be 'Proc/ProcSet', not")
			if depends:
				from . import PyPPL
				# only register the procs that will be involved.
				PyPPL._registerProc(self)

		elif name == 'script' and value.startswith('file:'):
			# convert relative path to absolute
			scriptpath = Path(value[5:])
			if not scriptpath.is_absolute():
				from inspect import getframeinfo, stack
				caller = getframeinfo(stack()[1][0])
				scriptdir = Path(caller.filename).parent.resolve()
				scriptpath = scriptdir / scriptpath
			if not scriptpath.is_file():
				raise ProcAttributeError(
					'Script file does not exist: %s' % scriptpath)
			self.config[name] = "file:%s" % scriptpath

		elif name == 'args' or name == 'tplenvs':
			self.config[name] = Box(value)

		elif name == 'input' \
			and self.config[name] \
			and not isinstance(value, str) \
			and not isinstance(value, dict):
			# specify data
			previn  = self.config[name]
			prevkey = ', '.join(previn) if isinstance(previn, list) else \
					  ', '.join(previn.keys()) if isinstance(previn, dict) else previn
			self.config[name] = {prevkey: value}
			if isinstance(previn, dict) and len(previn) > 1:
				logger.warning(
					"Previous input is a dict with multiple keys and key order may be changed.",
					proc = self.id)
				logger.warning("Now the key order is: %s" % prevkey, proc = self.id)
		elif name == 'runner':
			self.config[name] = value
			self.props[name]  = value
		elif name == 'tag' and (' ' in value or '@' in value):
			raise ProcAttributeError("No space or '@' is allowed in tag")
		else:
			self.config[name] = value
			# plugins can overwrite it
			pluginmgr.hook.procSetAttr(proc = self, name = name, value = value)

	def __repr__(self):
		return '<Proc(%s) @ %s>' %(self.name(), hex(id(self)))

	# pylint: disable=invalid-name
	def copy(self, id = None, tag = None, desc = None):
		"""@API
		Copy a process
		@params:
			id (str): The new id of the process, default: `None` (use the varname)
			tag (str):   The tag of the new process, default: `None` (used the old one)
			desc (str):  The desc of the new process, default: `None` (used the old one)
		@returns:
			(Proc): The new process
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

		for key in self.config:
			if key == 'id':
				conf[key] = id if id else utils.varname()
			elif key == 'tag' and tag:
				conf[key] = tag
			elif key == 'desc' and desc:
				conf[key] = desc
			elif key in ['workdir', 'resume']:
				conf[key] = ''
			elif isinstance(self.config[key], dict):
				conf[key] = pycopy.deepcopy(self.config[key])
			elif key == 'depends':
				continue
			else:
				conf[key] = self.config[key]

		for key in self.props:
			if key in ['depends', 'jobs', 'ncjobids']:
				props[key] = []
			elif key in ['procvars']:
				props[key] = {}
			elif key == 'origin':
				props['origin'] = self.origin
			elif key in ['workdir', '_suffix']:
				props[key] = ''
			elif key == 'channel':
				props[key] = Channel.create()
			elif key == 'sets':
				props[key] = self.props[key].copy() | newsets
			elif isinstance(self.props[key], dict):
				props[key] = pycopy.deepcopy(self.props[key])
			else:
				props[key] = self.props[key]

		newproc = Proc(**conf)
		newproc.depends = []
		dict.update(newproc.props, props)
		return newproc

	def name(self, procset = True):
		"""@API
		Get my name include `procset`, `id`, `tag`
		@params:
			procset (bool): Whether include the procset name or not.
		@returns:
			(str): the name
		"""
		tag = self.tag
		if '@' not in tag:
			tag += '@'
		tag, pst = tag.split('@')
		tag = '' if tag in ('notag', '') else '.' + tag
		pst = '@' + pst if pst else ''
		return self.id + tag + pst if procset else self.id + tag

	@property
	def procset(self):
		"""@API
		Get the name of the procset
		@returns:
			(str): The procset name
		"""
		parts = self.tag.split('@')
		if len(parts) == 1:
			return None
		return parts[1]

	@property
	def size(self):
		"""@API
		Get the size of the  process
		@returns:
			(int): The number of jobs
		"""
		return len(self.jobs)

	@property
	def suffix(self):
		"""@API
		Calcuate a uid for the process according to the configuration
		The philosophy:
		1. procs from different script must have different suffix (sys.argv[0])
		2. procs from the same script:
			- procs with different id or tag have different suffix
			- procs with different input have different suffix (depends, input)
		@returns:
			(str): The uniq id of the process
		"""
		if self.props._suffix:
			return self.props._suffix

		sigs = OBox()
		# use cmdy.which instead? what about "python test.py"
		sigs.argv0 = path.realpath(sys.argv[0])
		sigs.id    = self.id
		sigs.tag   = self.tag

		if isinstance(self.config.input, dict):
			sigs.input = pycopy.copy(self.config.input)
			for key, val in self.config.input.items():
				# lambda is not pickable
				# convert others to string to make sure it's pickable. Issue #65
				sigs.input[key] = utils.funcsig(val) if callable(val) else str(val)
		else:
			sigs.input = str(self.config.input)

		# Add depends to avoid the same suffix for processes with the same depends
		# but different input files
		# They could have the same suffix because they are using input callbacks
		# callbacks could be the same though even if the input files are different
		if self.depends:
			sigs.depends = [p.name(True) + '#' + p.suffix for p in self.depends]
		try:
			signature = sigs.to_json()
		except TypeError as exc: # pragma: no cover
			raise ProcInputError('Unexpected input data type: %s' % exc) from None
		logger.debug('Suffix decided by: %s' % signature, proc = self.id)
		# suffix is only depending on where it comes from (sys.argv[0]) and
		# it's name (id and tag) to avoid too many different workdirs being generated
		self.props._suffix = utils.uid(signature)
		#self.props.suffix = utils.uid(path.realpath(sys.argv[0]) + ':' + self.id)
		return self._suffix

	def _buildProps(self):
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
		if isinstance(self.config.rc, str):
			self.props.rc = [int(i) for i in utils.split(self.config.rc, ',') if i]
		elif isinstance(self.config.rc, int):
			self.props.rc = [self.config.rc]
		else:
			self.props.rc = self.config.rc

		# workdir
		if 'workdir' in self.sets:
			self.props.workdir = self.config.workdir
		elif not self.props.workdir:
			self.props.workdir = path.join(self.ppldir, "PyPPL.%s.%s.%s" %
				(self.id, self.tag, self.suffix))
		logger.workdir(utils.briefPath(self.workdir, self._log.shorten), proc = self.id)

		if not fs.exists(self.workdir):
			if self.resume in ['skip+', 'resume'] and self.cache != 'export':
				raise ProcAttributeError(self.workdir, 'Cannot skip process, as workdir not exists')
			fs.makedirs(self.workdir)

		self.props.lock = filelock.FileLock(path.join(self.workdir, 'proc.lock'))

		try:
			self.lock.acquire(timeout = 3)
		except filelock.Timeout: # pragma: no cover
			proclock = path.join(self.workdir, 'proc.lock')
			logger.warning('Another instance of this process is running, waiting ...',
				proc = self.id)
			logger.warning('If not, remove the process lock file (or hit Ctrl-c) and try again:',
				proc = self.id)
			logger.warning('- %s', proclock, proc = self.id)
			try:
				self.lock.acquire()
			except KeyboardInterrupt:
				fs.remove(path.join(proclock))
				self.lock.acquire()

		try:
			# exdir
			if self.exdir:
				self.config.exdir = path.abspath(self.exdir)
				if not fs.exists(self.exdir):
					fs.makedirs(self.exdir)

			# echo
			if self.config.echo in [True, False, 'stderr', 'stdout']:
				if self.config.echo is True:
					self.props.echo = Box({ 'jobs': 0 })
				elif self.config.echo is False:
					self.props.echo = Box({ 'jobs': [], 'type': 'all' })
				else:
					self.props.echo = Box({ 'jobs': 0, 'type': Box({self.config.echo: None}) })
			else:
				self.props.echo = Box(self.config.echo)

			if not 'jobs' in self.echo:
				self.echo['jobs'] = 0
			if isinstance(self.echo['jobs'], int):
				self.echo['jobs'] = [self.echo['jobs']]
			elif isinstance(self.echo['jobs'], str):
				self.echo['jobs'] = utils.expandNumbers(self.echo['jobs'])
			else:
				self.echo['jobs'] = list(self.echo['jobs'])

			if not 'type' in self.echo or self.echo['type'] == 'all':
				self.echo['type'] = {'stderr': None, 'stdout': None}
			if not isinstance(self.echo['type'], dict):
				# must be a string, either stderr or stdout
				self.echo['type'] = {self.echo['type']: None}
			if 'all' in self.echo['type']:
				self.echo['type'] = {
					'stderr': self.echo['type']['all'], 'stdout': self.echo['type']['all']}

			# do not cache for dry runner
			# runner is decided when run (in config)
			#if self.runner == 'dry':
			#	self.props.cache = False

			# expect
			self.props.expect = self.template(self.config.expect, **self.tplenvs)

			# expart
			expart = utils.alwaysList(self.config.expart)
			self.props.expart = [self.template(e, **self.tplenvs) for e in expart]

			logger.debug('Properties set explictly: %s' % self.sets, proc = self.id)

		except Exception: # pragma: no cover
			if self.lock.is_locked:
				self.lock.release()
			raise

	# self.resume != 'skip'
	def _buildInput(self):
		"""
		Build the input data
		Input could be:
		1. list: ['input', 'infile:file'] <=> ['input:var', 'infile:path']
		2. str : "input, infile:file" <=> input:var, infile:path
		3. dict: {"input": channel1, "infile:file": channel2}
		   or    {"input:var, input:file" : channel3}
		for 1,2 channels will be the combined channel from dependents,
			if there is not dependents, it will be sys.argv[1:]
		"""
		self.props.input = OrderedDict()

		if self.resume in ['skip+', 'resume']:
			# read input from settings file
			settingsfile = path.join(self.workdir, 'proc.settings.yaml')
			if not fs.isfile(settingsfile):
				raise ProcInputError(settingsfile,
					'Cannot parse input for skip+/resume process, no such file')

			with open(settingsfile, 'r') as fset:
				cached_props = yaml.load(fset, Loader = yaml.Loader)

			self.props.input = cached_props.get('input', OrderedDict())
			if self.props.input: # {'a': ('var', [1,2,3])}
				self.props.jobs = [None] * len(list(self.props.input.values())[0][1])
		else:
			indata = self.config.input
			# parse self.config.input keys
			# even for skipped or resumed process
			# because we need to keep the order
			# however, yaml does not
			# ['a:var', 'b:file', ...]
			input_keys_and_types = sum((utils.alwaysList(key) for key in indata), []) \
				if isinstance(indata, dict) else utils.alwaysList(indata) \
				if indata else []

			# {'a': 'var', 'b': 'file', ...}
			input_keytypes  = OrderedDict()
			for keytype in input_keys_and_types:
				if not keytype.strip():
					continue
				if ':' not in keytype:
					input_keytypes[keytype] = Proc.IN_VARTYPE[0]
				else:
					thekey, thetype = keytype.split(':', 1)
					if thetype not in Proc.IN_VARTYPE + Proc.IN_FILESTYPE + Proc.IN_FILETYPE:
						raise ProcInputError(thetype, 'Unknown input type')
					input_keytypes[thekey] = thetype
			del input_keys_and_types

			# no data specified, inherit from depends or argv
			input_values = list(indata.values()) \
				if isinstance(indata, dict) else [Channel.fromChannels(*[
					d.channel for d in self.depends])
					if self.depends else Channel.fromArgv()]
			input_channel = Channel.create()
			for invalue in input_values:
				# a callback, on all channels
				if callable(invalue):
					input_channel = input_channel.cbind(
						invalue(*[d.channel for d in self.depends] \
							if self.depends else Channel.fromArgv()))
				elif isinstance(invalue, Channel):
					input_channel = input_channel.cbind(invalue)
				else:
					input_channel = input_channel.cbind(Channel.create(invalue))

			self.props.jobs = [None] * input_channel.length()

			data_width = input_channel.width()
			key_width  = len(input_keytypes)
			if key_width < data_width:
				logger.warning('Not all data are used as input, %s column(s) wasted.',
					(data_width - key_width), proc = self.id)
			# compose self.props.input
			for i, inkey in enumerate(input_keytypes):
				intype = input_keytypes[inkey]
				self.props.input[inkey] = (intype, [])

				if i >= data_width:
					if intype in Proc.IN_FILESTYPE:
						self.props.input[inkey][1].extend([[]] * self.size)
					else:
						self.props.input[inkey][1].extend([''] * self.size)
					logger.warning('No data found for input key "%s"'
						', use empty strings/lists instead.' % inkey, proc = self.id)
				else:
					self.props.input[inkey][1].extend(input_channel.flatten(i))

	def _buildProcVars(self):
		"""
		Build proc attribute values for template rendering,
		and also echo some out.
		"""
		# attributes shown in log
		show    = {'size', 'runner'}
		# attributes hidden in log
		hide    = {'desc', 'id', 'sets', 'tag', 'suffix', 'workdir',
			'input', 'output', 'depends', 'script'}
		# keys should not be put in procvars for template rendering
		nokeys  = {'tplenvs', 'input', 'output', 'depends', 'lock', 'jobs', 'args',
				   '_log', '_flowchart', 'callback', 'callfront', 'channel', 'timer',
				   'ncjobids', '_suffix'}
		allkeys = set(self.props) | set(self.config) | {'size', 'suffix'}
		# preserved keys
		pvkeys  = {key for key in allkeys
			if key in show or (key in self.sets and key not in hide)}

		procvars = Box()
		procargs = self.args
		if not isinstance(procargs, Box):
			procargs = Box(procargs)

		alias   = { val:key for key, val in Proc.ALIAS.items() }
		maxlen  = 0 # used to calculate the alignment
		# props to be output in log
		propout = {}
		for key in allkeys:
			val = getattr(self, key)
			if key == 'args' and val:
				maxlen = max(maxlen, max(len(thekey) for thekey in val))
			elif key == 'runner':
				procvars[key] = val
				maxlen = max(maxlen, len(key))
				propout[key] = val if self.config.runner in (val, '__tmp__') \
					else val + ' [profile: %s]' % self.config.runner
			elif key == 'exdir':
				procvars[key] = val
				if val:
					maxlen = max(maxlen, len(key))
					propout[key] = utils.briefPath(val, self._log.shorten)
			elif key in pvkeys:
				procvars[key] = val
				maxlen = max(maxlen, len(key))
				propout[key] = val
			elif key not in nokeys:
				procvars[key] = val
		for key in sorted(propout):
			logger.p_props('%s => %s' % (key.ljust(maxlen),
					utils.formatDict(propout[key], keylen = maxlen, alias = alias.get(key))),
				proc = self.id)
		for key in sorted(procargs):
			logger.p_args('%s => %s' % (key.ljust(maxlen),
					utils.formatDict(procargs[key], keylen = maxlen)),
				proc = self.id)
		self.props.procvars = {'proc': procvars, 'args': procargs}

	def _buildOutput(self):
		"""
		Build the output data templates waiting to be rendered.
		"""
		# ['a:{{i.invar}}', 'b:file:{{i.infile|fn}}']
		output = self.config.output
		if isinstance(output, (list, str)):
			outlist = list(filter(None, utils.alwaysList(output)))
			output  = OrderedDict()
			for out in outlist:
				outparts = utils.split(out, ':')
				lenparts = len(outparts)
				if lenparts < 2:
					raise ProcOutputError(out,
						'One of <key>:<type>:<value> missed for process output in')
				if lenparts > 3:
					raise ProcOutputError(out, 'Too many parts for process output in')
				output[':'.join(outparts[:-1])] = outparts[-1]
		elif not (isinstance(output, (OBox, OrderedDict)) or (
			isinstance(output, dict) and len(output) == 1)):
			raise ProcOutputError(type(output).__name__,
				'Process output type should be one of list/str/OrderedDict/OBox/OrderedBox, '
				'or dict with len=1, not')

		# output => {'a': '{{i.invar}}', 'b:file': '{{i.infile | fn}}'}
		for keytype, outdata in output.items():
			if ':' not in keytype:
				keytype += ':' + Proc.OUT_VARTYPE[0]
			thekey, thetype = keytype.split(':', 1)

			if thetype not in Proc.OUT_DIRTYPE + Proc.OUT_FILETYPE + Proc.OUT_VARTYPE + \
				Proc.OUT_STDOUTTYPE + Proc.OUT_STDERRTYPE:
				raise ProcOutputError(thetype, 'Unknown output type')

			self.props.output[thekey] = (thetype, self.template(outdata, **self.tplenvs))

	def _buildScript(self):
		"""
		Build the script template waiting to be rendered.
		"""
		script = self.config.script.strip()
		if not script:
			logger.warning('No script specified', proc = self.id)

		if script.startswith ('file:'):
			tplfile = Path(script[5:])
			if not fs.exists (tplfile):
				raise ProcScriptError(tplfile, 'No such template file')
			logger.debug("Using template file: %s", tplfile, proc = self.id)
			script = tplfile.read_text()

		# original lines
		olines = script.splitlines()
		# new lines
		nlines = []
		indent = ''
		for line in olines:
			if '# PYPPL INDENT REMOVE' in line:
				indent = line[:-len(line.lstrip())]
			elif '# PYPPL INDENT KEEP' in line:
				indent = ''
			elif indent and line.startswith(indent):
				nlines.append(line[len(indent):])
			else:
				nlines.append(line)

		if not nlines or not nlines[0].startswith('#!'):
			nlines.insert(0, '#!/usr/bin/env ' + str(self.lang))
		nlines.append('')

		self.props.script = self.template('\n'.join(nlines), **self.tplenvs)

	def _saveSettings(self):
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

		logger.debug('Settings saved to: %s' % settingsfile, proc = self.id)

	def _buildJobs(self):
		"""
		Build the jobs.
		"""
		self.props.channel = Channel.nones(self.size, 1)

		if not self.input:
			logger.warning('No data found for jobs, process will be skipped.', proc = self.id)
			if self.jobs: # clear up Nones
				del self.jobs[:]
			return

		from . import PyPPL
		if self.runner not in PyPPL.RUNNERS:
			raise ProcAttributeError(
				'No such runner: {}. '.format(self.runner) +
				'If it is a profile, did you forget to specify a basic runner?')

		logger.debug('Constructing jobs ...', proc = self.id)
		for i in range(self.size):
			self.jobs[i] = PyPPL.RUNNERS[self.runner](i, self)

	def _readConfig(self, profile, config):
		"""
		Read the configuration
		@params:
			`config`: The configuration loaded by PyPPL()
		"""
		# if runner is set, then profile should be ignored
		if 'runner' in self.sets or not profile:
			profile = self.config.runner

		config_with_profiles = utils.config.copy()
		# make sure configs in __init__ be loaded
		config_with_profiles._load({'default': dict.copy(self.config)})

		assert isinstance(config, type(self.config))
		# load extra profiles specified to PyPPL()
		for key, val in config._protected['cached'].items():
			if '__noloading__' not in val:
				config_with_profiles._load(val)

		# configs have been set
		setconfigs = {key:self.config[key] for key in self.sets if key != 'runner'}
		if isinstance(profile, dict):
			profile['runner'] = profile.get('runner', self.config.runner)
			config_with_profiles._load({'__tmp__': profile})
			config_with_profiles._use('__tmp__')
			# now config_with_profiles carries the right profile
			# update it back to self.config
			self.config.update(config_with_profiles)
			self.config.update(setconfigs)
			# the real runner
			self.props.runner  = self.config.runner
			# the real profile
			self.config.runner = '__tmp__'
		else:
			try:
				config_with_profiles._use(profile, raise_exc = True)
			except NoSuchProfile:
				config_with_profiles._load({profile: dict(runner = profile)})
				config_with_profiles._use(profile)
			# now config_with_profiles carries the right profile
			# update it back to self.config
			self.config.update(config_with_profiles)
			self.config.update(setconfigs)
			self.props.runner  = self.config.runner
			self.config.runner = profile
		del config_with_profiles

	def _runCmd(self, key):
		"""
		Run the `beforeCmd` or `afterCmd`
		@params:
			key (str): "beforeCmd/preCmd/afterCmd/postCmd" or above without "Cmd"
		@returns:
			The return code of the command
		@raises:
			ProcRunCmdError: if command returns other than 1.
		"""
		if not key.endswith('Cmd'):
			key += 'Cmd'
		if key in Proc.ALIAS:
			key = Proc.ALIAS[key]

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

	# self.resume != 'skip'
	def _preRunTidy(self):
		"""
		Do some preparation before running jobs
		"""
		self._buildProps()
		try:
			if callable(self.callfront):
				logger.debug("Calling callfront ...", proc = self.id)
				self.callfront(self)
			self._buildInput()
			self._buildProcVars()
			self._buildOutput()
			self._buildScript()
			if self.resume not in ['skip+', 'resume']:
				self._saveSettings()
			self._buildJobs()
			self.props.timer = time()
		except Exception: # pragma: no cover
			if self.lock.is_locked:
				self.lock.release()
			raise

	def _runJobs(self):
		"""
		Submit and run the jobs
		"""
		logger.debug('Queue starts ...', proc = self.id)
		Jobmgr(self.jobs).start()

		self.props.channel = Channel.create([
			tuple(value for _, value in job.output.values())
			for job in self.jobs
		])
		if self.jobs:
			self.channel.attach(*self.jobs[0].output.keys())

	# self.resume != 'skip'
	def _postRunTidy(self):
		"""
		Do some cleaning after running jobs
		self.resume can only be:
		- '': normal process
		- skip+: skipped process but required workdir and data exists
		- resume: resume pipeline from this process, no requirement
		- resume+: get data from workdir/proc.settings, and resume
		"""
		if self.resume == 'skip+':
			if callable(self.callback):
				logger.debug('Calling callback ...', proc = self.id)
				self.callback(self)
		else: # '', resume, resume+
			# summarize jobs
			bfailedjobs = []
			sfailedjobs = []
			efailedjobs = []
			#killedjobs  = []
			successjobs = []
			cachedjobs  = []

			for job in self.jobs:
				#logger.debug(job.state)
				if job.state == STATES.BUILTFAILED:
					bfailedjobs.append(job.index)
				elif job.state == STATES.SUBMITFAILED:
					sfailedjobs.append(job.index)
				elif job.state == STATES.DONE:
					successjobs.append(job.index)
				elif job.state == STATES.DONECACHED:
					cachedjobs.append(job.index)
				elif job.state == STATES.ENDFAILED:
					efailedjobs.append(job.index)
				#elif job.state == STATES.KILLING or job.state == STATES.KILLED:
				#	killedjobs.append(job.index)

			(logger.P_DONE, logger.CACHED)[int(
				len(cachedjobs) == self.size and self.size > 0
			)]('Time: %s. Jobs (Cached: %s, Succ: %s, B.Fail: %s, S.Fail: %s, R.Fail: %s)',
				utils.formatSecs(time() - self.timer),
				len(cachedjobs),
				len(successjobs),
				len(bfailedjobs),
				len(sfailedjobs),
				len(efailedjobs),
				proc = self.id)

			logger.debug('Cached: %s', utils.briefList(cachedjobs, 1), proc = self.id)
			logger.debug('Succeeded: %s', utils.briefList(successjobs, 1), proc = self.id)
			if bfailedjobs:
				logger.error('Building failed: %s',
					utils.briefList(bfailedjobs, 1), proc = self.id)
			if sfailedjobs:
				logger.error('Submission failed: %s',
					utils.briefList(sfailedjobs, 1), proc = self.id)
			if efailedjobs:
				logger.error('Running failed: %s',
					utils.briefList(efailedjobs, 1), proc = self.id)

			donejobs = successjobs + cachedjobs
			failjobs = bfailedjobs + sfailedjobs + efailedjobs
			showjob  = failjobs[0] if failjobs else 0

			if (len(donejobs) == self.size or self.errhow == 'ignore') and \
				callable(self.callback):
				logger.debug('Calling callback ...', proc = self.id)
				self.callback(self)
			# there are jobs failed
			if len(donejobs) < self.size:
				self.jobs[showjob].showError(len(failjobs))
				if self.errhow != 'ignore':
					sys.exit(1)

	def run(self, profile = None, config = None):
		"""@API
		Run the process with a profile and/or a configuration
		@params:
			profile (str): The profile from a configuration file.
			config (dict): A configuration passed to PyPPL construct.
		"""
		self._readConfig(profile, config)
		if self.runner == 'dry':
			self.config.cache = False

		pluginmgr.hook.procPreRun(proc = self)
		if self.resume == 'skip':
			logger.skipped("Pipeline will resume from future processes.")
		elif self.resume == 'skip+':
			self._preRunTidy()
			logger.skipped("Data loaded, pipeline will resume from future processes.")
			try:
				self._postRunTidy()
			finally:
				self.lock.release()
				fs.remove(path.join(self.workdir, 'proc.lock'))
		else: # '', resume, resume+
			self._preRunTidy()
			try:
				self._runCmd('preCmd')
				if self.resume: # resume or resume+
					logger.resumed("Previous processes skipped.")
				self._runJobs()
				self._runCmd('postCmd')
				self._postRunTidy()
			finally:
				self.lock.release()
				# remove the lock file, so that I know this process has done
				# or hasn't started yet, externally.
				fs.remove(path.join(self.workdir, 'proc.lock'))
		pluginmgr.hook.procPostRun(proc = self)
		# gc
		del self.jobs[:]
