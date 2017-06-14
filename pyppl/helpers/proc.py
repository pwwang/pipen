"""
proc module for pyppl
"""
import copy as pycopy
import os
import pickle
import sys
import threading
from Queue import Queue
from random import randint
from subprocess import PIPE, Popen
from time import sleep, time

from . import utils
from .aggr import aggr
from .channel import channel
from .job import job as pjob

from ..runners import runner_local, runner_sge, runner_ssh


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
		'EXPORT_CACHE_USING_SYMLINK': 3,
		'BRINGFILE_OVERWRITING': 3,
		'OUTNAME_USING_OUTTYPES': 1,
		'SCRIPT_USING_TEMPLATE': 1,
		'SCRIPT_EXISTS': 1,
		'NOSCRIPT': 1,
		'INFILE_OVERWRITING': -3
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

	def __init__ (self, tag = 'notag'):
		"""
		Constructor
		@params:
			`tag`: The tag of the process
		"""
		
		# computed props
		self.__dict__['props']    = {}
		# configs
		self.__dict__['config']   = {}

		pid                       = utils.varname(self.__class__.__name__, 2)

		self.config['input']      = ''
		self.config['output']     = {}
		# where cache file and wdir located
		self.config['tmpdir']     = os.path.abspath("./workdir")
		self.config['forks']      = 1
		self.config['cache']      = True # False or 'export' or 'export+' (do True if failed do export)
		self.config['retcodes']   = [0]
		self.config['echo']       = False
		self.config['runner']     = 'local'
		self.config['script']     = ''
		self.config['depends']    = []
		self.config['tag']        = tag
		self.config['exportdir']  = ''
		self.config['exporthow']  = 'move' # symlink, copy, gzip 
		self.config['exportow']   = True # overwrite
		self.config['errorhow']   = "terminate" # retry, ignore
		self.config['errorntry']  = 3
		self.config['defaultSh']  = 'bash'
		self.config['beforeCmd']  = ""
		self.config['afterCmd']   = ""
		self.config['workdir']    = ''
		self.config['args']       = {}
		self.config['channel']    = channel.create()
		self.config['aggr']       = None
		self.config['callback']   = None
		self.config['brings']     = {}
		# init props

		# id of the process, actually it's the variable name of the process
		self.props['id']         = pid  
		# the tag
		self.props['tag']        = tag

		# the cachefile, cache file will be in <tmpdir>/<cachefile>
		#self.props['cachefile']  = 'cached.jobs'
		# which processes this one depents on
		self.props['depends']    = []
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
		self.props['cached']     = True
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
		self.props['logger']     = None
		self.props['args']       = self.config['args']
		self.props['checkrun']   = True
		self.props['aggr']       = self.config['aggr']
		self.props['callback']   = self.config['callback']
		self.props['brings']     = self.config['brings']
		self.props['lognline']   = {key:0 for key in proc.LOG_NLINE.keys()}
		self.props['suffix']     = ''

	def __getattr__ (self, name):
		if not self.props.has_key(name) and not proc.ALIAS.has_key(name) and not name.endswith ('Runner'):
			raise ValueError('Property "%s" of proc is not found' % name)
		
		if proc.ALIAS.has_key(name):
			name = proc.ALIAS[name]
			
		return self.props[name]

	def __setattr__ (self, name, value):
		if not self.config.has_key(name) and not proc.ALIAS.has_key(name) and not name.endswith ('Runner'):
			raise ValueError('Cannot set property "%s" for proc instance' % name)
		
		if proc.ALIAS.has_key(name):
			name = proc.ALIAS[name]
		
		self.sets.append(name)
		self.config[name] = value
		
		if name == 'depends':
			# remove me from nexts of my previous depends
			for depend in self.depends:
				if not self in depend.nexts: continue
				del depend.props['nexts'][depend.nexts.index(self)]
			self.props['depends'] = []
			
			depends = value
			if not isinstance (value, list): depends = [value]
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
		else:
			self.props[name] = value
		
	def log (self, msg, level="info", flag=None, key = ''):
		"""
		The log function with aggregation name, process id and tag integrated.
		@params:
			`msg`:   The message to log
			`levle`: The log level
			`flag`:  The flag
			`key`:   The type of messages
		"""
		if flag is None: 
			flag = level
		flag  = flag.upper().rjust(7)
		flag  = "[%s]" % flag
		title = self._name()
		func  = getattr(self.logger, level)
		
		maxline = proc.LOG_NLINE[key]
		if self.lognline[key] < abs(maxline):
			func ("%s %s: %s" % (flag, title, msg))
		elif self.lognline[key] == abs(maxline) and maxline < 0:
			func ("%s %s: %s" % (flag, title, "... omitting the same type of coming logs"))
		self.lognline[key] += 1

	def copy (self, tag=None, newid=None):
		"""
		Copy a process
		@params:
			`newid`: The new id of the process, default: `None` (use the varname)
			`tag`:   The tag of the new process, default: `None` (used the old one)
		@returns:
			The new process
		"""
		newproc = proc (tag if tag is not None else self.tag)
		config = {key:val for key, val in self.config.iteritems() if key not in ['tag', 'workdir', 'aggr']}
		config['tag']      = newproc.tag
		config['aggr']     = ''
		config['workdir']  = ''
		props   = {key:val for key, val in self.props.iteritems() if key not in ['cached', 'procvars', 'ncjobids', 'sets', 'channel', 'jobs', 'depends', 'nexts', 'tag', 'workdir', 'id', 'args']}
		props['cached']    = True
		props['procvars']  = {}
		props['channel']   = channel.create()
		props['depends']   = []
		props['nexts']     = []
		props['jobs']      = []
		props['ncjobids']  = []
		props['sets']      = []
		props['workdir']   = ''
		props['args']      = pycopy.copy(self.props['args'])
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

		config        = { key:val for key, val in self.config.iteritems() if key not in ['workdir', 'forks', 'cache', 'retcodes', 'echo', 'runner', 'exportdir', 'exporthow', 'exportow', 'errorhow', 'errorntry'] or key.endswith ('Runner') }
		config['id']  = self.id
		config['tag'] = self.tag
		
		if config.has_key ('callback'):
			config['callback'] = utils.funcsig(config['callback'])
		# proc is not picklable
		if config.has_key('depends'):
			depends = config['depends']
			pickable_depends = []
			if isinstance(depends, proc):
				depends = [depends]
			elif isinstance(depends, aggr):
				depends = depends.procs
			for depend in depends:
				pickable_depends.append(depend.id + '.' + depend.tag)
			config['depends'] = pickable_depends
		
		# lambda not pickable
		if config.has_key ('input') and isinstance(config['input'], dict):
			config['input'] = pycopy.copy(config['input'])
			for key, val in config['input'].iteritems():
				config['input'][key] = utils.funcsig(val) if callable(val) else val

		signature = pickle.dumps(str(config))
		self.props['suffix'] = utils.uid(signature)
		return self.suffix

	def _tidyBeforeRun (self):
		"""
		Do some preparation before running jobs
		"""
		self._buildProps ()
		self._buildInput ()
		self._buildProcVars ()
		self._buildJobs ()

	def _tidyAfterRun (self):
		"""
		Do some cleaning after running jobs
		"""
		failedjobs = []
		for i in self.ncjobids:
			job = self.jobs[i]
			if not job.succeed():
				failedjobs.append (job)
		
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

		self.logger.info ('[  START] ' + utils.padBoth(' ' + self._name() + ' ', 80, '-'))
		# log the dependencies
		self.log ("%s => %s => %s" % ([p._name() for p in self.depends] if self.depends else "START", self._name(), [p._name() for p in self.nexts] if self.nexts else "END"), "info", "depends")
		self._readConfig (config)
		self._tidyBeforeRun ()
		if self._runCmd('beforeCmd') != 0:
			raise Exception ('Failed to run beforeCmd: %s' % self.beforeCmd)
		if not self._isCached():
			# I am not cached, touch the input of my nexts?
			# but my nexts are not initized, how?
			# set cached to False, then my nexts will access it
			self.props['cached'] = False
			self.log (self.workdir, 'info', 'RUNNING')
			self._runJobs()
		if self._runCmd('afterCmd') != 0:
			raise Exception ('Failed to run afterCmd: %s' % self.afterCmd)
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
		for inkeys, invals in indata.iteritems():
			keys   = utils.split(inkeys, ',')
			if callable (invals):
				vals  = invals (*[d.channel.copy() for d in self.depends] if self.depends else channel.fromArgv())
				vals  = vals.split()
			elif isinstance (invals, basestring): # only for files: "/a/b/*.txt, /a/c/*.txt"
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
						if isinstance (v, basestring):
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
		alias = {val:key for key, val in proc.ALIAS.iteritems()}
		for prop in sorted(self.props.keys()):
			val = self.props[prop]
			if not prop in ['id', 'tag', 'tmpdir', 'forks', 'cache', 'workdir', 'echo', 'runner',
							'errorhow', 'errorntry', 'defaultSh', 'exportdir', 'exporthow', 'exportow',
							'indir', 'outdir', 'length', 'args']:
				continue
			
			if prop == 'args':
				self.props['procvars']['proc.args'] = val
				for k, v in val.iteritems():
					self.props['procvars']['proc.args.' + k] = v
					self.log('%s => %s' % (k, v), 'info', 'p.args')
			else:
				if alias.has_key (prop): 
					prop = alias[prop]
				self.props['procvars']['proc.' + prop] = val
				self.log ('%s => %s' % (prop, val), 'info', 'p.props')

				
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
		conf = { key:val for key, val in config.iteritems() if key not in self.sets }
		self.config.update (conf)

		for key, val in conf.iteritems():
			self.props[key] = val

	def _isCached (self):
		"""
		Tell whether the jobs are cached
		@returns:
			True if all jobs are cached, otherwise False
		"""
		self.props['ncjobids'] = range(self.length)
		if self.cache == False:
			self.log ('Not cached, because proc.cache is False', 'debug')
			return False
		
		if self.cache == True:
			for depend in self.depends:
				if depend.cached: continue
				self.log ('Not cached, my dependent "%s" not cached.' % depend._name(), 'debug')
				return False
		
		trulyCachedJids        = []
		exptCachedJids         = []
		self.props['ncjobids'] = []
		for i, job in enumerate(self.jobs):
			job = self.jobs[i]
			if job.isTrulyCached ():
				trulyCachedJids.append(i)
			elif job.isExptCached ():
				exptCachedJids.append (i)
			else:
				self.props['ncjobids'].append (i)
				
		self.log ('Truely cached jobs: %s' % (trulyCachedJids if len(trulyCachedJids) < self.length else 'ALL'), 'debug')
		self.log ('Export cached jobs: %s' % (exptCachedJids  if len(exptCachedJids)  < self.length else 'ALL'), 'debug')
		
		if self.ncjobids:
			if len(self.ncjobids) < self.length:
				self.log ('Partly cached, only run non-cached jobs.', 'info')
				self.log ('Jobs to be running: %s' % self.ncjobids, 'debug')
			else:
				self.log ('Not cached, none of the jobs are cached.', 'info')
			return False
		else:
			self.log (self.workdir, 'info', 'CACHED')
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
		self.log ('Running <%s>: %s' % (key, cmd), 'info')
		
		p = Popen (cmd, shell=True, stdin=PIPE, stderr=PIPE, stdout=PIPE)
		if self.echo:
			for line in iter(p.stdout.readline, ''):
				self.logger.info ('[ STDOUT] ' + line.rstrip("\n"))
		for line in iter(p.stderr.readline, ''):
			self.logger.error ('[ STDERR] ' + line.rstrip("\n"))
		return p.wait()

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
				(run, i) = q.get()
				sleep (i)
				if self.checkrun and run.isRunning(False):
					self.log ("Job #%s is already running, skip submitting." % run.job.index, 'info')
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
		for i in self.ncjobids:
			rjob = runner (self.jobs[i])
			tm = int(i/maxsubmit) * interval
			sq.put ((rjob, tm))

		# submit jobs
		nojobs2submit = min (self.forks, len(self.ncjobids))
		for i in range (nojobs2submit):
			t = threading.Thread(target = sworker, args = (sq, ))
			t.daemon = True
			t.start ()
		
		sq.join()

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
			
		if not proc.RUNNERS.has_key(runner_name):
			proc.RUNNERS[runner_name] = runner
			
proc.registerRunner (runner_local)
proc.registerRunner (runner_sge)
proc.registerRunner (runner_ssh)
