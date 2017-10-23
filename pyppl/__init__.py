VERSION = "0.9.2"

import json
import random
import sys
import six
import multiprocessing
import copy as pycopy
from os import path, makedirs
from time import time, sleep
from random import randint
from subprocess import PIPE, Popen
from collections import OrderedDict

from box import Box
from .aggr import Aggr
from .channel import Channel
from .job import Job
from .parameters import params, Parameter, Parameters
from .flowchart import Flowchart
from . import logger, utils, runners, templates

class Proc (object):
	"""
	The Proc class defining a process
	
	@static variables:
		`RUNNERS`:       The regiested runners
		`PROCS`:         The "<id>.<tag>" initialized processes, used to detected whether there are two processes with the same id and tag.
		`ALIAS`:         The alias for the properties
		`LOG_NLINE`:     The limit of lines of logging information of same type of messages
		
	@magic methods:
		`__getattr__(self, name)`: get the value of a property in `self.props`
		`__setattr__(self, name, value)`: set the value of a property in `self.config`
	"""

	# for future use, shortcuts
	ALIAS        = { }
	LOG_NLINE    = {
		'': 999,
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
		'CACHE_SIGINFILE_NEWER': -4,
		'CACHE_SIGINFILES_DIFF': -3,
		'CACHE_SIGINFILES_NEWER': -4,
		'CACHE_SIGOUTVAR_DIFF': -3,
		'CACHE_SIGOUTFILE_DIFF': -3,
		'CACHE_SIGOUTDIR_DIFF': -3,
		'CACHE_SIGFILE_NOTEXISTS': -1,
		'EXPECT_CHECKING': -1,
		'INFILE_RENAMING': -3,
		'OUTFILE_NOT_EXISTS': -1,
		'OUTDIR_CREATED_AFTER_RESET': -1,
		'SCRIPT_EXISTS': -2,
		'JOB_RESETTING': -1,
	}
	
	OUT_VARTYPE  = ['var']
	OUT_FILETYPE = ['file', 'path']
	OUT_DIRTYPE  = ['dir', 'folder']
	
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
			id, input, output, ppldir, forks, cache, rc, echo, runner, script, depends, tag, desc
			exdir, exhow, exow, errhow, errntry, lang, beforeCmd, afterCmd, workdir, args, aggr
			callfront, callback, brings, expect, expart, template, tplenvs, resume, profile
		@props
			input, output, rc, echo, script, depends, beforeCmd, afterCmd, workdir, brings, expect
			expart, template, channel, jobs, ncjobids, size, sets, procvars, suffix, lognline
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
			raise ValueError("No space is allowed in %s's tag. Do you mean 'desc' instead of 'tag' ?" % self.config['id'])

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

		# The output channel of the process
		self.props['channel']     = Channel.create()

		# The dependencies specified
		self.config['depends']    = []
		# The dependencies computed
		self.props['depends']     = []

		# The description of the job		
		self.config['desc']       = desc

		# Whether to print the stdout and stderr of the jobs to the screen
		# Could also be:
		# {
		#   'jobs':   0           # or [0, 1, 2], just echo output of those jobs.
		#   'type':   'stderr'    # only echo stderr. (stdout: only echo stdout; [don't specify]: echo all)
		#   'filter': r'^output:' # only echo string starting with "output:"
		# }
		# self.echo = True     <=> self.echo = { 'jobs': 0 }
		# self.echo = False    <=> self.echo = { 'jobs': [] }
		# self.echo = 'stderr' <=> self.echo = { 'jobs': 0, 'type': 'stderr' }
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

		# non-cached job ids
		self.props['ncjobids']    = []

		# The output that user specified
		self.config['output']     = ''
		# The computed output
		self.props['output']      = OrderedDict()

		# Where cache file and wdir located
		self.config['ppldir']     = path.abspath("./workdir")

		# data for proc.xxx in template
		self.props['procvars']    = {}

		# running profile
		self.config['profile']    = ''

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
		
		self.props['lognline']    = {'_PREV_LOG': ''}
		self.props['lognline'].update({key: 0 for key in Proc.LOG_NLINE.keys()})

		PyPPL._registerProc(self)
		

	def __getattr__ (self, name):
		if not name in self.props and not name in self.config and not name in Proc.ALIAS and not name.endswith ('Runner'):
			raise AttributeError('No such attribute "%s" for Proc.' % name)
		
		if name in Proc.ALIAS:
			name = Proc.ALIAS[name]
			
		return self.props[name] if name in self.props else self.config[name]

	def __setattr__ (self, name, value):
		if not name in self.config and not name in Proc.ALIAS and not name.endswith ('Runner'):
			raise AttributeError('Cannot set attribute "%s" for Proc instance' % name)
		
		if name in Proc.ALIAS:
			name = Proc.ALIAS[name]
		
		if name not in self.sets:
			self.sets.append(name)
		
		# depends have to be computed here, as it's used to infer the relation before run
		if name == 'depends':
			depends = value
			self.props['depends'] = []
			if isinstance(depends, tuple):
				depends = list(depends)
			elif isinstance(depends, Proc):
				depends = [depends]
			elif isinstance(depends, Aggr):
				depends = depends.ends
			for depend in depends:
				if isinstance(depend, Proc):
					if depend is self:
						raise ValueError('Proc(%s) cannot depend on itself.' % self.name(True))
					self.props['depends'].append(depend)
				elif isinstance(depend, Aggr):
					self.props['depends'].extend(depend.ends)
				else:
					raise TypeError('Unsupported dependent: %s, expect Proc or Aggr.' % repr(depend))
		elif name == 'script' and value.startswith('file:'):
			scriptpath = value[5:]
			if not path.isabs(scriptpath):
				from inspect import getframeinfo, stack
				caller = getframeinfo(stack()[1][0])
				scriptpath = path.join(path.dirname(caller.filename), scriptpath)
			self.config[name] = "file:%s" % scriptpath
		elif name == 'args' or name == 'tplenvs':
			self.config[name] = Box(value)
		elif name == 'input' and self.config[name] and not isinstance(value, six.string_types) and not isinstance(value, dict):
			# specify data
			previn  = self.config[name]
			prevkey = ', '.join(previn) if isinstance(previn, list) else \
					  ', '.join(previn.keys()) if isinstance(previn, dict) else \
					  previn
			self.config[name] = {prevkey: value}
			if isinstance(previn, dict) and len(previn) > 1:
				self.log("Previous input is a dict with multiple keys. Now the key sequence is: %s" % prevkey)
		else:
			self.config[name] = value
			
	def __repr__(self):
		return '<Proc(%s) at %s>' % (self.name(), hex(id(self)))
		
	def log (self, msg, level="info", key = ''):
		"""
		The log function with aggregation name, process id and tag integrated.
		@params:
			`msg`:   The message to log
			`level`: The log level
			`key`:   The type of messages
		"""
		level  = "[%s]" % level
		name   = self.name(True)
		
		maxline  = Proc.LOG_NLINE[key]
		PREV_LOG = self.lognline['_PREV_LOG']

		if key == PREV_LOG:
			if self.lognline[key] < abs(maxline):
				logger.logger.info ("%s %s: %s" % (level, name, msg))
		else:
			n_omit = self.lognline[PREV_LOG] - abs(Proc.LOG_NLINE[PREV_LOG])
			if n_omit > 0 and Proc.LOG_NLINE[PREV_LOG] < 0:
				logname = 'logs' if n_omit > 1 else 'log'
				maxinfo = '(%s, max=%s)' % (PREV_LOG, abs(Proc.LOG_NLINE[PREV_LOG])) if PREV_LOG else ''
				logger.logger.info ("[DEBUG] %s: ... and %s %s omitted %s." % (name, n_omit, logname, maxinfo))
			self.lognline[PREV_LOG]   = 0

			if self.lognline[key] < abs(maxline):
				logger.logger.info ("%s %s: %s" % (level, name, msg))

		self.lognline['_PREV_LOG'] = key
		self.lognline[key] += 1

	def copy (self, tag=None, newid=None, desc=None):
		"""
		Copy a process
		@params:
			`newid`: The new id of the process, default: `None` (use the varname)
			`tag`:   The tag of the new process, default: `None` (used the old one)
			`desc`:  The desc of the new process, default: `None` (used the old one)
		@returns:
			The new process
		"""
		newproc = Proc (
			tag  = tag  if tag is not None else self.tag,
			desc = desc if desc is not None else self.desc
		)
		
		config = {key: val for key, val in self.config.items()}
		config['id']       = newid if newid else utils.varname()
		config['tag']      = newproc.tag
		config['desc']     = newproc.desc
		config['aggr']     = ''
		config['workdir']  = ''
		config['tplenvs']  = Box()
		config['args']     = Box()
		config['resume']   = ''
		utils.dictUpdate(config['tplenvs'], self.config['tplenvs'])
		utils.dictUpdate(config['args'], self.config['args'])
		
		props   = {key:val for key, val in self.props.items()}
		props['sets']      = [s for s in self.sets]
		props['depends']   = []
		props['procvars']  = {}
		props['workdir']   = ''
		props['channel']   = Channel.create()
		props['jobs']      = []
		props['ncjobids']  = []
		props['size']      = 0
		props['suffix']    = ''
		props['lognline']  = newproc.props['lognline']
		newproc.__dict__['config'] = config
		newproc.__dict__['props']  = props
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
			self.props['rc'] = [int(i) for i in utils.split(self.config['rc'], ',')]
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
				raise Exception('Cannot skip process, as workdir not exists: %s' % self.workdir)
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
				self.props['echo'] = { 'jobs': 0, 'type': [] }
			else:
				self.props['echo'] = { 'jobs': 0, 'type': self.config['echo'] }
		else:
			self.props['echo'] = self.config['echo']
		
		if not 'jobs' in self.echo:
			self.echo['jobs'] = 0
		if isinstance(self.echo['jobs'], int):
			self.echo['jobs'] = [self.echo['jobs']]
		elif isinstance(self.echo['jobs'], six.string_types):
			self.echo['jobs'] = map(lambda x: int(x.strip()), self.echo['jobs'].split(','))
		
		if not 'type' in self.echo:
			self.echo['type'] = ['stderr', 'stdout']
		if not isinstance(self.echo['type'], list):
			self.echo['type'] = [self.echo['type']]
		
		if not 'filter' in self.echo:
			self.echo['filter'] = ''
		
		# don't cache for dry runner
		if self.runner == 'dry':
			self.props['cache'] = False

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
		with open(settingsfile, 'w') as f:
			for key in sorted(self.props.keys()):
				val = self.props[key]
				if key == 'input':
					f.write('\n[input]\n')
					for k in sorted(val.keys()):
						v = val[k]
						f.write (k + '.type: ' + str(v['type']) + '\n')
						for j, ds in enumerate(v['data']):
							f.write (k + '.data#%s: \n' % str(j))
							if isinstance(ds, list):
								for _ in ds:
									f.write('  ' + json.dumps(_, sort_keys = True) + '\n')
							else:
								f.write ('  ' + json.dumps(ds, sort_keys = True) + '\n')
				elif key == 'output':
					f.write('\n[output]\n')
					for k in sorted(val.keys()):
						v = val[k]
						f.write (k + '.type: ' + str(v[0]) + '\n')
						f.write (k + '.data: \n' + ('\n'.join(['  ' + l for l in str(v[1]).splitlines()])) + '\n')
				elif key == 'depends':
					f.write('\n['+ key +']\n')
					f.write('procs: ' + str([p.name() for p in val]) + '\n')
				elif key == 'jobs' or key == 'ncjobids':
					pass
				elif key == 'template':
					f.write('\n['+ key +']\n')
					f.write('name: ' + json.dumps(val.__class__.__name__) + '\n')
				elif key in ['lognline', 'args', 'procvars', 'echo'] or key.endswith('Runner'):
					f.write('\n['+ key +']\n')
					if not val:
						f.write('value: {}\n')
					for k in sorted(val.keys()):
						v = val[k]
						f.write ((k if k else "''") + ': ' + json.dumps(str(v), sort_keys = True) + '\n')
				elif key == 'brings':
					f.write('\n['+ key +']\n')
					if not val:
						f.write('value: {}\n')
					for k in sorted(val.keys()):
						v = val[k]
						f.write ((k if k else "''") + ': ' + json.dumps([str(vv) for vv in v], sort_keys = True) + '\n')
				elif key == 'script':
					f.write('\n['+ key +']\n')
					f.write('value:\n')
					f.write('\n'.join(['  ' + l for l in str(val).splitlines()]) + '\n')
				elif key == 'expart':
					f.write('\n['+ key +']\n')
					for i,v in enumerate(val):
						f.write('value_%s:\n' % i)
						f.write('\n'.join(['  ' + l for l in str(v).splitlines()]) + '\n')
				else:
					f.write('\n['+ key +']\n')
					f.write('value: ' + json.dumps(str(val), sort_keys = True) + '\n')
					
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
				raise OSError('Cannot skip+/resume process: %s, no such file: %s' % (self.name(), psfile))
	
			cp = ConfigParser()
			cp.optionxform = str
			cp.read(psfile)
			self.props['size'] = max(1, int(json.loads(cp.get('size', 'value'))))
			
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
						data = list(map(json.loads, list(filter(None, indata[key].split("\n")))))
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
						raise TypeError('Unknown input type: %s' % t)
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
				self.log('Not all data are used as input, %s columns wasted.' % (wdata - len(pinkeys)), 'warning')
			for i, inkey in enumerate(pinkeys):
				self.props['input'][inkey] = {}
				self.props['input'][inkey]['type'] = pintypes[i]
				if i < wdata:
					self.props['input'][inkey]['data'] = invals.colAt(i).flatten()
				else:
					self.log('No data found for input key "%s", use empty strings/lists instead.' % inkey, 'warning')
					self.props['input'][inkey]['data'] = [[] if pintypes[i] in Proc.IN_FILESTYPE else ''] * self.size
				
	def _buildProcVars (self):
		"""
		Build proc attribute values for template rendering,
		and also print some out.
		"""
		pvkeys = [
			"aggr", "args", "cache", "desc", "echo", "errhow", "errntry", "exdir", "exhow",
			"exow", "forks", "id", "lang", "ppldir", "procvars", "profile", "rc", "resume",
			"runner", "sets", "size", "suffix", "tag", "workdir"
		]
		show   = [ 'size' ]
		hidden = [ 'desc', 'id', 'sets', 'tag', 'suffix', 'workdir' ]
		hidden.extend([key for key in pvkeys if key not in self.sets if key not in show])
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
			elif key == 'procvars':
				procvars['procvars'] = val
			elif key in alias:
				key = alias[key]
				procvars[key] = val
				if (val is False or val) and key not in hidden:
					maxlen = max(maxlen, len(key))
					propout[key] = val
			else:
				procvars[key] = val
				if (val is False or val) and key not in hidden:
					maxlen = max(maxlen, len(key))
					propout[key] = val
		for key in sorted(procargs.keys()):
			self.log('%s => %s' % (key.ljust(maxlen), procargs[key]), 'p.args')
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
			# filter allow empty output
			output = list(filter(None, utils.alwaysList(output)))

		outdict = OrderedDict()
		if isinstance(output, list):
			for op in output:
				ops = utils.split(op, ':')
				lenops = len(ops)
				if lenops < 2:
					raise ValueError('Missing parts in output: %s' % op)
				elif lenops > 3:
					raise ValueError('too many parts in output: %s' % op)
				outdict[':'.join(ops[:-1])] = ops[-1]
		else:
			outdict = self.config['output']

		if not isinstance(outdict, OrderedDict):
			raise TypeError('Expect str, list, or OrderedDict. Dict is not allowed as key sequence has to be kept.')
		
		for key, val in outdict.items():
			kparts = utils.split(key, ':')
			lparts = len(kparts)
			if lparts == 1:
				k, t = key, Proc.OUT_VARTYPE[0]
			elif lparts == 2:
				k, t = kparts
			else:
				raise ValueError('too many parts in output key: %s' % key)
			
			if t not in Proc.OUT_DIRTYPE + Proc.OUT_FILETYPE + Proc.OUT_VARTYPE:
				raise TypeError('Unknown output type: %s' % t)
			self.props['output'][k] = [t, self.template(val, **self.tplenvs)]
		
	def _buildScript(self):
		"""
		Build the script template waiting to be rendered.
		"""
		script = self.config['script'].strip()
		
		# TODO add tests
		if not script:
			self.log ('No script specified', 'warning')
			
		if script.startswith ('file:'):
			tplfile = script[5:].strip()
			#if not path.isabs(tplfile):
			#	tplfile = path.join (path.dirname(sys.argv[0]), tplfile)
			if not path.exists (tplfile):
				raise OSError ('No such template file: %s.' % tplfile)
			self.log ("Using template file: %s" % tplfile, 'debug')
			with open(tplfile) as f:
				script = f.read().strip()

		olines = script.splitlines()
		nlines = []
		indent = ''
		for line in olines:
			if '## indent remove ##' in line:
				indent = line[:line.find('## indent remove ##')]
			elif '## indent keep ##' in line:
				indent = ''
			elif indent and line.startswith(indent):
				nlines.append(line[len(indent):])
			else:
				nlines.append(line)
				
		if not nlines or not nlines[0].startswith('#!'):
			nlines.insert(0, '#!/usr/bin/env ' + self.lang)

		self.props['script'] = self.template('\n'.join(nlines), **self.tplenvs)

	def _buildJobs (self):
		"""
		Build the jobs.
		"""
		self.props['channel'] = Channel.create()
		rptjob  = 0 if self.size == 1 else randint(0, self.size-1)
		outkeys = []
		for i in range(self.size):
			job = Job (i, self)
			job.init ()
			self.jobs[i] = job
			if not outkeys: outkeys = job.data['out'].keys()
			row = [job.data['out'][key] for key in outkeys]
			self.props['channel'] = self.channel.rbind (row)
		if outkeys:
			self.channel.attach(*outkeys)
		self.jobs[rptjob].report()

	def _readConfig (self, config):
		"""
		Read the configuration
		@params:
			`config`: The configuration
		"""
		conf = { (key if not key in Proc.ALIAS else Proc.ALIAS[key]):val for key, val in config.items() if key not in self.sets }
		self.config.update (conf)

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
		notTrulyCachedJids     = []
		exptCachedJids         = []
		self.props['ncjobids'] = []
		for i, job in enumerate(self.jobs):
			job = self.jobs[i]
			if job.isTrulyCached ():
				# make sure logs have the same type
				trulyCachedJids.append(i)
			else:
				notTrulyCachedJids.append(i)
		
		for i in notTrulyCachedJids:
			job = self.jobs[i]
			if job.isExptCached ():
				exptCachedJids.append (i)
			else:
				self.props['ncjobids'].append (i)
				
		self.log ('Truely cached jobs: %s' % (trulyCachedJids if len(trulyCachedJids) < self.size else 'ALL'), 'info')
		self.log ('Export cached jobs: %s' % (exptCachedJids  if len(exptCachedJids)  < self.size else 'ALL'), 'info')
		
		if self.ncjobids:
			if len(self.ncjobids) < self.size:
				self.log ('Partly cached, only run non-cached %s job(s).' % len(self.ncjobids), 'info')
				self.log ('Jobs to be running: %s' % self.ncjobids, 'debug')
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
		
		p = Popen (cmd, shell=True, stderr=PIPE, stdout=PIPE, universal_newlines=True)

		for line in iter(p.stdout.readline, ''):
			logger.logger.info ('[ CMDOUT] %s' % line.rstrip("\n"))
		for line in iter(p.stderr.readline, ''):
			logger.logger.info ('[ CMDERR] %s' % line.rstrip("\n"))
		rc = p.wait()
		p.stdout.close()
		p.stderr.close()
		if rc != 0:
			raise RuntimeError ('Failed to run %s: \n----------------------------------\n%s' % (key, cmd))
	
	def _runJobs (self):
		"""
		Submit and run the jobs
		"""
		runner    = PyPPL.RUNNERS[self.runner]
		maxsubmit = self.forks
		if hasattr(runner, 'maxsubmit'):
			maxsubmit = runner.maxsubmit
		interval  = .1
		if hasattr(runner, 'interval'):
			interval = runner.interval
			
		def _worker(q):
			"""
			The worker to run jobs with multiprocessing
			@params:
				`q`: The multiprocessing.JoinableQueue
			"""
			while True:
				if q.empty(): break
				try:
					data = q.get()
				except Exception:
					break
				if data is None: break
				index, cached = data

				try:
					r     = runner(self.jobs[index])
					batch = int(index/maxsubmit)
					if cached:
						sleep (.1)
						self.jobs[index].done()
					else:
						# check whether the job is running before submit it
						if r.isRunning():
							sleep (.1)
							self.log ("Job #%-3s is already running, skip submitting." % index, 'submit')
						else:
							sleep (batch * interval)
							r.submit()
						r.wait()
						r.finish()
				except Exception:
					raise
				finally:
					q.task_done()
		
		sq = multiprocessing.JoinableQueue()
		for i in list(range(self.size)):
			sq.put((i, i not in self.ncjobids))

		# submit jobs
		for i in range (min(self.forks, self.size)):
			t = multiprocessing.Process(target = _worker, args = (sq, ))
			t.daemon = True
			t.start ()
		
		sq.join()
			
class PyPPL (object):
	"""
	The PyPPL class
	
	@static variables:
		`TIPS`: The tips for users
		`RUNNERS`: Registered runners
		`PROCS`: The processes
		`DEFAULT_CFGFILES`: Default configuration file
	"""
	
	TIPS = [
		"You can find the stdout in <workdir>/<job.index>/job.stdout",
		"You can find the stderr in <workdir>/<job.index>/job.stderr",
		"You can find the script in <workdir>/<job.index>/job.script",
		"Check documentation at: https://www.gitbook.com/book/pwwang/pyppl",
		"You cannot have two processes with the same id and tag",
		"beforeCmd and afterCmd only run locally",
		"If 'workdir' is not set for a process, it will be PyPPL.<proc-id>.<proc-tag>.<uuid> under default <ppldir>",
		"The default <ppldir> will be './workdir'",
	]

	RUNNERS = {}
	PROCS   = []
	# ~/.PyPPL.json has higher priority
	DEFAULT_CFGFILES = ['~/.PyPPL', '~/.PyPPL.json']
	
	def __init__(self, config = None, cfgfile = None):
		"""
		Constructor
		@params:
			`config`: the configurations for the pipeline, default: {}
			`cfgfile`:  the configuration file for the pipeline, default: `~/.PyPPL.json` or `./.PyPPL`
		"""
		fconfig = {}
		for i in list(range(len(PyPPL.DEFAULT_CFGFILES))):
			cfile = path.expanduser(PyPPL.DEFAULT_CFGFILES[i])
			PyPPL.DEFAULT_CFGFILES[i] = cfile
			if path.exists(cfile):
				with open(cfile) as cf:
					utils.dictUpdate(fconfig, json.load(cf))
		
		if cfgfile is not None and path.exists(cfgfile):
			with open(cfgfile) as cfgf:
				utils.dictUpdate(fconfig, json.load(cfgf))
				
		if config is None:	config = {}
		utils.dictUpdate(fconfig, config)
		self.config = fconfig

		fcconfig = {
			'theme': 'default',
			'dot'  : "dot -Tsvg {{dotfile}} -o {{fcfile}}"
		}
		if 'flowchart' in self.config:
			utils.dictUpdate(fcconfig, self.config['flowchart'])
			del self.config['flowchart']
		self.fcconfig = fcconfig

		logconfig = {
			'levels': 'normal',
			'theme':   True,
			'lvldiff': [],
			'file':    path.splitext(sys.argv[0])[0] + ".pyppl.log"  
		}
		if 'log' in self.config:
			if self.config['log']['file'] is True:
				del self.config['log']['file']
			utils.dictUpdate(logconfig, self.config['log'])
			del self.config['log']

		logger.getLogger (logconfig['levels'], logconfig['theme'], logconfig['file'], logconfig['lvldiff'])

		logger.logger.info ('[  PYPPL] Version: %s' % (VERSION))
		logger.logger.info ('[   TIPS] %s' % (random.choice(PyPPL.TIPS)))

		for cfile in (PyPPL.DEFAULT_CFGFILES + [str(cfgfile)]):
			if not path.isfile(cfile): continue
			logger.logger.info ('[ CONFIG] Read from %s' % cfile)
			
		self.starts  = []
		self.nexts   = {}
		self.ends    = []
		self.paths   = {}

	def _procRelations(self, useStarts = True, force = False):
		"""
		Infer the processes relations
		@params:
			`useStarts`: Whether to use `self.starts` to infer or not. Default: True
			`force`: Force to replace `self.nexts, self.ends, self.paths`. Default: False
		@returns:
			`self.nexts, self.ends, self.paths`
		"""

		if self.nexts and not force:
			return self.nexts, self.ends, self.paths

		nexts   = {}
		ends    = []
		paths   = {}

		def getpaths(p, useStarts):
			if p in self.starts and useStarts: return []
			ret     = []
			for dep in p.depends:
				if not dep.depends or (dep in self.starts and useStarts):
					ps = [[dep]]
				else:
					ps  = getpaths(dep, useStarts)
					for p in ps:
						p.insert(0, dep)
				ret.extend(ps)
			return ret

		# nexts, paths
		for proc in PyPPL.PROCS:
			name = id(proc)
			paths[name] = getpaths(proc, useStarts)
			if not name in nexts: nexts[name] = []
			for dp in proc.depends:
				dpname = id(dp)
				if not dpname in nexts: nexts[dpname] = []
				if not proc in nexts[dpname]:
					nexts[dpname].append(proc)
		
		# ends
		for proc in PyPPL.PROCS:
			name     = id(proc)
			ppaths   = paths[name]
			# if some proc depends on it, it's not an ending for sure
			if nexts[name]: continue

			# if don't use starts, then no nexts means it's end
			if not useStarts:
				if proc not in ends: ends.append(proc)
			# if it is a start, then it's an end too
			elif proc in self.starts:
				if proc not in ends: ends.append(proc)
			# obosolete proc
			elif not ppaths: continue
			# else: start of each path should be in starts
			elif all([ps[-1] in self.starts for ps in ppaths]):
				if proc not in ends: ends.append(proc)

		if not ends and useStarts:
			raise ValueError('Cannot figure out ending processes, you probably missed to mark some starting processes.')

		self.nexts  = nexts
		self.ends   = ends
		self.paths  = paths
		return self.nexts, self.ends, self.paths
		
	def start (self, *args):
		"""
		Set the starting processes of the pipeline
		@params:
			`args`: the starting processes
		@returns:
			The pipeline object itself.
		"""
		self.starts = PyPPL._any2procs(*args)
		_, _, paths = self._procRelations(useStarts = False)
		nostarts = []
		for start in self.starts:
			name = start.name(False)
			if any([(set(ps) & set(self.starts)) for ps in paths[id(start)]]):
				logger.logger.info('[WARNING] Process %s will be ignored as a starting process as it depends on other starting processes.' % name)
				nostarts.append(start)
		self.starts = [start for start in self.starts if start not in nostarts]
		self._procRelations(useStarts = True, force = True)
		return self

	def _resume(self, *args):
		"""
		Mark processes as to be resumed
		@params:
			`args`: the processes to be marked. The last element is the mark for processes to be skipped.
		"""
		_, ends, paths = self._procRelations()
		flag    = args[-1]
		args    = args[:-1]
		rsprocs = PyPPL._any2procs(*args)
		
		for end in ends:
			if end in rsprocs: continue
			for ps in paths[id(end)]:
				if (set(ps) & set(rsprocs)): continue
				raise ValueError('None processes along %s\'s path [%s] is resumed.' % (end.name(), ' -> '.join([p.name() for p in reversed(ps)] + [end.name()])))

		ps2skip = []
		for rp in rsprocs:
			# True: totally resumed, 'resume': read from proc.settings
			rp.props['resume'] = 'resume+' if flag.endswith('+') else 'resume'
			rppaths = paths[id(rp)]
			if rppaths:
				ps2skip.extend(list(utils.reduce(lambda x,y: set(x) | set(y), rppaths)))
		ps2skip = set(ps2skip)
		
		for ps in ps2skip:
			if ps.resume: continue
			ps.props['resume'] = flag
	
	def resume (self, *args):
		"""
		Mark processes as to be resumed
		@params:
			`args`: the processes to be marked
		@returns:
			The pipeline object itself.
		"""
		args += ('skip',)
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
		args += ('skip+',)
		self._resume(*args)
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
		if 'proc' in self.config:
			utils.dictUpdate(config, self.config['proc'])
		
		if profile in self.config:
			utils.dictUpdate(config, self.config[profile])

		if not 'runner' in config:
			config['runner'] = profile if profile in PyPPL.RUNNERS else 'local'

		if 'id' in config:
			raise AttributeError('Cannot set a unique id for all process in configuration.')

		return config
	
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

		nexts, ends, paths = self._procRelations()

		doneprocs = set()
		next2run  = self.starts
		while next2run:
			next2run2 = set()
			for p in sorted(next2run, key = lambda x: x.name()):
				pnexts = nexts[id(p)]
				p.log (p.desc, '>>>>>>>')
				p.log ("%s => %s => %s" % (
					[d.name() for d in p.depends] if p.depends else "START",
					p.name(),
					[n.name() for n in pnexts] if pnexts else "END"
				), "depends")
				if p.profile and p.profile != profile:
					p.run(self._getProfile(p.profile))
				else:
					p.run(dftconfig)
				doneprocs |= set([p])
				next2run2 |= set(pnexts)
			# next procs to run must be not finished and all their depends are finished
			next2run = [n for n in next2run2 if n not in doneprocs and all(x in doneprocs for x in n.depends)]
			
		logger.logger.info ('[   DONE] Total time: %s' % utils.formatSecs (time()-timer))
		return self
		
	def flowchart (self, dotfile = None, fcfile = None, dot = None):
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
		import ctypes
		nexts, ends, paths = self._procRelations()

		dot = dot if dot else self.fcconfig['dot']
		fc  = Flowchart(dotfile = dotfile, fcfile = fcfile, dot = dot)
		fc.setTheme(self.fcconfig['theme'])

		for start in self.starts:
			fc.addNode(start, 'start')
			
		for end in self.ends:
			fc.addNode(end, 'end')
			for ps in paths[id(end)]:
				for p in ps: 
					fc.addNode(p)
					nextps = nexts[id(p)]
					if not nextps: continue
					for np in nextps: fc.addLink(p, np)

		fc.generate()
		logger.logger.info ('[   INFO] DOT file saved to: %s' % fc.dotfile)
		logger.logger.info ('[   INFO] Flowchart file saved to: %s' % fc.dotfile)
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
				for p in PyPPL.PROCS:
					if p.id == pany:
						found = True
						ret.append(p)
					elif p.id + '.' + p.tag == pany:
						found = True
						ret.append(p)
				if not found:
					raise ValueError('Cannot find any process associates with "%s"' % str(pany))
		return list(set(ret))

	@staticmethod
	def _registerProc(proc):
		"""
		Register the process
		@params:
			`proc`: The process
		"""
		if not proc in PyPPL.PROCS:
			PyPPL.PROCS.append(proc)

	@staticmethod
	def _checkProc(proc):
		"""
		Check processes, whether 2 processes have the same id and tag
		@params:
			`proc`: The process
		@returns:
			If there are 2 processes with the same id and tag, raise `ValueError`.
		"""
		for p in PyPPL.PROCS:
			if proc is p: continue
			if p.id == proc.id and p.tag == proc.tag:
				raise ValueError('You cannot have two processes with the same id(%s) ang tag(%s).' % (p.id, p.tag))

	@staticmethod
	def registerRunner(runner):
		"""
		Register a runner
		@params:
			`runner`: The runner to be registered.
		"""
		runnerName = runner.__name__
		if runnerName.startswith ('Runner'):
			runnerName = runnerName[6:].lower()
			
		if not runnerName in PyPPL.RUNNERS:
			PyPPL.RUNNERS[runnerName] = runner


for runnername in dir(runners):
	if not runnername.startswith('Runner') or runnername in ['Runner', 'RunnerQueue']:
		continue
	runner = getattr(runners, runnername)
	PyPPL.registerRunner(runner)
