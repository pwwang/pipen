"""job module for PyPPL"""
import re
from os import path, utime
from pathlib import Path
from datetime import datetime
import yaml
import cmdy
from .utils import Box, OBox, chmodX, briefPath, filesig, fileflush, fs
from .logger import logger as _logger
from .exception import JobInputParseError, JobOutputParseError
from .plugin import pluginmgr

# File names
DIR_INPUT       = 'input'
DIR_OUTPUT      = 'output'
DIR_CACHE       = '.jobcache' # under output
FILE_SCRIPT     = 'job.script'
FILE_SCRIPT_BAK = 'job.script._bak' # in case there is a runner: RunnerBak
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
	"""@API
	Describes a job, also as a base class for runner
	@static variables
		POLL_INTERVAL (int): The interval between each job state polling.
	"""

	POLL_INTERVAL = 1

	__slots__ = ('index', 'proc', 'dir', 'fout', 'ferr', 'lastout', 'lasterr', \
		'ntry', 'input', 'output', 'config', 'script', '_rc', '_pid')

	def __init__(self, index, proc):
		"""@API
		Initiate a job
		@params:
			index (int):  The index of the job.
			proc (Proc): The process of the job.
		"""

		self.index   = index
		self.proc    = proc

		self.logger('Initializing Job ...', level = 'debug')
		self.dir     = self.proc.workdir if isinstance(self.proc.workdir, Path) \
			else Path(self.proc.workdir)
		self.dir     = (self.dir / str(index+1)).resolve()
		self.fout    = None
		self.ferr    = None
		self.lastout = ''
		self.lasterr = ''
		self.ntry    = 0
		self.input   = {}
		self.output  = OBox()

		runner_name = self.__class__.__name__[6:].lower()
		self.config = self.proc.config.get(runner_name + 'Runner', {})
		# the wrapper script
		self.script = self.dir / (FILE_SCRIPT + '.' + runner_name)
		self._rc    = None
		self._pid   = None
		pluginmgr.hook.jobPreRun(job = self)

	@property
	def scriptParts(self):
		"""@API
		Prepare parameters for script wrapping
		@returns:
			(Box): A `Box` containing the parts to wrap the script.
		"""
		return Box(
			header  = '',
			pre     = self.config.get('preScript', ''),
			post    = self.config.get('postScript', ''),
			saveoe  = True,
			command = [cmdy._shquote(x) for x in chmodX(self.dir / 'job.script')])

	@property
	def data(self):
		"""@API
		Data for rendering templates
		@returns:
			(dict): The data used to render the templates.
		"""
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
		"""@API
		A logger wrapper to avoid instanize a logger object for each job
		@params:
			*args (str): messages to be logged.
			*kwargs: Other parameters for the logger.
		"""
		level = kwargs.pop('level', 'info')
		kwargs['proc']   = self.proc.name(False)
		kwargs['jobidx'] = self.index
		kwargs['joblen'] = self.proc.size
		if kwargs.pop('pbar', False):
			_logger.pbar[level](*args, **kwargs)
		else:
			_logger[level](*args, **kwargs)

	def wrapScript(self):
		"""@API
		Wrap the script to run
		"""
		self.logger('Wrapping up script: %s' % self.script, level = 'debug')
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

		trapcmd = "status=\\$?; echo \\$status > %r; exit \\$status" % str(self.dir / FILE_RC)
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

		self.script.write_text('\n'.join(src))

	def showError(self, totalfailed):
		"""@API
		Show the error message if the job failed.
		@params:
			totalfailed (int): Total number of jobs failed.
		"""
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

	def report(self):
		"""@API
		Report the job information to log
		"""
		procclass = self.proc.__class__
		maxlen = 0
		inkeys = [key for key, _ in self.input.items() if not key.startswith('_')]
		if self.input:
			maxken = max([len(key) for key in inkeys])
			maxlen = max(maxlen, maxken)

		if self.output:
			maxken = max([len(key) for key in self.output])
			maxlen = max(maxlen, maxken)

		for key in sorted(inkeys):
			intype, indata = self.input[key]
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

		for key in sorted(self.output):
			_, outdata = self.output[key]
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
			if ldata <= 1:
				self.logger("{} => [ {} ]".format(
					key.ljust(maxlen), data and data[0] or ''), level = loglevel)
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
		"""@API
		Initiate a job, make directory and prepare input, output and script.
		"""
		self.logger('Builing the job ...', level = 'debug')
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
		except Exception as ex: # pylint: disable=bare-except
			self.logger('Failed to build job: %s' % ex, level = 'debug')
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
	def _prepInput(self):
		"""
		Prepare input, create link to input files and set other placeholders
		"""
		procclass = self.proc.__class__
		#fs.remove(self.dir / DIR_INPUT)
		# fs.makedirs will clean existing dir
		fs.makedirs(self.dir / DIR_INPUT)

		for key, val in self.proc.input.items():
			# the original input file(s)
			intype, indata = val[0], val[1][self.index]
			if intype in procclass.IN_FILETYPE:
				if not isinstance(indata, (Path, str)):
					raise JobInputParseError(
						indata, 'Not a string or path for input [%s:%s]' % (key, intype))
				if not indata: # allow empty input
					infile  = ''
				elif not fs.exists(indata):
					raise JobInputParseError(
						indata, 'File not exists for input [%s:%s]' % (key, intype))
				else:
					indata = Path(indata).resolve()
					infile = self._linkInfile(indata)

					if indata.name != infile.name:
						self.logger("Input file renamed: %s -> %s" %
							(indata.name, infile.name),
							dlevel = 'INFILE_RENAMING', level = "warning")
				self.input[key] = (intype, str(infile))

			elif intype in procclass.IN_FILESTYPE:
				self.input[key] = (intype, [])

				if not indata:
					self.logger(
						'No data provided for [%s:%s], use empty list instead.' %
						(key, intype), dlevel = 'INFILE_EMPTY', level = "warning")
					continue

				if not isinstance(indata, list):
					raise JobInputParseError(
						indata, 'Not a list for input [%s:%s]' % (key, intype))

				for data in indata:
					if not isinstance(data, (Path, str)):
						raise JobInputParseError(data,
							'Not a string or path for element of input [%s:%s]' % (key, intype))

					if not data:
						infile  = ''
					elif not fs.exists(data):
						raise JobInputParseError(data,
							'File not exists for element of input [%s:%s]' % (key, intype))
					else:
						data   = Path(data).resolve()
						infile = self._linkInfile(data)
						if data.name != infile.name:
							self.logger('Input file renamed: %s -> %s' %
								(data.name, infile.name),
								dlevel = 'INFILE_RENAMING', level = "warning")
					self.input[key][1].append(str(infile))
			else:
				self.input[key] = (intype, indata)

	def _prepOutput(self):
		"""Build the output data"""
		procclass = self.proc.__class__
		# keep the output dir if exists
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
		script    = self.proc.script.render(self.data)
		# real script file
		realsfile = self.dir / FILE_SCRIPT
		if fs.isfile(realsfile) and realsfile.read_text() != script:
			fs.move(realsfile, self.dir / FILE_SCRIPT_BAK)
			self.logger("Script file updated: %s" % realsfile,
				dlevel = 'SCRIPT_EXISTS', level = 'debug')
			realsfile.write_text(script)
		elif not fs.isfile(realsfile):
			realsfile.write_text(script)
		self.wrapScript()

	@property
	def rc(self): # pylint: disable=invalid-name
		"""@API
		Get the return code
		@returns:
			(int): The return code.
		"""
		if self._rc is not None and self._rc != RC_NO_RCFILE:
			return self._rc

		if not fs.isfile(self.dir / FILE_RC):
			return RC_NO_RCFILE
		with (self.dir / FILE_RC).open('r') as frc:
			returncode = frc.read().strip()
			if not returncode or returncode == 'None':
				return RC_NO_RCFILE
			return int(returncode)

	@rc.setter
	def rc(self, val): # pylint: disable=invalid-name
		"""@API
		Set and save the return code
		@params:
			val (int|str): The return code.
		"""
		self._rc = val
		with (self.dir / FILE_RC).open('w') as frc:
			frc.write(str(val))

	@property
	def pid(self):
		"""@API
		Get pid of the job
		@returns:
			(str): The job id, could be the process id or job id for other platform.
		"""
		if self._pid:
			return self._pid
		if not fs.exists(self.dir / FILE_PID):
			return ''
		return (self.dir / FILE_PID).read_text().strip()

	@pid.setter
	def pid(self, val):
		"""@API
		Set and save the pid or job id.
		@params:
			val (int|str): The pid or the job id from other platform.
		"""
		self._pid = str(val)
		(self.dir / FILE_PID).write_text(str(val))

	def signature (self):
		"""@API
		Calculate the signature of the job based on the input/output and the script
		@returns:
			(Box): The signature of the job
		"""
		sig = filesig(self.dir / FILE_SCRIPT)
		if not sig:
			self.logger('Empty signature because of script file: %s.' %
				(self.dir / FILE_SCRIPT), dlevel = "CACHE_EMPTY_CURRSIG", level = 'debug')
			return ''

		procclass    = self.proc.__class__
		intype_var   = procclass.IN_VARTYPE[0]
		intype_file  = procclass.IN_FILETYPE[0]
		intype_files = procclass.IN_FILESTYPE[0]
		outype_var   = procclass.OUT_VARTYPE[0]
		outype_file  = procclass.OUT_FILETYPE[0]
		outype_dir   = procclass.OUT_DIRTYPE[0]

		ret        = Box()
		ret.script = sig
		ret.i      = {intype_var: {}, intype_file: {}, intype_files: {}}
		ret.o      = {outype_var: {}, outype_file: {}, outype_dir: {}}
		for key, val in self.input.items():
			(datatype, data) = val
			if datatype in procclass.IN_FILETYPE:
				sig = filesig(data, dirsig = self.proc.dirsig)
				if not sig:
					self.logger('Empty signature because of input file: %s.' % datatype,
						dlevel = "CACHE_EMPTY_CURRSIG", level = 'debug')
					return ''
				ret.i[intype_file][key] = sig
			elif datatype in procclass.IN_FILESTYPE:
				ret.i[intype_files][key] = []
				for infile in sorted(data):
					sig = filesig(infile, dirsig = self.proc.dirsig)
					if not sig:
						self.logger('Empty signature because of one of input files: %s.' %
							infile, dlevel = "CACHE_EMPTY_CURRSIG", level = 'debug')
						return ''
					ret.i[intype_files][key].append(sig)
			else:
				ret.i[intype_var][key] = data
		for key, val in self.output.items():
			(datatype, data) = val
			if datatype in procclass.OUT_FILETYPE:
				sig = filesig(data, dirsig = self.proc.dirsig)
				if not sig:
					self.logger('Empty signature because of output file: %s.' % data,
						dlevel = "CACHE_EMPTY_CURRSIG", level = 'debug')
					return ''
				ret.o[outype_file][key] = sig
			elif datatype in procclass.OUT_DIRTYPE:
				sig = filesig(data, dirsig = self.proc.dirsig)
				if not sig:
					self.logger('Empty signature because of output dir: %s.' % data,
						dlevel = "CACHE_EMPTY_CURRSIG", level = 'debug')
					return ''
				ret.o[outype_dir][key] = sig
			else:
				ret.o[outype_var][key] = str(data)
		return ret

	def _compareVar(self, osig, nsig, key, logkey):
		"""Compare var in signature"""
		for k in osig:
			# key has to be the same, otherwise the suffix will be different
			if nsig[k] == osig[k]:
				continue
			self.logger(("Not cached because {key} variable({k}) is different:\n" +
							"...... - Previous: {prev}\n" +
							"...... - Current : {curr}").format(
							key = key, k = k, prev = osig[k], curr = nsig[k]),
						dlevel = logkey, level = 'debug')
			return False
		return True

	def _compareFile(self, osig, nsig, key, logkey, timekey = None):
		"""Compare file in signature"""
		key = key if key.endswith(' file') or key.endswith(' dir') else key + ' file'
		for k in osig:
			ofile, otime = osig[k]
			nfile, ntime = nsig[k]
			if nfile == ofile and ntime <= otime:
				continue
			if nfile != ofile:
				self.logger(("Not cached because {key}({k}) is different:\n" +
							 "...... - Previous: {prev}\n" +
							 "...... - Current : {curr}").format(
								key = key, k = k, prev = ofile, curr = nfile),
							dlevel = logkey, level = 'debug')
				return False
			if timekey and ntime > otime:
				self.logger(("Not cached because {key}({k}) is newer: {ofile}\n" +
							 "...... - Previous: {otime} ({transotime})\n" +
							 "...... - Current : {ntime} ({transntime})").format(
								key = key, k = k, ofile = ofile, otime = otime,
								transotime = datetime.fromtimestamp(otime), ntime = ntime,
								transntime = datetime.fromtimestamp(ntime)),
							dlevel = timekey, level = 'debug')
				return False
		return True

	def _compareFiles(self, osig, nsig, key, logkey, timekey = True):
		"""Compare files in signature"""
		for k in osig:
			olen = len(osig[k])
			nlen = len(nsig[k])
			if olen != nlen:
				self.logger((
					"Not cached because lengths are different for {key} [files:{k}]:\n" +
					"...... - Previous: {olen}\n" +
					"...... - Current : {nlen}").format(
						key = key, k = k, olen = olen, nlen = nlen),
					dlevel = logkey, level = 'debug')
				return False

			for i in range(olen):
				if nsig[k][i][0] == osig[k][i][0] and nsig[k][i][1] <= osig[k][i][1]:
					# file not changed
					continue
				if nsig[k][i][0] != osig[k][i][0]:
					self.logger((
						"Not cached because file {i} is different for {key} [files:{k}]:\n" +
						"...... - Previous: {ofile}\n" +
						"...... - Current : {nfile}").format(
							i = i + 1, key = key, k = k,
							ofile = osig[k][i][0], nfile = nsig[k][i][0]),
						dlevel = logkey, level = 'debug')
					return False
				if timekey and nsig[k][i][1] > osig[k][i][1]:
					self.logger((
						"Not cached because file {i} is newer for {key} [files:{k}]: {ofile}\n" +
						"...... - Previous: {otime} ({transotime})\n" +
						"...... - Current : {ntime} ({transntime})").format(
							i = i + 1, key = key, k = k,
							ofile = osig[k][i][0], otime = osig[k][i][1],
							transotime = datetime.fromtimestamp(osig[k][i][1]),
							ntime = nsig[k][i][1],
							transntime = datetime.fromtimestamp(nsig[k][i][1])),
						dlevel = timekey, level = 'debug')
					return False
		return True

	# pylint: disable=too-many-return-statements
	def isTrulyCached (self):
		"""@API
		Check whether a job is truly cached (by signature)
		@returns:
			(bool): Whether the job is truly cached.
		"""
		if not self.proc.cache:
			return False

		if not fs.exists(self.dir / FILE_CACHE):
			self.logger("Not cached as cache file not exists.",
				dlevel = "CACHE_SIGFILE_NOTEXISTS", level = 'debug')
			return False

		cachedata = (self.dir / FILE_CACHE).read_text().strip()
		if not cachedata:
			self.logger("Not cached because previous signature is empty.",
				dlevel = "CACHE_EMPTY_PREVSIG", level = 'debug')
			return False

		sig_now = self.signature()
		if not sig_now:
			self.logger("Not cached because current signature is empty.",
				dlevel = "CACHE_EMPTY_CURRSIG", level = 'debug')
			return False

		sig_old = yaml.safe_load(cachedata)

		if not self._compareFile(
			{'script': sig_old['script']},
			{'script': sig_now['script']},
			'script', '', 'CACHE_SCRIPT_NEWER'):
			return False

		procclass    = self.proc.__class__
		intype_var   = procclass.IN_VARTYPE[0]
		if not self._compareVar(
			sig_old['i'][intype_var],
			sig_now['i'][intype_var],
			'input', 'CACHE_SIGINVAR_DIFF'):
			return False

		intype_file  = procclass.IN_FILETYPE[0]
		if not self._compareFile(
			sig_old['i'][intype_file],
			sig_now['i'][intype_file],
			'input', 'CACHE_SIGINFILE_DIFF', 'CACHE_SIGINFILE_NEWER'):
			return False

		intype_files = procclass.IN_FILESTYPE[0]
		if not self._compareFiles(
			sig_old['i'][intype_files],
			sig_now['i'][intype_files],
			'input', 'CACHE_SIGINFILES_DIFF', 'CACHE_SIGINFILES_NEWER'):
			return False

		outype_var   = procclass.OUT_VARTYPE[0]
		if not self._compareVar(
			sig_old['o'][outype_var],
			sig_now['o'][outype_var],
			'output', 'CACHE_SIGOUTVAR_DIFF'):
			return False

		outype_file  = procclass.OUT_FILETYPE[0]
		if not self._compareFile(
			sig_old['o'][outype_file],
			sig_now['o'][outype_file],
			'output', 'CACHE_SIGOUTFILE_DIFF'):
			return False

		outype_dir   = procclass.OUT_DIRTYPE[0]
		if not self._compareFile(
			sig_old['o'][outype_dir],
			sig_now['o'][outype_dir],
			'output dir', 'CACHE_SIGOUTDIR_DIFF'):
			return False

		self.rc = 0
		return True

	def isExptCached (self):
		"""@API
		Prepare to use export files as cached information
		@returns:
			(bool): Whether the job is export-cached.
		"""
		if self.proc.cache != 'export':
			return False

		procclass = self.proc.__class__
		if self.proc.exhow in procclass.EX_LINK:
			self.logger("Job is not export-cached using symlink export.",
				dlevel = "EXPORT_CACHE_USING_SYMLINK", level = "warning")
			return False
		if self.proc.expart and self.proc.expart[0].render(self.data):
			self.logger("Job is not export-cached using partial export.",
				dlevel = "EXPORT_CACHE_USING_EXPARTIAL", level = "warning")
			return False
		if not self.proc.exdir:
			self.logger("Job is not export-cached since export directory is not set.",
				dlevel = "EXPORT_CACHE_EXDIR_NOTSET", level = "warning")
			return False

		exdir = Path(self.proc.exdir)

		for outtype, outdata in self.output.values():
			if outtype in procclass.OUT_VARTYPE:
				continue
			exfile = exdir / outdata.name

			if self.proc.exhow in procclass.EX_GZIP:
				exfile = exfile.with_suffix(exfile.suffix + '.tgz') \
					if fs.isdir(outdata) or outtype in procclass.OUT_DIRTYPE \
					else exfile.with_suffix(exfile.suffix + '.gz')
				with fs.lock(exfile, outdata):
					if not fs.exists(exfile):
						self.logger(
							"Job is not export-cached since exported file not exists: %s" %
							exfile, dlevel = "EXPORT_CACHE_EXFILE_NOTEXISTS", level = "debug")
						return False

					if fs.exists(outdata):
						self.logger('Overwrite file for export-caching: %s' % outdata,
							dlevel = "EXPORT_CACHE_OUTFILE_EXISTS", level = "warning")
					fs.gunzip(exfile, outdata)
			else: # exhow not gzip
				with fs.lock(exfile, outdata):
					if not fs.exists(exfile):
						self.logger(
							"Job is not export-cached since exported file not exists: %s" %
							exfile, dlevel = "EXPORT_CACHE_EXFILE_NOTEXISTS", level = "debug")
						return False
					if fs.samefile(exfile, outdata):
						continue
					if fs.exists(outdata):
						self.logger("Overwrite file for export-caching: %s" % outdata,
							dlevel = "EXPORT_CACHE_OUTFILE_EXISTS", level = "warning")
					fs.link(exfile, outdata)
		self.rc = 0
		self.cache()
		return True

	def cache (self):
		"""@API
		Truly cache the job (by signature)
		"""
		if not self.proc.cache:
			return
		sig  = self.signature()
		if sig:
			sig.to_yaml(filename = self.dir / FILE_CACHE)

	def reset (self):
		"""@API
		Clear the intermediate files and output files"""
		retry    = self.ntry
		retrydir = self.dir / ('retry.' + str(retry))
		#cleanup retrydir
		if retry:
			# will be removed by fs.makedirs
			#fs.remove(retrydir)
			fs.makedirs(retrydir)
		else:
			for retrydir in self.dir.glob('retry.*'):
				fs.remove(retrydir)

		for jobfile in (FILE_RC, FILE_STDOUT, FILE_STDERR, FILE_PID):
			if retry and fs.exists(self.dir / jobfile):
				fs.move(self.dir / jobfile, retrydir / jobfile)
			else:
				fs.remove(self.dir / jobfile)
		# try to keep the cache dir, which, in case, if some program can resume from
		if not fs.exists(self.dir / DIR_OUTPUT / DIR_CACHE):
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

		(self.dir / FILE_STDOUT).write_text('')
		(self.dir / FILE_STDERR).write_text('')

		try:
			fs.makedirs(self.dir / DIR_OUTPUT, overwrite = False)
		except OSError:
			pass
		procclass = self.proc.__class__
		for outtype, outdata in self.output.values():
			if outtype in procclass.OUT_DIRTYPE:
				# it has been moved to retry dir or removed
				fs.makedirs(outdata)
			if outtype in procclass.OUT_STDOUTTYPE:
				fs.link(self.dir / FILE_STDOUT, outdata)
			if outtype in procclass.OUT_STDERRTYPE:
				fs.link(self.dir / FILE_STDERR, outdata)

	def export(self):
		"""@API
		Export the output files"""
		if not self.proc.exdir:
			return
		assert path.exists(self.proc.exdir) and path.isdir(self.proc.exdir), \
			'Export directory has to be a directory.'
		assert isinstance(self.proc.expart, list)

		procclass = self.proc.__class__
		# output files to export
		files2ex = []
		data     = self.data
		if not self.proc.expart or (
			len(self.proc.expart) == 1 and not self.proc.expart[0].render(data)):
			files2ex.extend(Path(outdata)
				for outtype, outdata in self.output.values()
				if outtype not in procclass.OUT_VARTYPE)
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

			self.logger('Exported: %s' % briefPath(exfile, self.proc._log.shorten),
				level = 'EXPORT')

	def succeed(self):
		"""@API
		Tell if a job succeeds.
		Check whether output files generated, expectation met and return code met.
		@return:
			(bool): `True` if succeeds else `False`
		"""
		procclass = self.proc.__class__
		# first check if bare rc is allowed
		if self.rc not in self.proc.rc:
			pluginmgr.hook.jobFail(job = self)
			return False

		# refresh output directory
		# check if output files have been generated
		utime(self.dir / DIR_OUTPUT, None)
		for outtype, outdata in self.output.values():
			if outtype not in procclass.OUT_VARTYPE and not fs.exists(outdata):
				self.rc += (1 << RCBIT_NO_OUTFILE)
				self.logger('Outfile not generated: {}'.format(outdata),
					dlevel = "OUTFILE_NOT_EXISTS", level = 'debug')
				pluginmgr.hook.jobFail(job = self)
				return False

		expect_cmd = self.proc.expect.render(self.data)
		if expect_cmd:
			self.logger('Check expectation: %s' % expect_cmd,
				dlevel = "EXPECT_CHECKING", level = 'debug')
			cmd = cmdy.bash(c = expect_cmd) # pylint: disable=no-member
			if cmd.rc != 0:
				self.rc += (1 << RCBIT_UNMET_EXPECT)
				pluginmgr.hook.jobFail(job = self)
				return False
		return True

	def done(self, cached = False):
		"""@API
		Do some cleanup when job finished
		@params:
			cached (bool): Whether this is running for a cached job.
		"""
		self.logger('Finishing up the job ...', level = 'debug')
		if not cached or self.proc.acache:
			self.export()
		if not cached:
			self.cache()
		pluginmgr.hook.jobPostRun(job = self)

	def isRunningImpl(self):
		"""@API
		Implemetation of telling whether the job is running
		@returns:
			(bool): Should return whether a job is running."""
		raise NotImplementedError()

	def submitImpl(self):
		"""@API
		Implemetation of submission"""
		raise NotImplementedError()

	def killImpl(self):
		"""@API
		Implemetation of killing a job"""
		raise NotImplementedError()

	def submit(self):
		"""@API
		Submit the job
		@returns:
			(bool): `True` if succeeds else `False`"""
		self.logger('Submitting the job ...', level = 'debug')
		if self.isRunningImpl():
			self.logger('is already running at %s, skip submission.' %
				self.pid, level = 'SBMTING')
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
		"""@API
		Check the status of a running job
		@returns:
			(bool|str): `True/False` if rcfile generared and whether job succeeds, \
				otherwise returns `running`.
		"""
		if not fs.isfile(self.dir / FILE_STDERR) or not fs.isfile(self.dir / FILE_STDOUT):
			self.logger('Polling the job ... stderr/out file not generared.', level = 'debug')
			return 'running'

		elif self.rc != RC_NO_RCFILE:
			self.logger('Polling the job ... done.', level = 'debug')
			self._flush(end = True)
			return self.succeed()
		else: # running
			self.logger('Polling the job ... rc file not generated.', level = 'debug')
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
		outfilter = self.proc.echo['type'].get('stdout', '__noout__')
		errfilter = self.proc.echo['type'].get('stderr', '__noerr__')

		if outfilter != '__noout__':
			lines, self.lastout = fileflush(self.fout, self.lastout, end)
			for line in lines:
				if not outfilter or re.search(outfilter, line):
					self.logger(line.rstrip('\n'), level = '_stdout')
		lines, self.lasterr = fileflush(self.ferr, self.lasterr, end)
		for line in lines:
			if line.startswith('pyppl.log'):
				logstr = line.rstrip('\n')[9:].lstrip()
				if ':' not in logstr:
					logstr += ':'
				loglevel, logmsg = logstr.split(':', 1)
				loglevel = loglevel[1:] if loglevel else 'log'
				# '_' makes sure it's not filtered by log levels
				self.logger(logmsg.lstrip(), level = '_' + loglevel)
			elif errfilter != '__noerr__':
				if not errfilter or re.search(errfilter, line):
					self.logger(line.rstrip('\n'), level = '_stderr')

		if end and self.fout and not self.fout.closed:
			self.fout.close()
		if end and self.ferr and not self.ferr.closed:
			self.ferr.close()

	def retry(self):
		"""@API
		If the job is available to retry
		@returns:
			(bool|str): `ignore` if `errhow` is `ignore`, otherwise \
				returns whether we could submit the job to retry.
		"""
		if self.proc.errhow == 'ignore':
			return 'ignored'
		if self.proc.errhow != 'retry':
			return False

		self.ntry += 1
		if self.ntry > self.proc.errntry:
			return False

		self.logger('Retrying {} out of {} time(s) ...'.format(
			str(self.ntry).rjust(len(str(self.proc.errntry)), '0'),
			self.proc.errntry
		), level = 'rtrying')
		return True

	def kill(self):
		"""@API
		Kill the job
		@returns:
			(bool): `True` if succeeds else `False`
		"""
		self.logger('Killing the job ...', level = 'debug')
		try:
			self.killImpl()
			return True
		except: # pylint: disable=bare-except
			self.pid = ''
			return False
