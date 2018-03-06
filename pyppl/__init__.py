VERSION = "0.9.5"

import json
import random
import sys
import six
import threading
import copy as pycopy
import traceback
from os import path, makedirs
from time import time, sleep
from random import randint
from subprocess import PIPE, Popen
from multiprocessing import JoinableQueue, Process, cpu_count
from collections import OrderedDict

from box import Box
from .aggr import Aggr
from .channel import Channel
from .job import Job, Jobmgr
from .parameters import params, Parameter, Parameters
from .flowchart import Flowchart
from .proctree import ProcTree
from .exception import ProcTagError, ProcAttributeError, ProcInputError, ProcOutputError, ProcScriptError, ProcRunCmdError, PyPPLProcFindError, PyPPLProcRelationError, PyPPLConfigError
from . import logger, utils, runners, templates

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
		'nsub'   : 'maxsubmit'
	}
	# deprecated
	DEPRECATED   = {
		'profile': 'runner'
	}
	LOG_NLINE    = {
		'EXPORT_CACHE_OUTFILE_EXISTS': -3,
		'EXPORT_CACHE_USING_SYMLINK': 1,
		'EXPORT_CACHE_USING_EXPARTIAL': 1,
		'EXPORT_CACHE_EXFILE_NOTEXISTS': 1,
		'EXPORT_CACHE_EXDIR_NOTSET': 1,
		'CACHE_EMPTY_PREVSIG': -1,
		'CACHE_EMPTY_CURRSIG': -2,
		'CACHE_SCRIPT_NEWER': -3,
		'CACHE_SIGINVAR_DIFF': -3,
		'CACHE_SIGINFILE_DIFF': -3,
		'CACHE_SIGINFILE_NEWER': -3,
		'CACHE_SIGINFILES_DIFF': -3,
		'CACHE_SIGINFILES_NEWER': -3,
		'CACHE_SIGOUTVAR_DIFF': -3,
		'CACHE_SIGOUTFILE_DIFF': -3,
		'CACHE_SIGOUTDIR_DIFF': -3,
		'CACHE_SIGFILE_NOTEXISTS': -1,
		'EXPECT_CHECKING': -1,
		'INFILE_RENAMING': -3,
		'BRINGFILE_NOTFOUND': -3,
		'OUTFILE_NOT_EXISTS': -1,
		'OUTDIR_CREATED_AFTER_RESET': -1,
		'SCRIPT_EXISTS': -2,
		'JOB_RESETTING': -1,
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

	def __init__ (self, tag = 'notag', desc = 'No description.', id = None):
		"""
		Constructor
		@params:
			`tag`:  The tag of the process
			`desc`: The description of the process
			`id`:   The identify of the process
		@config:
			id, input, output, ppldir, forks, cache, cclean, rc, echo, runner, script, depends, tag, desc, dirsig
			exdir, exhow, exow, errhow, errntry, lang, beforeCmd, afterCmd, workdir, args, aggr
			callfront, callback, brings, expect, expart, template, tplenvs, resume, nthread, maxsubmit
		@props
			input, output, rc, echo, script, depends, beforeCmd, afterCmd, workdir, brings, expect
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
			raise ProcTagError("No space is allowed in tag (%s). Do you mean 'desc' instead of 'tag' ?" % tag)

		# The command to run after jobs start
		self.config['afterCmd']   = ""

		# The aggregation name of the process
		self.config['aggr']       = None
		# The extra arguments for the process
		self.config['args']       = Box()

		# The command to run before jobs start
		self.config['beforeCmd']  = ""

		# The bring files that user specified
		self.config['brings']     = {}
		# The computed brings
		self.props['brings']      = {}

		# The cache option
		self.config['cache']      = True # False or 'export'

		# The callfront function of the process
		self.config['callfront']  = None
		# The callback function of the process
		self.config['callback']   = None

		# Do cleanup for cached jobs?
		self.config['cclean']     = False

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
		self.config['errhow']     = "terminate" # retry, ignore
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

		# max number of processes used to submit jobs
		self.config['maxsubmit']  = int(cpu_count() / 2)

		# non-cached job ids
		self.props['ncjobids']    = []
		# number of threads used to build jobs and to check job cache status
		self.config['nthread']    = 1

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

		# The template environment
		self.config['tplenvs']    = Box()

		# The workdir for the process
		self.config['workdir']    = ''
		# The computed workdir
		self.props['workdir']     = ''
		
		self.props['logs']        = {}

		PyPPL._registerProc(self)

	def __getattr__ (self, name):
		if not name in self.props \
			and not name in self.config \
			and not name in Proc.ALIAS \
			and not name.endswith ('Runner'):
			raise ProcAttributeError(name)
		
		if name in Proc.ALIAS:
			name = Proc.ALIAS[name]
			
		return self.props[name] if name in self.props else self.config[name]

	def __setattr__ (self, name, value):
		if not name in self.config and not name in Proc.ALIAS and not name.endswith ('Runner'):
			raise ProcAttributeError(name, 'Cannot set attribute for process')

		# profile will be deprecated, use runner instead
		if name in Proc.DEPRECATED:
			self.log('%s: Attribute "%s" is deprecated%s.' % (self.name(True), name, (', use "%s" instead' % Proc.DEPRECATED[name]) if Proc.DEPRECATED[name] else ''), 'warning')
		
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
			self.config[name] = Box(value)
			
		elif name == 'input' \
			and self.config[name] \
			and not isinstance(value, six.string_types) \
			and not isinstance(value, dict):
			# specify data
			previn  = self.config[name]
			prevkey = ', '.join(previn) if isinstance(previn, list) else \
					  ', '.join(previn.keys()) if isinstance(previn, dict) else previn
			self.config[name] = {prevkey: value}
			if isinstance(previn, dict) and len(previn) > 1:
				self.log("Previous input is a dict with multiple keys. Now the key sequence is: %s" % prevkey, 'warning')
		else:
			self.config[name] = value
			
	def __repr__(self):
		return '<Proc(%s) @ %s>' % (self.name(), hex(id(self)))
		
	def log (self, msg, level="info", key = None):
		"""
		The log function with aggregation name, process id and tag integrated.
		@params:
			`msg`:   The message to log
			`level`: The log level
			`key`:   The type of messages
		"""
		summary = False
		level   = "[%s]" % level
		if not key or key not in Proc.LOG_NLINE:
			logger.logger.info(level + ' ' + msg)
		else:
			maxline = Proc.LOG_NLINE[key]
			absline = abs(maxline)
			summary = maxline < 0
			n = 3 if key.startswith('CACHE_') and (key.endswith('_DIFF') or key.endswith('_NEWER')) else 1
			
			if key not in self.logs: self.logs[key] = []
			
			if not self.logs[key] or self.logs[key][-1] is not None:
				self.logs[key].append((level, msg))
			nlogs = len(self.logs[key])
			if nlogs == absline or nlogs == self.size * n:
				self.logs[key].append(None)
				for level, msg in filter(None, self.logs[key]):
					logger.logger.info (level + ' ' + msg)
				if summary and nlogs < self.size * n:
					logger.logger.info ('[debug] ...... max=%s (%s) reached, further information will be ignored.' % (absline, key))

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
		
		config.update(self.config)
		props.update(self.props)
		
		for key in config.keys():
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
			elif isinstance(config[key], Box):
				config[key] = Box()
				config[key].update(self.config[key])
			#elif isinstance(config[key], OrderedDict):
			#	config[key] = OrderedDict()
			#	config[key].update(self.config[key])
			elif isinstance(config[key], dict):
				config[key] = {}
				config[key].update(self.config[key])
		
		for key in props.keys():
			if key in ['depends', 'jobs', 'ncjobids']:
				props[key] = []
			elif key in ['procvars', 'logs']:
				props[key] = {}
			elif key == 'size':
				props[key] = 0
			elif key in ['workdir', 'suffix']:
				props[key] = ''
			elif key == 'channel':
				props[key] = Channel.create()
			elif key == 'sets':
				props[key] = self.props[key][:]
			#elif isinstance(props[key], Box):
			#	props[key] = Box()
			#	props[key].update(self.props[key])
			elif isinstance(props[key], OrderedDict):
				props[key] = OrderedDict()
				props[key].update(self.props[key])
			elif isinstance(props[key], dict):
				props[key] = {}
				props[key].update(self.props[key])
			
		newproc = Proc()
		newproc.props.update(props)
		newproc.config.update(config)
		return newproc

	def _suffix (self):
		"""
		Calcuate a uid for the process according to the configuration
		@returns:
			The uniq id of the process
		"""
		if self.suffix: return self.suffix
		
		config = { key:val for key, val in self.config.items() if key in [
			'id', 'tag', 'input', 'output', 'script', 'lang'
		] }
		
		# lambda is not pickable
		if isinstance(config['input'], dict):
			config['input'] = pycopy.copy(config['input'])
			for key, val in config['input'].items():
				config['input'][key] = utils.funcsig(val) if callable(val) else val

		# Add depends to avoid the same suffix for processes with the same depends but different input files
		# They could have the same suffix because they are using input callbacks
		# callbacks could be the same though even if the input files are different
		if self.depends:
			config['depends'] = [p.name(True) + '#' + p._suffix() for p in self.depends]

		signature = json.dumps(config, sort_keys = True)
		self.props['suffix'] = utils.uid(signature)
		return self.suffix

	# self.resume != 'skip'
	def _tidyBeforeRun (self):
		"""
		Do some preparation before running jobs
		"""
		self._buildProps ()
		if callable (self.callfront):
			self.log ("Calling callfront ...", "debug")
			self.callfront (self)
		self._buildInput ()
		self._buildProcVars ()
		self._buildBrings ()
		self._buildOutput()
		self._buildScript()
		if self.resume not in ['skip+', 'resume']:
			self._saveSettings()
		self._buildJobs ()

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
				self.log('Calling callback ...', 'debug')
				self.callback (self)
		else: # '', resume, resume+
			failedjobs = [job for job in self.jobs if not job.succeed()]
			if not failedjobs:
				self.log ('Successful jobs: ALL', 'debug')
				if callable (self.callback):		
					self.log('Calling callback ...', 'debug')
					self.callback (self)
			else:
				failedjobs[0].showError (len(failedjobs))
				if self.errhow != 'ignore':
					sys.exit (1) # don't go further
	
	def name (self, aggr = True):
		"""
		Get my name include `aggr`, `id`, `tag`
		@returns:
			the name
		"""
		aggrName  = "@%s" % self.aggr if self.aggr and aggr else ""
		tag   = ".%s" % self.tag  if self.tag != "notag" else ""
		return "%s%s%s" % (self.id, tag, aggrName)
		
	def run (self, config = None):
		"""
		Run the jobs with a configuration
		@params:
			`config`: The configuration
		"""
		if config is None: config = {}
		self._readConfig (config)
		
		if self.runner == 'dry':
			self.config['cache'] = False
		
		if self.resume == 'skip':
			self.log ("Pipeline will resume from future processes.", 'skipped')
		elif self.resume == 'skip+':
			self.log ("Data loaded, pipeline will resume from future processes.", 'skipped')
			self._tidyBeforeRun()
			self._tidyAfterRun ()
		else: # '', resume, resume+
			timer = time()
			self._tidyBeforeRun ()
			self._runCmd('beforeCmd')
			cached = self._checkCached()
			if self.resume: # resume or resume+
				self.log (self.workdir + (' [CACHED] ' if cached else ' [RUNNING]'), 'RESUMED')
			elif not cached:
				self.log (self.workdir, 'RUNNING')
			else:
				self.log (self.workdir, 'CACHED')
			self._runJobs()
			self._runCmd('afterCmd')
			self._tidyAfterRun ()
			self.log ('Done (time: %s).' % utils.formatSecs(time() - timer), 'info')
				
	def _buildProps (self):
		"""
		Compute some properties
		"""
		PyPPL._checkProc(self)

		# get Template
		if callable(self.config['template']):
			self.props['template'] = self.config['template']
		elif self.config['template'] == '':
			self.props['template'] = getattr(templates, 'TemplatePyPPL')
		else:
			self.props['template'] = getattr(templates, 'Template' + self.config['template'][0].upper() + self.config['template'][1:])

		# build rc
		if isinstance(self.config['rc'], six.string_types):
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
		
		if not path.exists (self.workdir):
			if self.resume in ['skip+', 'resume']:
				raise ProcAttributeError(self.workdir, 'Cannot skip process, as workdir not exists')
			makedirs (self.workdir)
			
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
		elif isinstance(self.echo['jobs'], six.string_types):
			self.echo['jobs'] = list(map(lambda x: int(x.strip()), self.echo['jobs'].split(',')))
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
		
		self.log ('Properties set explictly: %s' % str(self.sets), 'debug')
	
	def _saveSettings (self):
		"""
		Save all settings in proc.settings, mostly for debug
		"""
		settingsfile = path.join(self.workdir, 'proc.settings')
		
		def pickKey(key):
			return key if key else "''"
			
		def flatData(data):
			if isinstance(data, dict):
				return {k:flatData(v) for k,v in data.items()}
			elif isinstance(data, list):
				return [flatData(v) for v in data]
			elif isinstance(data, self.template):
				return str(data)
			elif callable(data):
				return utils.funcsig(data)
			else:
				return data
				
		def pickData(data, splitline = False, forcelist = False):
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
			ret = ['[%s]' % key]
			if key in ['jobs', 'ncjobids', 'logs']:
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
			elif key == 'brings':
				for k in sorted(data.keys()):
					v = val[k]
					ret.append('%s: %s' % (pickKey(k), pickData(v)))
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
				
		self.log ('Settings saved to: %s' % settingsfile, 'debug')
	
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
			from six.moves.configparser import ConfigParser
			psfile = path.join(self.workdir, 'proc.settings')
			if not path.isfile(psfile):
				raise ProcInputError(psfile, 'Cannot parse input for skip+/resume process, no such file')
	
			cp = ConfigParser()
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
				self.log('Not all data are used as input, %s column(s) wasted.' % (wdata - len(pinkeys)), 'warning')
			for i, inkey in enumerate(pinkeys):
				self.props['input'][inkey] = {}
				self.props['input'][inkey]['type'] = pintypes[i]
				if i < wdata:
					self.props['input'][inkey]['data'] = invals.flatten(i)
				else:
					self.log('No data found for input key "%s", use empty strings/lists instead.' % inkey, 'warning')
					self.props['input'][inkey]['data'] = [[] if pintypes[i] in Proc.IN_FILESTYPE else ''] * self.size
				
	def _buildProcVars (self):
		"""
		Build proc attribute values for template rendering,
		and also echo some out.
		"""
		show   = ['size', 'args']
		if self.runner != 'local':
			show.append('runner')
		hide   = ['desc', 'id', 'sets', 'tag', 'suffix', 'workdir', 'aggr', 'input', 'output', 'depends', 'script']
		pvkeys = [key for key in set(list(self.props.keys()) + list(self.config.keys())) \
			if key in show or (key in self.sets and key not in hide)]
			
		procvars = {}
		procargs = {}

		alias   = { val:key for key, val in Proc.ALIAS.items() }
		maxlen  = 0
		propout = {}
		for key in pvkeys:
			val = getattr(self, key)
			if key == 'args':
				procvars['args'] = val
				procargs = val
				if val: maxlen = max(maxlen, max(list(map(len, val.keys()))))
			#elif key == 'procvars':
			#	procvars['procvars'] = val
			else:
				procvars[key] = val
				maxlen = max(maxlen, len(key))
				propout[key] = (repr(val) + ' [%s]' % alias[key]) if key in alias else repr(val)
		for key in sorted(procargs.keys()):
			self.log('%s => %s' % (key.ljust(maxlen), repr(procargs[key])), 'p.args')
		for key in sorted(propout.keys()):
			self.log('%s => %s' % (key.ljust(maxlen), propout[key]), 'p.props')
		self.props['procvars'] = {'proc': procvars, 'args': procargs}

	def _buildBrings(self):
		"""
		Build the bring-file templates waiting to be rendered.
		"""
		for key, val in self.config['brings'].items():
			if not isinstance(val, list): val = [val]
			self.props['brings'][key] = []
			for v in val:
				self.props['brings'][key].append(self.template(v, **self.tplenvs))

	def _buildOutput(self):
		"""
		Build the output data templates waiting to be rendered.
		"""
		output = self.config['output']
		if isinstance(output, six.string_types):
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
			self.log ('No script specified', 'warning')
			
		if script.startswith ('file:'):
			tplfile = script[5:].strip()
			if not path.exists (tplfile):
				raise ProcScriptError (tplfile, 'No such template file')
			self.log ("Using template file: %s" % tplfile, 'debug')
			with open(tplfile) as f:
				script = f.read().strip()
		
		olines       = script.splitlines()
		nlines       = []
		# remove repeats
		repeats      = []
		repeat_opens = {}
		repeat_start = '# PYPPL REPEAT START:'
		repeat_end   = '# PYPPL REPEAT END:'
		switch       = True
		indent       = ''
		for line in olines:
			if repeat_start in line:
				rname = line[line.find(repeat_start) + len(repeat_start):].strip().split()[0]
				if rname in repeats:
					switch = False
				repeat_opens[rname] = True
			elif repeat_end in line:
				rname = line[line.find(repeat_end) + len(repeat_end):].strip().split()[0]
				if not rname in repeat_opens: continue
				del repeat_opens[rname]
				repeats.append(rname)
				switch = True
			elif switch:
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

		self.props['script'] = self.template('\n'.join(nlines) + '\n', **self.tplenvs)

	def _buildJobs (self):
		"""
		Build the jobs.
		"""
		self.props['channel'] = Channel.create([None] * self.size)
		if self.size == 0:
			self.log('No data found for jobs, process will be skipped.', 'warning')
			return
		rptjob  = 0 if self.size == 1 else randint(0, self.size-1)

		def bjSingle(i):
			job = Job(i, self)
			job.init()
			self.jobs[i] = job
			row = tuple(job.data['out'].values())
			self.props['channel'][i] = row

		utils.parallel(bjSingle, [(i, ) for i in range(self.size)], self.nthread)
		self.log('After job building, active threads: %s' % threading.active_count(), 'debug')

		if self.jobs[0].data['out']:
			self.channel.attach(*self.jobs[0].data['out'].keys())
		self.jobs[rptjob].report()

	def _readConfig (self, config):
		"""
		Read the configuration
		@params:
			`config`: The configuration
		"""
		for key, val in config.items():
			if key == 'runner': 
				self.props['runner'] = val
			elif key in self.sets:
				continue
			else:
				if key in Proc.ALIAS:
					key = Proc.ALIAS[key]
				self.config[key] = val

	def _checkCached (self):
		"""
		Tell whether the jobs are cached
		@returns:
			True if all jobs are cached, otherwise False
		"""
		self.props['ncjobids'] = range(self.size)
		if self.cache == False:
			self.log ('Not cached, because proc.cache is False', 'debug')
			return False

		trulyCachedJids        = []
		#notTrulyCachedJids     = []
		exptCachedJids         = []
		self.props['ncjobids'] = []

		def chkCached(i):
			job = self.jobs[i]
			if job.isTrulyCached():
				trulyCachedJids.append(i)
			elif job.isExptCached():
				exptCachedJids.append(i)
			else:
				self.props['ncjobids'].append (i)

		utils.parallel(chkCached, [(i, ) for i in range(self.size)], self.nthread)
				
		self.log ('Truly cached jobs : %s' % (utils.briefList(trulyCachedJids) if len(trulyCachedJids) < self.size else 'ALL'), 'info')
		self.log ('Export-cached jobs: %s' % (utils.briefList(exptCachedJids)  if len(exptCachedJids)  < self.size else 'ALL'), 'info')
		
		if self.ncjobids:
			if len(self.ncjobids) < self.size:
				self.log ('Partly cached, only run non-cached %s job(s).' % len(self.ncjobids), 'info')
				self.log ('Jobs to run: %s' % utils.briefList(self.ncjobids), 'debug')
			else:
				self.log ('Not cached, none of the jobs are cached.', 'debug')
			return False
		else:
			return True

	def _runCmd (self, key):
		"""
		Run the `beforeCmd` or `afterCmd`
		@params:
			`key`: "beforeCmd" or "afterCmd"
		@returns:
			The return code of the command
		"""
		if not self.config[key]: return
		cmd = self.template(self.config[key], **self.tplenvs).render(self.procvars)
		self.log ('Running <%s> ...' % (key), 'info')
		
		try:
			p = Popen (cmd, shell=True, stderr=PIPE, stdout=PIPE, universal_newlines=True)

			for line in iter(p.stdout.readline, ''):
				logger.logger.info ('[ CMDOUT] %s' % line.rstrip("\n"))
			for line in iter(p.stderr.readline, ''):
				logger.logger.info ('[ CMDERR] %s' % line.rstrip("\n"))
			rc = p.wait()
			p.stdout.close()
			p.stderr.close()
			if rc != 0:
				raise ProcRunCmdError(cmd, key)
		except Exception:
			raise ProcRunCmdError(cmd, key)
	
	def _runJobs (self):
		"""
		Submit and run the jobs
		"""
		runner    = PyPPL.RUNNERS[self.runner]
		jobmgr = Jobmgr(self, runner)
		jobmgr.run()
		
		self.log('After job run, active threads: %s' % threading.active_count(), 'debug')
			
class PyPPL (object):
	"""
	The PyPPL class
	
	@static variables:
		`TIPS`: The tips for users
		`RUNNERS`: Registered runners
		`DEFAULT_CFGFILES`: Default configuration file
	"""
	
	TIPS = [
		"You can find the stdout in <workdir>/<job.index>/job.stdout",
		"You can find the stderr in <workdir>/<job.index>/job.stderr",
		"You can find the script in <workdir>/<job.index>/job.script",
		"Check documentation at: https://www.gitbook.com/book/pwwang/pyppl",
		"You cannot have two processes with the same id and tag",
		"beforeCmd and afterCmd only run locally",
		"If 'workdir' is not set for a process, it will be PyPPL.<proc-id>.<proc-tag>.<suffix> under default <ppldir>",
		"The default <ppldir> is './workdir'",
	]

	RUNNERS  = {}
	# ~/.PyPPL.json has higher priority
	DEFAULT_CFGFILES = ['~/.PyPPL.yaml', '~/.PyPPL', '~/.PyPPL.json']
	# counter
	COUNTER  = 0
	
	def __init__(self, config = None, cfgfile = None):
		"""
		Constructor
		@params:
			`config`: the configurations for the pipeline, default: {}
			`cfgfile`:  the configuration file for the pipeline, default: `~/.PyPPL.json` or `./.PyPPL`
		"""
		self.counter = PyPPL.COUNTER
		PyPPL.COUNTER += 1
		
		fconfig    = {}
		cfgIgnored = {}
		for i in list(range(len(PyPPL.DEFAULT_CFGFILES))):
			cfile = path.expanduser(PyPPL.DEFAULT_CFGFILES[i])
			PyPPL.DEFAULT_CFGFILES[i] = cfile
			if path.exists(cfile):
				with open(cfile) as cf:
					if cfile.endswith('.yaml'):
						try:
							import yaml
							utils.dictUpdate(fconfig, yaml.load(cf.read().replace('\t', '  ')))
						except ImportError:
							cfgIgnored[cfile] = 1
					else:
						utils.dictUpdate(fconfig, json.load(cf))
		
		if cfgfile is not None and path.exists(cfgfile):
			with open(cfgfile) as cfgf:
				if cfgfile.endswith('.yaml'):
					try:
						import yaml
						utils.dictUpdate(fconfig, yaml.load(cfgf.read().replace('\t', '  ')))
					except ImportError:
						cfgIgnored[cfgfile] = 1
				else:
					utils.dictUpdate(fconfig, json.load(cfgf))
				
		if config is None:	config = {}
		utils.dictUpdate(fconfig, config)
		self.config = fconfig

		fcconfig = {
			'theme': 'default'
		}
		if 'flowchart' in self.config:
			utils.dictUpdate(fcconfig, self.config['flowchart'])
			del self.config['flowchart']
		self.fcconfig = fcconfig

		logconfig = {
			'levels': 'normal',
			'theme':   True,
			'lvldiff': [],
			'file':    '%s%s.pyppl.log' % (path.splitext(sys.argv[0])[0], ('_%s' % self.counter) if self.counter else '') 
		}
		if 'log' in self.config:
			if 'file' in self.config['log'] and self.config['log']['file'] is True:
				del self.config['log']['file']
			utils.dictUpdate(logconfig, self.config['log'])
			del self.config['log']
			
		logger.getLogger (logconfig['levels'], logconfig['theme'], logconfig['file'], logconfig['lvldiff'])

		logger.logger.info ('[  PYPPL] Version: %s' % (VERSION))
		logger.logger.info ('[   TIPS] %s' % (random.choice(PyPPL.TIPS)))
		
		for cfile in (PyPPL.DEFAULT_CFGFILES + [str(cfgfile)]):
			if not path.isfile(cfile): continue
			if cfile in cfgIgnored:
				logger.logger.info ('[WARNING] Module yaml not installed, config file ignored: %s' % (cfile))
			else:
				logger.logger.info ('[ CONFIG] Read from %s' % cfile)

		self.tree    = ProcTree()
		
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
				logger.logger.info('[WARNING] Start process %s ignored, depending on [%s]' % (
					start.name(True), 
					', '.join(names)
				))
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
			if end in resumes: continue
			paths = self.tree.getPathsToStarts(end)
			failedpaths = [ps for ps in paths if not any([p in ps for p in resumes])]
			if not failedpaths: continue
			failedpath = failedpaths[0]
			raise PyPPLProcRelationError('%s <- [%s]' % (end.name(), ', '.join([p.name() for p in failedpath])), 'One of the routes cannot be achived from resumed processes')
				
		# set prior processes to skip
		for rsproc in resumes:
			rsproc.resume = rflag
			paths = self.tree.getPathsToStarts(rsproc)
			for path in paths:
				for p in path:
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
		if not args or (len(args) == 1 and not args[0]): return self
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
		if not args or (len(args) == 1 and not args[0]): return self
		self._resume(*args, plus = True)
		return self

	def _getProfile(self, profile):
		"""
		Get running profile according to profile name
		@params:
			`profile`: The profile name
		@returns:
			The running configuration
		"""
		config = {}
		# get default profile first
		if 'proc' in self.config:
			utils.dictUpdate(config, self.config['proc'])
		
		# overwrite with the given profile
		if profile in self.config:
			utils.dictUpdate(config, self.config[profile])

		# set default runner
		if not 'runner' in config:
			if profile in PyPPL.RUNNERS:
				config['runner'] = profile
			else:
				config['runner'] = 'local'
				logger.logger.info("[WARNING] No runner specified in profile '%s', will use local runner." % (profile))

		# id is not allowed to set in profile
		if 'id' in config:
			raise PyPPLConfigError(config['id'], 'Cannot set a universal id for all process in configuration')

		return config

	def showAllRoutes(self):
		logger.logger.info('[DEBUG] ALL ROUTES:')
		#paths  = sorted([list(reversed(path)) for path in self.tree.getAllPaths()])
		paths  = sorted([[p.name() for p in reversed(ps)] for ps in self.tree.getAllPaths()])
		paths2 = [] # processes merged from the same aggr
		for path in paths:
			prevaggr = None
			path2    = []
			for p in path:
				if not '@' in p: path2.append(p)
				else:
					aggr = p.split('@')[-1]
					if not prevaggr or prevaggr != aggr:
						path2.append('[%s]' % aggr)
						prevaggr = aggr
					elif prevaggr == aggr:
						continue
			if not path2 in paths2:
				paths2.append(path2)
			# see details for aggregations
			#if path != path2:
			#	logger.logger.info('[  DEBUG] * %s' % (' -> '.join(path)))

		for path in paths2:
			logger.logger.info('[DEBUG] * %s' % (' -> '.join(path)))		
		return self
	
	def run (self, profile = 'local'):
		"""
		Run the pipeline
		@params:
			`profile`: the profile used to run, if not found, it'll be used as runner name. default: 'local'
		@returns:
			The pipeline object itself.
		"""
		timer     = time()

		dftconfig = self._getProfile(profile)
		procs     = self.tree.getNextToRun()
		while procs:
			for proc in procs:
				name = ' %s: %s ' % (proc.name(True), proc.desc)
				nlen = max(85, len(name) + 3)
				proc.log ('+' + '-'*(nlen-3) + '+', 'PROCESS')
				proc.log ('|%s%s|' % (name, ' '*(nlen - 3 - len(name))), 'PROCESS')
				proc.log ('+' + '-'*(nlen-3) + '+', 'PROCESS')
				proc.log ("%s => %s => %s" % (ProcTree.getPrevStr(proc), proc.name(), ProcTree.getNextStr(proc)), 'depends')
				if 'runner' in proc.sets and proc.config['runner'] != profile:
					proc.run(self._getProfile(proc.config['runner']))
				else:
					proc.run(dftconfig)
			procs = self.tree.getNextToRun()

		unran = self.tree.unranProcs()
		if unran:
			klen  = max([len(k) for k in unran.keys()])
			for key, val in unran.items():
				fmtstr = "[WARNING] %-"+ str(klen) +"s won't run as path can't be reached: %s <- %s"
				logger.logger.info (fmtstr % (key, key, ' <- '.join(val)))

		logger.logger.info ('[   DONE] Total time: %s' % utils.formatSecs (time()-timer))
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
		self.showAllRoutes()
		fcfile  = fcfile or '%s%s.pyppl.svg' % (path.splitext(sys.argv[0])[0], ('_%s' % self.counter) if self.counter else '') 
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
					if not nextps: continue
					for np in nextps: fc.addLink(p, np)

		fc.generate()
		logger.logger.info ('[   INFO] Flowchart file saved to: %s' % fc.fcfile)
		logger.logger.info ('[   INFO] DOT file saved to: %s' % fc.dotfile)
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
	def registerRunner(runner):
		"""
		Register a runner
		@params:
			`runner`: The runner to be registered.
		"""
		runnerName = runner.__name__
		if runnerName.startswith('Runner'):
			runnerName = runnerName[6:].lower()
			
		if not runnerName in PyPPL.RUNNERS:
			PyPPL.RUNNERS[runnerName] = runner


for runnername in dir(runners):
	if not runnername.startswith('Runner') or runnername in ['Runner', 'RunnerQueue']:
		continue
	runner = getattr(runners, runnername)
	PyPPL.registerRunner(runner)
