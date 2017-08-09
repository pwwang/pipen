"""
proc module for pyppl
"""
import copy as pycopy
import os
import pickle
import sys
import threading
from random import randint
from subprocess import PIPE, Popen
from time import sleep, time
try:
	from Queue import Queue
except ImportError:
	from queue import Queue

from . import utils, logger
from .aggr import aggr
from .channel import channel
from .job import job as pjob
from .doct import doct

from ..runners import runner_local, runner_sge, runner_ssh, runner_dry, runner_slurm

class proc (object):
	"""
	The proc class defining a process
	
	@static variables:
		`RUNNERS`:       The regiested runners
		`PROCS`:         The "<id>.<tag>" initialized processes, used to detected whether there are two processes with the same id and tag.
		`ALIAS`:         The alias for the properties
		`LOG_NLINE`:     The limit of lines of logging information of same type of messages
		
	@magic methods:
		`__getattr__(self, name)`: get the value of a property in `self.props`
		`__setattr__(self, name, value)`: set the value of a property in `self.config`
	"""

	RUNNERS      = {}
	PROCS        = {}
	ALIAS        = {
		'exdir':   'exportdir',
		'exhow':   'exporthow',
		'exow':    'exportow',
		'errhow':  'errorhow',
		'errntry': 'errorntry',
		'lang':    'defaultSh',
		'rc':      'retcodes',
		'ppldir':  'tmpdir'
	}
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
		'BRINGFILE_OVERWRITING': 3,
		'OUTNAME_USING_OUTTYPES': 1,
		'OUTDIR_CREATED': 0,
		'OUTDIR_CREATED_AFTER_RESET': 0,
		'SCRIPT_USING_TEMPLATE': 1,
		'SCRIPT_EXISTS': -2,
		'NOSCRIPT': 1,
		'JOB_RESETTING': 0,
		'INFILE_OVERWRITING': -3,
		'INFILE_RENAMING': -3
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
	EX_SYMLINK   = ['link', 'symlink', 'symbol']

	def __init__ (self, tag = 'notag', desc = 'No description.', id = None):
		"""
		Constructor
		@params:
			`tag`:  The tag of the process
			`desc`: The description of the process
			`id`:   The identify of the process
		"""
		
		# computed props
		self.__dict__['props']    = {}
		# configs
		self.__dict__['config']   = {}

		pid                       = utils.varname(self.__class__.__name__, 2) if id is None else id
		
		if ' ' in tag:
			raise ValueError("No space is allowed in %s's tag property. You probably mean 'desc' instead of 'tag'?" % pid)

		# The input that user specified
		self.config['input']      = ''
		# The output that user specified
		self.config['output']     = {}
		# Where cache file and wdir located
		self.config['tmpdir']     = os.path.abspath("./workdir")
		# How many jobs to run concurrently
		self.config['forks']      = 1
		# The cache option
		self.config['cache']      = True # False or 'export'
		# Valid return code
		self.config['retcodes']   = [0]
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
		# Select the runner
		self.config['runner']     = 'local'
		# The script of the jobs
		self.config['script']     = ''
		# The dependencies
		self.config['depends']    = []
		# The tag of the job
		self.config['tag']        = tag
		# The description of the job		
		self.config['desc']       = desc
		# The directory to export the output files
		self.config['exportdir']  = ''
		# How to export
		self.config['exporthow']  = 'move' # symlink, copy, gzip 
		# Whether to overwrite the existing files
		self.config['exportow']   = True # overwrite
		# How to deal with the errors
		self.config['errorhow']   = "terminate" # retry, ignore
		# How many times to retry to jobs once error occurs
		self.config['errorntry']  = 3
		# Default shell/language
		self.config['defaultSh']  = 'bash'
		# The command to run before jobs start
		self.config['beforeCmd']  = ""
		# The command to run after jobs start
		self.config['afterCmd']   = ""
		# The workdir for the process
		self.config['workdir']    = ''
		# The extra arguments for the process
		self.config['args']       = doct()
		# The output channel of the process
		self.config['channel']    = channel.create()
		# The aggregation name of the process
		self.config['aggr']       = None
		# The callfront function of the process
		self.config['callfront']  = None
		# The callback function of the process
		self.config['callback']   = None
		# The bring files that user specified
		self.config['brings']     = {}
		# expect
		self.config['expect']     = ''
		# partial export         
		# Either the key of output file or the pattern
		self.config['expart']     = ''

		# id of the process, actually it's the variable name of the process
		self.props['id']         = pid  
		# the tag
		self.props['tag']        = tag
		# the description
		self.props['desc']       = self.config['desc']

		# the cachefile, cache file will be in <tmpdir>/<cachefile>
		#self.props['cachefile']  = 'cached.jobs'
		# which processes this one depents on
		#self.props['depends']    = []
		# the script
		self.props['script']     = ""

		self.props['input']      = ''
		self.props['indata']     = {}
		self.props['output']     = ''
		self.props['depends']    = self.config['depends']
		self.props['nexts']      = []
		self.props['tmpdir']     = self.config['tmpdir']
		self.props['forks']      = self.config['forks']
		self.props['cache']      = self.config['cache']
		#self.props['cached']     = True
		self.props['retcodes']   = self.config['retcodes']
		self.props['beforeCmd']  = self.config['beforeCmd']
		self.props['afterCmd']   = self.config['afterCmd']
		self.props['echo']       = self.config['echo']
		self.props['runner']     = self.config['runner']
		self.props['exportdir']  = self.config['exportdir']
		self.props['exporthow']  = self.config['exporthow']
		self.props['exportow']   = self.config['exportow']
		self.props['errorhow']   = self.config['errorhow']
		self.props['errorntry']  = self.config['errorntry']
		self.props['jobs']       = []
		self.props['ncjobids']   = [] # non-cached job ids
		self.props['defaultSh']  = self.config['defaultSh']
		self.props['channel']    = channel.create()
		self.props['length']     = 0
		# remember which property is set, then it won't be overwritten by configurations
		self.props['sets']       = [] 
		self.props['procvars']   = {}
		self.props['workdir']    = ''
		# for unittest, in real case, the logger will be got from pyppl
		#self.props['logger']     = None
		self.props['args']       = self.config['args']
		self.props['aggr']       = self.config['aggr']
		self.props['callfront']  = self.config['callfront']
		self.props['callback']   = self.config['callback']
		self.props['brings']     = self.config['brings']
		self.props['suffix']     = ''
		self.props['lognline']   = {key:0 for key in proc.LOG_NLINE.keys()}
		self.props['lognline']['prevlog'] = ''
		self.props['expect']     = self.config['expect']
		self.props['expart']     = self.config['expart']
		

	def __getattr__ (self, name):
		if not name in self.props and not name in proc.ALIAS and not name.endswith ('Runner'):
			raise ValueError('Property "%s" of proc is not found' % name)
		
		if name in proc.ALIAS:
			name = proc.ALIAS[name]
			
		return self.props[name]

	def __setattr__ (self, name, value):
		if not name in self.config and not name in proc.ALIAS and not name.endswith ('Runner'):
			raise ValueError('Cannot set property "%s" for proc instance' % name)
		
		if name in proc.ALIAS:
			name = proc.ALIAS[name]
		
		if name not in self.sets:
			self.sets.append(name)
		self.config[name] = value
		
		if name == 'depends':
			# remove me from nexts of my previous depends
			for depend in self.depends:
				if not self in depend.nexts: 
					continue
				del depend.props['nexts'][depend.nexts.index(self)]
			self.props['depends'] = []
			
			depends = value
			if not isinstance (value, list): 
				depends = [value]
			for depend in depends:
				if isinstance (depend, proc):					
					self.props['depends'].append (depend)
					if self not in depend.nexts:
						depend.nexts.append (self)
						
				elif isinstance (depend, aggr):
					for p in depend.ends:
						self.props['depends'].append (p)
						if self not in p.nexts:
							p.nexts.append (self)
		elif name == 'args':
			self.config[name] = doct(value)
			self.props[name]  = self.config[name]
		else:
			self.props[name] = value
		
	def log (self, msg, level="info", key = ''):
		"""
		The log function with aggregation name, process id and tag integrated.
		@params:
			`msg`:   The message to log
			`level`: The log level
			`key`:   The type of messages
		"""
		level  = "[%s]" % level
		name   = self._name()
		
		maxline = proc.LOG_NLINE[key]
		prevlog = self.lognline['prevlog']

		if key == prevlog:
			if self.lognline[key] < abs(maxline):
				logger.logger.info ("%s %s: %s" % (level, name, msg))
		else:
			n_omit = self.lognline[prevlog] - abs(proc.LOG_NLINE[prevlog])
			if n_omit > 0 and proc.LOG_NLINE[prevlog] < 0: 
				logname = 'logs' if n_omit > 1 else 'log'
				maxinfo = ' (%s, max=%s)' % (prevlog, abs(proc.LOG_NLINE[prevlog])) if prevlog else ''
				logger.logger.info ("[DEBUG] %s: ... and %s %s omitted%s." % (name, n_omit, logname, maxinfo))
			self.lognline[prevlog]   = 0

			if self.lognline[key] < abs(maxline):
				logger.logger.info ("%s %s: %s" % (level, name, msg))

		self.lognline['prevlog'] = key
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
		newproc = proc (tag if tag is not None else self.tag, desc if desc is not None else self.desc)
		
		config = {key:val for key, val in self.config.items() if key not in ['tag', 'workdir', 'aggr', 'desc']}
		config['tag']      = newproc.tag
		config['desc']     = newproc.desc
		config['aggr']     = ''
		config['workdir']  = ''
		config['args']     = doct (self.config['args'])
		#props   = {key:val for key, val in self.props.items() if key not in ['cached', 'procvars', 'ncjobids', 'sets', 'channel', 'jobs', 'depends', 'nexts', 'tag', 'workdir', 'id', 'args']}
		props   = {key:val for key, val in self.props.items() if key not in ['procvars', 'sets', 'ncjobids', 'channel', 'jobs', 'depends', 'nexts', 'tag', 'workdir', 'id', 'args', 'desc']}
		props['sets']      = [s for s in self.sets]
		#props['cached']    = True
		props['procvars']  = {}
		props['channel']   = channel.create()
		props['depends']   = []
		props['nexts']     = []
		props['jobs']      = []
		props['ncjobids']  = []
		#props['sets']      = []
		props['workdir']   = ''
		props['args']      = config['args']
		props['id']        = utils.varname(r'\w+\.' + self.copy.__name__, 3) if newid is None else newid
		newproc.__dict__['config'].update(config)
		newproc.__dict__['props'].update(props)
		return newproc

	def _suffix (self):
		"""
		Calcuate a uid for the process according to the configuration
		@returns:
			The uid
		"""
		if self.suffix:
			return self.suffix
		
		config        = { key:val for key, val in self.config.items() if key not in ['desc', 'workdir', 'forks', 'cache', 'retcodes', 'expect', 'callback', 'echo', 'runner', 'exportdir', 'exporthow', 'exportow', 'errorhow', 'errorntry'] or key.endswith ('Runner') }
		config['id']  = self.id
		config['tag'] = self.tag
		
		if 'callfront' in config:
			config['callfront'] = utils.funcsig(config['callfront'])
		#if 'callback' in config:
		#	config['callback'] = utils.funcsig(config['callback'])
		# proc is not picklable
		if 'depends' in config:
			depends = config['depends']
			if not isinstance (depends, list):
				depends = [depends]
				
			pickable_depends = []			
			for depend in depends:
				if isinstance(depend, proc):
					# the suffix makes sure it's the dependent
					pickable_depends.append (depend._name(False) + depend.suffix)
				elif isinstance(depends, aggr):
					for depend in depends.ends:
						pickable_depends.append (depend._name(False) + depend.suffix)
				
			config['depends'] = pickable_depends
		
		# lambda not pickable
		if 'input' in config and isinstance(config['input'], dict):
			config['input'] = pycopy.copy(config['input'])
			for key, val in config['input'].items():
				config['input'][key] = utils.funcsig(val) if callable(val) else val
		
		signature = pickle.dumps(str(config))
		self.props['suffix'] = utils.uid(signature)
		return self.suffix

	def _tidyBeforeRun (self):
		"""
		Do some preparation before running jobs
		"""
		
		self._buildProps ()
		self._saveSettings()
		if callable (self.callfront):
			self.log ("Calling callfront ...", "debug")
			self.callfront (self)
		self._buildInput ()
		self._buildProcVars ()
		self._buildJobs ()

	def _tidyAfterRun (self):
		"""
		Do some cleaning after running jobs
		"""
		failedjobs = [job for job in self.jobs if not job.succeed()]
		
		if not failedjobs:	
			self.log ('Successful jobs: ALL', 'debug')
			if callable (self.callback):		
				self.log('Calling callback ...', 'debug')
				self.callback (self)
		else:
			failedjobs[0].showError (len(failedjobs))
			if self.errorhow != 'ignore': 
				sys.exit (1) # don't go further
	
	def _name (self, incAggr = True):
		"""
		Get my name include `aggr`, `id`, `tag`
		@returns:
			the name
		"""
		aggrName  = "@%s" % self.aggr if self.aggr and incAggr else ""
		tag   = ".%s" % self.tag  if self.tag != "notag" else ""
		return "%s%s%s" % (self.id, tag, aggrName)

	def run (self, config = None):
		"""
		Run the jobs with a configuration
		@params:
			`config`: The configuration
		"""
		
		timer = time()
		if config is None:
			config = {}
		
		self.log (self.desc, '>>>>>>>')
		# log the dependencies
		self.log ("%s => %s => %s" % (
			[p._name() for p in self.depends] if self.depends else "START", 
			self._name(), 
			[p._name() for p in self.nexts] if self.nexts else "END"
		), "depends")
		self._readConfig (config)
		self._tidyBeforeRun ()
		self._runCmd('beforeCmd')
		if not self._checkCached():
			self.log (self.workdir, 'RUNNING')
		else:
			self.log (self.workdir, 'CACHED')
		self._runJobs()
		self._runCmd('afterCmd')
		self._tidyAfterRun ()
		self.log ('Done (time: %s).' % utils.formatTime(time() - timer), 'info')

				
	def _buildProps (self):
		"""
		Compute some properties
		"""
		
		if isinstance (self.retcodes, int):
			self.props['retcodes'] = [self.retcodes]
		
		if isinstance (self.retcodes, str):
			self.props['retcodes'] = [int(i) for i in self.retcodes.split(',')]

		key = self._name(False)
		if key in proc.PROCS and proc.PROCS[key] != self:
			raise Exception ('A proc with id "%s" and tag "%s" already exists.' % (self.id, self.tag))
		proc.PROCS[key] = self
		
		if not 'workdir' in self.sets and not self.workdir:
			self.props['workdir'] = os.path.join(self.ppldir, "PyPPL.%s.%s.%s" % (self.id, self.tag, self._suffix()))
		
		if not os.path.exists (self.workdir): 
			os.makedirs (self.workdir)	

		if self.exdir and not os.path.exists (self.exdir):
			os.makedirs (self.exdir)
			
		if not isinstance(self.expart, list):
			self.props['expart'] = [self.expart]
		self.props['expart'] = list(filter(None, self.expart))
			
		if self.echo in [True, False, 'stderr', 'stdout']:
			if self.echo is True:
				self.props['echo'] = { 'jobs': 0 }
			elif self.echo is False:
				self.props['echo'] = { 'jobs': 0, 'type': [] }
			else:
				self.props['echo'] = { 'jobs': 0, 'type': self.echo }
				
		if not 'jobs' in self.echo:
			self.echo['jobs'] = 0
		if isinstance(self.echo['jobs'], int):
			self.echo['jobs'] = [self.echo['jobs']]
		elif isinstance(self.echo['jobs'], utils.basestring):
			self.echo['jobs'] = map(lambda x: int(x.strip()), self.echo['jobs'].split(','))
				
		if not 'type' in self.echo:
			self.echo['type'] = ['stderr', 'stdout']
		if not isinstance(self.echo['type'], list):
			self.echo['type'] = [self.echo['type']]
		
		if not 'filter' in self.echo:
			self.echo['filter'] = ''
		
		self.log ('Properties set explictly: %s' % str(self.sets), 'debug')
	
	def _saveSettings (self):
		"""
		Save all settings in proc.settings, mostly for debug
		"""
		settingsfile = os.path.join(self.workdir, 'proc.settings')
		with open(settingsfile, 'w') as f:
			for key in sorted(self.props.keys()):
				val = self.props[key]
				# deal with lambda functions
				if key == 'input':
					f.write('\n[input]\n')
					if not isinstance(val, dict):
						f.write('key: ' + str(val) + '\n')
					else:
						for k in sorted(val.keys()):
							v = val[k]
							if callable(v):
								f.write (k + ': ' + utils.funcsig(v) + '\n')
							else:
								f.write (k + ': ' + str(v) + '\n')
				elif key in ['depends', 'nexts']:
					f.write('\n['+ key +']\n')
					f.write('procs: ' + str([p._name() for p in val]) + '\n')
				elif key == 'jobs':
					pass
				elif key in ['callfront', 'callback']:
					f.write('\n['+ key +']\n')
					f.write('func: ' + utils.funcsig(val) + '\n')
				elif key == 'indata':
					f.write('\n['+ key +']\n')
					for k in sorted(val.keys()):
						v = val[k]
						f.write (k + '.type: ' + str(v['type']) + '\n')
						f.write (k + '.data: \n')
						for _ in v['data']:
							f.write ('  ' + str(_) + '\n')
				elif key in ['lognline', 'args'] or key.endswith('Runner'):
					f.write('\n['+ key +']\n')
					for k in sorted(val.keys()):
						v = val[k]
						f.write ((k if k else "''") + ': ' + str(v) + '\n')
				elif key == 'script':
					f.write('\n['+ key +']\n')
					f.write('value:\n')
					f.write('  ' + val.replace('\n', '\n  ') + '\n')
				else:
					f.write('\n['+ key +']\n')
					f.write('value: ' + str(val) + '\n')
					
		self.log ('Settings saved to: %s' % settingsfile, 'debug')
					
				
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

		indata    = self.config['input']
		if not isinstance (indata, dict):
			indata = ','.join(utils.alwaysList (indata))			
			depdchan = channel.fromChannels (*[d.channel for d in self.depends])
			indata = {indata: depdchan if self.depends else channel.fromArgv()}
			
		# expand to one key-channel pairs
		for inkeys, invals in indata.items():
			keys   = utils.split(inkeys, ',')
			# allow empty input
			if len(keys) == 1 and keys[0] == '':
				invals = ['']
				
			invals = utils.range2list(invals)
			if callable (invals):
				vals  = invals (*[d.channel.copy() for d in self.depends] if self.depends else channel.fromArgv())
				if not isinstance (vals, channel):
					vals = channel.create(vals)
				vals  = vals.split()
			elif isinstance (invals, utils.basestring): # only for files: "/a/b/*.txt, /a/c/*.txt"
				vals  = utils.split(invals, ',')
			elif isinstance (invals, channel):
				vals  = invals.split()
			elif isinstance (invals, list):
				vals  = channel.create(invals).split()
			else:
				raise ValueError ("%s: Unexpected values for input. Expect dict, list, str, channel, callable." % self._name())
				
			width = len (vals)
			if len (keys) > width:
				raise ValueError ('%s: Not enough data for input variables.\nVarialbes: %s\nData: %s' % (self._name(), keys, vals))
			
			for i, key in enumerate(keys):
				intype = key.split(':')[-1]
				thekey = key.split(':')[0]
				val    = vals[i].toList() #if isinstance(vals[i], channel) else vals[i]

				if intype not in proc.IN_VARTYPE + proc.IN_FILESTYPE + proc.IN_FILETYPE:
					intype = proc.IN_VARTYPE[0]
				
				if intype in proc.IN_FILESTYPE:
					for x, v in enumerate(val):
						if isinstance (v, utils.basestring):
							val[x] = channel.fromPath (v).toList()
				
				if self.length == 0: 
					self.props['length'] = len (val)
				if self.length != len (val):
					raise ValueError ('%s: Expect same lengths for input channels, but got %s and %s (keys: %s).' % (self._name(), self.length, len (val), key))
				self.props['indata'][thekey] = {
					'type': intype,
					'data': val
				}
			self.props['jobs'] = [None] * self.length
				
	def _buildProcVars (self):
		"""
		also add proc.props, mostly scalar values
		"""
		alias = {val:key for key, val in proc.ALIAS.items()}
		for prop in sorted(self.props.keys()):
			val = self.props[prop]
			if not prop in ['id', 'tag', 'tmpdir', 'forks', 'cache', 'workdir', 'runner', 'errorhow', 'errorntry', 'expart',
							'defaultSh', 'exportdir', 'exporthow', 'exportow', 'echo', 'length', 'args', 'suffix', 'expect']:
				continue
			
			if prop == 'args':
				self.props['procvars']['args'] = val
				for k in sorted(val.keys()):
					self.props['procvars']['args.' + k] = val[k]
					if not k.startswith('_'):
						self.log('%s => %s' % (k, val[k]), 'p.args')
			else:
				self.props['procvars']['proc.' + prop] = val
				if prop in alias: 
					self.props['procvars']['proc.' + alias[prop]] = val
					if val is False or val:
						self.log ('%s (%s) => %s' % (prop, alias[prop], val), 'p.props')
				else:
					if val is False or val:
						self.log ('%s => %s' % (prop, val), 'p.props')

				
	def _buildJobs (self):
		rptjob = randint(0, self.length-1)
		for i in range(self.length):
			job = pjob (i, self)
			self.jobs[i] = job
			job.init ()
			row = [x['data'] for x in job.output.values()]
			self.channel.rbind (row)
		self.jobs[rptjob].report()

	def _readConfig (self, config):
		"""
		Read the configuration
		@params:
			`config`: The configuration
		"""
		conf = { (key if not key in proc.ALIAS else proc.ALIAS[key]):val for key, val in config.items() if key not in self.sets }
		self.config.update (conf)
		
		for key, val in conf.items():
			self.props[key] = val

	def _checkCached (self):
		"""
		Tell whether the jobs are cached
		@returns:
			True if all jobs are cached, otherwise False
		"""
		self.props['ncjobids'] = range(self.length)
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
				
		self.log ('Truely cached jobs: %s' % (trulyCachedJids if len(trulyCachedJids) < self.length else 'ALL'), 'info')
		self.log ('Export cached jobs: %s' % (exptCachedJids  if len(exptCachedJids)  < self.length else 'ALL'), 'info')
		
		if self.ncjobids:
			if len(self.ncjobids) < self.length:
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
		if not self.props[key]:	
			return 0
		cmd = utils.format(self.props[key], self.procvars)
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
			raise Exception ('Failed to run %s: \n----------------------------------\n%s' % (key, cmd))
		return rc

	def _runJobs (self):
		"""
		Submit and run the jobs
		"""
		# submit jobs
		def sworker (q):
			"""
			The worker to run jobs
			"""
			while True:
				data = q.get()
				
				if data is None:
					break
					
				(run, i) = data
				sleep (i)	
				#if hasattr(run, 'checkRunning') and run.checkRunning and run.isRunning():
				# anyway check whether the job is running before submit it
				if run.isRunning():
					self.log ("Job #%-3s is already running, skip submitting." % run.job.index, 'submit')
				else:
					run.submit()
				run.wait() 
				run.finish()
				q.task_done()
		
		runner    = proc.RUNNERS[self.runner]
		maxsubmit = self.forks
		if hasattr(runner, 'maxsubmit'): 
			maxsubmit = runner.maxsubmit
		interval  = .1
		if hasattr(runner, 'interval'): 
			interval = runner.interval
		
		sq = Queue()
		for i, job in enumerate(self.jobs):
			if i in self.ncjobids:
				rjob = runner (job)
				tm = int(i/maxsubmit) * interval
				sq.put ((rjob, tm))
			else:
				job.done()

		# submit jobs
		threads       = []
		nojobs2submit = min (self.forks, len(self.ncjobids))
		for i in range (nojobs2submit):
			t = threading.Thread(target = sworker, args = (sq, ))
			t.daemon = True
			t.start ()
			threads.append (t)
		
		sq.join()
		
		for i in range(nojobs2submit):
			sq.put (None)
		for thr in threads:
			thr.join()
		
		# make sure only one thread left
		self.log('Active thread(s): %s' % str(threading.activeCount()), 'debug')

	@staticmethod
	def registerRunner (runner):
		"""
		Register a runner
		@params:
			`runner`: The runner to be registered.
		"""
		runner_name = runner.__name__
		if runner_name.startswith ('runner_'):
			runner_name = runner_name[7:]
			
		if not runner_name in proc.RUNNERS:
			proc.RUNNERS[runner_name] = runner
			
proc.registerRunner (runner_local)
proc.registerRunner (runner_sge)
proc.registerRunner (runner_ssh)
proc.registerRunner (runner_slurm)
proc.registerRunner (runner_dry)
