"""
job module for PyPPL
"""
import json
from os import path, makedirs, utime
from glob import glob
from collections import OrderedDict
from datetime import datetime
from .logger import logger
from .utils import cmd, safefs, string_types
from .utils.box import Box
from .exception import JobInputParseError, JobOutputParseError

class Job(object):
	"""
	PyPPL Job
	"""

	# 0b
	# 1 (0: Job needs running, 1: Job done)
	# 1 (0: Non-killing step, 1: Killing step)
	# 1 (0: Non-building step, 1: Building step) 
	# 1 (0: Non-submitting step, 1: Submitting step)
	# 1 (0: Non-running step, 1: Running step) 
	# 1 (0: Non-ing, 1: -ing)
	# 1 (0: Sucessded, 1: Failed)

	STATUS_INITIATED    = 0b0000000
	STATUS_BUILDING     = 0b0010010
	STATUS_BUILT        = 0b0010001
	STATUS_BUILTFAILED  = 0b1010000
	STATUS_SUBMITTING   = 0b0001011
	STATUS_SUBMITTED    = 0b0001000
	STATUS_SUBMITFAILED = 0b1001001
	STATUS_RUNNING      = 0b0000110
	STATUS_RETRYING     = 0b0000111
	STATUS_DONE         = 0b1000100
	STATUS_DONECACHED   = 0b1000000
	STATUS_DONEFAILED   = 0b0000101
	STATUS_ENDFAILED    = 0b1000101
	STATUS_KILLING      = 0b1100010
	STATUS_KILLED       = 0b1100001

	RC_NOTGENERATE = 99

	def __init__(self, index, config):
		self.index     = index
		self.status    = Job.STATUS_INITIATED
		self.config    = config
		self.dir       = path.abspath(path.join (config['workdir'], str(index + 1)))
		self.indir     = path.join (self.dir, "input")
		self.outdir    = path.join (self.dir, "output")
		self.script    = path.join (self.dir, "job.script")
		self.rcfile    = path.join (self.dir, "job.rc")
		self.outfile   = path.join (self.dir, "job.stdout")
		self.errfile   = path.join (self.dir, "job.stderr")
		self.cachefile = path.join (self.dir, "job.cache")
		self.pidfile   = path.join (self.dir, "job.pid")
		self.logger    = config.get('logger', logger)
		self.ntry      = 0
		self.input     = {}
		# need to pass this to next procs, so have to keep order
		self.output    = OrderedDict()
		self.data      = Box(
			job = Box(
				index   = self.index,
				indir   = self.indir,
				outdir  = self.outdir,
				dir     = self.dir,
				outfile = self.outfile,
				errfile = self.errfile,
				pidfile = self.pidfile
			),
			i = Box(),
			o = Box()
		)
		self.data.update(self.config.get('procvars', {}))
		self.runner = None
		self._rc    = None
		self._pid   = None

	def showError (self, totalfailed):
		"""
		Show the error message if the job failed.
		"""

		msg = []
		if self.rc == Job.RC_NOTGENERATE:
			msg.append('Rcfile not generated')
		if self.rc & 0b100000000:
			msg.append('Outfile not generated')
		if self.rc & 0b1000000000:
			msg.append('Expectation not met')
		msg = ', '.join(msg)
		if self.config['errhow'] == 'ignore':
			self.logger.warning('Failed but ignored (totally {total}). Return code: {rc} {msg}.'.format(
				total = totalfailed,
				rc    = self.rc & 0b0011111111,
				msg   = msg if not msg else '({})'.format(msg)
			), extra = {
				'proc'  : self.config['proc'],
				'jobidx': self.index,
				'joblen': self.config['procsize'],
				'pbar'  : False
			})
			return

		self.logger.error('Failed (totally {total}). Return code: {rc} {msg}.'.format(
			total = totalfailed,
			rc    = self.rc & 0b0011111111,
			msg   = msg if not msg else '({})'.format(msg)
		), extra = {
			'proc'  : self.config['proc'],
			'jobidx': self.index,
			'joblen': self.config['procsize'],
			'pbar'  : False
		})
		
		self.logger.error('Script: {}'.format(self.script), extra = {
			'proc': self.config['proc'], 'jobidx': self.index, 'joblen': self.config['procsize']})
		self.logger.error('Stdout: {}'.format(self.outfile), extra = {
			'proc': self.config['proc'], 'jobidx': self.index, 'joblen': self.config['procsize']})
		self.logger.error('Stderr: {}'.format(self.errfile), extra = {
			'proc': self.config['proc'], 'jobidx': self.index, 'joblen': self.config['procsize']})

		# errors are not echoed, echo them out
		if self.index not in self.config['echo']['jobs'] or 'stderr' not in self.config['echo']['type']:
			self.logger.error('Check STDERR below:', extra = {
				'proc': self.config['proc'], 'jobidx': self.index, 'joblen': self.config['procsize']})
			errmsgs = []
			if path.exists (self.errfile):
				with open(self.errfile) as f:
					errmsgs = [line.rstrip("\n") for line in f]

			if not errmsgs:
				errmsgs = ['<EMPTY STDERR>']

			for errmsg in errmsgs[-20:] if len(errmsgs) > 20 else errmsgs:
				self.logger.info(errmsg, extra = {
					'loglevel': 'stderr',
					'proc'    : self.config['proc'],
					'jobidx'  : self.index,
					'joblen'  : self.config['procsize']
				})

			if len(errmsgs) > 20:
				self.logger.info(' ... top {top} line(s) ignored (see all in "{errfile}").'.format(
					top     = len(errmsgs) - 20,
					errfile = self.errfile
				), extra = {
					'loglevel': 'stderr',
					'proc'    : self.config['proc'],
					'jobidx'  : self.index,
					'joblen'  : self.config['procsize']
				})

	def report (self):
		"""
		Report the job information to logger
		"""
		from . import Proc
		maxlen = 0
		inkeys = [key for key in self.input.keys() if not key.startswith('_')]
		if self.input:
			maxken = max([len(key) for key in inkeys])
			maxlen = max(maxlen, maxken)
		
		if self.output:
			maxken = max([len(key) for key in self.output.keys()])
			maxlen = max(maxlen, maxken)

		for key in sorted(inkeys):
			if key.startswith('_'): continue
			if self.input[key]['type'] in Proc.IN_VARTYPE:
				self._reportItem(key, maxlen, self.input[key]['data'], 'input')
			else:
				self._reportItem(key, maxlen, self.input[key]['data'], 'input')
				#self._reportItem('_' + key, maxlen, self.input[key]['orig'], 'input')
		
		for key in sorted(self.output.keys()):
			self._reportItem(key, maxlen, self.output[key]['data'], 'output')

	def _reportItem(self, key, maxlen, data, loglevel):
		"""
		Report the item on logs
		@params:
			`key`: The key of the item
			`maxlen`: The max length of the key
			`data`: The data of the item
			`loglevel`: The log level
		"""
		logitem = lambda msg: self.logger.info(msg, extra = {
			'loglevel': loglevel,
			'proc'    : self.config['proc'],
			'jobidx'  : self.index,
			'joblen'  : self.config['procsize'],
			'pbar'    : False
		})

		if not isinstance(data, list):
			logitem("{} => {}".format(key.ljust(maxlen), data))
		else:
			ldata = len(data)
			if ldata == 0:
				logitem("{} => [ {} ]".format(key.ljust(maxlen), ''))
			elif ldata == 1:
				logitem("{} => [ {} ]".format(key.ljust(maxlen), data[0]))
			elif ldata == 2:
				logitem("{} => [ {},".format(key.ljust(maxlen), data[0]))
				logitem("{}      {} ]".format(' '.ljust(maxlen), data[1]))
			elif ldata == 3:
				logitem("{} => [ {},".format(key.ljust(maxlen), data[0]))
				logitem("{}      {},".format(' '.ljust(maxlen), data[1]))
				logitem("{}      {} ]".format(' '.ljust(maxlen), data[2]))
			else:
				logitem("{} => [ {},".format(key.ljust(maxlen), data[0]))
				logitem("{}      {},".format(' '.ljust(maxlen), data[1]))
				logitem("{}      ... ({}),".format(' '.ljust(maxlen), len(data) - 3))
				logitem("{}      {} ]".format(' '.ljust(maxlen), data[-1]))

	def build(self):
		"""
		Initiate a job, make directory and prepare input, output and script.
		"""
		try:
			self.status = Job.STATUS_BUILDING
			if not path.exists(self.dir):
				makedirs (self.dir)
			# run may come first before submit
			# preserve the outfile and errfile of previous run
			# issue #30
			safefs.move(self.outfile, self.outfile + '.bak')
			safefs.move(self.errfile, self.errfile + '.bak')
			# did in reset
			#open(self.outfile, 'w').close()
			#open(self.errfile, 'w').close()
			self._prepInput()
			self._prepOutput()
			if self.index == 0:
				self.report()
			self._prepScript()
			# check cache
			if self.isTrulyCached() or self.isExptCached():
				self.status = Job.STATUS_DONECACHED
				self.done()
			else:
				self.runner = self.config['runner'](self)
				self.status = Job.STATUS_BUILT
		except Exception:
			from traceback import format_exc
			with open(self.errfile, 'w') as f:
				f.write(str(format_exc()))
			self.status = Job.STATUS_BUILTFAILED

	def _linkInfile(self, orgfile):
		"""
		Create links for input files
		@params:
			`orgfile`: The original input file
		@returns:
			The link to the original file.
		"""
		basename = safefs.SafeFs.basename (orgfile)
		infile   = path.join (self.indir, basename)
		safefs.link(orgfile, infile, overwrite = False)
		if safefs.SafeFs(infile, orgfile).samefile():
			return infile

		if '.' in basename:
			(fn, ext) = basename.split('.', 1)
			ext       = '.' + ext
		else:
			fn, ext = basename, ''
		# takes long time if we have a long list of files
		existInfiles = glob (path.join(self.indir, fn + '[[]*[]]' + ext))
		if not existInfiles:
			infile = path.join (self.indir, fn + '[1]' + ext)
			safefs.link(orgfile, infile, overwrite = False)
		elif len(existInfiles) < 100:
			num = 0
			for eifile in existInfiles:
				if safefs.SafeFs(eifile, orgfile).samefile():
					num = 0
					return eifile
				n   = int(path.basename(eifile)[len(fn)+1 : -len(ext)-1])
				num = max (num, n)

			if num > 0:
				infile = path.join (self.indir, fn + '[' + str(num+1) + ']' + ext)
				safefs.link(orgfile, infile)
		else: # pragma: no cover
			num = max([
				int(path.basename(eifile)[len(fn)+1 : -len(ext)-1]) 
				for eifile in existInfiles
			])
			infile = path.join (self.indir, fn + '[' + str(num+1) + ']' + ext)
			safefs.link(orgfile, infile)
		return infile

	def _prepInput (self):
		"""
		Prepare input, create link to input files and set other placeholders
		"""
		from . import Proc
		safefs.remove(self.indir)
		makedirs(self.indir)

		for key, val in self.config['input'].items():
			self.input[key] = {}
			intype = val['type']
			# the original input file(s)
			indata = val['data'][self.index]

			if intype in Proc.IN_FILETYPE:
				if not isinstance(indata, string_types):
					raise JobInputParseError(indata, 'Not a string for input type "%s"' % intype)
				if not indata:
					infile  = ''
				else:
					if not path.exists(indata):
						raise JobInputParseError(indata, 'File not exists for input type "%s"' % intype)

					indata   = path.abspath(indata)
					basename = safefs.SafeFs.basename(indata)
					infile   = self._linkInfile(indata)
					if basename != safefs.SafeFs.basename(infile):
						self.logger.warning ("Input file renamed: %s -> %s" % (basename, safefs.SafeFs.basename(infile)), extra = {
							'proc'  : self.config['proc'],
							'joblen': self.config['procsize'],
							'jobidx': self.index,
							'level2': 'INFILE_RENAMING',
							'pbar'  : False
						})

				if self.config['iftype'] == 'origin':
					self.data['i'][key] = indata
				elif self.config['iftype'] == 'indir':
					self.data['i'][key] = infile
				else:
					self.data['i'][key] = path.realpath(indata)

				self.data['i']['IN_' + key] = infile
				self.data['i']['OR_' + key] = indata
				self.data['i']['RL_' + key] = path.realpath(indata)

				self.input[key]['type'] = intype
				self.input[key]['data'] = infile
				self.input[key]['orig'] = indata

			elif intype in Proc.IN_FILESTYPE:
				self.input[key]['type']       = intype
				self.input[key]['orig']       = []
				self.input[key]['data']       = []
				self.data  ['i'][key]         = []
				self.data  ['i']['IN_' + key] = []
				self.data  ['i']['OR_' + key] = []
				self.data  ['i']['RL_' + key] = []

				if not isinstance(indata, list):
					raise JobInputParseError(indata, 'Not a list for input type "%s"' % intype)

				for data in indata:
					if not isinstance(data, string_types):
						raise JobInputParseError(data, 'Not a string for element of input type "%s"' % intype)

					if not data:
						infile  = ''
					else:
						if not path.exists(data):
							raise JobInputParseError(data, 'File not exists for element of input type "%s"' % intype)

						data     = path.abspath(data)
						basename = path.basename(data)
						infile   = self._linkInfile(data)
						if basename != path.basename(infile):
							self.logger.warning('Input file renamed: {} -> {}'.format(basename, path.basename(infile)), extra = {
								'proc'  : self.config['proc'],
								'joblen': self.config['procsize'],
								'jobidx': self.index,
								'level2': 'INFILE_RENAMING',
								'pbar'  : False
							})

					if self.config['iftype'] == 'origin':
						self.data['i'][key].append(data)
					elif self.config['iftype'] == 'indir':
						self.data['i'][key].append(infile)
					else:
						self.data['i'][key].append(path.realpath(data))

					self.data['i']['IN_' + key].append (infile)
					self.data['i']['OR_' + key].append (data)
					self.data['i']['RL_' + key].append (path.realpath(data))

					self.input[key]['orig'].append (data)
					self.input[key]['data'].append (infile)
			else:
				self.input[key]['type'] = intype
				self.input[key]['data'] = indata
				self.data['i'][key]    = indata

	def _prepOutput (self):
		"""
		Build the output data.
		Output could be:
		1. list: `['output:var:{{input}}', 'outfile:file:{{infile.bn}}.txt']`
			or you can ignore the name if you don't put it in script:
				`['var:{{input}}', 'path:{{infile.bn}}.txt']`
			or even (only var type can be ignored):
				`['{{input}}', 'file:{{infile.bn}}.txt']`
		2. str : `'output:var:{{input}}, outfile:file:{{infile.bn}}.txt'`
		3. OrderedDict: `{"output:var:{{input}}": channel1, "outfile:file:{{infile.bn}}.txt": channel2}`
		   or    `{"output:var:{{input}}, output:file:{{infile.bn}}.txt" : channel3}`
		for 1,2 channels will be the property channel for this proc (i.e. p.channel)
		"""
		from . import Proc
		if not path.exists (self.outdir):
			makedirs (self.outdir)

		output = self.config['output']
		# has to be OrderedDict
		assert isinstance(output, dict)
		# allow empty output
		if not output: return
		for key, val in output.items():
			outtype, outtpl = val
			outdata = outtpl.render(self.data)
			self.data['o'][key] = outdata
			self.output[key] = {
				'type': outtype,
				'data': outdata
			}
			if outtype in Proc.OUT_FILETYPE + Proc.OUT_DIRTYPE + Proc.OUT_STDOUTTYPE + Proc.OUT_STDERRTYPE:
				if path.isabs(outdata):
					raise JobOutputParseError(outdata, 'Absolute path not allowed for output file/dir for key %s' % repr(key))
				self.output[key]['data'] = path.join(self.outdir, outdata)
				self.data['o'][key] = path.join(self.outdir, outdata)

	def _prepScript (self):
		"""
		Build the script, interpret the placeholders
		"""
		script = self.config['script'].render(self.data)

		write = True
		if path.isfile (self.script):
			with open(self.script) as f:
				prevscript = f.read()
			if prevscript == script:
				write = False
			else:
				# for debug
				safefs.move(self.script, self.script + '.bak')
				self.logger.debug ("Script file updated: %s" % self.script, extra = {
					'level2': 'SCRIPT_EXISTS',
					'jobidx': self.index,
					'joblen': self.config['procsize']
				})
		
		if write:
			with open (self.script, 'w') as f:
				f.write (script)

	@property
	def rc(self):
		"""
		Get the return code
		Exception not meet
		  |
		0b1100000000
		   |
		   outfile not generated
		"""
		if self._rc is not None:
			return self._rc
		if not path.exists(self.rcfile):
			open(self.rcfile, 'w').close()
			return Job.RC_NOTGENERATE
		with open(self.rcfile, 'r') as f:
			r = f.read().strip()
			if not r: 
				return Job.RC_NOTGENERATE
			return int(r)

	@rc.setter
	def rc(self, val):
		self._rc = val
		with open(self.rcfile, 'w') as f:
			f.write(str(val))
	
	@property
	def pid(self):
		"""
		Get pid of the job
		@return:
			The job id, could be the process id or job id for other platform.
		"""
		if self._pid is not None:
			return self._pid
		if not path.exists(self.pidfile):
			return ''
		with open(self.pidfile, 'r') as f:
			return f.read().strip()
	
	@pid.setter
	def pid(self, val):
		self._pid = str(val)
		with open(self.pidfile, 'w') as f:
			f.write(str(val))

	def isTrulyCached (self):
		"""
		Check whether a job is truly cached (by signature)
		"""
		if not self.config['cache']:
			return False
		from . import Proc
		if not path.exists (self.cachefile):
			self.logger.debug("Not cached as cache file not exists.", extra = {
				'level2': "CACHE_SIGFILE_NOTEXISTS",
				'jobidx': self.index,
				'joblen': self.config['procsize'],
				'pbar'  : False,
				'proc'  : self.config['proc']
			})
			return False

		with open (self.cachefile, 'rb') as f:
			sig = f.read().decode()

		if not sig:
			self.logger.debug("Not cached because previous signature is empty.", extra = {
				'level2': "CACHE_EMPTY_PREVSIG",
				'jobidx': self.index,
				'joblen': self.config['procsize'],
				'pbar'  : False,
				'proc'  : self.config['proc']
			})
			return False

		sigOld = json.loads(sig)
		sigNow = self.signature()
		if not sigNow:
			self.logger.debug("Not cached because current signature is empty.", extra = {
				'level2': "CACHE_EMPTY_CURRSIG",
				'jobidx': self.index,
				'joblen': self.config['procsize'],
				'pbar'  : False,
				'proc'  : self.config['proc']
			})
			return False

		def compareVar(osig, nsig, key, logkey):
			"""Compare var in signature"""
			for k in osig.keys():
				oval = osig[k]
				nval = nsig[k]
				if nval == oval: continue
				#with Job.LOGLOCK:
				self.logger.debug((
					"Not cached because {key} variable({k}) is different:\n" +
					"...... - Previous: {prev}\n" +
					"...... - Current : {curr}"
				).format(key = key, k = k, prev = oval, curr = nval), extra = {
					'level2': logkey,
					'jobidx': self.index,
					'joblen': self.config['procsize'],
					'pbar'  : False,
					'proc'  : self.config['proc']
				})
				return False
			return True

		def compareFile(osig, nsig, key, logkey, timekey = None):
			"""Compare var in file"""
			for k in osig.keys():
				ofile, otime = osig[k]
				nfile, ntime = nsig[k]
				if nfile == ofile and ntime <= otime: continue
				if nfile != ofile:
					#with Job.LOGLOCK:
					self.logger.debug((
						"Not cached because {key} file({k}) is different:\n" +
						"...... - Previous: {prev}\n" + 
						"...... - Current : {curr}"
					).format(key = key, k = k, prev = ofile, curr = nfile), extra = {
						'level2': logkey,
						'jobidx': self.index,
						'joblen': self.config['procsize'],
						'pbar'  : False,
						'proc'  : self.config['proc']
					})
					return False
				if timekey and ntime > otime:
					#with Job.LOGLOCK:
					self.logger.debug((
						"Not cached because {key} file({k}) is newer: {ofile}\n" +
						"...... - Previous: {otime} ({transotime})\n" +
						"...... - Current : {ntime} ({transntime})"
					).format(
						key        = key,
						k          = k,
						ofile      = ofile,
						otime      = otime,
						transotime = datetime.fromtimestamp(otime),
						ntime      = ntime,
						transntime = datetime.fromtimestamp(ntime)
					), extra = {
						'level2': timekey,
						'jobidx': self.index,
						'joblen': self.config['procsize'],
						'pbar'  : False,
						'proc'  : self.config['proc']
					})
					return False
			return True

		def compareFiles(osig, nsig, key, logkey, timekey = True):
			"""Compare var in files"""
			for k in osig.keys():
				oval = sorted(osig[k])
				nval = sorted(nsig[k])
				olen = len(oval)
				nlen = len(nval)
				for i in range(max(olen, nlen)):
					if i >= olen:
						ofile, otime = None, None
					else:
						ofile, otime = oval[i]
					if i >= nlen:
						nfile, ntime = None, None
					else:
						nfile, ntime = nval[i]
					if nfile == ofile and ntime <= otime: continue
					if nfile != ofile:
						#with Job.LOGLOCK:
						self.logger.debug((
							"Not cached because file {i} is different for {key} files({k}):\n" +
							"...... - Previous: {ofile}\n" +
							"...... - Current : {nfile}"
						).format(
							i     = i + 1,
							key   = key,
							k     = k,
							ofile = ofile,
							nfile = nfile
						), extra = {
							'level2': logkey,
							'jobidx': self.index,
							'joblen': self.config['procsize'],
							'pbar'  : False,
							'proc'  : self.config['proc']
						})
						return False
					if timekey and ntime > otime:
						#with Job.LOGLOCK:
						self.logger.debug((
							"Not cached because file {i} is newer for {key} files({k}): {ofile}\n" +
							"...... - Previous: {otime} ({transotime})\n" +
							"...... - Current : {ntime} ({transntime})"
						).format(
							i          = i + 1,
							key        = key,
							k          = k,
							ofile      = ofile,
							otime      = otime,
							transotime = datetime.fromtimestamp(otime),
							ntime      = ntime,
							transntime = datetime.fromtimestamp(ntime)
						), extra = {
							'level2': timekey,
							'jobidx': self.index,
							'joblen': self.config['procsize'],
							'pbar'  : False,
							'proc'  : self.config['proc']
						})
						return False
			return True

		if not compareFile(
			{'script': sigOld['script']},
			{'script': sigNow['script']},
			'script',
			'',
			'CACHE_SCRIPT_NEWER'
		): return False

		if not compareVar(
			sigOld['i'][Proc.IN_VARTYPE[0]],
			sigNow['i'][Proc.IN_VARTYPE[0]],
			'input',
			'CACHE_SIGINVAR_DIFF'
		): return False

		if not compareFile(
			sigOld['i'][Proc.IN_FILETYPE[0]],
			sigNow['i'][Proc.IN_FILETYPE[0]],
			'input',
			'CACHE_SIGINFILE_DIFF',
			'CACHE_SIGINFILE_NEWER'
		): return False

		if not compareFiles(
			sigOld['i'][Proc.IN_FILESTYPE[0]],
			sigNow['i'][Proc.IN_FILESTYPE[0]],
			'input',
			'CACHE_SIGINFILES_DIFF',
			'CACHE_SIGINFILES_NEWER'
		): return False

		if not compareVar(
			sigOld['o'][Proc.OUT_VARTYPE[0]],
			sigNow['o'][Proc.OUT_VARTYPE[0]],
			'output',
			'CACHE_SIGOUTVAR_DIFF'
		): return False

		if not compareFile(
			sigOld['o'][Proc.OUT_FILETYPE[0]],
			sigNow['o'][Proc.OUT_FILETYPE[0]],
			'output',
			'CACHE_SIGOUTFILE_DIFF'
		): return False

		if not compareFile(
			sigOld['o'][Proc.OUT_DIRTYPE[0]],
			sigNow['o'][Proc.OUT_DIRTYPE[0]],
			'output dir',
			'CACHE_SIGOUTDIR_DIFF'
		): return False
		self.rc = 0
		#safefs.move(self.outfile + '.bak', self.outfile)
		#safefs.move(self.errfile + '.bak', self.errfile)
		return True

	def isExptCached (self):
		"""
		Prepare to use export files as cached information
		True if succeed, otherwise False
		"""
		from . import Proc
		if self.config['cache'] != 'export':
			return False
		if self.config['exhow'] in Proc.EX_LINK:
			self.logger.warning("Job is not export-cached using symlink export.", extra = {
				'level2': "EXPORT_CACHE_USING_SYMLINK",
				'jobidx': self.index,
				'joblen': self.config['procsize'],
				'pbar'  : False,
				'proc'  : self.config['proc']
			})
			return False
		if self.config['expart'] and self.config['expart'][0].render(self.data):
			self.logger.warning("Job is not export-cached using partial export.", extra = {
				'level2': "EXPORT_CACHE_USING_EXPARTIAL",
				'jobidx': self.index,
				'joblen': self.config['procsize'],
				'pbar'  : False,
				'proc'  : self.config['proc']
			})
			return False
		if not self.config['exdir']:
			self.logger.debug("Job is not export-cached since export directory is not set.", extra = {
				'level2': "EXPORT_CACHE_EXDIR_NOTSET",
				'jobidx': self.index,
				'joblen': self.config['procsize'],
				'pbar'  : False,
				'proc'  : self.config['proc']
			})
			return False

		for out in self.output.values():
			if out['type'] in Proc.OUT_VARTYPE: continue
			exfile = path.join (self.config['exdir'], path.basename(out['data']))

			if self.config['exhow'] in Proc.EX_GZIP:
				if path.isdir(out['data']) or out['type'] in Proc.OUT_DIRTYPE:
					exfile += '.tgz'
					if not path.exists(exfile):
						self.logger.debug("Job is not export-cached since exported file not exists: %s." % exfile, extra = {
							'level2': "EXPORT_CACHE_EXFILE_NOTEXISTS",
							'jobidx': self.index,
							'joblen': self.config['procsize'],
							'pbar'  : False,
							'proc'  : self.config['proc']
						})
						return False

					if path.exists (out['data']) or path.islink (out['data']):
						self.logger.warning('Overwrite file for export-caching: %s' % out['data'], extra = {
							'level2': "EXPORT_CACHE_OUTFILE_EXISTS",
							'jobidx': self.index,
							'joblen': self.config['procsize'],
							'pbar'  : False,
							'proc'  : self.config['proc']
						})
						safefs.remove(out['data'])

					makedirs(out['data'])
					safefs.ungz (exfile, out['data'])
				else:
					exfile += '.gz'
					if not path.exists (exfile):
						self.logger.debug("Job is not export-cached since exported file not exists: %s." % exfile, extra = {
							'level2': "EXPORT_CACHE_EXFILE_NOTEXISTS",
							'jobidx': self.index,
							'joblen': self.config['procsize'],
							'pbar'  : False,
							'proc'  : self.config['proc']
						})
						return False

					if path.exists (out['data']) or path.islink (out['data']):
						self.logger.warning('Overwrite file for export-caching: %s' % out['data'], extra = {
							'level2': "EXPORT_CACHE_OUTFILE_EXISTS",
							'jobidx': self.index,
							'joblen': self.config['procsize'],
							'pbar'  : False,
							'proc'  : self.config['proc']
						})
						safefs.remove(out['data'])

					safefs.ungz (exfile, out['data'])
			else:
				if not path.exists (exfile):
					self.logger.debug("Job is not export-cached since exported file not exists: %s." % exfile, extra = {
						'level2': "EXPORT_CACHE_EXFILE_NOTEXISTS",
						'jobidx': self.index,
						'joblen': self.config['procsize'],
						'pbar'  : False,
						'proc'  : self.config['proc']
					})
					return False
				if safefs.SafeFs(exfile, out['data']).samefile():
					continue
				if path.exists (out['data']) or path.islink(out['data']):
					self.logger.warning('Overwrite file for export-caching: %s' % out['data'], extra = {
						'level2': "EXPORT_CACHE_OUTFILE_EXISTS",
						'jobidx': self.index,
						'joblen': self.config['procsize'],
						'pbar'  : False,
						'proc'  : self.config['proc']
					})
					safefs.remove(out['data'])

				safefs.link(path.realpath(exfile), out['data'])

		# Make sure no need to calculate next time
		self.cache()
		self.rc = 0
		#safefs.move(self.outfile + '.bak', self.outfile)
		#safefs.move(self.errfile + '.bak', self.errfile)
		return True

	def cache (self):
		"""
		Truly cache the job (by signature)
		"""
		if not self.config['cache']:
			return
		sig  = self.signature()
		if sig:
			with open (self.cachefile, 'w') as f:
				f.write (sig if not sig else json.dumps(sig))

	def reset (self):
		"""
		Clear the intermediate files and output files
		"""
		from . import Proc
		#self.logger.info('Resetting job #%s ...' % self.index, 'debug', 'JOB_RESETTING')
		retry = self.ntry
		retrydir = path.join(self.dir, 'retry.' + str(retry))
		
		if retry:
			safefs.remove(retrydir)
			makedirs(retrydir)
		else:
			for retrydir in glob(path.join(self.dir, 'retry.*')):
				safefs.remove(retrydir)

		for jobfile in [self.rcfile, self.outfile, self.errfile, self.pidfile, self.outdir]:
			if retry:
				safefs.move(jobfile, path.join(retrydir, path.basename(jobfile)))
			else:
				safefs.remove(jobfile)
		open(self.outfile, 'w').close()
		open(self.errfile, 'w').close()
		
		makedirs(self.outdir)
		for out in self.output.values():
			if out['type'] in Proc.OUT_DIRTYPE:
				makedirs(out['data'])
			if out['type'] in Proc.OUT_STDOUTTYPE:
				safefs.SafeFs._link(self.outfile, out['data'])
			if out['type'] in Proc.OUT_STDERRTYPE:
				safefs.SafeFs._link(self.errfile, out['data'])

	def export (self):
		"""
		Export the output files
		"""
		if not self.config['exdir']:
			return

		assert path.exists(self.config['exdir'])
		assert isinstance(self.config['expart'], list)
		
		from . import Proc
		# output files to export
		files2ex = []
		if not self.config['expart'] or (
			len(self.config['expart']) == 1 and not self.config['expart'][0].render(self.data)):
			for out in self.output.values():
				if out['type'] in Proc.OUT_VARTYPE: continue
				files2ex.append (out['data'])
		else:
			for expart in self.config['expart']:
				expart = expart.render(self.data)
				if expart in self.output:
					files2ex.append(self.output[expart]['data'])
				else:
					files2ex.extend(glob(path.join(self.outdir, expart)))
		
		files2ex = set(files2ex)
		for file2ex in files2ex:
			bname  = path.basename (file2ex)
			# exported file
			exfile = path.join (self.config['exdir'], bname)

			if self.config['exhow'] in Proc.EX_GZIP:
				exfile += '.tgz' if path.isdir(file2ex) else '.gz'
				safefs.gz(file2ex, exfile, overwrite = self.config['exow'])
			elif self.config['exhow'] in Proc.EX_COPY:
				safefs.copy(file2ex, exfile, overwrite = self.config['exow'])
			elif self.config['exhow'] in Proc.EX_LINK:
				safefs.link(file2ex, exfile, overwrite = self.config['exow'])
			else: # move
				if path.islink(file2ex):
					safefs.copy(file2ex, exfile, overwrite = self.config['exow'])
				else:
					safefs.moveWithLink(file2ex, exfile, overwrite = self.config['exow'])

			self.logger.info('Exported: {}'.format(exfile), extra = {
				'joblen'  : self.config['procsize'],
				'jobidx'  : self.index,
				'proc'    : self.config['proc'],
				'loglevel': 'EXPORT'
			})

	def succeed(self):
		"""
		Tell if a job succeeds.
		Check whether output files generated, expectation met and return code met.
		@return:
			`True` if succeed else `False`
		"""
		from . import Proc
		utime (self.outdir, None)
		for out in self.output.values():
			if out['type'] in Proc.OUT_VARTYPE: continue
			if not path.exists(out['data']):
				self.rc = self.rc | 0b100000000
				self.logger.debug('Outfile not generated: {}'.format(out['data']), extra = {
					'level2': 'OUTFILE_NOT_EXISTS',
					'jobidx': self.index,
					'joblen': self.config['procsize'],
					'proc'  : self.config['proc']
				})

		expectCmd = self.config['expect'].render(self.data)

		if expectCmd:
			self.logger.debug ('Check expectation: %s' % (expectCmd), extra = {
					'level2': 'EXPECT_CHECKING',
					'jobidx': self.index,
					'joblen': self.config['procsize'],
					'proc'  : self.config['proc']
				})
			#rc = utils.dumbPopen (expectCmd, shell=True).wait()
			c = cmd.run(expectCmd, raiseExc = False, shell = True)
			if c.rc != 0:	
				self.rc = self.rc | 0b1000000000
		return self.rc in self.config['rcs']

	def done (self):
		"""
		Do some cleanup when job finished
		"""
		#if self.succeed():
		self.export()
		self.cache()

	def signature (self):
		"""
		Calculate the signature of the job based on the input/output and the script
		@returns:
			The signature of the job
		"""
		from . import Proc
		ret = {}
		sig = safefs.SafeFs(self.script).filesig()
		if not sig:
			self.logger.debug('Empty signature because of script file: %s.' % (self.script), extra = {
				'level2': 'CACHE_EMPTY_CURRSIG',
				'jobidx': self.index,
				'joblen': self.config['procsize'],
				'proc'  : self.config['proc'],
				'pbar'  : False,
			})
			return ''
		ret['script'] = sig
		ret['i']     = {
			Proc.IN_VARTYPE[0]:   {},
			Proc.IN_FILETYPE[0]:  {},
			Proc.IN_FILESTYPE[0]: {}
		}
		ret['o']    = {
			Proc.OUT_VARTYPE[0]:  {},
			Proc.OUT_FILETYPE[0]: {},
			Proc.OUT_DIRTYPE[0]:  {}
		}

		for key, val in self.input.items():
			if val['type'] in Proc.IN_VARTYPE:
				ret['i'][Proc.IN_VARTYPE[0]][key] = val['data']
			elif val['type'] in Proc.IN_FILETYPE:
				sig = safefs.SafeFs(val['data']).filesig(self.config['dirsig'])
				if not sig:
					self.logger.debug('Empty signature because of input file: %s.' % (val['data']), extra = {
						'level2': 'CACHE_EMPTY_CURRSIG',
						'jobidx': self.index,
						'joblen': self.config['procsize'],
						'proc'  : self.config['proc'],
						'pbar'  : False,
					})
					return ''
				ret['i'][Proc.IN_FILETYPE[0]][key] = sig
			elif val['type'] in Proc.IN_FILESTYPE:
				ret['i'][Proc.IN_FILESTYPE[0]][key] = []
				for infile in sorted(val['data']):
					sig = safefs.SafeFs(infile).filesig(self.config['dirsig'])
					if not sig:
						self.logger.debug('Empty signature because of one of input files: %s.' % (infile), extra = {
							'level2': 'CACHE_EMPTY_CURRSIG',
							'jobidx': self.index,
							'joblen': self.config['procsize'],
							'proc'  : self.config['proc'],
							'pbar'  : False,
						})
						return ''
					ret['i'][Proc.IN_FILESTYPE[0]][key].append (sig)

		for key, val in self.output.items():
			if val['type'] in Proc.OUT_VARTYPE:
				ret['o'][Proc.OUT_VARTYPE[0]][key] = val['data']
			elif val['type'] in Proc.OUT_FILETYPE:
				sig = safefs.SafeFs(val['data']).filesig(self.config['dirsig'])
				if not sig:
					self.logger.debug('Empty signature because of output file: %s.' % (val['data']), extra = {
						'level2': 'CACHE_EMPTY_CURRSIG',
						'jobidx': self.index,
						'joblen': self.config['procsize'],
						'proc'  : self.config['proc'],
						'pbar'  : False,
					})
					return ''
				ret['o'][Proc.OUT_FILETYPE[0]][key] = sig
			elif val['type'] in Proc.OUT_DIRTYPE:
				sig = safefs.SafeFs(val['data']).filesig(self.config['dirsig'])
				if not sig:
					self.logger.debug('Empty signature because of output dir: %s.' % (val['data']), extra = {
						'level2': 'CACHE_EMPTY_CURRSIG',
						'jobidx': self.index,
						'joblen': self.config['procsize'],
						'pbar'  : False,
						'proc'  : self.config['proc']
					})
					return ''
				ret['o'][Proc.OUT_DIRTYPE[0]][key] = sig
		return ret

	def submit(self):
		"""
		Submit the job
		"""
		self.status = Job.STATUS_SUBMITTING
		if self.runner.isRunning():
			self.logger.info('is already running at {pid}, skip submission.'.format(pid = self.pid), extra = {
				'proc'    : self.config['proc'],
				'jobidx'  : self.index,
				'joblen'  : self.config['procsize'],
				'loglevel': 'submit',
				'pbar'    : False,
			})
			self.status = Job.STATUS_RUNNING
		else:
			self.reset()
			rs = self.runner.submit()
			if rs.rc == 0:
				self.status = Job.STATUS_SUBMITTED
			else:
				self.logger.error(
					'Submission failed (rc = {rc}, cmd = {cmd})'.format(rc = rs.rc, cmd = rs.cmd), 
					extra = {
						'level2': 'SUBMISSION_FAIL',
						'jobidx'  : self.index,
						'joblen'  : self.config['procsize'],
						'pbar'    : False,
						'proc'    : self.config['proc']
					}
				)
				self.status = Job.STATUS_SUBMITFAILED

	def run(self):
		"""
		Wait for the job to run
		"""
		self.status = Job.STATUS_RUNNING
		self.runner.run()
		if self.succeed():
			self.status = Job.STATUS_DONE
			self.done()
		elif self.config['errhow'] != 'retry' or self.ntry > self.config['errntry']:
			self.status = Job.STATUS_ENDFAILED
		else:
			self.status = Job.STATUS_DONEFAILED

	def retry(self):
		"""
		If the job is available to retry
		@return:
			`True` if it is else `False`
		"""
		if not self.status & 0b100 or not self.status & 0b1:
			return False
		if self.config['errhow'] == 'halt':
			self.status = Job.STATUS_ENDFAILED
			return 'halt'
		if self.config['errhow'] != 'retry':
			self.status = Job.STATUS_ENDFAILED
			return False
		self.status = Job.STATUS_RETRYING
		self.ntry += 1
		return True

	def kill(self):
		"""
		Kill the job
		"""
		self.status = Job.STATUS_KILLING
		try:
			self.runner.kill()
		except Exception:
			pass
		self.status = Job.STATUS_KILLED
