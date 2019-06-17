"""job module for PyPPL"""
import re
from os import path, utime
from pathlib import Path
from datetime import datetime
import cmdy
from .utils import Box, OBox, chmodX, briefPath, filesig, fileflush, fs
from .logger import logger as _logger
from .exceptions import JobInputParseError, RunnerClassNameError, JobOutputParseError

# File names
DIR_INPUT       = 'input'
DIR_OUTPUT      = 'output'
DIR_CACHE       = '.jobcache' # under output
FILE_SCRIPT     = 'job.script'
FILE_RC         = 'job.rc'
FILE_STDOUT     = 'job.stdout'
FILE_STDERR     = 'job.stderr'
FILE_STDOUT_BAK = 'job.stdout.bak'
FILE_STDERR_BAK = 'job.stderr.bak'
FILE_CACHE      = 'job.cache'
FILE_PID        = 'job.pid'

RC_NO_RCFILE           = 511 # bit 8: 1, bit 9: 0
RC_ERROR_SUBMISSION    = 510

RCBIT_NO_OUTFILE       = 9
RCBIT_UNMET_EXPECT     = 10

RCMSG_NO_OUTFILE       = 'Outfile not generated'
RCMSG_ERROR_SUBMISSION = 'Submission failed'
RCMSG_UNMET_EXPECT     = 'Expectation not met'
RCMSG_NO_RCFILE        = 'Rcfile not generated'

class Job(object):
	"""Describes a job, also as a base class for runner"""

	def __init__(self, index, proc):
		"""
		Initiate a job
		@params:
			`index`:  The index of the job.
			`config`: The configurations of the job.
		"""
		self._checkClassName()
		self.index     = index
		self.proc      = proc

		self.dir       = (Path(self.proc.workdir) / str(index+1)).resolve()
		# self.indir     = path.join(self.dir, "input")
		# self.outdir    = path.join(self.dir, "output")
		# self.script    = path.join(self.dir, "job.script")
		# self.rcfile    = path.join(self.dir, "job.rc")
		# self.outfile   = path.join(self.dir, "job.stdout")
		# self.errfile   = path.join(self.dir, "job.stderr")
		self.fout      = None
		self.ferr      = None
		self.lastout   = ''
		self.lasterr   = ''
		# self.cachefile = path.join(self.dir, "job.cache")
		# self.cachedir  = path.join(self.outdir, '.jobcache')
		# self.pidfile   = path.join(self.dir, "job.pid")
		self.ntry      = 0
		self.input     = {}
		# need to pass this to next procs, so have to keep order
		self.output    = OBox()

		runner_name = self.__class__.__name__[6:].lower()
		self.config = self.proc.config.get(runner_name + 'Runner', {})
		self.script = self.dir / (FILE_SCRIPT + '.' + runner_name)
		self._rc    = None
		self._pid   = None

	@property
	def scriptParts(self):
		"""Prepare parameters for script wrapping"""
		return Box(
			header  = '',
			pre     = self.config.get('preScript', ''),
			post    = self.config.get('postScript', ''),
			saveoe  = True,
			command = [cmdy._shquote(x) for x in chmodX(str(self.dir / 'job.script'))])

	@property
	def data(self):
		"""Data for rendering templates"""
		ret  = Box(
			job = Box(
				index    = self.index,
				indir    = str(self.dir / DIR_INPUT),
				outdir   = str(self.dir / DIR_OUTPUT),
				dir      = str(self.dir),
				outfile  = str(self.dir / FILE_STDOUT),
				errfile  = str(self.dir / FILE_STDERR),
				pidfile  = str(self.dir / FILE_PID),
				cachedir = str(self.dir / DIR_OUTPUT / '.jobcache')),
			i = Box({key: val[1] for key, val in self.input.items()}),
			o = Box({key: val[1] for key, val in self.output.items()}))
		ret.update(self.proc.procvars)
		return ret

	def logger(self, *args, **kwargs):
		"""A logger wrapper to avoid instanize a logger object for each job"""
		level = kwargs.pop('level', 'info')
		kwargs['proc']   = self.proc.name(False)
		kwargs['jobidx'] = self.index
		kwargs['joblen'] = self.proc.size
		_logger[level](*args, **kwargs)

	def _checkClassName(self):
		if not self.__class__.__name__.startswith('Runner'):
			raise RunnerClassNameError('Runner class name is supposed to start with "Runner"')

	def wrapScript(self):
		"""
		Wrap the script to run
		"""
		self.logger('Wrapping up script: %s', self.script, level = 'debug')
		script_parts = self.scriptParts

		# redirect stdout and stderr
		if script_parts.saveoe:
			if isinstance(script_parts.command, list): # pylint: disable=no-member
				script_parts.command[-1] += ' 1> %s 2> %s' % ( # pylint: disable=no-member
					cmdy._shquote(str(self.dir / FILE_STDOUT)),
					cmdy._shquote(str(self.dir / FILE_STDERR)))
			else:
				script_parts.command += ' 1> %s 2> %s' % ( # pylint: disable=no-member
					cmdy._shquote(str(self.dir / FILE_STDOUT)),
					cmdy._shquote(str(self.dir / FILE_STDERR)))

		src       = ['#!/usr/bin/env bash']
		srcappend = src.append
		srcextend = src.extend
		addsrc    = lambda code: (srcextend if isinstance(code, list) else \
			srcappend)(code) if code else None

		addsrc(script_parts.header)
		addsrc('#')
		addsrc('# Collect return code on exit')

		trapcmd = "status = \\$?; echo \\$status > %r; exit \\$status" % str(self.dir / FILE_RC)
		addsrc('trap "%s" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT' % trapcmd)
		addsrc('#')
		addsrc('# Run pre-script')
		addsrc(script_parts.pre)
		addsrc('#')
		addsrc('# Run the real script')
		addsrc(script_parts.command) # pylint: disable=no-member
		addsrc('#')
		addsrc('# Run post-script')
		addsrc(script_parts.post)
		addsrc('#')

		with self.script.open('w') as fscript:
			fscript.write('\n'.join(src))

	def showError(self, totalfailed):
		"""Show the error message if the job failed."""
		msg = []
		rc  = self.rc
		if rc >> RCBIT_NO_OUTFILE:
			msg.append(RCMSG_NO_OUTFILE)
			rc &= ~(1 << RCBIT_NO_OUTFILE)
		if rc >> RCBIT_UNMET_EXPECT:
			msg.append(RCMSG_UNMET_EXPECT)
			rc &= ~(1 << RCBIT_UNMET_EXPECT)
		if rc == RC_NO_RCFILE:
			msg.append(RCMSG_NO_RCFILE)
		elif rc == RC_ERROR_SUBMISSION:
			msg.append(RCMSG_ERROR_SUBMISSION)

		msg = '; '.join(msg)
		msg = '%s [%s]' % (rc, msg) if msg else str(rc)

		if self.proc.errhow == 'ignore':
			self.logger(
				'Failed but ignored (totally {total}). Return code: {msg}.'.format(
					total = totalfailed, msg = msg), level = 'warning')
			return

		self.logger('Failed (totally {total}). Return code: {msg}.'.format(
			total = totalfailed, msg = msg), level = 'error')

		self.logger('Script: {}'.format(
			briefPath(self.dir / FILE_SCRIPT, self.proc._log.shorten)), level = 'error')
		self.logger('Stdout: {}'.format(
			briefPath(self.dir / FILE_STDOUT, self.proc._log.shorten)), level = 'error')
		self.logger('Stderr: {}'.format(
			briefPath(self.dir / FILE_STDERR, self.proc._log.shorten)), level = 'error')

		# errors are not echoed, echo them out
		if self.index not in self.proc.echo.jobs or \
			'stderr' not in self.proc.echo.type:

			self.logger('Check STDERR below:', level = 'error')
			errmsgs = []
			if (self.dir / FILE_STDERR).exists():
				errmsgs = (self.dir / FILE_STDERR).read_text().splitlines()

			if not errmsgs:
				errmsgs = ['<EMPTY STDERR>']

			for errmsg in errmsgs[-20:] if len(errmsgs) > 20 else errmsgs:
				self.logger(errmsg, level = 'stderr')

			if len(errmsgs) > 20:
				self.logger(
					'[ Top {top} line(s) ignored, see all in stderr file. ]'.format(
						top = len(errmsgs) - 20), level = 'stderr')

	def report (self):
		"""Report the job information to logger"""
		procclass = self.proc.__class__
		maxlen = 0
		inkeys = [key for key, _ in self.input.items() if not key.startswith('_')]
		if self.input:
			maxken = max([len(key) for key in inkeys])
			maxlen = max(maxlen, maxken)

		if self.output:
			maxken = max([len(key) for key in self.output.keys()])
			maxlen = max(maxlen, maxken)

		for key in sorted(inkeys):
			if key.startswith('_'):
				continue
			indata, intype = self.input[key]
			if intype in procclass.IN_VARTYPE:
				if isinstance(indata, str) and self.proc._log.shorten \
					and len(indata) > self.proc._log.shorten:
					indata = indata[:int((self.proc._log.shorten / 2) - 3)] + ' ... ' + \
							 indata[-int((self.proc._log.shorten / 2) - 3):]
			elif isinstance(indata, list):
				indata = [briefPath(d, self.proc._log.shorten) for d in indata]
			else:
				indata = briefPath(indata, self.proc._log.shorten)
			self._reportItem(key, maxlen, indata, 'input')

		for key in sorted(self.output.keys()):
			outdata, _ = self.output[key]
			if isinstance(outdata, list):
				outdata = [briefPath(d, self.proc._log.shorten) for d in outdata]
			else:
				outdata = briefPath(outdata, self.proc._log.shorten)
			self._reportItem(key, maxlen, outdata, 'output')

	def _reportItem(self, key, maxlen, data, loglevel):
		"""
		Report the item on logs
		@params:
			`key`: The key of the item
			`maxlen`: The max length of the key
			`data`: The data of the item
			`loglevel`: The log level
		"""

		if not isinstance(data, list):
			self.logger("{} => {}".format(key.ljust(maxlen), data), level = loglevel)
		else:
			ldata = len(data)
			if ldata == 0:
				self.logger("{} => [ {} ]".format(
					key.ljust(maxlen), ''), level = loglevel)
			elif ldata == 1:
				self.logger("{} => [ {} ]".format(
					key.ljust(maxlen), data[0]), level = loglevel)
			elif ldata == 2:
				self.logger("{} => [ {},".format(
					key.ljust(maxlen), data[0]), level = loglevel)
				self.logger("{}      {} ]".format(
					' '.ljust(maxlen), data[1]), level = loglevel)
			elif ldata == 3:
				self.logger("{} => [ {},".format(
					key.ljust(maxlen), data[0]), level = loglevel)
				self.logger("{}      {},".format(
					' '.ljust(maxlen), data[1]), level = loglevel)
				self.logger("{}      {} ]".format(
					' '.ljust(maxlen), data[2]), level = loglevel)
			else:
				self.logger("{} => [ {},".format(
					key.ljust(maxlen), data[0]), level = loglevel)
				self.logger("{}      {},".format(
					' '.ljust(maxlen), data[1]), level = loglevel)
				self.logger("{}      ... ({}),".format(
					' '.ljust(maxlen), len(data) - 3), level = loglevel)
				self.logger("{}      {} ]".format(
					' '.ljust(maxlen), data[-1]), level = loglevel)

	def build(self):
		"""
		Initiate a job, make directory and prepare input, output and script.
		"""
		self.logger('debug', 'Builing the job ...')
		try:
			if not self.dir.exists():
				self.dir.mkdir()
			# preserve the outfile and errfile of previous run
			# issue #30
			if (self.dir / FILE_STDOUT).exists():
				(self.dir / FILE_STDOUT).rename(self.dir / FILE_STDOUT_BAK)
			if (self.dir / FILE_STDERR).exists():
				(self.dir / FILE_STDERR).rename(self.dir / FILE_STDERR_BAK)

			self._prepInput()
			self._prepOutput()
			if self.index == 0:
				self.report()
			self._prepScript()
			# check cache
			if self.isTrulyCached() or self.isExptCached():
				return 'cached'
			return True
		except: # pylint: disable=bare-except
			from traceback import format_exc
			with (self.dir / FILE_STDERR).open('w') as ferr:
				ferr.write(str(format_exc()))
			return False

	def _linkInfile(self, orgfile):
		"""
		Create links for input files
		@params:
			`orgfile`: The original input file
		@returns:
			The link to the original file.
		"""
		infile = self.dir / DIR_INPUT / orgfile.name
		try:
			fs.link(orgfile, infile, overwrite = False)
		except OSError:
			pass
		if fs.samefile(infile, orgfile):
			return infile

		exist_infiles = (self.dir / DIR_INPUT).glob('[[]*[]]*')
		num = 0
		for i, eifile in enumerate(exist_infiles):
			# The GIL here takes time, if there are more than 100 files,
			# Just don't check
			if i < 100 and fs.samefile(eifile, orgfile):
				return eifile
			try:
				nexist = int(eifile.name[1:eifile.name.find(']')])
			except ValueError:
				pass
			else:
				num = max(num, nexist)

		infile = self.dir / DIR_INPUT / '[{}]{}'.format(num + 1, orgfile.name)
		fs.link(orgfile, infile)
		return infile

	# pylint: disable=too-many-branches
	def _prepInput (self):
		"""
		Prepare input, create link to input files and set other placeholders
		"""
		procclass = self.proc.__class__
		#fs.remove(self.dir / DIR_INPUT)
		# fs.makedirs will clean existing dir
		fs.makedirs(self.dir / DIR_INPUT)

		for key, val in self.proc.input.items():
			self.input[key] = {}
			intype = val['type']
			# the original input file(s)
			indata = val['data'][self.index]
			if intype in procclass.IN_FILETYPE:
				if not isinstance(indata, str):
					raise JobInputParseError(
						indata, 'Not a string for input "%s:%s"' % (key, intype))
				if not indata:
					infile  = ''
				elif not fs.exists(indata):
					raise JobInputParseError(
						indata, 'File not exists for input "%s:%s"' % (key, intype))
				else:
					indata   = path.abspath(indata)
					basename = path.basename(indata)
					infile   = self._linkInfile(indata)
					if basename != path.basename(infile):
						self.logger("warning", "Input file renamed: %s -> %s" %
							(basename, path.basename(infile)), dlevel = 'INFILE_RENAMING')
				self.input[key]['type'] = intype
				self.input[key]['data'] = infile

			elif intype in procclass.IN_FILESTYPE:
				self.input[key]['type']       = intype
				self.input[key]['data']       = []

				if not indata:
					self.logger("warning",
						'No data provided for "{}:{}", use empty list instead.'.format(
							key, intype), dlevel = 'INFILE_EMPTY')
					continue

				if not isinstance(indata, list):
					raise JobInputParseError(
						indata, 'Not a list for input "%s:%s"' % (key, intype))

				for data in indata:
					if not isinstance(data, str):
						raise JobInputParseError(
							data, 'Not a string for element of input "%s:%s"' % (key, intype))

					if not data:
						infile  = ''
					elif not fs.exists(data):
						raise JobInputParseError(data,
							'File not exists for element of input "%s:%s"' % (key, intype))
					else:
						data     = path.abspath(data)
						basename = path.basename(data)
						infile   = self._linkInfile(data)
						if basename != path.basename(infile):
							self.logger("warning", 'Input file renamed: {} -> {}'.format(
								basename, path.basename(infile)), dlevel = 'INFILE_RENAMING')
					self.input[key]['data'].append (infile)
			else:
				self.input[key]['type'] = intype
				self.input[key]['data'] = indata

	def _prepOutput (self):
		"""Build the output data"""
		procclass = self.proc.__class__
		if not fs.exists (self.dir / DIR_OUTPUT):
			fs.makedirs (self.dir / DIR_OUTPUT)

		output = self.proc.output
		# has to be OrderedDict
		assert isinstance(output, dict)
		# allow empty output
		if not output:
			return
		for key, val in output.items():
			outtype, outtpl = val
			outdata = outtpl.render(self.data)
			#self.output[key] = {'type': outtype, 'data': outdata}
			if outtype in procclass.OUT_FILETYPE + procclass.OUT_DIRTYPE + \
				procclass.OUT_STDOUTTYPE + procclass.OUT_STDERRTYPE:
				if path.isabs(outdata):
					raise JobOutputParseError(outdata,
						'Absolute path not allowed for output file/dir for key %r' % key)
				self.output[key] = (outtype, self.dir / DIR_OUTPUT / outdata)
			else:
				self.output[key] = (outtype, outdata)

	def _prepScript (self):
		"""
		Build the script, interpret the placeholders
		"""
		script = self.proc.script.render(self.data)

		write = True
		if path.isfile (self.script):
			with open(self.script) as fscript:
				prevscript = fscript.read()
			if prevscript == script:
				write = False
			else:
				# for debug
				fs.move(self.script, self.script + '.bak')
				self.logger('debug', "Script file updated: %s" %
					self.script, dlevel = 'SCRIPT_EXISTS')
		if write:
			with open (self.script, 'w') as fscript:
				fscript.write(script)

		self.wrapScript()

	@property
	def rc(self): # pylint: disable=invalid-name
		"""
		Get the return code
		Exception not meet
		  |
		0b1100000000
		   |
		   outfile not generated
		"""
		if self._rc is not None and self._rc != RC_NO_RCFILE:
			return self._rc

		if not fs.isfile(self.dir / FILE_RC):
			return RC_NO_RCFILE
		with (self.dir / FILE_RC).open('r') as frc:
			returncode = frc.read().strip()
			if not returncode:
				return RC_NO_RCFILE
			return int(returncode)

	@rc.setter
	def rc(self, val): # pylint: disable=invalid-name
		self._rc = val
		with (self.dir / FILE_RC).open('w') as frc:
			frc.write(str(val))

	@property
	def pid(self):
		"""
		Get pid of the job
		@return:
			The job id, could be the process id or job id for other platform.
		"""
		if self._pid:
			return self._pid
		if not fs.exists(self.dir / FILE_PID):
			return ''
		with (self.dir / FILE_PID).open('r') as fpid:
			return fpid.read().strip()

	@pid.setter
	def pid(self, val):
		self._pid = str(val)
		with (self.dir / FILE_PID).open('w') as fpid:
			fpid.write(str(val))

	# pylint: disable=too-many-return-statements
	def isTrulyCached (self):
		"""
		Check whether a job is truly cached (by signature)
		"""
		if not self.proc.cache:
			return False
		procclass = self.proc.__class__

		if not fs.exists(self.dir / FILE_CACHE):
			self.logger('debug', "Not cached as cache file not exists.",
				dlevel = "CACHE_SIGFILE_NOTEXISTS")
			return False

		with (self.dir / FILE_CACHE).open('r') as fcache:
			if not fcache.read().strip():
				self.logger('debug', "Not cached because previous signature is empty.",
					dlevel = "CACHE_EMPTY_PREVSIG")
				return False

		sig_old = Box.from_yaml(filename = self.dir / FILE_CACHE)
		sig_now = self.signature()
		if not sig_now:
			self.logger('debug', "Not cached because current signature is empty.",
				dlevel = "CACHE_EMPTY_CURRSIG")
			return False

		def compareVar(osig, nsig, key, logkey):
			"""Compare var in signature"""
			for k in osig.keys():
				oval = osig[k]
				nval = nsig[k]
				if nval == oval:
					continue
				self.logger('debug', (
					"Not cached because {key} variable({k}) is different:\n" +
					"...... - Previous: {prev}\n" +
					"...... - Current : {curr}"
				).format(key = key, k = k, prev = oval, curr = nval), dlevel = logkey)
				return False
			return True

		def compareFile(osig, nsig, key, logkey, timekey = None):
			"""Compare var in file"""
			for k in osig.keys():
				ofile, otime = osig[k]
				nfile, ntime = nsig[k]
				if nfile == ofile and ntime <= otime:
					continue
				if nfile != ofile:
					self.logger('debug', (
						"Not cached because {key} file({k}) is different:\n" +
						"...... - Previous: {prev}\n" +
						"...... - Current : {curr}"
					).format(key = key, k = k, prev = ofile, curr = nfile), dlevel = logkey)
					return False
				if timekey and ntime > otime:
					self.logger('debug', (
						"Not cached because {key} file({k}) is newer: {ofile}\n" +
						"...... - Previous: {otime} ({transotime})\n" +
						"...... - Current : {ntime} ({transntime})"
					).format(
						key = key, k = k, ofile = ofile, otime = otime,
						transotime = datetime.fromtimestamp(otime), ntime = ntime,
						transntime = datetime.fromtimestamp(ntime)
					), dlevel = timekey)
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
					ofile, otime = (None, None) if i >= olen else oval[i]
					nfile, ntime = (None, None) if i >= nlen else nval[i]
					if nfile == ofile and ntime <= otime:
						continue
					if nfile != ofile:
						self.logger('debug', (
							"Not cached because file {i} is different for {key} files({k}):\n" +
							"...... - Previous: {ofile}\n" +
							"...... - Current : {nfile}"
						).format(
							i = i + 1, key = key, k = k, ofile = ofile, nfile = nfile
						), dlevel = logkey)
						return False
					if timekey and ntime > otime:
						self.logger('debug', (
							"Not cached because file {i} is newer for {key} files({k}): " +
							"{ofile}\n...... - Previous: {otime} ({transotime})\n" +
							"...... - Current : {ntime} ({transntime})"
						).format(
							i = i + 1, key = key, k = k, ofile = ofile, otime = otime,
							transotime = datetime.fromtimestamp(otime), ntime = ntime,
							transntime = datetime.fromtimestamp(ntime)
						), dlevel = timekey)
						return False
			return True
		if not compareFile(
			{'script': sig_old['script']},
			{'script': sig_now['script']},
			'script',
			'',
			'CACHE_SCRIPT_NEWER'
		): return False
		if not compareVar(
			sig_old['i'][procclass.IN_VARTYPE[0]],
			sig_now['i'][procclass.IN_VARTYPE[0]],
			'input',
			'CACHE_SIGINVAR_DIFF'
		): return False
		if not compareFile(
			sig_old['i'][procclass.IN_FILETYPE[0]],
			sig_now['i'][procclass.IN_FILETYPE[0]],
			'input',
			'CACHE_SIGINFILE_DIFF',
			'CACHE_SIGINFILE_NEWER'
		): return False
		if not compareFiles(
			sig_old['i'][procclass.IN_FILESTYPE[0]],
			sig_now['i'][procclass.IN_FILESTYPE[0]],
			'input',
			'CACHE_SIGINFILES_DIFF',
			'CACHE_SIGINFILES_NEWER'
		): return False
		if not compareVar(
			sig_old['o'][procclass.OUT_VARTYPE[0]],
			sig_now['o'][procclass.OUT_VARTYPE[0]],
			'output',
			'CACHE_SIGOUTVAR_DIFF'
		): return False
		if not compareFile(
			sig_old['o'][procclass.OUT_FILETYPE[0]],
			sig_now['o'][procclass.OUT_FILETYPE[0]],
			'output',
			'CACHE_SIGOUTFILE_DIFF'
		): return False
		if not compareFile(
			sig_old['o'][procclass.OUT_DIRTYPE[0]],
			sig_now['o'][procclass.OUT_DIRTYPE[0]],
			'output dir',
			'CACHE_SIGOUTDIR_DIFF'
		): return False
		self.rc = 0 # pylint: disable=invalid-name
		#fs.move(self.outfile + '.bak', self.outfile)
		#fs.move(self.errfile + '.bak', self.errfile)
		return True

	def isExptCached (self):
		"""
		Prepare to use export files as cached information
		True if succeed, otherwise False
		"""
		procclass = self.proc.__class__
		if self.proc.cache != 'export':
			return False
		if self.proc.exhow in procclass.EX_LINK:
			self.logger("warning",
				"Job is not export-cached using symlink export.",
				dlevel = "EXPORT_CACHE_USING_SYMLINK")
			return False
		if self.proc.expart and self.proc.expart[0].render(self.data):
			self.logger("warning", "Job is not export-cached using partial export.",
				dlevel = "EXPORT_CACHE_USING_EXPARTIAL")
			return False
		if not self.proc.exdir:
			self.logger('debug', "Job is not export-cached since export directory is not set.",
				dlevel = "EXPORT_CACHE_EXDIR_NOTSET")
			return False

		for out in self.output.values():
			if out['type'] in procclass.OUT_VARTYPE:
				continue
			exfile = path.abspath(path.join(self.proc.exdir, path.basename(out['data'])))

			if self.proc.exhow in procclass.EX_GZIP:
				exfile += '.tgz' if path.isdir(out['data']) or \
					out['type'] in procclass.OUT_DIRTYPE else '.gz'
				with fs.lock(exfile, out['data']):
					exfile_exists  = fs.exists(exfile)
					outdata_exists = fs.exists(out['data'])
					outdata_islink = fs.islink(out['data'])
					if not exfile_exists:
						self.logger('debug',
							"Job is not export-cached since exported file not exists: " +
							"%s." % exfile, dlevel = "EXPORT_CACHE_EXFILE_NOTEXISTS")
						return False

					if outdata_exists or outdata_islink:
						self.logger("warning",
							'Overwrite file for export-caching: %s' % out['data'],
							dlevel = "EXPORT_CACHE_OUTFILE_EXISTS")
					fs.gunzip(exfile, out['data'])
			else: # exhow not gzip
				with fs.lock(exfile, out['data']):
					exfile_exists  = fs.exists(exfile)
					outdata_exists = fs.exists(out['data'])
					outdata_islink = fs.islink(out['data'])
					if not exfile_exists:
						self.logger('debug',
							"Job is not export-cached since exported file not exists: " +
							"%s." % exfile, dlevel = "EXPORT_CACHE_EXFILE_NOTEXISTS")
						return False
					if fs.samefile(exfile, out['data']):
						continue
					if outdata_exists or outdata_islink:
						self.logger("warning",
							'Overwrite file for export-caching: %s' % out['data'],
							dlevel = "EXPORT_CACHE_OUTFILE_EXISTS")
					fs.link(exfile, out['data'])
		self.rc = 0
		return True

	def cache (self):
		"""Truly cache the job (by signature)"""
		if not self.proc.cache:
			return
		sig  = self.signature()
		if sig:
			sig.to_yaml(filename = self.dir / FILE_CACHE)

	def reset (self):
		"""Clear the intermediate files and output files"""
		procclass = self.proc.__class__
		retry    = self.ntry
		retrydir = self.dir / ('retry.' + str(retry))
		#cleanup retrydir
		if retry:
			fs.remove(retrydir)
			fs.makedirs(retrydir)
		else:
			for retrydir in retrydir.glob('retry.*'):
				fs.remove(retrydir)

		for jobfile in (FILE_RC, FILE_STDOUT, FILE_STDERR, FILE_PID):
			if retry:
				fs.move(self.dir / jobfile, retrydir / jobfile)
			else:
				fs.remove(jobfile)
		# try to keep the cache dir, which, in case, if some program can resume from
		if not fs.exists(self.dir / FILE_CACHE):
			if retry:
				fs.move(self.dir / DIR_OUTPUT, retrydir / DIR_OUTPUT)
			else:
				fs.remove(self.dir / DIR_OUTPUT)
		elif retry:
			retryoutdir = retrydir / DIR_OUTPUT
			fs.makedirs(retryoutdir)
			# move everything to retrydir but the cachedir
			for outfile in (self.dir / DIR_OUTPUT).glob('*'):
				if outfile.name == DIR_CACHE:
					continue
				fs.move(outfile, retryoutdir / outfile.name)
		else:
			for outfile in (self.dir / DIR_OUTPUT).glob('*'):
				if outfile.name == DIR_CACHE:
					continue
				fs.remove(outfile)

		open(self.dir / FILE_STDOUT, 'w').close()
		open(self.dir / FILE_STDERR, 'w').close()

		try:
			fs.makedirs(self.dir / DIR_OUTPUT, overwrite = False)
		except OSError:
			pass
		for out in self.output.values():
			if out['type'] in procclass.OUT_DIRTYPE:
				try:
					fs.makedirs(out['data'], overwrite = False)
				except OSError:
					pass
			if out['type'] in procclass.OUT_STDOUTTYPE:
				fs.link(self.dir / FILE_STDOUT, out['data'])
			if out['type'] in procclass.OUT_STDERRTYPE:
				fs.link(self.dir / FILE_STDERR, out['data'])

	def export(self):
		"""Export the output files"""
		if not self.proc.exdir:
			return
		assert path.exists(self.proc.exdir) and path.isdir(self.proc.exdir), \
			'Export directory has to be a directory.'
		assert isinstance(self.proc.expart, list)

		procclass = self.proc.__class__
		# output files to export
		files2ex = []
		data     = self.data
		if not self.proc.expart or (len(self.proc.expart) == 1 \
			and not self.proc.expart[0].render(data)):
			for outtype, outdata in self.output.values():
				if outtype in procclass.OUT_VARTYPE:
					continue
				files2ex.append(Path(outdata))
		else:
			for expart in self.proc.expart:
				expart = expart.render(data)
				if expart in self.output:
					files2ex.append(Path(self.output[expart][1]))
				else:
					files2ex.extend((self.dir / DIR_OUTPUT).glob(expart))

		files2ex  = set(files2ex)
		for file2ex in files2ex:
			bname  = file2ex.name
			# exported file
			exfile = path.join(self.proc.exdir, bname)
			if self.proc.exhow in procclass.EX_GZIP:
				exfile += '.tgz' if fs.isdir(file2ex) else '.gz'

			with fs.lock(file2ex, exfile):
				if self.proc.exhow in procclass.EX_GZIP:
					fs.gzip(file2ex, exfile, overwrite = self.proc.exow)
				elif self.proc.exhow in procclass.EX_COPY:
					fs.copy(file2ex, exfile, overwrite = self.proc.exow)
				elif self.proc.exhow in procclass.EX_LINK:
					fs.link(file2ex, exfile, overwrite = self.proc.exow)
				else: # move
					if fs.islink(file2ex):
						fs.copy(file2ex, exfile, overwrite = self.proc.exow)
					else:
						fs.move(file2ex, exfile, overwrite = self.proc.exow)
						fs.link(exfile, file2ex)

			self.logger('export', 'Exported: {}'.format(briefPath(exfile, self.proc._log.shorten)))

	def succeed(self):
		"""
		Tell if a job succeeds.
		Check whether output files generated, expectation met and return code met.
		@return:
			`True` if succeed else `False`
		"""
		procclass = self.proc.__class__
		utime(self.dir / DIR_OUTPUT, None)
		for out in self.output.values():
			if out['type'] in procclass.OUT_VARTYPE:
				continue
			if not path.exists(out['data']):
				self.rc |= 0b100000000
				self.logger('debug', 'Outfile not generated: {}'.format(out['data']),
					dlevel = "OUTFILE_NOT_EXISTS")
		expect_cmd = self.proc.expect.render(self.data)

		if expect_cmd:
			self.logger('debug', 'Check expectation: %s' % expect_cmd, dlevel = "EXPECT_CHECKING")
			cmd = cmdy.bash(c = expect_cmd) # pylint: disable=no-member
			if cmd.rc != 0:
				self.rc |= 0b1000000000
		return self.rc in self.proc.rc

	def done(self, cached = False):
		"""
		Do some cleanup when job finished
		@params:
			`export`: Whether do export
		"""
		self.logger('debug', 'Finishing up the job ...')
		if not cached or self.proc.acache:
			self.export()
		if not cached:
			self.cache()

	def signature (self):
		"""
		Calculate the signature of the job based on the input/output and the script
		@returns:
			The signature of the job
		"""
		procclass = self.proc.__class__
		ret = Box()
		sig = filesig(self.script)
		if not sig:
			self.logger('debug', 'Empty signature because of script file: %s.' %
				self.script, dlevel = "CACHE_EMPTY_CURRSIG")
			return ''
		ret.script = sig
		ret.i = {
			procclass.IN_VARTYPE  [0]: {},
			procclass.IN_FILETYPE [0]: {},
			procclass.IN_FILESTYPE[0]: {}}
		ret.o = {
			procclass.OUT_VARTYPE [0]: {},
			procclass.OUT_FILETYPE[0]: {},
			procclass.OUT_DIRTYPE [0]: {}}
		for key, val in self.input.items():
			if val['type'] in procclass.IN_VARTYPE:
				ret.i[procclass.IN_VARTYPE[0]][key] = val['data']
			elif val['type'] in procclass.IN_FILETYPE:
				sig = filesig(val['data'], dirsig = self.proc.dirsig)
				if not sig:
					self.logger('debug',
						'Empty signature because of input file: %s.' % val['data'],
						dlevel = "CACHE_EMPTY_CURRSIG")
					return ''
				ret.i[procclass.IN_FILETYPE[0]][key] = sig
			elif val['type'] in procclass.IN_FILESTYPE:
				ret.i[procclass.IN_FILESTYPE[0]][key] = []
				for infile in sorted(val['data']):
					sig = filesig(infile, dirsig = self.proc.dirsig)
					if not sig:
						self.logger('debug',
							'Empty signature because of one of input files: %s.' % infile,
							dlevel = "CACHE_EMPTY_CURRSIG")
						return ''
					ret.i[procclass.IN_FILESTYPE[0]][key].append (sig)
		for key, val in self.output.items():
			if val['type'] in procclass.OUT_VARTYPE:
				ret.o[procclass.OUT_VARTYPE[0]][key] = val['data']
			elif val['type'] in procclass.OUT_FILETYPE:
				sig = filesig(val['data'], dirsig = self.proc.dirsig)
				if not sig:
					self.logger('debug',
						'Empty signature because of output file: %s.' % val['data'],
						dlevel = "CACHE_EMPTY_CURRSIG")
					return ''
				ret.o[procclass.OUT_FILETYPE[0]][key] = sig
			elif val['type'] in procclass.OUT_DIRTYPE:
				sig = filesig(val['data'], dirsig = self.proc.dirsig)
				if not sig:
					self.logger('debug',
						'Empty signature because of output dir: %s.' % val['data'],
						dlevel = "CACHE_EMPTY_CURRSIG")
					return ''
				ret.o[procclass.OUT_DIRTYPE[0]][key] = sig
		return ret

	def isRunningImpl(self):
		"""Implemetation of telling whether the job is running"""
		raise NotImplementedError()

	def submitImpl(self):
		"""Implemetation of submission"""
		raise NotImplementedError()

	def submit(self):
		"""Submit the job"""
		self.logger('debug', 'Submitting the job ...')
		if self.isRunningImpl():
			self.logger('is already running at {}, skip submission.'.format(self.pid),
				level = 'submit')
			return True
		self.reset()
		rscmd = self.submitImpl()
		if rscmd.rc == 0:
			return True
		self.logger(
			'Submission failed (rc = {rscmd.rc}, cmd = {rscmd.cmd})\n{rscmd.stderr}'.format(
				rscmd = rscmd), dlevel = 'SUBMISSION_FAIL', level = 'error')
		return False

	def poll(self):
		"""Check the status of a running job"""
		self.logger('debug', 'Polling the job ...')
		if not fs.isfile(self.dir / FILE_STDERR) or not fs.isfile(self.dir / FILE_STDOUT):
			return 'running'

		elif self.rc != RC_NO_RCFILE:
			self._flush(end = True)
			return self.succeed()
		else: # running
			self._flush()
			return 'running'

	def _flush (self, end = False):
		"""
		Flush stdout/stderr
		@params:
			`fout`: The stdout file handler
			`ferr`: The stderr file handler
			`lastout`: The leftovers of previously readlines of stdout
			`lasterr`: The leftovers of previously readlines of stderr
			`end`: Whether this is the last time to flush
		"""
		if self.index not in self.proc.echo['jobs']:
			return

		if not self.fout or self.fout.closed:
			self.fout = (self.dir / FILE_STDOUT).open()
		if not self.ferr or self.ferr.closed:
			self.ferr = (self.dir / FILE_STDERR).open()

		if 'stdout' in self.proc.echo['type']:
			lines, self.lastout = fileflush(self.fout, self.lastout, end)
			outfilter = self.proc.echo['type']['stdout']
			for line in lines:
				if not outfilter or re.search(outfilter, line):
					self.logger(line.rstrip('\n'), level = '_stdout')
		lines, self.lasterr = fileflush(self.ferr, self.lasterr, end)
		for line in lines:
			if line.startswith('pyppl.log'):
				line = line.rstrip('\n')
				logstrs  = line[9:].lstrip().split(':', 1)
				if len(logstrs) == 1:
					logstrs.append('')
				(loglevel, logmsg) = logstrs
				loglevel = loglevel[1:] if loglevel else 'log'
				# '_' makes sure it's not filtered by log levels
				self.logger['_' + loglevel](logmsg.lstrip())
			elif 'stderr' in self.proc.echo['type']:
				errfilter = self.proc.echo['type']['stderr']
				if not errfilter or re.search(errfilter, line):
					self.logger(line.rstrip('\n'), level = '_stderr')

		if end and self.fout and not self.fout.closed:
			self.fout.close()
		if end and self.ferr and not self.ferr.closed:
			self.ferr.close()

	def retry(self):
		"""
		If the job is available to retry
		@return:
			`True` if it is else `False`
		"""
		if self.proc.errhow == 'ignore':
			return 'ignored'
		if self.proc.errhow != 'retry':
			return False

		self.logger('Retrying {} out of {} times ...'.format(
			str(self.ntry + 1).rjust(len(str(self.proc.errntry)), '0'),
			self.proc.errntry
		), level = 'rtrying')
		self.ntry += 1
		return self.ntry < self.proc.errntry

	def kill(self):
		"""
		Kill the job
		"""
		self.logger('debug', 'Killing the job ...')
		try:
			self.killImpl()
			return True
		except: # pylint: disable=bare-except
			self.pid = ''
			return False
