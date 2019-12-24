"""Implementations for Proc"""

import sys
import uuid
from pathlib import Path
import cmdy
from simpleconf import NoSuchProfile
from diot import OrderedDiot, Diot
from liquid.stream import LiquidStream
from . import template
from .runner import use_runner
from .config import config
from .exception import ProcessAttributeError, ProcessInputError, \
	ProcessOutputError, ProcessScriptError
from .channel import Channel
from .logger import logger
from .utils import funcsig, always_list, fs

# pylint: disable=unused-argument

OUT_VARTYPE    = ['var']
OUT_FILETYPE   = ['file', 'path']
OUT_DIRTYPE    = ['dir', 'folder']
OUT_STDOUTTYPE = ['stdout']
OUT_STDERRTYPE = ['stderr']

IN_VARTYPE   = ['var']
IN_FILETYPE  = ['file', 'path', 'dir', 'folder']
IN_FILESTYPE = ['files', 'paths', 'dirs', 'folders']

def _require(this, name, strict = True, msg = None):
	"""
	strict:
		True: any falsy values not allowed
		False: only None not allowed
	"""
	if not hasattr(this, name):
		raise ProcessAttributeError(msg or \
			'Process has no such attribute {!r}.'.format(name))
	value = getattr(this, name)
	if (strict and not value) or value is None:
		raise ProcessAttributeError(msg or \
			'Process attribute {!r} has not been initialized.'.format(name))

def _decache(this, name):
	if name in this.__attrs_property_cached__:
		del this.__attrs_property_cached__[name]

def proc_setter_count(this, value = None, name = None):
	"""Counter for some properties
	in order to prevent overwriting by runtime_config if
	they are set by `pXXX.dirsig = True`
	"""
	this._setcounter.setdefault(name, -1)
	# set it to 0 in __init__
	this._setcounter[name] += 1

def proc_runtime_config_setter(this, value):
	"""Try to override the proc property values
	if possible from runtime config"""
	# replace the values in runtime config
	if not value:
		return
	for key, val in value.items():
		if key == 'envs':
			this.envs.update(val)
		elif key == 'plugin_config':
			this.plugin_config.update(val)
		elif this._setcounter.get(key) or key == 'runner':
			continue
		else:
			setattr(this, key, val)

def proc_id_setter(this, value):
	"""Don't allow id to be set using setter"""
	if this._setcounter.get('id'):
		raise ProcessAttributeError('Process id should be passed while instantization.')
	proc_tag_setter(this, value, name = 'id')
	this._setcounter['id'] += 1

def proc_tag_setter(this, value, name = 'tag'):
	"""Tag setter"""
	this._setcounter.setdefault(name, -1)
	this._setcounter[name] += 1
	_decache(this, 'name')
	_decache(this, 'shortname')
	_decache(this, 'procset')

def proc_procset(this, value):
	"""Parse the procset from tag"""
	_require(this, 'tag', strict = False, msg = 'Process procset requires tag to be specified.')
	if '@' not in this.tag:
		return ''
	return this.tag.split('@', 1)[1]

def proc_name(this, value):
	"""Get the name of the process, including all parts of tag"""
	return '{}.{}'.format(this.id, this.tag)

def proc_shortname(this, value):
	"""Get the shortname of the process,
	if tag starts with "notag", don't include it"""
	if not this.tag or this.tag == 'notag':
		return this.id
	if this.tag[:6] == 'notag@':
		return '{}@{}'.format(this.id, this.tag[6:])
	return this.name

def proc_runner(this, value):
	"""Turn a runner profile to a runner config
	If it is a config, update the default one with it,
	otherwise, read the runner config from profile
	"""
	# Use runtime_config's runner if not set
	if not this._setcounter.get('runner') and this.runtime_config:
		value = this.runtime_config.get('runner', {})

	# If it is a profile or direct runner
	config_to_look_for = this.runtime_config or config
	if isinstance(value, str):
		try:
			with config_to_look_for._with(profile = value, raise_exc = True) as rconfig:
				value = rconfig.get('runner', {})
		except NoSuchProfile:
			pass

		if not isinstance(value, dict):
			value = dict(runner = value)

	assert isinstance(value, dict)
	with config_to_look_for._with(profile = 'default', copy = True) as rconfig:
		runner_config = rconfig.get('runner', {})
		if not isinstance(runner_config, dict):
			runner_config = Diot(runner = runner_config)
		runner_config.update(value)

	if 'runner' not in runner_config:
		runner_config.runner = 'local'
	return runner_config

def proc_depends_setter(this, value):
	"""Try to convert all possible dependencies to processes"""
	from .pyppl import _anything2procs
	depends = _anything2procs(value, procset = 'ends')
	try:
		prev_depends = this._depends
	except KeyError:
		prev_depends = []
	# remove process in previous depends' nexts
	for prevdep in prev_depends:
		prevdep.nexts.remove(this)
	for depend in depends:
		depend.nexts.append(this)
	return depends

def proc_input_setter(this, value):
	"""Allow input to be set twice:
	proc.input = 'a'
	proc.input = [1]
	Then real input would be:
	proc.input = {'a': [1]}
	"""
	# reset the size and jobs
	_decache(this, 'size')
	_decache(this, 'jobs')
	_decache(this, 'suffix')
	if isinstance(value, str):
		return value
	try:
		prev_input = this._input
	except KeyError:
		return value
	if isinstance(prev_input, str):
		return {prev_input: value}
	return value

def proc_input(this, value): # pylint: disable=too-many-locals,too-many-branches
	"""Parse and prepare the input, allowing jobs to easily access it"""
	# parse this.config.input keys
	# even for skipped or resumed process
	# because we need to keep the order
	# however, yaml does not
	# ['a:var', 'b:file', ...]

	# make sure it's called after .run()
	_require(this, 'runtime_config', strict = False,
		msg = 'Process input should be accessed after it starts running')
	input_keys_and_types = sum((always_list(key) for key in value), []) \
		if isinstance(value, dict) else always_list(value) \
		if value else []

	# {'a': 'var', 'b': 'file', ...}
	input_keytypes  = OrderedDiot()
	for keytype in input_keys_and_types:
		if not keytype.strip():
			continue
		if ':' not in keytype:
			input_keytypes[keytype] = IN_VARTYPE[0]
		else:
			thekey, thetype = keytype.split(':', 1)
			if thetype not in IN_VARTYPE + IN_FILESTYPE + IN_FILETYPE:
				del this.__attrs_property_raw__['input']
				raise ProcessInputError('Unknown input type: ' + thetype)
			input_keytypes[thekey] = thetype
	del input_keys_and_types

	ret = OrderedDiot()
	# no data specified, inherit from depends or argv
	input_values = list(value.values()) \
		if isinstance(value, dict) else [Channel.from_channels(*[
			d.channel for d in this.depends])
			if this.depends else Channel.from_argv()]

	input_channel = Channel.create()
	for invalue in input_values:
		# a callback, on all channels
		if callable(invalue):
			input_channel = input_channel.cbind(
				invalue(*[d.channel for d in this.depends] \
					if this.depends else Channel.from_argv()))
		elif isinstance(invalue, Channel):
			input_channel = input_channel.cbind(invalue)
		else:
			input_channel = input_channel.cbind(Channel.create(invalue))

	data_width = input_channel.width()
	key_width  = len(input_keytypes)
	if key_width < data_width:
		logger.warning('Not all data are used as input, %s column(s) wasted.',
			(data_width - key_width), proc = this.id)
	# compose ret
	for i, inkey in enumerate(input_keytypes):
		intype = input_keytypes[inkey]
		ret[inkey] = (intype, [])

		if i >= data_width:
			if intype in IN_FILESTYPE:
				ret[inkey][1].extend([[]] * input_channel.length())
			else:
				ret[inkey][1].extend([''] * input_channel.length())
			logger.warning('No data found for input key "%s"'
				', use empty strings/lists instead.' % inkey, proc = this.id)
		else:
			ret[inkey][1].extend(input_channel.flatten(i))

	return ret

def proc_output(this, value):
	"""Parse the output for jobs to easily access it"""
	# ['a:{{i.invar}}', 'b:file:{{i.infile|fn}}']
	if isinstance(value, (list, str)):
		outlist = list(filter(None, always_list(value)))
		output  = OrderedDiot()
		for out in outlist:
			outparts = LiquidStream.from_string(out).split(':')
			lenparts = len(outparts)
			if not outparts[0].isidentifier():
				raise ProcessOutputError(out,
					'Invalid output idnentifier {!r} in'.format(outparts[0]))
			if lenparts < 2:
				raise ProcessOutputError(out,
					'One of <key>:<type>:<value> missed for process output in')
			if lenparts > 3:
				raise ProcessOutputError(out, 'Too many parts for process output in')
			output[':'.join(outparts[:-1])] = outparts[-1]
	elif not (isinstance(value, OrderedDiot) or (
		isinstance(value, dict) and len(value) == 1)):
		raise ProcessOutputError(type(value).__name__,
			'Process output type should be one of list/str/OrderedDiot, '
			'or dict with len=1, not')

	# output => {'a': '{{i.invar}}', 'b:file': '{{i.infile | fn}}'}
	ret = OrderedDiot()
	for keytype, outdata in output.items():
		if ':' not in keytype:
			keytype += ':' + OUT_VARTYPE[0]
		thekey, thetype = keytype.split(':', 1)

		if thetype not in OUT_DIRTYPE + OUT_FILETYPE + OUT_VARTYPE + \
			OUT_STDOUTTYPE + OUT_STDERRTYPE:
			raise ProcessOutputError(thetype, 'Unknown output type')
		ret[thekey] = (thetype, this.template(outdata, **this.envs))
	return ret

def proc_size(this, value):
	"""Deduce the size (# jobs) of the processes from input"""
	_require(this, 'input', strict = False, msg = 'Process size needs input to be initialized.')
	if not this.input:
		return 0
	return len(list(this.input.values())[0][1])

def proc_jobs(this, value):
	"""Prepare the jobs"""
	_require(this, 'size', strict = False, msg = 'Jobs need size to be initialized.')
	use_runner(this.runner.runner)
	# have to make sure this is the first time it is imported,
	# as we need the runner to be set correctly for the
	# default value of runner for Job
	from .job import Job
	if this.size == 0:
		logger.warning('No data found for jobs, process will be skipped.', proc = this.id)
		return []
	logger.debug('Constructing jobs ...', proc = this.id)
	return [Job(i, this) for i in range(this.size)]

def proc_lang(this, value):
	"""Get the path of the interpreter from lang"""
	return cmdy.which(value).strip()

def proc_script(this, value):
	"""Prepare the script"""
	_require(this, 'lang', msg = 'Process script needs lang to be initialized.')
	_require(this, 'template', msg = 'Process script needs template to be initialized.')
	if not value:
		logger.warning('No script specified', proc = this.id)
		value = ''

	if value.startswith ('file:'):
		tplfile = Path(value[5:])
		if not fs.exists (tplfile):
			raise ProcessScriptError(tplfile, 'No such template file')
		logger.debug("Using template file: %s", tplfile, proc = this.id)
		value = tplfile.read_text()

	# original lines
	olines = value.splitlines()
	# new lines
	nlines = []
	indent = ''
	for line in olines:
		if '# PYPPL INDENT REMOVE' in line:
			indent = line[:-len(line.lstrip())]
		elif '# PYPPL INDENT KEEP' in line:
			indent = ''
		elif indent and line.startswith(indent):
			nlines.append(line[len(indent):])
		else:
			nlines.append(line)

	if not nlines or not nlines[0].startswith('#!'):
		nlines.insert(0, '#!' + this.lang)
	nlines.append('')

	return this.template('\n'.join(nlines), **this.envs)

def proc_template(this, value):
	"""Prepare the template"""
	if callable(value):
		return value
	if not value:
		return getattr(template, 'TemplateLiquid')
	return getattr(template, 'Template' + value.capitalize())

def proc_suffix(this, value):
	"""Calculate the suffix"""
	_require(this, 'input', msg = 'Process suffix needs input to be initialized.')
	_require(this, 'name', msg = 'Process suffix needs name to be initialized.')
	_require(this, 'output', msg = 'Process suffix needs output to be initialized.')
	_require(this, 'depends', strict = False, msg = 'Process suffix needs depends to be initialized.')
	determines       = OrderedDiot()
	# Process belongs to just one program
	determines.argv0 = Path(sys.argv[0]).resolve()
	determines.name  = this.name
	if isinstance(this._input, dict):
		determines.input = this._input.copy()
		for key, val in this._input.items():
			# lambda is not pickable
			# convert others to string to make sure it's pickable. Issue #65
			determines.input[key] = funcsig(val) if callable(val) else str(val)
		determines.input = sorted(determines.input.items())
	else:
		determines.input = str(this._input)
	determines.depends = [proc.name + '#' + proc.suffix for proc in this.depends]
	determines.output = this._output
	return str(uuid.uuid5(uuid.NAMESPACE_URL, str(determines)))[:8]

def proc_workdir(this, value):
	"""Get the work directory and try to create it"""
	if not value:
		_require(this, 'ppldir', msg = 'Process workdir needs ppldir to be specified.')
		_require(this, 'suffix', msg = 'Process workdir needs suffix to be initialized.')
		workdir = this.ppldir.joinpath('PyPPL.{}.{}'.format(this.name, this.suffix))
	elif '/' not in str(value):
		_require(this, 'ppldir', msg = 'Process workdir needs ppldir to be specified.')
		workdir = this.ppldir / value
	else:
		workdir = Path(value)

	if not workdir.is_dir():
		workdir.mkdir(parents = True)
	return workdir

def proc_channel(this, value):
	"""Assign the output of jobs to processes as channel"""
	# make sure it's called after run
	_require(this, 'runtime_config', strict = False,
		msg = 'Process channel can only be accessed after run.')
	if this.jobs:
		chan = Channel.create([
			tuple(value for _, value in job.output.values())
			for job in this.jobs
		])
		chan.attach(*this.jobs[0].output.keys())
		return chan
	return value
