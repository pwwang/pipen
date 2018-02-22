
from .template import Template

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
