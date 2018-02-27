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
import re, traceback
from .template import Template
from ..exception import TemplatePyPPLSyntaxError, TemplatePyPPLRenderError
from .. import utils


class TemplatePyPPLLine(object):
	"""
	Line of compiled code
	"""
	
	def __init__(self, line, src, indent = 0):
		"""
		Constructor of line
		"""
		self.line  = line
		self.src   = src
		self.ndent = indent
	
	def __str__(self):
		return ("\t" * self.ndent) + str(self.line) + "\n"

class TemplatePyPPLCodeBuilder(object):
	"""
	Build source code conveniently.
	"""

	INDENT_STEP = 1

	def __init__(self, indent = 0):
		"""
		Constructor of code builder
		@params:
			indent: The initial indent level
		"""
		self.code   = []
		self.ndent = indent

	def __str__(self):
		"""
		Concatnate of the codes
		@returns:
			The concatnated string
		"""
		return "".join(str(c) for c in self.code)

	def addLine(self, line, src = ""):
		"""
		Add a line of source to the code.
		Indentation and newline will be added for you, don't provide them.
		@params:
			line: The line to add
		"""
		line = TemplatePyPPLLine(line, src, self.ndent)
		self.code.append(line)

	def addSection(self):
		"""
		Add a section, a sub-CodeBuilder.
		@returns:
			The section added.
		"""
		section = TemplatePyPPLCodeBuilder(self.ndent)
		self.code.append(section)
		return section

	def indent(self):
		"""
		Increase the current indent for following lines.
		"""
		self.ndent += self.INDENT_STEP

	def dedent(self):
		"""
		Decrease the current indent for following lines.
		"""
		self.ndent -= self.INDENT_STEP

	def _nlines(self):
		"""
		Get the number of lines in the builder
		@returns:
			The number of lines.
		"""
		return sum(1 if isinstance(c, TemplatePyPPLLine) else c._nlines() for c in self.code)

	def lineByNo(self, lineno):
		"""
		Get the line by line number
		@params:
			`lineno`: The line number
		@returns:
			The TemplatePyPPLLine object at `lineno`.
		"""
		if lineno <= 0: return None

		n = 0
		for c in self.code:
			if isinstance(c, TemplatePyPPLLine):
				n += 1
				if n == lineno: 
					return c
			else:
				nlines = c._nlines()
				n += nlines
				if n >= lineno:
					return c.lineByNo(lineno - n + nlines)
		
	def getGlobals(self):
		"""
		Execute the code, and return a dict of globals it defines.
		"""
		# A check that the caller really finished all the blocks they started.
		assert self.ndent == 0
		# Get the Python source as a single string.
		python_source = str(self)
		# Execute the source, defining globals, and return them.
		global_namespace = {}
		exec(python_source, global_namespace)
		return global_namespace


class TemplatePyPPLEngine(object): # pragma: no cover
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
		"""
		Construct a Templite with the given `text`.
		`contexts` are dictionaries of values to use for future renderings.
		These are good for filters and global values.
		@params:
			`text`: The template text
			`contexts`: The contexts used to render.
		"""
		self.text      = text
		self.context   = {}
		self.buffered  = []
		self.all_vars  = {}
		self.loop_vars = {}
		for context in contexts:
			self.context.update(context)

		# We construct a function in source form, then compile it and hold onto
		# it, and execute it to render the template.
		self.code = TemplatePyPPLCodeBuilder()

		self.code.addLine("def renderFunction(context, do_dots):")
		self.code.indent()
		self.code.addLine("result = []")
		self.code.addLine("append_result = result.append")
		self.code.addLine("extend_result = result.extend")
		self.code.addLine("to_str = str")
		vars_code = self.code.addSection()

		ops_stack = []

		# Split the text to form a list of tokens.
		tokens = re.split(r"(?s)({{.*?}}|{%.*?%}|{#.*?#})", text)
		lineno = 1
		for token in tokens:
			lnstr = "Line %s: %s" % (lineno, token.rstrip('\n'))
			if token.startswith('{#'):
				# Comment: ignore it and move on.
				self._parseComments(token, lnstr)
				
			elif token.startswith('{{'):
				# An expression to evaluate.
				self._parseExpression(token, lnstr)
				
			elif token.startswith('{%'):
				# Action tag: split into words and parse further.
				self.flushOutput()
				self._parseTag(token, lnstr, ops_stack)
				
			else:
				# Literal content.  If it isn't empty, output it.
				if token: 
					tokenlines = token.split('\n')
					self._parseLiteral(tokenlines, lnstr)
					lineno += len(tokenlines) - 1

		if ops_stack:
			raise TemplatePyPPLSyntaxError(name = ops_stack[-1][1], msg = 'Unclosed template tag')

		self.flushOutput()
		
		for var_name, src in [(k, v) for k, v in self.all_vars.items() if k not in self.loop_vars]:
			vars_code.addLine(("c_%s = context[%r]" % (var_name, var_name)), 'unknown template variable: "%s" at %s' % (var_name, src))

		self.code.addLine("return ''.join(result)")
		self.code.dedent()
		self._renderFunction = self.code.getGlobals()['renderFunction']
		self.renderFunctionStr = str(self.code)
	
	@classmethod
	def _parseComments(self, token, src):
		if '\n' in token:
			raise TemplatePyPPLSyntaxError(src = src, msg = 'No new line is allowed')
	
	def _parseExpression(self, token, src):
		if '\n' in token:
			raise TemplatePyPPLSyntaxError(src = src, msg = 'No new line is allowed')
		expr = self._exprCode(token[2:-2].strip(), src)
		self.buffered.append(("to_str(%s)" % expr, src))
		
	def _parseTag(self, token, src, ops_stack):
		if '\n' in token:
			raise TemplatePyPPLSyntaxError(src = src, msg = 'No new line is allowed')
		words = token[2:-2].strip().split()
		if words[0] == 'if' or words[0] == 'elif':
			# An if statement: evaluate the expression to determine if.
			if len(words) < 2:
				raise TemplatePyPPLSyntaxError(name = 'if/elif', src = src, msg = 'No condition offered')
			if words[0] == 'if':
				ops_stack.append(('if', src))
			else:
				self.code.dedent()
			self.code.addLine(("%s %s:" % (words[0], self._exprCode(words[1:], src))), src)
			self.code.indent()
		elif words[0] == 'else':
			if len(words) > 1:
				raise TemplatePyPPLSyntaxError(name = 'else', src = src, msg = 'Extra condition offered')
			self.code.dedent()
			self.code.addLine("else:", src)
			self.code.indent()
		elif words[0] == 'for':
			# A loop: iterate over expression result.
			if len(words) < 4 or 'in' not in words or words.index('in') < 2:
				raise TemplatePyPPLSyntaxError(name = 'for', src = src, msg = 'Cannot understand for loop')
			ops_stack.append(('for', src))
			inidx = words.index('in')
			keys  = list(map(lambda x: x.strip(), ''.join(words[1:inidx]).split(',')))
			for key in keys:
				TemplatePyPPLEngine._variable(key, src, self.loop_vars)
			self.code.addLine((
				"for %s in %s:" % (
					', '.join(['c_%s' % key for key in keys]),
					self._exprCode(words[(inidx+1):], src)
				)), src
			)
			self.code.indent()
		elif words[0].startswith('end'):
			# Endsomething.  Pop the ops stack.
			if len(words) != 1:
				raise TemplatePyPPLSyntaxError(name = words[0], src = src, msg = 'Extra expression offered for end')
			end_what = words[0][3:]
			if not ops_stack:
				raise TemplatePyPPLSyntaxError(name = words[0], src = src, msg = 'Too many ends')
			start_what = ops_stack.pop()
			if start_what[0] != end_what:
				raise TemplatePyPPLSyntaxError(name = words[0], src = src, msg = 'End statement not paired with "%s"' % start_what[1])
			self.code.dedent()
		else:
			raise TemplatePyPPLSyntaxError(name = words[0], src = src, msg = 'No such keyword')

	def _parseLiteral(self, tokenlines, src):
		for i, line in enumerate(tokenlines):
			reprstr = repr(line) if i == len(tokenlines) - 1 else repr(line + '\n')
			self.buffered.append((reprstr, src))

	def flushOutput(self):
		"""
		Force `self.buffered` to the code builder.
		@params:
			`code`: The code builder
		"""
		if len(self.buffered) == 1:
			self.code.addLine(("append_result(%s)" % self.buffered[0][0]), self.buffered[0][1])
		elif len(self.buffered) > 1:
			self.code.addLine("extend_result([")
			self.code.indent()
			for buf, src in self.buffered:
				self.code.addLine(buf + ',', src)
			self.code.dedent()
			self.code.addLine("])")
		del self.buffered[:]
		
	def _exprCode(self, expr, src):
		"""
		Generate a Python expression for `expr`.
		@params:
			`expr`: The expression
			`src`:  The source of the expression
		@returns:
			The code after the expression being parsed.
		"""
		if isinstance(expr, list):
			expr = ' '.join(expr)
		expr   = expr.strip()
		pipes  = utils.split(expr, '|')
		commas = utils.split(expr, ',')
		dots   = utils.split(expr, '.')
		if len(pipes) > 1:
			code = self._exprCode(pipes[0], src)
			for func in pipes[1:]:
				if func.startswith('[') or func.startswith('.'):
					code = "%s%s" % (code, func)
				elif func.startswith('lambda '):
					code = "(%s)(%s)" % (func, code)
				elif '.' in func:
					code = "%s(%s)" % (self._exprCode(func, src), code)
				else:
					TemplatePyPPLEngine._variable(func, src, self.all_vars)
					code = "c_%s(%s)" % (func, code)
		elif len(commas) > 1:
			codes = [self._exprCode(comma, src) for comma in commas]
			code = ', '.join(codes)
		elif len(dots) > 1:
			code = self._exprCode(dots[0], src)
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
			TemplatePyPPLEngine._variable(var, src, self.all_vars)
			code = "c_%s" % expr
		return code

	def __str__(self):
		"""
		Stringize the engine.
		@returns:
			The string of the stringized engine.
		"""
		return 'TemplatePyPPLEngine with _renderFunction: \n' + self.renderFunctionStr
	
	@staticmethod
	def _variable(name, src, vars_set):
		"""
		Track that `name` is used as a variable.
		Adds the name to `vars_set`, a set of variable names.
		Raises an syntax error if `name` is not a valid name.
		@params:
			`name`: The name of the variable
			`src`:  The source of the variable
			`vars_set`: The variable set
		"""
		if not re.match(r"[_a-zA-Z][_a-zA-Z0-9]*$", name):
			raise TemplatePyPPLSyntaxError(name = name, src = src, msg = 'Invalid variable name')
		vars_set[name] = src
			
	@staticmethod
	def _do_dots(value, *dots):
		"""
		Evaluate dotted expressions at runtime.
		@params:
			`value`: The value
			`dots`:  The set of dots to do one after another
		@returns:
			The value after dots being done
		"""
		for dot in dots:
			try:
				value = getattr(value, dot)
			except (AttributeError, TypeError):
				try:
					value = value[dot]
				except (TypeError, KeyError):
					try:
						if dot.isdigit(): # names.0 == names[0]
							value = value[int(dot)]
						else:
							raise
					except Exception:
						# will be later raised in render method
						raise TemplatePyPPLRenderError(stack = 'No such attribute/index %s found for %s' % (repr(dot), repr(value)))
		return value

	def render(self, context=None):
		"""
		Render this template by applying it to `context`.
		@params:
			`context`: a dictionary of values to use in this rendering.
		@returns:
			The rendered string
		"""
		# Make the complete context we'll use.
		render_context = dict(self.context)
		if context:
			render_context.update(context)
		
		try:
			return self._renderFunction(render_context, TemplatePyPPLEngine._do_dots)
		except Exception:
			stacks = list(reversed(traceback.format_exc().splitlines()))
			for stack in stacks:
				stack = stack.strip()
				if stack.startswith('File "<string>"'):
					lineno = int(stack.split(', ')[1].split()[-1]) 
					line   = self.code.lineByNo(lineno)
					src    = line.src if line else '<unknown source>'
					raise TemplatePyPPLRenderError(stacks[0], src)
			raise

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

	def _render(self, data):
		"""
		Render the template
		@params:
			`data`: The data used for rendering
		@returns:
			The rendered string
		"""
		return self.engine.render(data)

