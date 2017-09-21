
from .template import Template

class TemplateJinja2 (Template):
	
	def __init__(self, source, **envs):
		import jinja2
		super(TemplateJinja2, self).__init__(source ,**envs)
		self.engine = jinja2.Template(source)
		self.engine.globals = self.envs
		self.source = source

	def __str__(self):
		return 'TemplateJinja2 with source: ' + self.source

	def _render(self, data):
		return self.engine.render(data)
