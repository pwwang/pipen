"""Job for PyPPL"""
import attr
import toml
from attr_property import attr_property_class, attr_property
from diot import Diot
from .runner import runnermgr, current_runner
from .plugin import pluginmgr, PluginConfig
from .utils import fs, filesig
from ._proc import OUT_DIRTYPE, OUT_STDOUTTYPE, OUT_STDERRTYPE, OUT_VARTYPE
from ._job import job_dir, job_input, job_output, job_signature, \
	job_rc_setter, job_rc_getter, job_data, job_script, job_logger, \
	job_pid_setter, job_pid_getter, job_script_parts, RC_NO_RCFILE

@attr_property_class
@attr.s(slots = True)
class Job:
	"""@API
	Job class

	@arguments:
		index (int): The index of the job
		proc (Proc): The process
	"""

	index = attr.ib()
	proc = attr.ib()

	# allow state machine to add attributes
	__dict__ = attr.ib(
		init = False,
		repr = False)

	# the job directory
	dir = attr_property(
		init   = False,
		repr   = False,
		getter = job_dir,
		doc    = 'The directory of the job.')
	# max number of retries
	ntry = attr.ib(
		default = 0,
		init    = False,
		repr    = False)
	# the compiled input
	input = attr_property(
		init   = False,
		repr   = False,
		getter = job_input)
	# the compiled output
	output = attr_property(
		init   = False,
		repr   = False,
		getter = job_output)
	# the compiled script
	script = attr_property(
		init   = False,
		repr   = False,
		getter = job_script)
	# parts of the script for runner
	script_parts = attr_property(
		init   = False,
		repr   = False,
		getter = job_script_parts)
	# the signature of the job
	signature = attr_property(
		init   = False,
		repr   = False,
		getter = job_signature)
	# the returncode of the job
	rc = attr_property(
		init   = False,
		repr   = False,
		setter = job_rc_setter,
		getter = job_rc_getter,
		doc    = 'The returncode of the job.')
	# the pid or job id in runner system
	pid = attr_property(
		init   = False,
		repr   = False,
		getter = job_pid_getter,
		setter = job_pid_setter,
		doc    = 'The pid/job id of the job in the running system.')
	# current runner name
	# make sure use_runner was called before class definitions
	runner = attr_property(
		init   = False,
		repr   = False,
		getter = lambda this, value: current_runner(),
		doc    = 'The name of current runner.')
	# data to render templates
	data = attr_property(
		init   = False,
		repr   = False,
		getter = job_data,
		doc    = 'The data used to render templates.')
	# job logger
	logger = attr_property(
		init   = False,
		repr   = False,
		getter = job_logger)
	# configs for plugins
	plugin_config = attr.ib(
		default = attr.Factory(PluginConfig),
		kw_only = True,
		repr    = False)

	def __attrs_post_init__(self):
		pluginmgr.hook.job_init(job = self)

	def add_config(self, name, default = None, converter = None):
		"""@API
		Add a config to plugin config, used for plugins
		@params:
			name (str): The name of the config.
				To proptect your config, better use a prefix
			default (Any): The default value for the config
			converter (callable): The converter for the value
		"""
		self.plugin_config.add(name, default, converter)

	def cache(self):
		"""@API
		Truly cache the job (by signature)
		"""
		if self.proc.cache:
			self.signature.to_toml(filename = self.dir / 'job.cache')

	def _is_cached_without_cachefile(self):
		# check if outfiles/dirs are newer than any input files/dirs
		for datatype, data in self.output.values():
			if datatype in OUT_VARTYPE:
				continue
			sig = filesig(data, dirsig = self.proc.dirsig and datatype in OUT_DIRTYPE)
			if sig[1] < self.signature.mtime:
				return False
		return True

	def is_cached(self):
		"""Tell if the job is cached
		@returns:
			(bool): True if the job is cached else False
		"""
		if not self.proc.cache or not self.is_succeeded():
			self.logger('Not cached as proc.cache is False or job failed.',
						slevel = "CACHE_FAILED", level = 'debug')
			return False

		if not self.dir.joinpath('job.cache').is_file():
			return self._is_cached_without_cachefile()

		sig_now = self.signature
		with open(self.dir.joinpath('job.cache')) as fcache:
			sig_old = Diot(toml.load(fcache))
		# time is easy to check, check it first
		if sig_now.mtime > sig_old.mtime:
			self.logger('Input or script has been modified.',
						slevel = "CACHE_INPUT_MODIFIED", level = 'debug')
			return False

		# check items
		if list(sig_now.i.keys()) != list(sig_old.i.keys()):
			additional= [key for key in sig_now.i if key not in sig_old.i]
			if additional:
				self.logger('Additional input items found: %s.' % additional,
						slevel = "CACHE_INPUT_MODIFIED", level = 'debug')
				return False
			missing = [key for key in sig_old.i if key not in sig_now.i]
			if missing:
				self.logger('Missing input items: %s.' % missing,
						slevel = "CACHE_INPUT_MODIFIED", level = 'debug')
				return False
		elif sig_now.i != sig_old.i:
			diff_key = [key for key in sig_now.i
				if sig_now.i[key] != sig_old.i[key]][0]
			self.logger('Input item %r changed: %s -> %s' % (
				diff_key, sig_old.i[diff_key], sig_now.i[diff_key]),
				slevel = "CACHE_INPUT_MODIFIED", level = 'debug')
			return False

		if list(sig_now.o.keys()) != list(sig_old.o.keys()):
			additional= [key for key in sig_now.o if key not in sig_old.o]
			if additional:
				self.logger('Additional output items found: %s.' % additional,
						slevel = "CACHE_OUTPUT_MODIFIED", level = 'debug')
				return False
			missing = [key for key in sig_old.o if key not in sig_now.o]
			if missing:
				self.logger('Missing output items: %s.' % missing,
						slevel = "CACHE_OUTPUT_MODIFIED", level = 'debug')
				return False
		elif sig_now.o != sig_old.o:
			diff_key = [key for key in sig_now.o
				if sig_now.o[key] != sig_old.o[key]][0]
			self.logger('Output item %r changed: %s -> %s' % (
				diff_key, sig_old.o[diff_key], sig_now.o[diff_key]),
				slevel = "CACHE_OUTPUT_MODIFIED", level = 'debug')
			return False
		return True

	def build(self):
		"""@API
		Initiate a job, make directory and prepare input, output and script.
		"""
		self.logger('Builing the job ...', level = 'debug')
		try:
			# trigger input/output/script building
			self.input  # pylint: disable=pointless-statement
			self.output # pylint: disable=pointless-statement
			self.script # pylint: disable=pointless-statement

			pluginmgr.hook.job_prebuild(job = self)
			# check cache
			outfile = self.dir / 'job.stdout'
			errfile = self.dir / 'job.stderr'
			if self.is_cached():
				# we should get stdout/err file back, since job is cached,
				# there is no way to generate new stdout/err,
				# in case they are used somewhere later.
				# we just link them back
				if not fs.exists(outfile):
					outfile.write_text('')
				if not fs.exists(errfile):
					errfile.write_text('')
				pluginmgr.hook.job_build(job = self, status = 'cached')
				return 'cached'

			outfile_bak = self.dir / 'job.stdout.bak'
			errfile_bak = self.dir / 'job.stderr.bak'
			# preserve the outfile and errfile of previous run
			# issue #30
			if fs.exists(outfile):
				fs.move(outfile, outfile_bak)
				outfile.write_text('')
			if fs.exists(errfile):
				fs.move(errfile, errfile_bak)
				errfile.write_text('')

			pluginmgr.hook.job_build(job = self, status = 'succeeded')
			return True
		except BaseException as ex:
			self.logger('Failed to build job: %s: %s' % (type(ex).__name__, ex), level = 'debug')
			from traceback import format_exc
			with (self.dir / 'job.stderr').open('w') as ferr:
				ferr.write(str(format_exc()))
			pluginmgr.hook.job_build(job = self, status = 'failed')
			return False

	def is_succeeded(self):
		"""See if the job is successfully done
		Allow plugins to override the status
		By default, we just do a simple check to see if
		the return code is 0
		"""
		ret = pluginmgr.hook.job_succeeded(job = self)
		if ret and any(state is False for state in ret):
			return False
		return self.rc == 0

	def done(self, cached = False, status = True):
		"""@API
		Do some cleanup when job finished
		@params:
			cached (bool): Whether this is running for a cached job.
		"""
		self.logger('Finishing up the job ...', level = 'debug')

		if cached:
			pluginmgr.hook.job_done(job = self, status = 'cached')

		if status:
			self.cache()

		pluginmgr.hook.job_done(job = self, status = 'succeeded' if status else 'failed')

	def reset (self): # pylint: disable=too-many-branches
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

		for jobfile in ('job.rc', 'job.stdout', 'job.stderr', 'job.pid', 'job.cache'):
			if retry and fs.exists(self.dir / jobfile):
				fs.move(self.dir / jobfile, retrydir / jobfile)
			else:
				fs.remove(self.dir / jobfile)
		# try to keep the cache dir, which, in case, if some program can resume from
		if not fs.exists(self.dir / 'output/.jobcache'):
			if retry:
				fs.move(self.dir / 'output', retrydir / 'output')
			else:
				fs.remove(self.dir / 'output')
		elif retry:
			retryoutdir = retrydir / 'output'
			fs.makedirs(retryoutdir)
			# move everything to retrydir but the cachedir
			for outfile in (self.dir / 'output').glob('*'):
				if outfile.name == '.jobcache':
					continue
				fs.move(outfile, retryoutdir / outfile.name)
		else:
			for outfile in (self.dir / 'output').glob('*'):
				if outfile.name == '.jobcache':
					continue
				fs.remove(outfile)

		(self.dir / 'job.stdout').write_text('')
		(self.dir / 'job.stderr').write_text('')

		try:
			fs.makedirs(self.dir / 'output', overwrite = False)
		except OSError:
			pass

		for outtype, outdata in self.output.values():
			if outtype in OUT_DIRTYPE:
				# it has been moved to retry dir or removed
				fs.makedirs(outdata)
			if outtype in OUT_STDOUTTYPE:
				fs.link(self.dir / 'job.stdout', outdata)
			if outtype in OUT_STDERRTYPE:
				fs.link(self.dir / 'job.stderr', outdata)

	def submit(self):
		"""@API
		Submit the job
		@returns:
			(bool): `True` if succeeds else `False`"""
		self.logger('Submitting the job ...', level = 'debug')
		# If I am retrying, submit the job anyway.
		if self.ntry == 0 and runnermgr.hook.isrunning(job = self):
			self.logger('is already running at %s, skip submission.' %
				self.pid, level = 'SBMTING')
			pluginmgr.hook.job_submit(job = self, status = 'running')
			return True
		self.reset()
		rscmd = runnermgr.hook.submit(job = self)
		if rscmd.rc == 0:
			pluginmgr.hook.job_submit(job = self, status = 'succeeded')
			return True
		self.logger(
			'Submission failed (rc = {rscmd.rc}, cmd = {rscmd.cmd})\n{rscmd.stderr}'.format(
				rscmd = rscmd), slevel = 'SUBMISSION_FAIL', level = 'error')
		pluginmgr.hook.job_submit(job = self, status = 'failed')
		return False

	def poll(self):
		"""@API
		Check the status of a running job
		@returns:
			(bool|str): `True/False` if rcfile generared and whether job succeeds, \
				otherwise returns `running`.
		"""
		# force to read rc from rcfile
		del self.rc

		if not self.dir.joinpath('job.stderr').is_file() or \
			not self.dir.joinpath('job.stdout').is_file():
			self.logger('Polling the job ... stderr/out file not generared.', level = 'debug')
			pluginmgr.hook.job_poll(job = self, status = 'running')
			return 'running'

		if self.rc != RC_NO_RCFILE:
			self.logger('Polling the job ... done.', level = 'debug')
			pluginmgr.hook.job_poll(job = self, status = 'done')
			return self.is_succeeded()
		# running
		self.logger('Polling the job ... rc file not generated.', level = 'debug')
		pluginmgr.hook.job_poll(job = self, status = 'running')
		return 'running'

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
			status = runnermgr.hook.kill(job = self)
		except BaseException:
			self.pid = ''
			pluginmgr.hook.job_poll(job = self, status = 'failed')
			return False

		if status:
			self.pid = ''
		pluginmgr.hook.job_kill(job = self, status = 'succeeded' if status else 'failed')
		return status
