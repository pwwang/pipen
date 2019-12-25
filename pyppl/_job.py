"""Implementations for Job"""
from pathlib import Path
import cmdy
from diot import Diot, OrderedDiot
from .logger import logger
from .runner import runnermgr
from .utils import chmod_x, fs, filesig
from .exception import JobInputParseError, JobOutputParseError
from ._proc import OUT_VARTYPE, OUT_FILETYPE, \
	OUT_DIRTYPE, OUT_STDOUTTYPE, OUT_STDERRTYPE, \
	IN_VARTYPE, IN_FILETYPE,IN_FILESTYPE

# pylint: disable=unused-argument

RC_NO_RCFILE = 511

def _link_infile(orgfile, indir):
	"""
	Create links for input files
	@params:
		`orgfile`: The original input file
	@returns:
		The link to the original file.
	"""
	infile = indir / orgfile.name
	try:
		fs.link(orgfile, infile, overwrite = False)
	except OSError:
		pass

	if fs.samefile(infile, orgfile):
		return infile

	exist_infiles = (indir).glob('[[]*[]]*')
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

	infile = indir / '[{}]{}'.format(num + 1, orgfile.name)
	fs.link(orgfile, infile)
	return infile

def job_dir(this, value):
	"""Try to create job dir when access it"""
	ret = this.proc.workdir.joinpath(str(this.index + 1)).resolve()
	if not ret.is_dir():
		ret.mkdir(exist_ok = True)
	return ret

def job_input(this, value): # pylint: disable=too-many-branches
	"""
	Prepare input, create link to input files and set other placeholders
	"""
	#fs.remove(this.dir / 'input')
	# fs.makedirs will clean existing dir
	fs.makedirs(this.dir / 'input')
	ret = OrderedDiot()
	for key, val in this.proc.input.items():
		# the original input file(s)
		key = key.strip()
		intype, indata = val[0], val[1][this.index]
		if intype in IN_FILETYPE:
			if not isinstance(indata, (Path, str)):
				raise JobInputParseError(
					'Not a string or path for input [%s:%s]: %r' % (key, intype, indata))
			if not indata: # allow empty input
				infile  = ''
			elif not fs.exists(indata):
				raise JobInputParseError(
					'File not exists for input [%s:%s]: %r' % (key, intype, indata))
			else:
				indata = Path(indata).resolve()
				infile = _link_infile(indata, this.dir / 'input')

				if indata.name != infile.name:
					this.logger("Input file renamed: %s -> %s" %
						(indata.name, infile.name),
						slevel = 'INFILE_RENAMING', level = "warning")
			ret[key] = (intype, str(infile))

		elif intype in IN_FILESTYPE:
			ret[key] = (intype, [])

			if not indata:
				this.logger(
					'No data provided for [%s:%s], use empty list instead.' %
					(key, intype), slevel = 'INFILE_EMPTY', level = "warning")
				continue

			if not isinstance(indata, list):
				raise JobInputParseError(
					'Not a list for input [%s:%s]: %r' % (key, intype, indata))

			for data in indata:
				if not isinstance(data, (Path, str)):
					raise JobInputParseError(
						'Not a string or path as an element of input [%s:%s]: %r' % (
							key, intype, data))

				if not data:
					infile  = ''
				elif not fs.exists(data):
					raise JobInputParseError(
						'File not exists as an element of input [%s:%s]: %r' % (
							key, intype, data))
				else:
					data   = Path(data).resolve()
					infile = _link_infile(data, this.dir / 'input')
					if data.name != infile.name:
						this.logger('Input file renamed: %s -> %s' %
							(data.name, infile.name),
							slevel = 'INFILE_RENAMING', level = "warning")
				ret[key][1].append(str(infile))
		else:
			ret[key] = (intype, indata)
		this.data.i[key] = indata
	return ret

def job_output(this, value):
	"""Build the output data"""
	# keep the output dir if exists
	if not fs.exists (this.dir / 'output'):
		fs.makedirs (this.dir / 'output')

	output = this.proc.output
	# has to be OrderedDict
	assert isinstance(output, dict)
	ret = OrderedDiot()
	# allow empty output
	if not output:
		return ret
	for key, val in output.items():
		outtype, outtpl = val
		outdata = outtpl.render(this.data)
		#this.output[key] = {'type': outtype, 'data': outdata}
		if outtype in OUT_FILETYPE + OUT_DIRTYPE + \
			OUT_STDOUTTYPE + OUT_STDERRTYPE:
			if Path(outdata).is_absolute():
				raise JobOutputParseError(
					'Absolute path not allowed for [%s:%s]: %r' % (key, outtype, outdata))
			ret[key] = (outtype, this.dir / 'output' / outdata)
		else:
			ret[key] = (outtype, outdata)
		this.data.o[key] = str(this.dir / 'output' / outdata)
	return ret

def job_signature(this, value):
	"""@API
	Calculate the signature of the job based on the input/output and the script.
	If file does not exist, it will not be in the signature.
	The signature is like:
	```json
	{
		"i": {
			"invar:var": <invar>,
			"infile:file": <infile>,
			"infiles:files": [<infiles...>]
		},
		"o": {
			"outvar:var": <outvar>,
			"outfile:file": <outfile>,
			"outdir:dir": <outdir>
		}
		"mtime": <max mtime of input and script>,
	}
	```
	@returns:
		(Diot): The signature of the job
	"""
	script_sig = filesig(this.dir / 'job.script')
	ret = Diot(
		i = {}, o = {},
		mtime = script_sig[1] if script_sig else 0
	)

	for key, val in this.input.items():
		(datatype, data) = val
		if datatype in IN_FILETYPE:
			sig = filesig(data, dirsig = this.proc.dirsig)
			if not sig:
				continue
			ret.mtime = max(ret.mtime, sig[1])
			ret.i[key + ":" + IN_FILETYPE[0]] = sig[0]
		elif datatype in IN_FILESTYPE:
			ret.i[key + ":" + IN_FILESTYPE[0]] = []
			for infile in sorted(data):
				sig = filesig(infile, dirsig = this.proc.dirsig)
				if not sig:
					continue
				ret.mtime = max(ret.mtime, sig[1])
				ret.i[key + ":" + IN_FILESTYPE[0]].append(sig[0])
		else:
			ret.i[key + ":" + IN_VARTYPE[0]] = str(data)

	for key, val in this.output.items():
		(datatype, data) = val
		if datatype in OUT_VARTYPE:
			ret.o[key + ":" + OUT_VARTYPE[0]] = str(data)
			continue
		if not fs.exists(data):
			continue
		key += ':'
		key += OUT_FILETYPE[0] if datatype in OUT_FILETYPE else OUT_DIRTYPE[0]
		ret.o[key] = str(data)
	return ret

def job_rc_setter(this, value):
	"""Try to save the returncode while set it to job.rc"""
	if value is not None:
		with (this.dir / 'job.rc').open('w') as frc:
			frc.write(str(value))

def job_rc_getter(this, value):
	"""Try to read the returncode from job.rc file"""
	if not fs.isfile(this.dir / 'job.rc'):
		return RC_NO_RCFILE
	with (this.dir / 'job.rc').open('r') as frc:
		returncode = frc.read().strip()
		if not returncode or returncode == 'None':
			return RC_NO_RCFILE
		return int(returncode)

def job_data(this, value):
	"""
	Data for rendering templates
	@returns:
		(dict): The data used to render the templates.
	"""
	return Diot(
		job = dict(
			index    = this.index,
			indir    = str(this.dir / 'input'),
			outdir   = str(this.dir / 'output'),
			dir      = str(this.dir),
			outfile  = str(this.dir / 'job.stdout'),
			errfile  = str(this.dir / 'job.stderr'),
			pidfile  = str(this.dir / 'job.pid'),
			cachedir = str(this.dir / 'output/.jobcache')),
		i    = {},
		o    = {},
		proc = this.proc,
		args = this.proc.args)

def job_script(this, value):
	"""Try to create the script while accessing it"""
	scriptfile = this.dir.joinpath('job.script.' + this.runner)
	this.logger('Wrapping up script: %s' % scriptfile, level = 'debug')
	script_parts = this.script_parts

	# redirect stdout and stderr
	if script_parts.saveoe:
		if isinstance(script_parts.command, list):
			script_parts.command[-1] += ' 1> %s 2> %s' % (
				cmdy._shquote(str(this.dir / 'job.stdout')),
				cmdy._shquote(str(this.dir / 'job.stderr')))
		else:
			script_parts.command += ' 1> %s 2> %s' % (
				cmdy._shquote(str(this.dir / 'job.stdout')),
				cmdy._shquote(str(this.dir / 'job.stderr')))

	src       = ['#!/usr/bin/env bash']
	srcappend = src.append
	srcextend = src.extend
	addsrc    = lambda code: (srcextend if isinstance(code, list) else \
		srcappend)(code) if code else None

	addsrc(script_parts.header)
	addsrc('#')
	addsrc('# Collect return code on exit')

	trapcmd  = "status=\\$?; echo \\$status > {!r}; ".format(str(this.dir / 'job.rc'))
	# make sure stdout/err has been created when script exits.
	trapcmd += "if [ ! -e {0!r} ]; then touch {0!r}; fi; ".format(str(this.dir / 'job.stdout'))
	trapcmd += "if [ ! -e {0!r} ]; then touch {0!r}; fi; ".format(str(this.dir / 'job.stderr'))
	trapcmd += "exit \\$status"
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

	scriptfile.write_text('\n'.join(src))
	return chmod_x(scriptfile)

def job_script_parts(this, value):
	"""Allow runners to modify the script parts"""
	script = this.proc.script.render(this.data)
		# real script file
	realsfile = this.dir / 'job.script'
	if fs.isfile(realsfile) and realsfile.read_text() != script:
		fs.move(realsfile, this.dir / 'job.script._bak')
		this.logger("Script file updated: %s" % realsfile,
			slevel = 'SCRIPT_EXISTS', level = 'debug')
		realsfile.write_text(script)
	elif not fs.isfile(realsfile):
		realsfile.write_text(script)

	base = Diot(header = '',
		pre = this.proc.runner.get(this.runner + '_prescript', ''),
		post = this.proc.runner.get(this.runner + '_postscript', ''),
		saveoe = True,
		command = [cmdy._shquote(x) for x in chmod_x(realsfile)]
	)
	ret = runnermgr.hook.script_parts(job = this, base = base)
	return ret or base

def job_logger(this, value):
	"""@API
	A logger wrapper to avoid instanize a logger object for each job
	@params:
		*args (str): messages to be logged.
		*kwargs: Other parameters for the logger.
	"""
	def _logger(*args, **kwargs):
		level = kwargs.pop('level', 'info')
		kwargs['proc']   = this.proc.shortname
		kwargs['jobidx'] = this.index
		kwargs['joblen'] = this.proc.size
		if kwargs.pop('pbar', False):
			logger.pbar[level](*args, **kwargs)
		else:
			logger[level](*args, **kwargs)
	return _logger

def job_pid_setter(this, value):
	"""Try to save the pid while setting it to job.pid"""
	if value is None:
		return ''
	this.dir.joinpath('job.pid').write_text(str(value))
	return str(value)

def job_pid_getter(this, value):
	"""Try to read the pid from job.pid"""
	if not this.dir.joinpath('job.pid').is_file():
		return ''
	return this.dir.joinpath('job.pid').read_text().strip()
