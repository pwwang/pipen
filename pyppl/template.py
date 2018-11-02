"""
Template adaptor for PyPPL
"""

__all__ = ['Template', 'TemplateLiquid', 'TemplateJinja2']

import json
from os import path, readlink
from liquid import Liquid
from .utils import string_types
Liquid.MODE  = 'mixed'
Liquid.DEBUG = False

def _read(x):
	with open(x) as f:
		return f.read()

def _readlines(x, skipEmptyLines = True):
	ret = []
	with open(x) as f:
		for line in f:
			line = line.rstrip('\n\r')
			if not line and skipEmptyLines:
				continue
			ret.append(line)
	return ret

def _basename(x, orig = False):
	bn       = path.basename(x)
	if orig: return bn
	filename = path.splitext(bn)[0]
	if not filename.endswith(']'): return bn
	if not '[' in filename: return bn
	return filename.rpartition('[')[0] + path.splitext(bn)[1]

def _filename(x, orig = False):
	return path.splitext(_basename(x, orig))[0]

def _R(x, ignoreintkey = True):
	if x is True:
		return 'TRUE'
	if x is False:
		return 'FALSE'
	if x is None:
		return 'NULL'
	if isinstance(x, string_types):
		if x.upper() in ['+INF', 'INF']:
			return 'Inf'
		if x.upper() == '-INF':
			return '-Inf'
		if x.upper() == 'TRUE':
			return 'TRUE'
		if x.upper() == 'FALSE':
			return 'FALSE'
		if x.upper() == 'NA' or x.upper() == 'NULL':
			return x
		if x.startswith('r:') or x.startswith('R:'):
			return str(x)[2:]
		return repr(str(x))
	if isinstance(x, (list, tuple, set)):
		return 'c({})'.format(','.join([_R(i) for i in x]))
	if isinstance(x, dict):
		#                                                   list allow repeated names
		return 'list({})'.format(','.join([
			'`{0}`={1}'.format(k, _R(v)) if isinstance(k, int) and not ignoreintkey else \
			_R(v) if isinstance(k, int) and ignoreintkey else \
			'{0}={1}'.format(str(k).split('#')[0], _R(v)) for k, v in sorted(x.items())
		]))
	return repr(x)

def _Rlist(x, ignoreintkey = True):
	assert isinstance(x, (list, tuple, set, dict))
	if isinstance(x, dict):
		return _R(x, ignoreintkey)
	return 'as.list({})'.format(_R(x, ignoreintkey))

class Template(object):
	"""
	Template wrapper base
	"""

	DEFAULT_ENVS = {
		'R'        : _R,
		'Rvec'     : _R, # will be deprecated!
		'Rlist'    : _Rlist,
		'realpath' : path.realpath,
		'readlink' : readlink,
		'dirname'  : path.dirname,
		# /a/b/c[1].txt => c.txt
		'basename' : _basename,
		'bn'       : _basename,
		'stem'     : _filename,
		'filename' : _filename,
		'fn'       : _filename,
		# /a/b/c.d.e.txt => c
		'filename2': lambda x, orig = False: _filename(x, orig).split('.')[0],
		'fn2'      : lambda x, orig = False: _filename(x, orig).split('.')[0],
		# /a/b/c.txt => .txt
		'ext'      : lambda x: path.splitext(x)[1],
		# /a/b/c[1].txt => /a/b/c
		'prefix'   : lambda x, orig = False: path.join(path.dirname(x), _filename(x, orig)),
		# /a/b/c.d.e.txt => /a/b/c
		'prefix2'  : lambda x, orig = False: path.join(path.dirname(x), _filename(x, orig).split('.')[0]),
		'quote'    : lambda x: json.dumps(str(x)),
		'squote'   : repr,
		'json'     : json.dumps,
		'read'     : _read,
		'readlines': _readlines,
		'asquote'  : lambda x: '''%s''' % (" " .join([json.dumps(str(e)) for e in x])),
		'acquote'  : lambda x: """%s""" % (", ".join([json.dumps(str(e)) for e in x]))
	}

	def __init__(self, source, **envs):
		self.source = source
		self.envs   = Template.DEFAULT_ENVS.copy()
		self.envs.update(envs)

	def registerEnvs(self, **envs):
		"""
		Register extra environment
		@params:
			`**envs`: The environment
		"""
		self.envs.update(envs)

	def render(self, data = None):
		"""
		Render the template
		@parmas:
			`data`: The data used to render
		"""
		return self._render(data or {})

	# in order to dump setting
	def __str__(self):
		lines = self.source.splitlines()
		if len(lines) <= 1:
			return '%s < %s >' % (self.__class__.__name__, ''.join(lines))

		ret  = ['%s <<<' % self.__class__.__name__]
		ret += ['\t' + line for line in self.source.splitlines()]
		ret += ['>>>']
		return '\n'.join(ret)

	def __repr__(self):
		return str(self)

	def _render(self, data):
		raise NotImplementedError()

class TemplateLiquid (Template):
	"""
	liquidpy template wrapper.
	"""

	def __init__(self, source, **envs):
		"""
		Initiate the engine with source and envs
		@params:
			`source`: The souce text
			`envs`: The env data
		"""
		super(TemplateLiquid, self).__init__(source ,**envs)
		self.engine = Liquid(source, **self.envs)
		self.source = source

	def _render(self, data):
		"""
		Render the template
		@params:
			`data`: The data used for rendering
		@returns:
			The rendered string
		"""
		return self.engine.render(**data)

class TemplateJinja2 (Template):
	"""
	Jinja2 template wrapper
	"""

	def __init__(self, source, **envs):
		"""
		Initiate the engine with source and envs
		@params:
			`source`: The souce text
			`envs`: The env data
		"""
		import jinja2
		super(TemplateJinja2, self).__init__(source ,**envs)
		self.engine = jinja2.Template(source)
		self.engine.globals = self.envs
		self.source = source

	def _render(self, data):
		"""
		Render the template
		@params:
			`data`: The data used for rendering
		@returns:
			The rendered string
		"""
		return self.engine.render(data)
