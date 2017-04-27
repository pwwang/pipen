import os, pickle, shlex, shutil, threading, sys
import copy as pycopy
from time import sleep, time
from glob import glob
from random import randint
from channel import channel
from aggr import aggr
from job import job as pjob
import utils
from subprocess import Popen, PIPE
from Queue import Queue
from collections import OrderedDict
from ..runners import runner_local, runner_sge, runner_ssh


class proc (object):
	"""
	The proc class defining a process
	
	@static variables:
		`runners`: The regiested runners
		`ids`:     The "<id>.<tag>" initialized processes, used to detected whether there are two processes with the same id and tag.
		`alias`:   The alias for the properties
		
	@magic methods:
		`__getattr__(self, name)`: get the value of a property in `self.props`
		`__setattr__(self, name, value)`: set the value of a property in `self.config`
	"""

	runners = {}
	ids     = {}
	alias   = {
		'exdir':   'exportdir',
		'exhow':   'exporthow',
		'exow':    'exportow',
		'errhow':  'errorhow',
		'errntry': 'errorntry',
		'lang':    'defaultSh',
		'rc':      'retcodes'
	}

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
		self.config['errorntry']  = 1
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
		self.props['id']         =  pid  
		# the tag
		self.props['tag']        = tag

		# the cachefile, cache file will be in <tmpdir>/<cachefile>
		self.props['cachefile']  = 'cached.jobs'
		# which processes this one depents on
		self.props['depends']    = []
		# the script
		self.props['script']     = ""

		self.props['input']      = {}
		self.props['output']     = {}
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
		self.props['sets']       = []
		self.props['procvars']   = {}
		self.props['workdir']    = ''
		self.props['logger']     = utils.getLogger('debug', self.__class__.__name__ + utils.randstr())
		self.props['args']       = self.config['args']
		self.props['indir']      = ''
		self.props['outdir']     = ''
		self.props['aggr']       = self.config['aggr']
		self.props['callback']   = self.config['callback']
		self.props['brings']     = self.config['brings']


	def __getattr__ (self, name):
		if not self.props.has_key(name) and not proc.alias.has_key(name) and not name.endswith ('Runner'):
			raise ValueError('Property %s not found in pyppl.proc' % name)
		if proc.alias.has_key(name): name = proc.alias[name]
		return self.props[name]

	def __setattr__ (self, name, value):
		if not self.config.has_key(name) and not proc.alias.has_key(name) and not name.endswith ('Runner'):
			raise ValueError('Cannot set property "%s" for <proc>' % name)
		if proc.alias.has_key(name): name = proc.alias[name]
		
		self.config[name] = value
		self.props [name] = value
		self.sets.append(name)
		
		if name == 'depends':
			depends               = value
			self.props['depends'] = []
			if not isinstance (value, list): depends = [value]
			for depend in depends:
				if isinstance (depend, proc):					
					self.props['depends'].append (depend)
					depend.nexts.append (self)
				elif isinstance (depend, aggr):
					for p in depend.ends:
						self.props['depends'].append (p)
						p.nexts.append (self)
	
	def setLogger (self, logger):
		"""
		Set the pipeline logger to the process
		@params:
			`logger`: The logger
		"""
		self.props['logger'] = logger
		
	def log (self, msg, level="info", flag=None):
		"""
		The log function with aggregation name, process id and tag integrated.
		@params:
			`msg`:   The message to log
			`levle`: The log level
			`flag`:  The flag
		"""
		if flag is None: flag = level
		flag = flag.upper().rjust(7)
		flag  = "[%s]" % flag
		title = "%s%s.%s:" % (("%s -> " % self.aggr if self.aggr else ""), self.id, self.tag)
		func  = getattr(self.logger, level)
		func ("%s %s %s" % (flag, title, msg))

	def copy (self, tag=None, newid=None):
		"""
		Copy a process
		@params:
			`tag`:   The tag of the new process, default: `None` (used the old one)
			`newid`: Set the id if you don't want to use the variable name
		@returns:
			The new process
		"""
		newproc = pycopy.copy (self)
		if tag is not None:	newproc.tag = tag
		pid                       = utils.varname('\w+\.' + self.copy.__name__, 3)
		newproc.props['id']       = pid if newid is None else newid
		newproc.props['workdir']  = '' # force the newproc to calcuate a new workdir
		return newproc

	def _suffix (self):
		"""
		Calcuate a uid for the process according to the configuration
		@returns:
			The uid
		"""
		config        = { key:val for key, val in self.config.iteritems() if key not in ['workdir'] }
		config['id']  = self.id
		config['tag'] = self.tag
		
		if config.has_key ('callback'):
			config['callback'] = utils.funcSig(config['callback'])
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
				config['input'][key] = utils.funcSig(val) if callable(val) else val
			
		signature = pickle.dumps(str(config))
		return utils.uid(signature)

	def _tidyBeforeRun (self):
		"""
		Do some preparation before running jobs
		"""
		self._buildProps ()
		self._buildInput ()
		self._buildBrings ()
		self._buildOutput ()
		self._buildScript ()

	def _tidyAfterRun (self):
		"""
		Do some cleaning after running jobs
		"""
		sucJids = self._checkStatus ()
		if sucJids == False: return
		self.log ('Successful jobs: %s' % (sucJids if len(sucJids) < len(self.ncjobids) else 'ALL'), 'debug')
		#self._doCache (sucJids) # cached in check status
		if len (sucJids) < len(self.ncjobids):
			self.log ('Callback will not be called until all non-cached jobs run successfully.', 'warning')
		else:
			if callable (self.callback):
				self.log('Calling callback ...', 'debug')
				self.callback (self)

	def run (self, config = {}):
		"""
		Run the jobs with a configuration
		@params:
			`config`: The configuration
		"""
		self.logger.info ('[  START] ' + utils.padBoth(' ' + ("%s -> " % self.aggr if self.aggr else "") + self.id + '.' + self.tag + ' ', 80, '-'))
		timer = time()
		self._readConfig (config)
		self._tidyBeforeRun ()
		if self._runCmd('beforeCmd') != 0:
			raise Exception ('Failed to run beforeCmd: %s' % self.beforeCmd)
		if not self._isCached():
			# I am not cached, touch the input of my nexts
			# but my nexts are not initized, how?
			# set cached to False, then my nexts will access it
			self.props['cached'] = False
			self.log (self.workdir, 'info', 'RUNNING')
			self._runJobs()
		if self._runCmd('afterCmd') != 0:
			raise Exception ('Failed to run afterCmd: %s' % self.afterCmd)
		self._tidyAfterRun ()
		self.log ('Done (time: %s).' % utils.formatTime(time() - timer), 'info')

	def _checkStatus (self):
		"""
		Check the status of each job
		@returns
			False if jobs are completely failed
			Otherwise return the successful job indices.
		"""
		cachefile  = os.path.join (self.workdir, self.cachefile)
		ret        = []
		failedjobs = []
		failedrcs  = []

		if self.exportdir and not os.path.exists(self.exportdir):
			os.makedirs (self.exportdir)
			
		for i in self.ncjobids:
			job   = self.jobs[i]
			#st    = job.status(self.retcodes)
			rc    = job.rc()
			if rc in self.retcodes:
				job.cache(cachefile)
				job.export (self.exportdir, self.exporthow, self.exportow)
				ret.append (i)
			else:
				failedjobs.append (job)
				failedrcs.append  (rc)
				
		def rc2msg (rc):
			msg = "Program error."
			if rc == -9999:	msg = "No rcfile generated."
			elif rc == -1:	msg = "Failed to submit the jobs."
			elif rc < 0:	msg = "Output files not generated."
			return msg
		
		if self.errorhow == 'ignore' and failedjobs:
			for i, fjob in enumerate(failedjobs):
				self.log ("Job #%s failed but ignored with return code: %s (%s)" % (fjob.index, failedrcs[i], rc2msg(failedrcs[i])) , "warning")
			return ret + [j.index for j in failedjobs]
		
		if not failedjobs: return ret  # all jobs successfully finished
		# just inform the first failed job
		failedjob = failedjobs[0]
		failedrc  = failedrcs [0]
			
		self.log('Job #%s: return code %s expected, but get %s: %s' % (failedjob.index, self.retcodes, failedrc, rc2msg(failedrc)), 'error')
		
		if not self.echo:
			self.log('Job #%s: check STDERR below:' % (failedjob.index), 'error')
			errmsgs = []
			if os.path.exists (failedjob.errfile):
				errmsgs = ['[  ERROR] ' + line.rstrip() for line in open(failedjob.errfile)]					
			if not errmsgs: errmsgs = ['[ STDERR] <EMPTY STDERR>']
			for errmsg in errmsgs: self.logger.error(errmsg)
		
		sys.exit (1) # Don't goto next proc
	
	
	def _prepInfile (self, infile, key, index, warnings, multi=False):
		"""
		Prepare input file, create link to it and set other placeholders
		@params:
			`infile`:    The input files
			`key`:       The base placeholder
			`index`:     The index of the job
			`warnings`:  The warnings during the process
			`multi`:     Whether it's a list of files or not
		"""
		if not self.input.has_key(key): self.input[key] = [''] * self.length
		if not self.input.has_key(key + '.bn'):  self.input[key + '.bn']  = [''] * self.length
		if not self.input.has_key(key + '.fn'):  self.input[key + '.fn']  = [''] * self.length
		if not self.input.has_key(key + '.ext'): self.input[key + '.ext'] = [''] * self.length
		
		job     = self.jobs[index]
		srcfile = os.path.abspath(infile)
		bn      = os.path.basename(srcfile)
		infile  = os.path.join (self.indir, bn)
		fn, ext = os.path.splitext (os.path.basename(infile))
		if not os.path.exists (infile):
			# make sure it's not a link to non-exist file
			if os.path.islink(infile): os.remove (infile)
			os.symlink (srcfile, infile)
		elif not utils.isSameFile (srcfile, infile):
			os.remove (infile)
			os.symlink (srcfile, infile)
			warnings.append (infile)
		
		if multi:
			if not isinstance(self.input[key][index], list):
				self.input[key][index]          = [infile]
				self.input[key + '.bn'][index]  = [bn]
				self.input[key + '.fn'][index]  = [fn]
				self.input[key + '.ext'][index] = [ext]
			else:
				self.input[key][index].append(infile)
				self.input[key + '.bn'][index].append(bn)
				self.input[key + '.fn'][index].append(fn)
				self.input[key + '.ext'][index].append(ext)
			job.input['files'].append(infile)
		else:
			self.input[key][index]          = infile
			self.input[key + '.bn'][index]  = bn
			self.input[key + '.fn'][index]  = fn
			self.input[key + '.ext'][index] = ext
			job.input['file'].append(infile)
				
	def _buildProps (self):
		"""
		Compute some properties
		"""
		#print getsource(self.input.values()[0])
		if isinstance (self.retcodes, int):
			self.props['retcodes'] = [self.retcodes]
		
		if isinstance (self.retcodes, str):
			self.props['retcodes'] = [int(i) for i in utils.split(self.retcodes, ',')]

		key = self.id + '.' + self.tag
		if key in proc.ids and proc.ids[key] != self:
			raise Exception ('A proc with id %s and tag %s already exists.' % (self.id, self.tag))
		proc.ids[key] = self

		if not 'workdir' in self.sets and not self.workdir:
			self.props['workdir'] = os.path.join(self.tmpdir, "PyPPL.%s.%s.%s" % (self.id, self.tag, self._suffix()))

		self.props['indir']   = os.path.join(self.workdir, 'input')
		self.props['outdir']  = os.path.join(self.workdir, 'output')
		
		if not os.path.exists (self.workdir): os.makedirs (self.workdir)
		if not os.path.exists (self.indir):   os.makedirs (self.indir)
		if not os.path.exists (self.outdir):  os.makedirs (self.outdir)
		if not os.path.exists (os.path.join(self.workdir, 'scripts')):
			os.makedirs (os.path.join(self.workdir, 'scripts'))
		
		self.props['jobs'] = [] # in case the proc is reused, maybe other properties to reset ?
		
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

		input    = self.config['input']

		argvchan = channel.fromArgv()
		depdchan = channel.fromChannels (*[d.channel for d in self.depends])
		
		if not isinstance (input, dict):
			input = ','.join(utils.alwaysList (input))			
			input = {input: depdchan if self.depends else argvchan}
		# expand to one key-channel pairs
		inputs = {}
		for keys, vals in input.iteritems():
			keys   = utils.split(keys, ',')
			if callable (vals):
				vals  = vals (depdchan if self.depends else argv)
				vals  = vals.split()
			elif isinstance (vals, (str, unicode)): # only for files: "/a/b/*.txt, /a/c/*.txt"
				vals  = utils.split(vals, ',')
			elif isinstance (vals, channel):
				vals  = vals.split()
			elif isinstance (vals, list):
				vals  = channel.create(vals)
				vals  = vals.split()
			else:
				raise ValueError ("%s%s.%s: Unexpected values for input. Expect dict, list, str, channel, callable." % (
					("%s -> " % self.aggr if self.aggr else ""),
					 self.id, self.tag))
			width = len (vals)
			if len (keys) > width:
				raise ValueError ('%s%s.%s: Not enough data for input variables.\nVarialbes: %s\nData: %s' % (
					("%s -> " % self.aggr if self.aggr else ""),
					 self.id, self.tag,
					 keys, vals))
			for i, key in enumerate(keys):
				toExpand = (key.endswith(':files') or key.endswith(':paths')) and isinstance(vals[i], (str, unicode))
				chan = channel.fromPath(vals[i]) if toExpand else vals[i]
				if self.length == 0: self.props['length'] = chan.length()
				if self.length != chan.length():
					raise ValueError ('%s%s.%s: Expect same lengths for input channels, but got %s and %s (keys: %s).' % (
					("%s -> " % self.aggr if self.aggr else ""),
					 self.id, self.tag,
					self.length, chan.length(), key))
				inputs[key] = chan
			
		self.input = {'#': []}
		for i in range (self.length):
			self.jobs.append (pjob (i, self.workdir, self.log))
			self.input['#'].append(i)
			self.ncjobids.append (i)
			
		warnings = []
		for keyinfo, chan in inputs.iteritems():
			if keyinfo.endswith (':files') or keyinfo.endswith (':paths'):
				key = keyinfo[:-6]				
				# [([f1,f2],), ([f3,f4],)] => [[f1,f2], [f3,f4]]
				for i, ch in enumerate(chan.toList()):
					for infile in ch: self._prepInfile (infile, key, i, warnings, True)
				
			elif keyinfo.endswith (':file') or keyinfo.endswith (':path'):
				key = keyinfo[:-5]
				for i, ch in enumerate(chan.toList()):
					self._prepInfile (ch, key, i, warnings, False)
			else: # var
				if not keyinfo.endswith(':var'): keyinfo = keyinfo + ':var'
				key = keyinfo[:-4]
				self.input[key] = []
				for i, ch in enumerate(chan.toList()):
					job = self.jobs[i]
					job.input['var'].append (ch)
					self.input[key].append (ch)
		if warnings:
			warn = warnings.pop(0)
			self.log ("Overwriting existing input file: %s" % warn, 'debug', 'warning')
			if warnings:
				self.log ("... and %s others" % len(warnings), 'debug', 'warning')

		# also add proc.props, mostly scalar values
		alias = {val:key for key, val in proc.alias.iteritems()}
		for prop, val in self.props.iteritems():
			if not prop in ['id', 'tag', 'tmpdir', 'forks', 'cache', 'workdir', 'echo', 'runner', 'errorhow', 'errorntry', 'defaultSh', 'exportdir', 'exporthow', 'exportow', 'args', 'indir', 'outdir', 'length']: continue
			if prop == 'args':
				for k, v in val.iteritems():
					self.props['procvars']['proc.args.' + k] = v
					self.log('PROC_ARGS: %s => %s' % (k, v), 'debug')
			else:
				if alias.has_key (prop): prop = alias[prop]
				else: self.log ('PROC_VARS: %s => %s' % (prop, val), 'debug')
				self.props['procvars']['proc.' + prop] = val
	
	def _buildBrings (self):
		"""
		Build the brings to bring some files to indir
		The brings can be set as: `p.brings = {"infile": "{{infile.bn}}*.bai"}`
		If you have multiple files to bring in:
		`p.brings = {"infile": "{{infile.bn}}*.bai", "infile#": "{{infile.bn}}*.fai"}`
		You can use wildcards to search the files, but only the first file will return
		To access the brings in your script: `{{ infile.bring }}`, `{{ infile#.bring }}`
		If original input file is a link, will try to find it along each directory the link is in.
		"""
		warnings = []
		for key, val in self.config['brings'].iteritems():
			brkey   = key + ".bring"
			self.input [brkey] = [""] * self.length
			for i in self.input['#']:
				data = {key:val[i] for key, val in self.input.iteritems()}
				data.update (self.procvars)
				
				pattern = utils.format (val, data)
				inkey   = key.replace("#", "")
				infile  = self.input[inkey][i]
				while os.path.exists(infile):
					bring = glob (os.path.join (os.path.dirname(infile), pattern))
					if bring:
						dstfile = os.path.join (self.indir, os.path.basename(bring[0]))
						self.input[brkey][i] = dstfile
						if os.path.exists(dstfile) and not utils.isSameFile (dstfile, bring[0]):
							warnings.append (dstfile)
							os.remove (dstfile)
							os.symlink (bring[0], dstfile)
						elif not os.path.exists(dstfile):
							if os.path.islink (dstfile): os.remove (dstfile)
							os.symlink (bring[0], dstfile)
						break
					if not os.path.islink (infile): break
					infile = os.readlink(infile)
					
		if warnings:
			warn = warnings.pop(0)
			self.log ("Overwriting existing bring file: %s" % warn, 'debug', 'warning')
			if warnings:
				self.log ("... and %s others" % len(warnings), 'debug', 'warning')		

		ridx = randint(0, self.length-1)
		for key, val in self.input.iteritems():
			self.log ('INPUT [%s/%s]: %s => %s' % (ridx, self.length-1, key, val[ridx]), 'debug')
				
	def _buildOutput (self):
		"""
		Build the output data.
		Output could be:
		1. list: ['output:var:{{input}}', 'outfile:file:{{infile.bn}}.txt']
		   or you can ignore the name if you don't put it in script:
				 ['var:{{input}}', 'path:{{infile.bn}}.txt']
		   or even (only var type can be ignored):
				 ['{{input}}', 'file:{{infile.bn}}.txt']
		2. str : 'output:var:{{input}}, outfile:file:{{infile.bn}}.txt'
		3. dict: {"output:var:{{input}}": channel1, "outfile:file:{{infile.bn}}.txt": channel2}
		   or    {"output:var:{{input}}, output:file:{{infile.bn}}.txt" : channel3}
		for 1,2 channels will be the property channel for this proc (i.e. p.channel)
		"""
		output = self.config['output']
		
		if not isinstance (output, dict):
			output = ','.join(utils.alwaysList (output))
		else:
			output = ','.join([key + ':' + val for key, val in output.iteritems()])
			
		self.props['output'] = {}
		for key in utils.split(output, ','):
			(oname, otype, oexp) = utils.sanitizeOutKey(key)
			if otype in ['file', 'path', 'dir']: oexp = os.path.join (self.outdir, oexp)
			self.props['output'][oname] = []
			
			for i in self.input['#']:
				data = {key:val[i] for key, val in self.input.iteritems()}
				data.update (self.procvars)
				val  = utils.format(oexp, data)
				if otype == 'dir' and not os.path.exists (val):
					os.makedirs (val)
				self.props['output'][oname].append (val)
				self.props['jobs'][i].output['var' if otype == 'var' else 'file'].append(val)
			self.props['channel'].merge(self.props['output'][oname])
		
		utils.sanitizeOutKey.index = 0
		
		ridx = randint(0, self.length-1)
		for key, val in self.output.iteritems():
			self.log ('OUTPUT [%s/%s]: %s => %s' % (ridx, self.length-1, key, val[ridx]), 'debug')

	def _buildScript (self): # make self.jobs
		"""
		Build the script, interpret the placeholders
		"""
		if not self.script:	self.log ('No script specified', 'warning')
		
		scriptdir = os.path.join (self.workdir, 'scripts')
		script    = self.script.strip()
		
		if script.startswith ('template:'):
			tplfile = script[9:].strip()
			if not os.path.exists (tplfile):
				raise ValueError ('Script template file "%s" does not exist.' % tplfile)
			script = open(tplfile).read().strip()
		
		if not script.startswith ("#!"):
			script = "#!/usr/bin/env " + self.defaultSh + "\n\n" + script
		
		scriptExists = []
		for index in self.input['#']:
			data    = {key:val[index] for key, val in self.input.iteritems()}
			data.update({key:val[index] for key, val in self.output.iteritems()})
			data.update(self.procvars)
			jscript = utils.format (script, data)
		
			scriptfile = os.path.join (scriptdir, 'script.%s' % index)
			if os.path.exists(scriptfile) and open(scriptfile).read() == jscript:
				scriptExists.append (index)
				continue # don't touch it if contest is the same
			open (scriptfile, 'w').write (jscript)
		if scriptExists:
			se = scriptExists.pop(0)
			self.log ("Script files exist and contents are the same, didn't touch them for job #%s" % se, 'debug')
			if scriptExists:
				self.log ("... and %s others" % len(scriptExists), 'debug')

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
		if self.cache == False:
			self.log ('Not cached, because proc.cache = False', 'debug')
			return False
	
		sigCachedJids = []
		exCachedJids  = []
		if self.cache in [True, 'export+']:
			cachefile = os.path.join (self.workdir, self.cachefile)
			jobsigs   = [''] * self.length
			
			if os.path.exists (cachefile): #jobsigs = pickle.load(open(cachefile))
				with open (cachefile) as f:
					for line in f:
						line = line.strip()
						if not line: continue
						jid, sig = line.split("\t")
						jobsigs[int(jid)] = sig
			elif self.cache == True:
				self.log ('Not cached, cache file %s not exists.' % cachefile, 'debug')
				return False
			
			# check my depends
			if self.cache == True:
				for depend in self.depends:
					if depend.cached: continue
					self.log ('Not cached, my dependent %s not cached.' % depend.id + '.' + depend.tag, 'debug')
					return False
			# sigCachedJids = [i for i in self.input['#'] if jobsigs[i] == self.jobs[i].signature(self.log) and jobsigs[i] != False]
			# job.signature() can't be "False" just can be False
			sigCachedJids = [i for i in self.input['#'] if jobsigs[i] == self.jobs[i].signature()]

		if self.cache in ['export', 'export+']:
			warnings      = []
			exCachedJids  = [i for i in self.input['#'] if self.jobs[i].exportCached(self.exportdir, self.exporthow, warnings)]
			nwarn         = len (warnings)
			for warnings in warnings[:3]:
				self.log(warnings, 'warning')
			if nwarn > 3:
				self.log("... and %s others" % (nwarn - 3), 'warning')
			
		elif not isinstance(self.cache, bool):
			raise ValueError ('Cache option expects True/False/"export"/"export+"')
		
		cachedJids = [i for i in sigCachedJids if i not in exCachedJids] + exCachedJids
		
		if not cachedJids:
			self.log ('Not cached, none of the jobs are cached.', 'debug')
			return False
		
		self.props['ncjobids'] = [i for i in self.input['#'] if i not in cachedJids]
		# in case some programs don't overwrite output files
		## This caused problems for jobs running, cuz output files cleared
		## Ask the job itself to clear the output when it tries to run
		# for i in self.ncjobids: self.jobs[i].clearOutput()
		
		self.log ('Truely cached jobs: %s' % (sigCachedJids if len(sigCachedJids) < self.length else 'ALL'), 'debug')
		self.log ('Export cached jobs: %s' % (exCachedJids  if len (exCachedJids) < self.length else 'ALL'), 'debug')
		if len (cachedJids) < self.length:
			self.log ('Partly cached, only run non-cached jobs.', 'info')
			self.log ('Jobs to be running: %s' % self.ncjobids, 'debug')
			return False
		
		self.log ('Skip running jobs.', 'info', 'CACHED')
		return True

	def _runCmd (self, key):
		"""
		Run the `beforeCmd` or `afterCmd`
		@params:
			`key`: "beforeCmd" or "afterCmd"
		@returns:
			The return code of the command
		"""
		if not self.props[key]:	return 0
		data = {key:val for key,val in self.procvars.iteritems()}
		data.update (self.input)
		data.update (self.output)
		cmd = utils.format(self.props[key], data)
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
			while True:
				(ru, i) = q.get()
				sleep (i)
				if not ru.isRunning():
					ru.submit()
				else:
					self.log ("Job #%s is already running, skip submitting." % ru.job.index, 'info')
				ru.wait() # don't check submision
				ru.finish()
				q.task_done()
		
		runner    = proc.runners[self.runner]
		maxsubmit = self.forks
		if hasattr(runner, 'maxsubmit'): maxsubmit = runner.maxsubmit
		interval  = .1
		if hasattr(runner, 'interval'): interval = runner.interval
		
		sq = Queue()
		for i in self.ncjobids:
			rjob = runner (self.jobs[i], self.props)
			tm = int(i/maxsubmit) * interval
			sq.put ((rjob, tm))

		# submit jobs
		
		nojobs2submit = min (self.forks, len(self.jobs))
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
			
		if not proc.runners.has_key(runner_name):
			proc.runners[runner_name] = runner
			
proc.registerRunner (runner_local)
proc.registerRunner (runner_sge)
proc.registerRunner (runner_ssh)



