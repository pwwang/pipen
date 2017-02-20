import logging, os, strtpl, pickle, shlex, shutil, threading, sys
import copy as pycopy
from random import randint
from traceback import extract_stack
from channel import channel
import strtpl
from tempfile import gettempdir
from md5 import md5
from re import split
from subprocess import Popen, PIPE
from Queue import Queue
from collections import OrderedDict
from inspect import getsource
from ..runners import runner_local, runner_sge, runner_ssh

# logging.basicConfig(level=logging.INFO)
# deepcopy does not work if this is ON

class proc (object):

	runners = {}
	ids     = {}

	def __init__ (self, tag = 'notag'):
		# computed props
		self.__dict__['props']    = {}
		# configs
		self.__dict__['config']   = {}

		pid                       = extract_stack()[-2][3]
		if pid is None: pid       = extract_stack()[-4][3]
		pid                       = pid[:pid.find('=')].strip()	

		self.config['input']      = {'input': sys.argv[1:] if len(sys.argv)>1 else []}
		self.config['output']     = {}
		# where cache file and wdir located
		self.config['tmpdir']     = gettempdir()
		self.config['forks']      = 1
		self.config['cache']      = True
		self.config['retcodes']   = [0]
		self.config['echo']       = False
		self.config['runner']     = 'local'
		self.config['script']     = ''
		self.config['depends']    = []
		self.config['tag']        = tag
		self.config['exportdir']  = ''
		self.config['exporthow']  = 'copy' # symlink, move, gzip (TODO)
		self.config['exportow']   = True # overwrite
		self.config['errorhow']   = "terminate" # retry, ignore
		self.config['errorntry']  = 1
		self.config['defaultSh']  = 'bash'
		self.config['beforeCmd']  = ""
		self.config['afterCmd']   = ""
		self.config['workdir']    = ''
		self.config['args']       = {}
		self.config['callback']   = None
		self.config['callfront']  = None
		# init props

		# id of the process, actually it's the variable name of the process
		self.props['id']         =  pid  
		# whether the process is cached or not
		#self.props['cached']     = True
		# the tag
		self.props['tag']        = tag

		# the cachefile, cache file will be in <tmpdir>/<cachefile>
		self.props['cachefile']  = ''
		# which processes this one depents on
		self.props['depends']    = []
		# the script
		self.props['script']     = ""
		# the script prepend to the script
		self.props['preScript']  = ""
		# the script append to the script
		self.props['postScript'] = ""

		self.props['input']      = {}
		self.props['output']     = {}
		self.props['depends']    = self.config['depends']
		self.props['nexts']      = []
		self.props['tmpdir']     = self.config['tmpdir']
		self.props['forks']      = self.config['forks']
		self.props['cache']      = self.config['cache']
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
		self.props['defaultSh']  = self.config['defaultSh']
		self.props['isValid']    = True
		self.props['channel']    = channel()
		self.props['length']     = 0
		self.props['sets']       = []
		self.props['infiletime'] = 0
		self.props['outfiles']   = []
		self.props['infiles']    = []
		self.props['procvars']   = {}
		self.props['workdir']    = ''
		self.props['logger']     = logging.getLogger(__name__)
		self.props['args']       = self.config['args']
		self.props['callback']   = self.config['callback']
		self.props['callfront']  = self.config['callfront']
		self.props['indir']      = ''
		self.props['outdir']     = ''
		self.props['cached']     = False


	def __getattr__ (self, name):
		if not self.props.has_key(name) and not name.endswith ('Runner'):
			raise AttributeError('Property %s not found in <proc>' % name)
		return self.props[name]

	def __setattr__ (self, name, value):
		if not self.config.has_key(name) and not name.endswith ('Runner'):
			raise AttributeError('Cannot set %s for <proc>' % name)
		self.config[name] = value
		self.props [name] = value
		self.props['sets'].append(name)
		if (name == 'output' or name == 'input') and isinstance(value, list) and isinstance(value[0], tuple):
			self.config[name] = OrderedDict(value)
			self.props [name] = OrderedDict(value)

		if name == 'depends':
			if isinstance(self.depends, proc):
				self.props['depends'] = [self.depends]
			for depend in self.props['depends']:
				depend.props['nexts'].append (self)
	
	def setLogger (self, logger):
		self.props['logger'] = logger

	def copy (self, tag=None):
		newproc = pycopy.deepcopy (self)
		if tag is not None:
			newproc.tag = tag
		pid                  = extract_stack()[-2][3]
		if pid is None: pid  = extract_stack()[-4][3]
		pid                  = pid[:pid.find('=')].strip()	
		newproc.props['pid'] = pid
		return newproc

	def _suffix (self):
		config = pycopy.copy(self.config)
		if config.has_key('workdir'):
			del config['workdir']

		if config.has_key('depends'):
			depends = config['depends']
			pickable_depends = []
			if isinstance(depends, proc):
				depends = [depends]
			for depend in depends:
				pickable_depends.append(depend.id + '.' + depend.tag)
			config['depends'] = pickable_depends

		if config.has_key('nexts'):
			nexts = config['nexts']
			pickable_nexts = []
			if isinstance(nexts, proc):
				nexts = [nexts]
			for n in nexts:
				pickable_nexts.append(ndepend.id + '.' + n.tag)
			config['nexts'] = pickable_nexts

		if config.has_key ('callback'):
			if callable (config['callback']):
				try:
					config['callback'] = getsource(config['callback'])
				except:
					config['callback'] = config['callback'].__name__
			else:
				config['callback'] = 'None'
	
		if config.has_key ('callfront'):
			if callable (config['callfront']):
				try:
					config['callfront'] = getsource(config['callfront'])
				except:
					config['callfront'] = config['callfront'].__name__
			else:
				config['callfront'] = 'None'

		signature = pickle.dumps(config) + '@' + pickle.dumps(sorted(sys.argv))
		return md5(signature).hexdigest()[:8]

	def _tidyBeforeRun (self):
		self._buildProps ()
		self.logger.info ('[RUNNING] %s.%s: %s' % (self.id, self.tag, self.workdir))
		self._buildInput ()
		self._buildOutput ()
		self._buildScript ()

	def _tidyAfterRun (self):
		if self._checkStatus ():
			self._export ()
			self._doCache ()
		if callable (self.callback):
			self.callback (self)

	def _init (self, config):
		self._readConfig (config)
		self.props['cached']   = self._isCached()
		if callable (self.callfront):
			self.callfront (self)		
		if self.cached: return False
		self.props['infiles']  = []
		self.props['outfiles'] = []
		self.props['jobs']     = []
		'''
		for n in self.nexts: # if i am not cached, then none of depends
			self.logger.debug ('[  DEBUG] %s.%s: I`m not cached, so my dependent %s have to rerun.' % (self.id, self.tag, n.id))
			n.cache = False
		'''
		self._tidyBeforeRun ()
		return True

	def run (self, config = {}):
		if not self._init(config): 
			self.logger.info ('[ CACHED] %s.%s: %s' % (self.id, self.tag, self.workdir))
			self._tidyAfterRun ()
			return

		if self._runCmd('beforeCmd') != 0:
			raise Exception ('Failed to run <beforeCmd>')
		self._runJobs()
		self._runCmd('afterCmd')
		if self._runCmd('afterCmd') != 0:
			raise Exception ('Failed to run <afterCmd>')
		self._tidyAfterRun ()

	def _checkStatus (self): # whether return values allowed or outfiles generated
		for i in range(self.length):
			rcfile = os.path.join (self.workdir, 'scripts', 'script.%s.rc' % i)
			rc = 0
			with open (rcfile, 'r') as f:
				rc = f.read().strip()
			rc = -1 if rc == '' else int(rc)
			if rc not in self.retcodes:
				if not self.echo:
					errfile = os.path.join (self.workdir, 'scripts', 'script.%s.stderr' % i)
					errmsgs = ['[  ERROR] !  ' + line.strip() for line in open(errfile)]
					if not errmsgs: errmsgs = ['[  ERROR] ! <EMPTY STDERR>']
					self.logger.info ('[  ERROR] %s.%s: See STDERR below.' % (self.id, self.tag))
					for errmsg in errmsgs:
						self.logger.info (errmsg)
				raise Exception ('[#%s]: Return code is %s, but %s expected.' % (i, rc, self.retcodes))

		for of in self.outfiles:
			if not os.path.exists (of):
				raise Exception ('Output file %s not generated.' % (of))
		return True

	def _buildProps (self):
		if isinstance (self.retcodes, int):
			self.props['retcodes'] = [self.retcodes]
		
		if isinstance (self.retcodes, str):
			self.props['retcodes'] = [int(i) for i in split(r'\s*,\s*', self.retcodes)]

		key = self.id + '.' + self.tag
		if key in proc.ids and proc.ids[key] != self:
			raise Exception ('A proc with id %s and tag %s already exists.' % (self.id, self.tag))
		else:
			proc.ids[key] = self

		if not 'workdir' in self.sets and not self.workdir:
			self.props['workdir'] = os.path.join(self.tmpdir, "PyPPL_%s_%s.%s" % (self.id, self.tag, self._suffix()))

		self.props['indir']   = os.path.join(self.workdir, 'input')
		self.props['outdir']  = os.path.join(self.workdir, 'output')
		
		if not os.path.exists (self.workdir):
			os.makedirs (self.workdir)
		if not os.path.exists (self.indir):
			os.makedirs (self.indir)
		if not os.path.exists (self.outdir):
			os.makedirs (self.outdir)
		if not os.path.exists (os.path.join(self.workdir, 'scripts')):
			os.makedirs (os.path.join(self.workdir, 'scripts'))

	"""
	Input could be:
	1. list: ['input', 'infile:file'] <=> ['input:var', 'infile:path']
	2. str : "input, infile:file" <=> input:var, infile:path
	3. dict: {"input": channel1, "infile:file": channel2}
	   or    {"input:var, input:file" : channel3}
	for 1,2 channels will be the combined channel from dependents, if there is not dependents, it will be sys.argv[1:]
	"""
	def _buildInput (self):
		# if config.input is list, build channel from depends
		# else read from config.input
		input0 = self.config['input']
		if isinstance(input0, list):
			input0 = ', '.join(input0)
		if isinstance(input0, str):
			cs = channel.fromChannels(*[d.channel for d in self.depends]) if self.depends else channel.fromArgv(None)
			input0 = {input0: cs}
		
		if not isinstance(input0, dict):
			raise Exception('Expect <list>, <str> or <dict> as input.')

		self.props['input'] = {}
		for key, val in input0.iteritems():
			if not isinstance (val, channel):
				val = channel.create(val)

			keys = split(r'\s*,\s*', key)
			if self.length == 0:
				self.props['length'] = val.length()
			elif self.length != val.length():
				raise Exception ('Expection same lengths for input channels')
			vals = val.split()
			if len(keys) > len(vals):
				raise Exception('Not enough data for input variables.\nVarialbes: %s\nData: %s' % (keys, vals))

			for i, k in enumerate(keys):
				vv = vals[i].toList()
				if k.endswith (':file') or k.endswith(':path'):
					k = k[:-5]
					for j, v in enumerate(vv):
						#(v, ) = v
						if not os.path.exists (v):
							raise Exception('Input file %s does not exist.' % v)
						v = os.path.realpath(v)
						vv[j] = os.path.join(self.indir, os.path.basename(v))
						if v not in self.infiles: # doesn't need to do repeatedly
							self.props['infiles'].append (v)
							self.props['infiletime'] = max (self.infiletime, os.path.getmtime(v))
							
							if os.path.islink(vv[j]):
								self.logger.info ('[WARNING] %s.%s: Overwriting existing input file (link) %s' % (self.id, self.tag, vv[j]))
								os.remove (vv[j])
							if os.path.exists (vv[j]):
								self.logger.info ('[WARNING] %s.%s: Overwriting existing file/dir %s' % (self.id, self.tag, vv[j]))
								if os.path.isfile(vv[j]):
									os.remove (vv[j])
								else:
									shutil.rmtree(vv[j])
							os.symlink (v, vv[j])
					self.props['input'][k] = vv
					self.props['input'][k + '.bn']  = map (lambda x: os.path.basename(x), vv)
					self.props['input'][k + '.fn']  = map (lambda x: os.path.basename(os.path.splitext(x)[0]), vv)
					self.props['input'][k + '.ext'] = map (lambda x: os.path.splitext(x)[1], vv)
					
				else:
					if k.endswith(":var"): k = k[:-4]
					self.props['input'][k] = vv

		ridx = randint(0, self.length-1)
		for key, val in self.input.iteritems():
			self.logger.debug ('[  DEBUG] %s.%s INPUT [%s/%s]: %s => %s' % (self.id, self.tag, ridx, self.length-1, key, val[ridx]))

		# also add proc.props, mostly scalar values
		for prop, val in self.props.iteritems():
			if not prop in ['id', 'tag', 'tmpdir', 'forks', 'cache', 'workdir', 'echo', 'runner', 'errorhow', 'errorntry', 'defaultSh', 'exportdir', 'exporthow', 'exportow', 'args', 'indir', 'outdir']: continue
			if prop == 'args':
				for k, v in val.iteritems():
					self.props['procvars']['proc.args.' + k] = v
					self.logger.debug ('[  DEBUG] %s.%s PROC_ARGS: %s => %s' % (self.id, self.tag, k, v))
			else:
				self.props['procvars']['proc.' + prop] = val
				self.logger.debug ('[  DEBUG] %s.%s PROC_VARS: %s => %s' % (self.id, self.tag, prop, val))

	"""
	Output could be:
	1. list: ['output:var:{input}', 'outfile:file:{infile.bn}.txt']
	   or you can ignore the name if you don't put it in script:
	         ['var:{input}', 'path:{infile.bn}.txt']
	   or even (only var type can be ignored):
	         ['{input}', 'file:{infile.bn}.txt']
	2. str : 'output:var:{input}, outfile:file:{infile.bn}.txt'
	3. dict: {"output:var:{input}": channel1, "outfile:file:{infile.bn}.txt": channel2}
	   or    {"output:var:{input}, output:file:{infile.bn}.txt" : channel3}
	for 1,2 channels will be the property channel for this proc (i.e. p.channel)
	"""
	def _buildOutput (self):

		output = self.config['output']

		if isinstance(output, list):
			output = ', '.join(output)
		if isinstance(output, str):
			output = {output: self.props['channel']}

		if not isinstance(output, dict):
			raise Exception('Expect <list>, <str> or <dict> as output.')
		
		def sanitizeKey (key):
			its = [it.strip() for it in strtpl.split(key, ':')]
			
			if len(its) == 1:
				its = ['__out%s__' % sanitizeKey.out_idx, 'var', its[0]]
				sanitizeKey.out_idx += 1
			elif len(its) == 2:
				if its[0] in ['var', 'file', 'path']:
					its = ['__out%s__' % sanitizeKey.out_idx, its[0], its[1]]
					sanitizeKey.out_idx += 1
				else:
					its = [its[0], 'var', its[1]]
			elif its[1] not in ['var', 'file', 'path']:
				raise Exception ('Expect type: var, file or path instead of %s' % items[1])
			return tuple (its)
		sanitizeKey.out_idx = 1

		self.props['output'] = {}
		for key, val in output.iteritems():
			keys    = strtpl.split(key, ',')
			
			for k in keys:
				(oname, otype, oexp) = sanitizeKey(k)
				if self.input.has_key(oname):
					raise Exception ('Ouput variable name %s is already taken by input' % oname)

				if otype in ['file', 'path']:
					oexp = os.path.join (self.outdir, oexp)
				# build channels
				chv = []
				for i in range(self.length):
					data = {}
					for ink, inv in self.input.iteritems():
						data[ink] = inv[i]
					data.update (self.procvars)
					chv.append (strtpl.format (oexp, data))
				if otype in ['file', 'path']:
					self.props['outfiles'] += chv
				chv = channel.create (chv)
				val.merge(chv)
				if val != self.channel:
					self.props['channel'].merge (chv)
				self.props['output'][oname] = chv.toList()
		
		ridx = randint(0, self.length-1)
		for key, val in self.output.iteritems():
			self.logger.debug ('[  DEBUG] %s.%s OUTPUT [%s/%s]: %s => %s' % (self.id, self.tag, ridx, self.length-1, key, val[ridx]))

	def _buildScript (self): # make self.jobs
		if not self.script:
			raise Exception ('Please specify script to run')
		
		scriptdir = os.path.join (self.workdir, 'scripts')
		
		script = self.script.strip()
		if script.startswith ('template:'):
			tplfile = script[9:].strip()
			if not os.path.exists (tplfile):
				raise Exception ('Script template file %s does not exist.' % tplfile)
			with open (tplfile, 'r') as f:
				script = f.read().strip()
		
		if not script.startswith ("#!"):
			script = "#!/usr/bin/env " + self.defaultSh + "\n\n" + script

		
		for i in range(self.length):
			data = {'#': i}
			d   = {}
			for k,v in self.input.iteritems():
				d[k] = v[i]
			for k,v in self.output.iteritems():
				d[k] = v[i]
			data.update(d)
			data.update(self.procvars)
			script1 = strtpl.format (script, data)
		
			scriptfile = os.path.join (scriptdir, 'script.%s' % i)
			with open(scriptfile, 'w') as f:
				f.write (script1)

			self.jobs.append (scriptfile)
	
	def _export (self):
		if not self.exportdir: return
		if not os.path.exists(self.exportdir):
			os.makedirs (self.exportdir)
		
		for outfile in self.outfiles:
			bn = os.path.basename (outfile)
			target = os.path.join (self.exportdir, bn)

			if os.path.exists (target):
				if self.exportow == True:
					if os.path.isdir (target):
						shutil.rmtree (target)
					else:
						os.remove (target)
				else:
					self.logger.info ('[ EXPORT] %s.%s: %s (target exists, skipped)' % (self.id, self.tag, target))
			
			if not os.path.exists (target):
				self.logger.info ('[ EXPORT] %s.%s: %s (%s)' % (self.id, self.tag, target, self.exporthow))
				if self.exporthow == 'copy':
					if os.path.isdir (outfile):
						shutil.copytree (outfile, target)
					else:
						shutil.copyfile (outfile, target)
				elif self.exporthow == 'move':
					shutil.move (outfile, target)
					os.symlink(target, outfile) # make sure dependent proc can run
				elif self.exporthow == 'symlink':
					os.symlink (outfile, target)

	def _readConfig (self, config):
		conf = pycopy.copy (config)
		for s in self.sets:
			if conf.has_key(s): del conf[s]
		self.config.update (conf)

		for key, val in conf.iteritems():
			self.props[key] = val

		self.props['cachefile'] = "PyPPL.%s.%s.%s.cache" % (
			self.id,
			self.tag,
			self._suffix()
		)

	def _doCache (self):
		cachefile = os.path.join (self.tmpdir, self.cachefile)
		with open (cachefile, 'w') as f:
			props = pycopy.copy(self.props)
			if props.has_key('logger'):
				del props['logger']
			if props.has_key('depends'):
				del props['depends']
			if props.has_key('nexts'):
				del props['nexts']
			if props.has_key ('callback'):
				del props['callback']
			if props.has_key ('callfront'):
				del props['callfront']
			pickle.dump(props, f)
	
	def _isCached (self):
		if not self.cache:	
			self.logger.debug ('[  DEBUG] %s.%s: Not cached, because proc.cache = False.' % (self.id, self.tag))
			return False

		cachefile = os.path.join (self.tmpdir, self.cachefile)
		if not os.path.exists(cachefile): 
			self.logger.debug ('[  DEBUG] %s.%s: Not cached, cache file %s not exists.' % (self.id, self.tag, cachefile))
			return False
		
		with open(cachefile, 'r') as f:
			props = pickle.load(f)
		self.props.update(props)
		
		# check input files, outputfiles
		for infile in self.infiles:
			if not os.path.exists(infile):	
				self.logger.debug ('[  DEBUG] %s.%s: Not cached, input file %s not exists.' % (self.id, self.tag, infile))
				return False
			if os.path.getmtime(infile) > self.infiletime and self.infiletime != 0:
				self.logger.debug ('[  DEBUG] %s.%s: Not cached, input file %s is newer.' % (self.id, self.tag, infile))
				return False
			inlink =  os.path.join(self.indir, os.path.basename (infile))
			if not os.path.islink (inlink):
				self.logger.debug ('[  DEBUG] %s.%s: Not cached, input file link %s not exists.' % (self.id, self.tag, inlink))
				return False
		
		for outfile in self.outfiles:
			if not os.path.exists(outfile):
				self.logger.debug ('[  DEBUG] %s.%s: Not cached, output file %s not exists' % (self.id, self.tag, outfile))
				return False
		
		for d in self.depends:
			if not d.cached:
				self.logger.debug ('[  DEBUG] %s.%s: Not cached, because my dependent %s is not cached.' % (self.id, self.tag, d.id))
				return False

		return True

	def _runCmd (self, key):
		if not self.props[key]:
			return 0
		p = Popen (shlex.split(strtpl.format(self.props[key], self.procvars)), stdin=PIPE, stderr=PIPE, stdout=PIPE)
		if self.echo:
			for line in iter(p.stdout.readline, ''):
				sys.stdout.write (line)
		for line in iter(p.stderr.readline, ''):
			sys.stderr.write (line)
		return p.wait()

	def _runJobs (self):
		def worker (q):
			while True:
				q.get().run()
				q.task_done()
		
		q = Queue()
		for i in range (self.forks):
			t = threading.Thread(target = worker, args = (q, ))
			t.daemon = True
			t.start ()
		
		for job in self.jobs:
			q.put (proc.runners[self.runner] (job, self.props))
		q.join()

	@staticmethod
	def registerRunner (runner):
		runner_name = runner.__name__
		if runner_name.startswith ('runner_'):
			runner_name = runner_name[7:]
			
		if not proc.runners.has_key(runner_name):
			proc.runners[runner_name] = runner
			
proc.registerRunner (runner_local)
proc.registerRunner (runner_sge)
proc.registerRunner (runner_ssh)



