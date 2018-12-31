"""
Template adaptor for PyPPL
"""

__all__ = ['Template', 'TemplateLiquid', 'TemplateJinja2']

import json, inspect
from os import path, readlink
from liquid import Liquid, LiquidRenderError
from .utils import string_types
Liquid.MODE  = 'mixed'
Liquid.DEBUG = False

class _TemplateFilter(object):
	"""
	A set of builtin filters
	"""

	@staticmethod
	def read(x):
		with open(x) as f:
			return f.read()

	@staticmethod
	def readlines(x, skipEmptyLines = True):
		ret = []
		with open(x) as f:
			for line in f:
				line = line.rstrip('\n\r')
				if not line and skipEmptyLines:
					continue
				ret.append(line)
		return ret

	@staticmethod
	def basename(x, orig = False):
		bname = path.basename(x)
		if orig: 
			return bname

		filename = bname.split('.', 1)
		if len(filename) == 1:
			filename, ext = filename[0], ''
		else:
			filename, ext = filename
			ext = '.' + ext

		if  not filename.endswith(']') or \
			not '[' in filename or \
			not filename[:-1].split('[', 1)[1].isdigit(): 
			return bname
		
		return filename.split('[', 1)[0] + ext

	@staticmethod
	def filename(x, orig = False, dot = -1):
		"""
		Return the stem of the basename (stripping extension(s))
		@params:
			`x`: The path
			`orig`: If the path is a renamed file (like: `origin[1].txt`), whether return its original filename or the parsed filename (`origin.txt`)
			`dot`: Strip to which dot. 
				- `-1`: the last one
				- `-2`: the 2nd last one ...
				- `1` : remove all dots.
		"""
		return '.'.join(_TemplateFilter.basename(x, orig).split('.')[0:dot])
	
	@staticmethod
	def prefix(x, orig = False, dot = -1):
		return path.join(path.dirname(x), _TemplateFilter.filename(x, orig, dot))

	@staticmethod
	def R(x, ignoreintkey = True):
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
			return 'c({})'.format(','.join([_TemplateFilter.R(i) for i in x]))
		if isinstance(x, dict):
			#                                                   list allow repeated names
			return 'list({})'.format(','.join([
				'`{0}`={1}'.format(k, _TemplateFilter.R(v)) if isinstance(k, int) and not ignoreintkey else \
				_TemplateFilter.R(v) if isinstance(k, int) and ignoreintkey else \
				'{0}={1}'.format(str(k).split('#')[0], _TemplateFilter.R(v)) for k, v in sorted(x.items())
			]))
		return repr(x)

	@staticmethod
	def Rlist(x, ignoreintkey = True):
		assert isinstance(x, (list, tuple, set, dict))
		if isinstance(x, dict):
			return _TemplateFilter.R(x, ignoreintkey)
		return 'as.list({})'.format(_TemplateFilter.R(x, ignoreintkey))
	
	@staticmethod
	def render(x, data = None):
		"""
		Render a template variable, using the shared environment
		"""
		if not isinstance(x, string_types):
			return x
		frames = inspect.getouterframes(inspect.currentframe())
		evars  = data or {}
		for frame in frames:
			lvars = frame[0].f_locals
			if lvars.get('__engine') == 'liquid':
				lvars.update(evars)
				evars = lvars
				break
			if '_Context__self' in lvars:
				lvars = dict(lvars['_Context__self'])
				lvars.update(evars)
				evars = lvars
				break
		
		engine = evars.get('__engine')
		if not engine:
			raise RuntimeError("I don't know which template engine to use to render {}...".format(x[:10]))
		
		engine = TemplateJinja2 if engine == 'jinja2' else TemplateLiquid
		return engine(x).render(evars)

class Template(object):
	"""
	Template wrapper base
	"""

	DEFAULT_ENVS = {
		'R'        : _TemplateFilter.R,
		'Rvec'     : _TemplateFilter.R, # will be deprecated!
		'Rlist'    : _TemplateFilter.Rlist,
		'realpath' : path.realpath,
		'readlink' : readlink,
		'dirname'  : path.dirname,
		# /a/b/c[1].txt => c.txt
		'basename' : _TemplateFilter.basename,
		'bn'       : _TemplateFilter.basename,
		'stem'     : _TemplateFilter.filename,
		'filename' : _TemplateFilter.filename,
		'fn'       : _TemplateFilter.filename,
		# /a/b/c.d.e.txt => c
		'filename2': lambda x, orig = False, dot = 1: _TemplateFilter.filename(x, orig, dot),
		'fn2'      : lambda x, orig = False, dot = 1: _TemplateFilter.filename(x, orig, dot),
		# /a/b/c.txt => .txt
		'ext'      : lambda x: path.splitext(x)[1],
		# /a/b/c[1].txt => /a/b/c
		'prefix'   : _TemplateFilter.prefix,
		# /a/b/c.d.e.txt => /a/b/c
		'prefix2'  : lambda x, orig = False, dot = 1: _TemplateFilter.prefix(x, orig, dot),
		'quote'    : lambda x: json.dumps(str(x)),
		'squote'   : repr,
		'json'     : json.dumps,
		'read'     : _TemplateFilter.read,
		'readlines': _TemplateFilter.readlines,
		'render'   : _TemplateFilter.render,
		# single quote of all elements of an array
		'asquote'  : lambda x: '''%s''' % (" " .join([json.dumps(str(e)) for e in x])),
		# double quote of all elements of an array
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
		self.envs['__engine'] = 'liquid'
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
		self.envs['__engine'] = 'jinja2'
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
