"""
This template engine is borrowed from Templite
The code is here: https://github.com/aosabook/500lines/blob/master/template-engine/code/templite.py
Author: Ned Batchelder
Project: Template engine
Requirements: Python

Modified by: pwwang
Functions added:
	- support elif, else
	- support for dict: for k,v in dict.items()
	- support [] to get element from list or dict.
	- support multivariables in expression:
	  {{d1,d2|concate}}
	  {'concate': lambda x,y: x+y}
"""
import re
from sys import stderr
from .template import Template
from .. import utils

class TemplatePyPPLSyntaxError(ValueError):
	"""Raised when a template has a syntax error."""
	pass


class TemplatePyPPLCodeBuilder(object):
	"""Build source code conveniently."""

	INDENT_STEP = 4	  # PEP8 says so!

	def __init__(self, indent=0):
		self.code = []
		self.indent_level = indent

	def __str__(self):
		return "".join(str(c) for c in self.code)

	def add_line(self, line):
		"""Add a line of source to the code.
		Indentation and newline will be added for you, don't provide them.
		"""
		self.code.extend([" " * self.indent_level, line, "\n"])

	def add_section(self):
		"""Add a section, a sub-CodeBuilder."""
		section = TemplatePyPPLCodeBuilder(self.indent_level)
		self.code.append(section)
		return section

	def indent(self):
		"""Increase the current indent for following lines."""
		self.indent_level += self.INDENT_STEP

	def dedent(self):
		"""Decrease the current indent for following lines."""
		self.indent_level -= self.INDENT_STEP

	def get_globals(self):
		"""Execute the code, and return a dict of globals it defines."""
		# A check that the caller really finished all the blocks they started.
		assert self.indent_level == 0
		# Get the Python source as a single string.
		python_source = str(self)
		# Execute the source, defining globals, and return them.
		global_namespace = {}
		exec(python_source, global_namespace)
		return global_namespace


class TemplatePyPPLEngine(object):
	"""A simple template renderer, for a nano-subset of Django syntax.
	Supported constructs are extended variable access::
		{{var.modifer.modifier|filter|filter}}
	loops::
		{% for var in list %}...{% endfor %}
	and ifs::
		{% if var %}...{% endif %}
	Comments are within curly-hash markers::
		{# This will be ignored #}
	Construct a Templite with the template text, then use `render` against a
	dictionary context to create a finished string::
		templite = Templite('''
			<h1>Hello {{name|upper}}!</h1>
			{% for topic in topics %}
				<p>You are interested in {{topic}}.</p>
			{% endif %}
			''',
			{'upper': str.upper},
		)
		text = templite.render({
			'name': "Ned",
			'topics': ['Python', 'Geometry', 'Juggling'],
		})
	"""
	def __init__(self, text, *contexts):
		"""Construct a Templite with the given `text`.
		`contexts` are dictionaries of values to use for future renderings.
		These are good for filters and global values.
		"""
		self.text    = text
		self.context = {}
		for context in contexts:
			self.context.update(context)

		self.all_vars = set()
		self.loop_vars = set()

		# We construct a function in source form, then compile it and hold onto
		# it, and execute it to render the template.
		code = TemplatePyPPLCodeBuilder()

		code.add_line("def render_function(context, do_dots):")
		code.indent()
		vars_code = code.add_section()
		code.add_line("result = []")
		code.add_line("append_result = result.append")
		code.add_line("extend_result = result.extend")
		code.add_line("to_str = str")

		buffered = []
		def flush_output():
			"""Force `buffered` to the code builder."""
			if len(buffered) == 1:
				code.add_line("append_result(%s)" % buffered[0])
			elif len(buffered) > 1:
				code.add_line("extend_result([")
				code.indent()
				for buffer in buffered:
					code.add_line(buffer + ',')
				code.dedent()
				code.add_line("])")
			del buffered[:]

		ops_stack = []

		# Split the text to form a list of tokens.
		tokens = re.split(r"(?s)({{.*?}}|{%.*?%}|{#.*?#})", text)
		for token in tokens:
			if token.startswith('{#'):
				# Comment: ignore it and move on.
				continue
			elif token.startswith('{{'):
				# An expression to evaluate.
				expr = self._expr_code(token[2:-2].strip())
				buffered.append("to_str(%s)" % expr)
			elif token.startswith('{%'):
				# Action tag: split into words and parse further.
				flush_output()
				words = token[2:-2].strip().split()
				if words[0] == 'if' or words[0] == 'elif':
					# An if statement: evaluate the expression to determine if.
					if len(words) < 2:
						self._syntax_error("Don't understand if/elif", token)
					if words[0] == 'if':
						ops_stack.append('if')
					else:
						code.dedent()
					code.add_line("%s %s:" % (words[0], self._expr_code(words[1:])))
					code.indent()
				elif words[0] == 'else':
					if len(words) > 1:
						self._syntax_error("Don't understand else", token)
					code.dedent()
					code.add_line("else:")
					code.indent()
				elif words[0] == 'for':
					# A loop: iterate over expression result.
					if len(words) < 4 or 'in' not in words or words.index('in') < 2:
						self._syntax_error("Don't understand for", token)
					ops_stack.append('for')
					inidx = words.index('in')
					keys  = list(map(lambda x: x.strip(), ''.join(words[1:inidx]).split(',')))
					for key in keys:
						self._variable(key, self.loop_vars)
					code.add_line(
						"for %s in %s:" % (
							', '.join(['c_%s' % key for key in keys]),
							self._expr_code(words[(inidx+1):])
						)
					)
					code.indent()
				elif words[0].startswith('end'):
					# Endsomething.  Pop the ops stack.
					if len(words) != 1:
						self._syntax_error("Don't understand end", token)
					end_what = words[0][3:]
					if not ops_stack:
						self._syntax_error("Too many ends", token)
					start_what = ops_stack.pop()
					if start_what != end_what:
						self._syntax_error("Mismatched end tag", end_what)
					code.dedent()
				else:
					self._syntax_error("Don't understand tag", words[0])
			else:
				# Literal content.  If it isn't empty, output it.
				if token:
					buffered.append(repr(token))

		if ops_stack:
			self._syntax_error("Unmatched action tag", ops_stack[-1])

		flush_output()

		for var_name in self.all_vars - self.loop_vars:
			vars_code.add_line("c_%s = context[%r]" % (var_name, var_name))

		code.add_line("return ''.join(result)")
		code.dedent()
		self._render_function = code.get_globals()['render_function']
		self._render_function_code = str(code)

	def _expr_code(self, expr):
		"""Generate a Python expression for `expr`."""
		if isinstance(expr, list):
			expr = ' '.join(expr)
		expr   = expr.strip()
		pipes  = utils.split(expr, '|')
		commas = utils.split(expr, ',')
		dots   = utils.split(expr, '.')
		if len(pipes) > 1:
			code = self._expr_code(pipes[0])
			for func in pipes[1:]:
				if func.startswith('[') or func.startswith('.'):
					code = "%s%s" % (code, func)
				elif func.startswith('lambda '):
					code = "(%s)(%s)" % (func, code)
				elif '.' in func:
					code = "%s(%s)" % (self._expr_code(func), code)
				else:
					self._variable(func, self.all_vars)
					code = "c_%s(%s)" % (func, code)
		elif len(commas) > 1:
			codes = [self._expr_code(comma) for comma in commas]
			code = ', '.join(codes)
		elif len(dots) > 1:
			code = self._expr_code(dots[0])
			for dot in dots[1:]:
				b1     = dot.find('(')
				b2     = dot.find('[')
				bindex = min(b1, b2) if b1 >= 0 and b2 >=0 else b1 if b1 >= 0 else b2
				if bindex == -1:
					code = "do_dots(%s, %s)" % (code, repr(dot))
				else:
					code = "do_dots(%s, %s)%s" % (code, repr(dot[:bindex]), dot[bindex:])
		else:
			b1     = expr.find('(')
			b2     = expr.find('[')
			bindex = min(b1, b2) if b1 >= 0 and b2 >=0 else b1 if b1 >= 0 else b2
			var    = expr if bindex == -1 else expr[:bindex]
			self._variable(var, self.all_vars)
			code = "c_%s" % expr
		return code

	def __str__(self):
		return 'TemplatePyPPLEngine with _render_function: \n' + self._render_function_code

	@classmethod
	def _syntax_error(self, msg, thing):
		"""Raise a syntax error using `msg`, and showing `thing`."""
		raise TemplatePyPPLSyntaxError("%s: %r" % (msg, thing))

	def _variable(self, name, vars_set):
		"""Track that `name` is used as a variable.
		Adds the name to `vars_set`, a set of variable names.
		Raises an syntax error if `name` is not a valid name.
		"""
		if not re.match(r"[_a-zA-Z][_a-zA-Z0-9]*$", name):
			self._syntax_error("Not a valid name", name)
		vars_set.add(name)

	def render(self, context=None):
		"""Render this template by applying it to `context`.
		`context` is a dictionary of values to use in this rendering.
		"""
		# Make the complete context we'll use.
		render_context = dict(self.context)
		if context:
			render_context.update(context)
		try:
			return self._render_function(render_context, self._do_dots)
		except KeyError:
			stderr.write('>>> Probably variable not found in the template, check your data for rendering!\n')
			stderr.write('>>> Current data keys are: %s\n>>> ' % sorted(render_context.keys()))
			raise
		except Exception:
			stderr.write(
				'\n>>> Failed to render:\n%s\n>>> With context:\n%s\n>>> The render function is:\n%s\n\n' % (
					'\n'.join(['  ' + line for line in self.text.splitlines()]),
					'\n'.join(['  %-10s: %s' % (k,v) for k,v in render_context.items()]),
					'\n'.join(['  %-3s %s' % (str(i+1) + '.', line) for i,line in enumerate(self._render_function_code.splitlines())])
				))
			raise

	@classmethod
	def _do_dots(self, value, *dots):
		"""Evaluate dotted expressions at runtime."""
		for dot in dots:
			try:
				value = getattr(value, dot)
			except (AttributeError, TypeError):
				try:
					value = value[dot]
				except TypeError:
					if dot.isdigit(): # names.0 == names[0]
						value = value[int(dot)]
					else:
						raise
		return value

class TemplatePyPPL (Template):
	"""
	Built-in template wrapper.
	"""

	def __init__(self, source, **envs):
		"""
		Initiate the engine with source and envs
		@params:
			`source`: The souce text
			`envs`: The env data
		"""
		super(TemplatePyPPL, self).__init__(source ,**envs)
		self.engine = TemplatePyPPLEngine(source, envs)
		self.source = source

	def __str__(self):
		return 'TemplatePyPPL with source: ' + self.source

	def _render(self, data):
		"""
		Render the template
		@params:
			`data`: The data used for rendering
		@returns:
			The rendered string
		"""
		return self.engine.render(data)

