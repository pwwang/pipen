"""job module for PyPPL"""
import re
from os import path, utime, listdir
from datetime import datetime
from threading import Lock
from glob import glob
from collections import OrderedDict
from box import Box
import safefs
from .logger import logger
from .utils import cmdy, string_types, briefPath, filesig, fileflush
from .exceptions import JobInputParseError, JobOutputParseError

class Job(object):
	"""
	PyPPL Job
	@static variables:
		`STATUS_INITIATED`    : Job status when a job has just initiated
		`STATUS_BUILDING`     : Job status when a job is being built
		`STATUS_BUILT`        : Job status when a job has been built
		`STATUS_BUILTFAILED`  : Job status when a job fails to build
		`STATUS_SUBMITTING`   : Job status when a job is submitting
		`STATUS_SUBMITTED`    : Job status when a job has submitted
		`STATUS_SUBMITFAILED` : Job status when a job fails to submit
		`STATUS_RUNNING`      : Job status when a job is running
		`STATUS_RETRYING`     : Job status when a job is about to retry
		`STATUS_DONE`         : Job status when a job has done
		`STATUS_DONECACHED`   : Job status when a job has cached
		`STATUS_DONEFAILED`   : Job status when a job fails temporarily (may retry later)
		`STATUS_ENDFAILED`    : Job status when a job fails finally
		`STATUS_KILLING`      : Job status when a job is being killed
		`STATUS_KILLED`       : Job status when a job has been killed

		`RC_NOTGENERATE` : A return code if no rcfile has been generated
		`RC_SUBMITFAILED`: A return code when a job fails to submit
	"""
	# 0b
	# 1 (0: Job needs running, 1: Job done)
	# 1 (0: Non-killing step, 1: Killing step)
	# 1 (0: Non-building step, 1: Building step)
	# 1 (0: Non-submitting step, 1: Submitting step)
	# 1 (0: Non-running step, 1: Running step)
	# 1 (0: Non-ing, 1: -ing)
	# 1 (0: Sucessded, 1: Failed)
	STATUS_INITIATED    = 0b0000000 # 0
	STATUS_BUILDING     = 0b0010010 # 18
	STATUS_BUILT        = 0b0010000 # 16
	STATUS_BUILTFAILED  = 0b1010001 # 81
	STATUS_SUBMITTING   = 0b0001010 # 10
	STATUS_SUBMITTED    = 0b0001000 # 8
	STATUS_SUBMITFAILED = 0b1001001 # 73
	STATUS_RUNNING      = 0b0000110 # 6
	STATUS_RETRYING     = 0b0000111 # 7
	STATUS_DONE         = 0b1000100 # 68
	STATUS_DONECACHED   = 0b1000000 # 64
	STATUS_DONEFAILED   = 0b0000101 # 5
	STATUS_ENDFAILED    = 0b1000101 # 69
	STATUS_KILLING      = 0b1100010 # 98
	STATUS_KILLED       = 0b1100000 # 96

	RC_NOTGENERATE  = 99
	RC_SUBMITFAILED = 88
	LOGLOCK = Lock()

	def __init__(self, index, config):
		"""
		Initiate a job
		@params:
			`index`:  The index of the job.
			`config`: The configurations of the job.
		"""
		self.index     = index
		self.status    = Job.STATUS_INITIATED
		self.config    = config
		self.dir       = path.abspath(path.join (config['workdir'], str(index + 1)))
		self.indir     = path.join(self.dir, "input")
		self.outdir    = path.join(self.dir, "output")
		self.script    = path.join(self.dir, "job.script")
		self.rcfile    = path.join(self.dir, "job.rc")
		self.outfile   = path.join(self.dir, "job.stdout")
		self.errfile   = path.join(self.dir, "job.stderr")
		self.fout      = None
		self.ferr      = None
		self.lastout   = ''
		self.lasterr   = ''
		self.cachefile = path.join(self.dir, "job.cache")
		self.cachedir  = path.join(self.outdir, '.jobcache')
		self.pidfile   = path.join(self.dir, "job.pid")
		self.ntry      = 0
		self.input     = {}
		# need to pass this to next procs, so have to keep order
		self.output    = OrderedDict()
		self.data      = Box(
			job = Box(
				index    = self.index,   indir    = self.indir,
				outdir   = self.outdir,  dir      = self.dir,
				outfile  = self.outfile, errfile  = self.errfile,
				pidfile  = self.pidfile, cachedir = self.cachedir
			), i = Box(), o = Box()
		)
		self.data.update(self.config.get('procvars', {}))
		self.runner   = None
		self._rc      = None
		self._pid     = None
		self.logger   = logger.bake(
			proc   = self.config['proc'], jobidx = self.index,
			joblen = self.config['procsize'],
		)

	def showError (self, totalfailed):
		"""Show the error message if the job failed."""
		msg   = []
		if self.rc == Job.RC_NOTGENERATE:
			msg.append('Rcfile not generated')
		if self.rc & 0b100000000:
			msg.append('Outfile not generated')
		if self.rc & 0b1000000000:
			msg.append('Expectation not met')
		if self.rc == Job.RC_SUBMITFAILED:
			msg.append('Submission failed')
		msg = ', '.join(msg)
		if self.config['errhow'] == 'ignore':
			self.logger.warning(
				'Failed but ignored (totally {total}). Return code: {rc}{msg}.'.format(
					total = totalfailed, rc = self.rc & 0b0011111111,
					msg   = msg if not msg else ' ({})'.format(msg)))
			return

		self.logger.error('Failed (totally {total}). Return code: {rc}{msg}.'.format(
			total = totalfailed,
			rc    = self.rc & 0b0011111111,
			msg   = msg if not msg else ' ({})'.format(msg)
		))

		from . import Proc
		self.logger.error('Script: {}'.format(briefPath(self.script,  **Proc.SHORTPATH)))
		self.logger.error('Stdout: {}'.format(briefPath(self.outfile, **Proc.SHORTPATH)))
		self.logger.error('Stderr: {}'.format(briefPath(self.errfile, **Proc.SHORTPATH)))

		# errors are not echoed, echo them out
		if self.index not in self.config['echo']['jobs'] or \
			'stderr' not in self.config['echo']['type']:

			self.logger.error('Check STDERR below:')
			errmsgs = []
			if path.exists (self.errfile):
				with open(self.errfile) as ferr:
					errmsgs = [line.rstrip("\n") for line in ferr]

			if not errmsgs:
				errmsgs = ['<EMPTY STDERR>']

			for errmsg in errmsgs[-20:] if len(errmsgs) > 20 else errmsgs:
				self.logger.stderr(errmsg)

			if len(errmsgs) > 20:
				self.logger.stderr('[ Top {top} line(s) ignored, see all in stderr file. ]'.format(
						top = len(errmsgs) - 20))

	def report (self):
		"""Report the job information to logger"""
		from . import Proc
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
			if self.input[key]['type'] in Proc.IN_VARTYPE:
				data = self.input[key]['data']
				if isinstance(data, string_types) and len(data) > 100:
					data = data[:47] + ' ... ' + data[-48:]
				self._reportItem(key, maxlen, data, 'input')
			else:
				if isinstance(self.input[key]['data'], list):
					data = [briefPath(d, **Proc.SHORTPATH) for d in self.input[key]['data']]
				else:
					data = briefPath(self.input[key]['data'], **Proc.SHORTPATH)
				self._reportItem(key, maxlen, data, 'input')

		for key in sorted(self.output.keys()):
			if isinstance(self.output[key]['data'], list):
				data = [briefPath(d, **Proc.SHORTPATH) for d in self.output[key]['data']]
			else:
				data = briefPath(self.output[key]['data'], **Proc.SHORTPATH)
			self._reportItem(key, maxlen, data, 'output')

	def _reportItem(self, key, maxlen, data, loglevel):
		"""
		Report the item on logs
		@params:
			`key`: The key of the item
			`maxlen`: The max length of the key
			`data`: The data of the item
			`loglevel`: The log level
		"""
		logfunc = getattr(self.logger, loglevel)

		if not isinstance(data, list):
			logfunc("{} => {}".format(key.ljust(maxlen), data))
		else:
			ldata = len(data)
			if ldata == 0:
				logfunc("{} => [ {} ]".format(key.ljust(maxlen), ''))
			elif ldata == 1:
				logfunc("{} => [ {} ]".format(key.ljust(maxlen), data[0]))
			elif ldata == 2:
				logfunc("{} => [ {},".format(key.ljust(maxlen), data[0]))
				logfunc("{}      {} ]".format(' '.ljust(maxlen), data[1]))
			elif ldata == 3:
				logfunc("{} => [ {},".format(key.ljust(maxlen), data[0]))
				logfunc("{}      {},".format(' '.ljust(maxlen), data[1]))
				logfunc("{}      {} ]".format(' '.ljust(maxlen), data[2]))
			else:
				logfunc("{} => [ {},".format(key.ljust(maxlen), data[0]))
				logfunc("{}      {},".format(' '.ljust(maxlen), data[1]))
				logfunc("{}      ... ({}),".format(' '.ljust(maxlen), len(data) - 3))
				logfunc("{}      {} ]".format(' '.ljust(maxlen), data[-1]))

	def build(self):
		"""
		Initiate a job, make directory and prepare input, output and script.
		"""
		try:
			if not path.exists(self.dir):
				safefs.makedirs (self.dir)
			# preserve the outfile and errfile of previous run
			# issue #30
			if safefs.exists(self.outfile):
				safefs.move(self.outfile, self.outfile + '.bak')
			if safefs.exists(self.errfile):
				safefs.move(self.errfile, self.errfile + '.bak')
			self._prepInput()
			self._prepOutput()
			if self.index == 0:
				self.report()
			self._prepScript()
			# check cache
			if self.isTrulyCached() or self.isExptCached():
				self.status = Job.STATUS_DONECACHED
				self.done(export = self.config['acache'])
			else:
				self.runner = self.config['runner'](self)
				self.status = Job.STATUS_BUILT
		except Exception:
			from traceback import format_exc
			with open(self.errfile, 'w') as ferr:
				ferr.write(str(format_exc()))
			self.status = Job.STATUS_BUILTFAILED

	def _linkInfile(self, orgfile):
		"""
		Create links for input files
		@params:
			`orgfile`: The original input file
		@returns:
			The link to the original file.
		"""
		basename = path.basename(orgfile)
		infile   = path.join(self.indir, basename)
		try:
			safefs.link(orgfile, infile, overwrite = False)
		except OSError:
			pass
		if safefs.samefile(infile, orgfile):
			return infile

		exist_infiles = [filename for filename in listdir(self.indir)
			if filename.endswith(']' + basename)]
		if not exist_infiles:
			num = 1
		elif len(exist_infiles) < 100:
			num = 0
			for eifile in exist_infiles:
				infile = path.join(self.indir, eifile)
				if safefs.samefile(infile, orgfile):
					return infile
				nexist = int(eifile[1:eifile.find(']')])
				num    = max(num, nexist) + 1
		else: # pragma: no cover
			num = max(int(eifile[1:eifile.find(']')]) for eifile in exist_infiles) + 1

		infile = path.join(self.indir, '[{}]{}'.format(num, basename))
		safefs.link(orgfile, infile)
		return infile

	# pylint: disable=too-many-branches
	def _prepInput (self):
		"""
		Prepare input, create link to input files and set other placeholders
		"""
		from . import Proc
		safefs.remove(self.indir)
		safefs.makedirs(self.indir)

		for key, val in self.config['input'].items():
			self.input[key] = {}
			intype = val['type']
			# the original input file(s)
			indata = val['data'][self.index]
			if intype in Proc.IN_FILETYPE:
				if not isinstance(indata, string_types):
					raise JobInputParseError(
						indata, 'Not a string for input "%s:%s"' % (key, intype))
				if not indata:
					infile  = ''
				elif not path.exists(indata):
					raise JobInputParseError(
						indata, 'File not exists for input "%s:%s"' % (key, intype))
				else:
					indata   = path.abspath(indata)
					basename = path.basename(indata)
					infile   = self._linkInfile(indata)
					if basename != path.basename(infile):
						self.logger.warning("Input file renamed: %s -> %s" %
							(basename, path.basename(infile)), dlevel = 'INFILE_RENAMING')

				self.data['i'][key] = infile

				self.input[key]['type'] = intype
				self.input[key]['data'] = infile

			elif intype in Proc.IN_FILESTYPE:
				self.input[key]['type']       = intype
				self.input[key]['data']       = []
				self.data  ['i'][key]         = []

				if not indata:
					self.logger.warning(
						'No data provided for "{}:{}", use empty list instead.'.format(
							key, intype), dlevel = 'INFILE_EMPTY')
					continue

				if not isinstance(indata, list):
					raise JobInputParseError(
						indata, 'Not a list for input "%s:%s"' % (key, intype))

				for data in indata:
					if not isinstance(data, string_types):
						raise JobInputParseError(
							data, 'Not a string for element of input "%s:%s"' % (key, intype))

					if not data:
						infile  = ''
					elif not path.exists(data):
						raise JobInputParseError(data,
							'File not exists for element of input "%s:%s"' % (key, intype))
					else:
						data     = path.abspath(data)
						basename = path.basename(data)
						infile   = self._linkInfile(data)
						if basename != path.basename(infile):
							self.logger.warning('Input file renamed: {} -> {}'.format(
								basename, path.basename(infile)), dlevel = 'INFILE_RENAMING')

					self.data['i'][key].append(infile)
					self.input[key]['data'].append (infile)
			else:
				self.input[key]['type'] = intype
				self.input[key]['data'] = indata
				self.data['i'][key]    = indata

	def _prepOutput (self):
		"""Build the output data"""
		from . import Proc
		if not path.exists (self.outdir):
			safefs.makedirs (self.outdir)

		output = self.config['output']
		# has to be OrderedDict
		assert isinstance(output, dict)
		# allow empty output
		if not output:
			return
		for key, val in output.items():
			outtype, outtpl = val
			outdata = outtpl.render(self.data)
			self.data['o'][key] = outdata
			self.output[key] = {'type': outtype, 'data': outdata}
			if outtype in Proc.OUT_FILETYPE + Proc.OUT_DIRTYPE + \
				Proc.OUT_STDOUTTYPE + Proc.OUT_STDERRTYPE:
				if path.isabs(outdata):
					raise JobOutputParseError(outdata,
						'Absolute path not allowed for output file/dir for key %s' % repr(key))
				self.output[key]['data'] = path.join(self.outdir, outdata)
				self.data['o'][key] = path.join(self.outdir, outdata)

	def _prepScript (self):
		"""
		Build the script, interpret the placeholders
		"""
		script = self.config['script'].render(self.data)

		write = True
		if path.isfile (self.script):
			with open(self.script) as fscript:
				prevscript = fscript.read()
			if prevscript == script:
				write = False
			else:
				# for debug
				safefs.move(self.script, self.script + '.bak')
				self.logger.debug("Script file updated: %s" %
					self.script, dlevel = 'SCRIPT_EXISTS')
		if write:
			with open (self.script, 'w') as fscript:
				fscript.write(script)

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
		if self._rc is not None and self._rc != Job.RC_NOTGENERATE:
			return self._rc

		if not path.isfile(self.rcfile):
			return Job.RC_NOTGENERATE
		with open(self.rcfile, 'r') as frc:
			returncode = frc.read().strip()
			if not returncode:
				return Job.RC_NOTGENERATE
			return int(returncode)

	@rc.setter
	def rc(self, val): # pylint: disable=invalid-name
		self._rc = val
		with open(self.rcfile, 'w') as frc:
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
		if not path.exists(self.pidfile):
			return ''
		with open(self.pidfile, 'r') as fpid:
			return fpid.read().strip()

	@pid.setter
	def pid(self, val):
		self._pid = str(val)
		with open(self.pidfile, 'w') as fpid:
			fpid.write(str(val))

	# pylint: disable=too-many-return-statements
	def isTrulyCached (self):
		"""
		Check whether a job is truly cached (by signature)
		"""
		if not self.config['cache']:
			return False
		from . import Proc

		if not path.exists(self.cachefile):
			self.logger.debug("Not cached as cache file not exists.",
				dlevel = "CACHE_SIGFILE_NOTEXISTS")
			return False

		with open(self.cachefile) as fcache:
			if not fcache.read().strip():
				self.logger.debug("Not cached because previous signature is empty.",
					dlevel = "CACHE_EMPTY_PREVSIG")
				return False

		sig_old = Box.from_yaml(filename = self.cachefile)
		sig_now = self.signature()
		if not sig_now:
			self.logger.debug("Not cached because current signature is empty.",
				dlevel = "CACHE_EMPTY_CURRSIG")
			return False

		def compareVar(osig, nsig, key, logkey):
			"""Compare var in signature"""
			for k in osig.keys():
				oval = osig[k]
				nval = nsig[k]
				if nval == oval:
					continue
				self.logger.debug((
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
					self.logger.debug((
						"Not cached because {key} file({k}) is different:\n" +
						"...... - Previous: {prev}\n" +
						"...... - Current : {curr}"
					).format(key = key, k = k, prev = ofile, curr = nfile), dlevel = logkey)
					return False
				if timekey and ntime > otime:
					self.logger.debug((
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
						self.logger.debug((
							"Not cached because file {i} is different for {key} files({k}):\n" +
							"...... - Previous: {ofile}\n" +
							"...... - Current : {nfile}"
						).format(
							i = i + 1, key = key, k = k, ofile = ofile, nfile = nfile
						), dlevel = logkey)
						return False
					if timekey and ntime > otime:
						self.logger.debug((
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
			sig_old['i'][Proc.IN_VARTYPE[0]],
			sig_now['i'][Proc.IN_VARTYPE[0]],
			'input',
			'CACHE_SIGINVAR_DIFF'
		): return False
		if not compareFile(
			sig_old['i'][Proc.IN_FILETYPE[0]],
			sig_now['i'][Proc.IN_FILETYPE[0]],
			'input',
			'CACHE_SIGINFILE_DIFF',
			'CACHE_SIGINFILE_NEWER'
		): return False
		if not compareFiles(
			sig_old['i'][Proc.IN_FILESTYPE[0]],
			sig_now['i'][Proc.IN_FILESTYPE[0]],
			'input',
			'CACHE_SIGINFILES_DIFF',
			'CACHE_SIGINFILES_NEWER'
		): return False
		if not compareVar(
			sig_old['o'][Proc.OUT_VARTYPE[0]],
			sig_now['o'][Proc.OUT_VARTYPE[0]],
			'output',
			'CACHE_SIGOUTVAR_DIFF'
		): return False
		if not compareFile(
			sig_old['o'][Proc.OUT_FILETYPE[0]],
			sig_now['o'][Proc.OUT_FILETYPE[0]],
			'output',
			'CACHE_SIGOUTFILE_DIFF'
		): return False
		if not compareFile(
			sig_old['o'][Proc.OUT_DIRTYPE[0]],
			sig_now['o'][Proc.OUT_DIRTYPE[0]],
			'output dir',
			'CACHE_SIGOUTDIR_DIFF'
		): return False
		self.rc = 0 # pylint: disable=invalid-name
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
			self.logger.warning(
				"Job is not export-cached using symlink export.",
				dlevel = "EXPORT_CACHE_USING_SYMLINK")
			return False
		if self.config['expart'] and self.config['expart'][0].render(self.data):
			self.logger.warning("Job is not export-cached using partial export.",
				dlevel = "EXPORT_CACHE_USING_EXPARTIAL")
			return False
		if not self.config['exdir']:
			self.logger.debug("Job is not export-cached since export directory is not set.",
				dlevel = "EXPORT_CACHE_EXDIR_NOTSET")
			return False

		for out in self.output.values():
			if out['type'] in Proc.OUT_VARTYPE:
				continue
			exfile = path.abspath(path.join(self.config['exdir'], path.basename(out['data'])))

			if self.config['exhow'] in Proc.EX_GZIP:
				exfile += '.tgz' if path.isdir(out['data']) or \
					out['type'] in Proc.OUT_DIRTYPE else '.gz'
				with safefs.lock(exfile, out['data']): # pylint: disable=not-context-manager
					exfile_exists  = safefs.exists(exfile)
					outdata_exists = safefs.exists(out['data'])
					outdata_islink = safefs.islink(out['data'])
					if not exfile_exists:
						self.logger.debug(
							"Job is not export-cached since exported file not exists: " +
							"%s." % exfile, dlevel = "EXPORT_CACHE_EXFILE_NOTEXISTS")
						return False

					if outdata_exists or outdata_islink:
						self.logger.warning(
							'Overwrite file for export-caching: %s' % out['data'],
							dlevel = "EXPORT_CACHE_OUTFILE_EXISTS")
					safefs.gunzip(exfile, out['data'])
			else: # exhow not gzip
				with safefs.lock(exfile, out['data']): # pylint: disable=not-context-manager
					exfile_exists  = safefs.exists(exfile)
					outdata_exists = safefs.exists(out['data'])
					outdata_islink = safefs.islink(out['data'])
					if not exfile_exists:
						self.logger.debug(
							"Job is not export-cached since exported file not exists: " +
							"%s." % exfile, dlevel = "EXPORT_CACHE_EXFILE_NOTEXISTS")
						return False
					if safefs.samefile(exfile, out['data']):
						continue
					if outdata_exists or outdata_islink:
						self.logger.warning(
							'Overwrite file for export-caching: %s' % out['data'],
							dlevel = "EXPORT_CACHE_OUTFILE_EXISTS")
					safefs.link(exfile, out['data'])
		self.rc = 0
		return True

	def cache (self):
		"""Truly cache the job (by signature)"""
		if not self.config['cache']:
			return
		sig  = self.signature()
		if sig:
			sig.to_yaml(filename = self.cachefile)

	def reset (self):
		"""Clear the intermediate files and output files"""
		from . import Proc
		retry    = self.ntry
		retrydir = path.join(self.dir, 'retry.' + str(retry))
		#cleanup retrydir
		if retry:
			safefs.remove(retrydir)
			safefs.makedirs(retrydir)
		else:
			for retrydir in glob(path.join(self.dir, 'retry.*')):
				safefs.remove(retrydir)

		for jobfile in (self.rcfile, self.outfile, self.errfile, self.pidfile):
			if retry:
				safefs.move(jobfile, path.join(retrydir, path.basename(jobfile)))
			else:
				safefs.remove(jobfile)
		# try to keep the cache dir, which, in case, if some program can resume from
		if not self.cachedir:
			if retry:
				safefs.move(self.outdir, path.join(retrydir, path.basename(self.outdir)))
			else:
				safefs.remove(self.outdir)
		elif retry:
			retryoutdir = path.join(retrydir, path.basename(self.outdir))
			safefs.makedirs(retryoutdir)
			# move everything to retrydir but the cachedir
			for filename in listdir(self.outdir):
				if filename == path.basename(self.cachedir):
					continue
				safefs.move(path.join(self.outdir, filename), path.join(retryoutdir, filename))
		else:
			for filename in listdir(self.outdir):
				if filename == path.basename(self.cachedir):
					continue
				safefs.remove(path.join(self.outdir, filename))

		open(self.outfile, 'w').close()
		open(self.errfile, 'w').close()

		try:
			safefs.makedirs(self.outdir, overwrite = False)
		except OSError:
			pass
		for out in self.output.values():
			if out['type'] in Proc.OUT_DIRTYPE:
				try:
					safefs.makedirs(out['data'], overwrite = False)
				except OSError:
					pass
			if out['type'] in Proc.OUT_STDOUTTYPE:
				safefs.link(self.outfile, out['data'])
			if out['type'] in Proc.OUT_STDERRTYPE:
				safefs.link(self.errfile, out['data'])

	def export(self):
		"""Export the output files"""
		if not self.config['exdir']:
			return

		assert path.exists(self.config['exdir'])
		assert isinstance(self.config['expart'], list)

		from . import Proc
		# output files to export
		files2ex = []
		if not self.config['expart'] or (len(self.config['expart']) == 1 \
			and not self.config['expart'][0].render(self.data)):
			for out in self.output.values():
				if out['type'] in Proc.OUT_VARTYPE:
					continue
				files2ex.append (out['data'])
		else:
			for expart in self.config['expart']:
				expart = expart.render(self.data)
				if expart in self.output:
					files2ex.append(self.output[expart]['data'])
				else:
					files2ex.extend(glob(path.join(self.outdir, expart)))

		files2ex  = set(files2ex)
		for file2ex in files2ex:
			bname  = path.basename (file2ex)
			# exported file
			exfile = path.join(self.config['exdir'], bname)
			if self.config['exhow'] in Proc.EX_GZIP:
				exfile += '.tgz' if path.isdir(file2ex) else '.gz'

			with safefs.exists(file2ex, _context = True), \
				safefs.exists(exfile, _context = True):

				if self.config['exhow'] in Proc.EX_GZIP:
					safefs.gzip(file2ex, exfile, overwrite = self.config['exow'])
				elif self.config['exhow'] in Proc.EX_COPY:
					safefs.copy(file2ex, exfile, overwrite = self.config['exow'])
				elif self.config['exhow'] in Proc.EX_LINK:
					safefs.link(file2ex, exfile, overwrite = self.config['exow'])
				else: # move
					if safefs.islink(file2ex):
						safefs.copy(file2ex, exfile, overwrite = self.config['exow'])
					else:
						safefs.move(file2ex, exfile, overwrite = self.config['exow'])
						safefs.link(exfile, file2ex)

			self.logger.export('Exported: {}'.format(briefPath(exfile, **Proc.SHORTPATH)))

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
			if out['type'] in Proc.OUT_VARTYPE:
				continue
			if not path.exists(out['data']):
				self.rc |= 0b100000000
				self.logger.debug('Outfile not generated: {}'.format(out['data']),
					dlevel = "OUTFILE_NOT_EXISTS")
		expect_cmd = self.config['expect'].render(self.data)

		if expect_cmd:
			self.logger.debug('Check expectation: %s' % expect_cmd, dlevel = "EXPECT_CHECKING")
			cmd = cmdy.bash(c = expect_cmd)
			if cmd.rc != 0:
				self.rc |= 0b1000000000
		return self.rc in self.config['rcs']

	def done(self, export = True):
		"""
		Do some cleanup when job finished
		@params:
			`export`: Whether do export
		"""
		if export:
			self.export()
		self.cache()

	def signature (self):
		"""
		Calculate the signature of the job based on the input/output and the script
		@returns:
			The signature of the job
		"""
		from . import Proc
		ret = Box()
		sig = filesig(self.script)
		if not sig:
			self.logger.debug('Empty signature because of script file: %s.' %
				self.script, dlevel = "CACHE_EMPTY_CURRSIG")
			return ''
		ret.script = sig
		ret.i = {Proc.IN_VARTYPE[0]: {}, Proc.IN_FILETYPE[0]: {}, Proc.IN_FILESTYPE[0]: {}}
		ret.o = {Proc.OUT_VARTYPE[0]: {}, Proc.OUT_FILETYPE[0]: {}, Proc.OUT_DIRTYPE[0]: {}}
		for key, val in self.input.items():
			if val['type'] in Proc.IN_VARTYPE:
				ret.i[Proc.IN_VARTYPE[0]][key] = val['data']
			elif val['type'] in Proc.IN_FILETYPE:
				sig = filesig(val['data'], dirsig = self.config['dirsig'])
				if not sig:
					self.logger.debug(
						'Empty signature because of input file: %s.' % val['data'],
						dlevel = "CACHE_EMPTY_CURRSIG")
					return ''
				ret.i[Proc.IN_FILETYPE[0]][key] = sig
			elif val['type'] in Proc.IN_FILESTYPE:
				ret.i[Proc.IN_FILESTYPE[0]][key] = []
				for infile in sorted(val['data']):
					sig = filesig(infile, dirsig = self.config['dirsig'])
					if not sig:
						self.logger.debug(
							'Empty signature because of one of input files: %s.' % infile,
							dlevel = "CACHE_EMPTY_CURRSIG")
						return ''
					ret.i[Proc.IN_FILESTYPE[0]][key].append (sig)
		for key, val in self.output.items():
			if val['type'] in Proc.OUT_VARTYPE:
				ret.o[Proc.OUT_VARTYPE[0]][key] = val['data']
			elif val['type'] in Proc.OUT_FILETYPE:
				sig = filesig(val['data'], dirsig = self.config['dirsig'])
				if not sig:
					self.logger.debug(
						'Empty signature because of output file: %s.' % val['data'],
						dlevel = "CACHE_EMPTY_CURRSIG")
					return ''
				ret.o[Proc.OUT_FILETYPE[0]][key] = sig
			elif val['type'] in Proc.OUT_DIRTYPE:
				sig = filesig(val['data'], dirsig = self.config['dirsig'])
				if not sig:
					self.logger.debug(
						'Empty signature because of output dir: %s.' % val['data'],
						dlevel = "CACHE_EMPTY_CURRSIG")
					return ''
				ret.o[Proc.OUT_DIRTYPE[0]][key] = sig
		return ret

	def submit(self):
		"""Submit the job"""
		if self.runner.isRunning():
			self.logger.submit(
				'is already running at {pid}, skip submission.'.format(pid = self.pid))
			return True
		self.reset()
		rscmd = self.runner.submit()
		if rscmd.rc == 0:
			return True
		self.logger.error(
			'Submission failed (rc = {rscmd.rc}, cmd = {rscmd.cmd})\n{rscmd.stderr}'.format(
				rscmd = rscmd), dlevel = 'SUBMISSION_FAIL')
		return False

	def poll(self):
		"""Check the status of a running job"""
		if not path.isfile(self.errfile) or not path.isfile(self.outfile):
			self.status = Job.STATUS_RUNNING
		elif self.rc != Job.RC_NOTGENERATE:
			self._flush(end = True)
			if self.succeed():
				self.done()
				self.status = Job.STATUS_DONE
			else:
				self.status = Job.STATUS_DONEFAILED
		else: # running
			self._flush()
			self.status = Job.STATUS_RUNNING

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
		if self.index not in self.config['echo']['jobs']:
			return
		self.fout = self.fout or open(self.outfile)
		self.ferr = self.ferr or open(self.errfile)
		if 'stdout' in self.config['echo']['type']:
			lines, self.lastout = fileflush(self.fout, self.lastout, end)
			outfilter = self.config['echo']['type']['stdout']
			for line in lines:
				if not outfilter or re.search(outfilter, line):
					self.logger._stdout(line.rstrip('\n'))
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
			elif 'stderr' in self.config['echo']['type']:
				errfilter = self.config['echo']['type']['stderr']
				if not errfilter or re.search(errfilter, line):
					self.logger._stderr(line.rstrip('\n'))
		if end and self.fout:
			self.fout.close()
		if end and self.ferr:
			self.ferr.close()

	def retry(self):
		"""
		If the job is available to retry
		@return:
			`True` if it is else `False`
		"""
		# if job is not running or job hasn't failed
		if not self.status & 0b100 or not self.status & 0b1:
			return False
		if self.config['errhow'] == 'halt':
			self.status = Job.STATUS_ENDFAILED
			return 'halt'
		if self.config['errhow'] != 'retry':
			self.status = Job.STATUS_ENDFAILED
			return False
		if self.ntry >= self.config['errntry']:
			self.status = Job.STATUS_ENDFAILED
			return False
		self.status  = Job.STATUS_RETRYING
		self.ntry   += 1
		self.rc      = Job.RC_NOTGENERATE
		self.pid     = ''
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
