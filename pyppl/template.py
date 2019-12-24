"""
Template adaptor for PyPPL

@variables:
	DEFAULT_ENVS (dict): The default environments for templates
"""
from liquid import Liquid

__all__ = ['Template', 'TemplateLiquid', 'TemplateJinja2']

DEFAULT_ENVS = {}

class Template:
	"""@API
	Base class wrapper to wrap template for PyPPL
	"""

	def __init__(self, source, **envs):
		"""@API
		Template construct
		"""
		self.source = source
		self.envs   = DEFAULT_ENVS.copy()
		self.envs.update(envs)

	def register_envs(self, **envs):
		"""@API
		Register extra environment
		@params:
			**envs: The environment
		"""
		self.envs.update(envs)

	def render(self, data = None):
		"""@API
		Render the template
		@parmas:
			data (dict): The data used to render
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
	"""@API
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
	"""@API
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
