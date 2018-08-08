import testly, helpers, unittest
from os import path
from collections import OrderedDict
from pyppl.templates import Template
from pyppl.templates.template_jinja2 import TemplateJinja2
from pyppl.templates.template_pyppl import TemplatePyPPLCodeBuilder, TemplatePyPPLLine, TemplatePyPPLEngine, TemplatePyPPL
from pyppl.exception import TemplatePyPPLSyntaxError, TemplatePyPPLRenderError

class TestTemplatePyPPLLine(testly.TestCase):

	def dataProvider_testInit(self):
		yield '', ''
		yield 0, 0
		yield '{{}}', '{{a}}', 8

	def testInit(self, line, src, indent = 0):
		tpline = TemplatePyPPLLine(line, src, indent)
		self.assertIsInstance(tpline, TemplatePyPPLLine)
		self.assertEqual(tpline.line, line)
		self.assertEqual(tpline.src,  src)
		self.assertEqual(tpline.ndent,  indent)

class TestTemplatePyPPLCodeBuilder(testly.TestCase):

	def dataProvider_testInit(self):
		yield 1,
		yield 0,

	def testInit(self, indent):
		cb = TemplatePyPPLCodeBuilder(indent)
		self.assertIsInstance(cb, TemplatePyPPLCodeBuilder)
		self.assertEqual(cb.code, [])
		self.assertEqual(cb.ndent, indent)

	def dataProvider_testStr(self):
		yield '', '', 0, '\n'
		yield '', '', 1, '\t\n'
		yield 'hello', '', 1, '\thello\n'

	def testStr(self, line, src, indent, out):
		tpline = TemplatePyPPLLine(line, src, indent)
		self.assertEqual(str(tpline), out)

	def dataProvider_testAddLine(self):
		indent = 0
		line   = "a"
		src    = ""
		out    = "a\n"
		yield indent, line, src, out

		indent = 1
		line   = "abc"
		src    = ""
		out    = "\tabc\n"
		yield indent, line, src, out

	def testAddLine(self, indent, line, src, out):
		cb = TemplatePyPPLCodeBuilder(indent)
		cb.addLine(line, src)
		self.assertEqual(str(cb), out)

	def dataProvider_testAddSection(self):
		indent = 0
		line   = "a"
		src    = ""
		out    = "a\n"
		yield indent, line, src, out

		indent = 1
		line   = "abc"
		src    = ""
		out    = "\tabc\n"
		yield indent, line, src, out

	def testAddSection(self, indent, line, src, out):
		cb  = TemplatePyPPLCodeBuilder(indent)
		sec = cb.addSection()
		sec.addLine(line, src)
		self.assertEqual(str(cb), out)

	def dataProvider_testInDedent(self):
		yield 1,
		yield 2,
		yield 0,

	def testInDedent(self, indent):
		cb  = TemplatePyPPLCodeBuilder(indent)
		cb.indent()
		self.assertEqual(cb.ndent, indent + 1)
		cb.indent()
		self.assertEqual(cb.ndent, indent + 2)
		cb.dedent()
		self.assertEqual(cb.ndent, indent + 1)
		cb.dedent()
		self.assertEqual(cb.ndent, indent)

	def dataProvider_testGetGlobals(self):
		cb = TemplatePyPPLCodeBuilder(0)
		cb.addLine('a = 1')
		cb.addLine('def add():')
		cb.indent()
		cb.addLine('global a')
		cb.addLine('a += 1')
		cb.dedent()
		cb.addLine('add()')
		yield cb, {'a': 2}

		cb = TemplatePyPPLCodeBuilder(0)
		cb.addLine('a = 1')
		cb.addLine('def localvar():')
		cb.indent()
		cb.addLine('b = 2')
		cb.addLine('c = 3')
		cb.dedent()
		cb.addLine('localvar()')
		yield cb, {'a': 1}, {'b': 2, 'c': 3}

	def testGetGlobals(self, cb, gs, gsnot = None):
		cbgs = cb.getGlobals()
		self.assertDictContains(gs, cbgs)
		if gsnot:
			self.assertDictNotContains(gs, gsnot)

	def dataProvider_testNlines(self):
		cb1 = TemplatePyPPLCodeBuilder()
		yield cb1, 0

		cb2 = TemplatePyPPLCodeBuilder()
		cb2.addLine('', '')
		cb2.addLine('', '')
		cb2.addLine('', '')
		yield cb2, 3

		cb3 = TemplatePyPPLCodeBuilder()
		cb3.addLine('1', '')
		cb3.addLine('', '')
		cb3.addLine('2', '')
		yield cb3, 3

		cb4 = TemplatePyPPLCodeBuilder()
		cb4.addLine('1', '')
		sec = cb4.addSection()
		sec.addLine('2', '')
		sec.addLine('3', '')
		cb4.addLine('4', '')
		sec = cb4.addSection()
		sec.addLine('5', '')
		sec2 = sec.addSection()
		sec2.addLine('6', '')
		cb4.addLine('7', '')
		yield cb4, 7

	def testNlines(self, cb, nlines):
		self.assertEqual(cb._nlines(), nlines)

	def dataProvider_testLineByNo(self):
		cb1 = TemplatePyPPLCodeBuilder()
		yield cb1, 0, None

		cb2 = TemplatePyPPLCodeBuilder()
		cb2.addLine('a1', 'a2')
		cb2.addLine('b1', 'b2')
		cb2.addLine('c1', 'c2')
		yield cb2, 0, None
		yield cb2, 1, TemplatePyPPLLine('a1', 'a2', 0)
		yield cb2, 2, TemplatePyPPLLine('b1', 'b2', 0)
		yield cb2, 3, TemplatePyPPLLine('c1', 'c2', 0)
		yield cb2, 4, None

		cb3 = TemplatePyPPLCodeBuilder()
		cb3.addLine('1', '')
		sec = cb3.addSection()
		sec.addLine('2', '')
		sec.addLine('3', '')
		cb3.addLine('4', '')
		sec = cb3.addSection()
		sec.addLine('5', '')
		sec2 = sec.addSection()
		sec2.addLine('6', '')
		cb3.addLine('7', '')
		yield cb3, 0, None
		yield cb3, 1, TemplatePyPPLLine('1', '', 0)
		yield cb3, 2, TemplatePyPPLLine('2', '', 0)
		yield cb3, 3, TemplatePyPPLLine('3', '', 0)
		yield cb3, 4, TemplatePyPPLLine('4', '', 0)
		yield cb3, 5, TemplatePyPPLLine('5', '', 0)
		yield cb3, 6, TemplatePyPPLLine('6', '', 0)
		yield cb3, 7, TemplatePyPPLLine('7', '', 0)
		yield cb3, 8, None

	def testLineByNo(self, cb, lineno, out):
		line = cb.lineByNo(lineno)
		if line is None:
			self.assertIsNone(out)
		else:
			self.assertIsNotNone(out)
			self.assertEqual(line.line, out.line)
			self.assertEqual(line.src, out.src)
			self.assertEqual(line.ndent, out.ndent)

class TestTemplatePyPPLEngine(testly.TestCase):

	renderFunc_start = "def renderFunction(context, do_dots):\n" + \
		"	result = []\n" + \
		"	append_result = result.append\n" + \
		"	extend_result = result.extend\n" + \
		"	to_str = str\n"

	renderFunc_end = "	return ''.join(result)\n"

	str_prefix = "TemplatePyPPLEngine with _renderFunction: \n"

	def dataProvider_testInit(self):
		yield '', [], ''
		yield '{##}', [], ''
		yield '{{a}}', [], \
		"""
			c_a = context['a']
			append_result(to_str(c_a))
		"""
		yield '{% if a%}{{b}}{% endif %}', [], \
		"""
			c_a = context['a']
			c_b = context['b']
			if c_a:
				append_result(to_str(c_b))
		"""
		yield '{% for a in b %}1{{a}}2{% endfor %}', [], \
		"""
			c_b = context['b']
			for c_a in c_b:
				extend_result([
					'1',
					to_str(c_a),
					'2',
				])
		"""
		yield '{% for a in b %}{{a}}{% endif %}', [], '', TemplatePyPPLSyntaxError, "End statement not paired with \"Line 1: {% for a in b %}\" in \"Line 1: {% endif %}\": 'endif'"
		yield '{% if x %}{% for a in b %}{{a}}{% endfor %}', [], '', TemplatePyPPLSyntaxError, "Unclosed template tag: 'Line 1: {% if x %}'"
		yield '''
		literal1
		literal2
		{% if %}
		''', [], '', TemplatePyPPLSyntaxError, "No condition offered in \"Line 4: {% if %}\": 'if/elif'"
		yield '''
		literal1
		literal2
		{% endif %}literal3
		''', [], '', TemplatePyPPLSyntaxError, "Too many ends in \"Line 4: {% endif %}\": 'endif'"


	def testInit(self, text, contexts, renderfunc, exception = None, msg = None):
		if exception and not msg:
			self.assertRaises(exception, TemplatePyPPLEngine, text, *contexts)
		elif exception:
			self.assertRaisesRegex(exception, msg, TemplatePyPPLEngine, text, *contexts)
		else:
			engine = TemplatePyPPLEngine(text, *contexts)
			renderfunc = renderfunc.lstrip('\n').split('\n')
			renderfunc = '\n'.join(line[2:] for line in renderfunc)
			helpers.assertTextEqual(self, engine.renderFunctionStr[len(self.renderFunc_start):-len(self.renderFunc_end)], renderfunc)

	def dataProvider_testParseComments(self):
		yield '', ''
		yield '', None
		yield '{# a \n b #}', '', TemplatePyPPLSyntaxError
		yield '{% a \n b %}', '', TemplatePyPPLSyntaxError
		yield '{{ a \n b }}', '', TemplatePyPPLSyntaxError

	def testParseComments(self, token, src, exception = None):
		engine = TemplatePyPPLEngine('')
		if exception:
			self.assertRaises(exception, engine._parseComments, token, src)
		else:
			self.assertIsNone(engine._parseComments(token, src))

	def dataProvider_testParseExpression(self):
		yield '{{a}}', 'a', [('to_str(c_a)', 'a')]
		yield '{{a(1)}}', '{{1}}', [('to_str(c_a(1))', '{{1}}')]
		yield '{{a | b | c}}', '{{1}}', [('to_str(c_c(c_b(c_a)))', '{{1}}')]

	def testParseExpression(self, token, src, buffer):
		engine = TemplatePyPPLEngine('')
		self.assertIsNone(engine._parseExpression(token, src))
		self.assertListEqual(engine.buffered, buffer)

	def dataProvider_testParseTag(self):
		# if/elif
		yield '{% if %}', '', [], None, True
		yield '{% elif %}', '', [], None, True
		yield '{% if a | b %}', '', [], "if c_b(c_a):\n"
		yield '{% elif a(1) %}', '', [], "elif c_a(1):\n"
		# else
		yield '{% else 1 %}', '', [], None, True
		yield '{% else %}', '', [], "else:\n"
		# for
		yield '{% for %}', '', [], None, True
		yield '{% for a %}', '', [], None, True
		yield '{% for a b c %}', '', [], None, True
		yield '{% for in b c %}', '', [], None, True
		yield '{% for a in c %}', '', [], "for c_a in c_c:\n"
		yield '{% for a, b in c.items() %}', '', [], "for c_a, c_b in do_dots(c_c, 'items')():\n"
		# end
		yield '{% end x %}', '', [], None, True
		yield '{% endx %}', '', [], None, True # too many ends
		yield '{% endfor %}', '{% endfor %}', [('if', '{% if ... %}')], None, True
		yield '{% endif %}', '{% endif %}', [('if', '{% if ... %}')], ''
		# other
		yield '{% x %}', '', [], None, True

	def testParseTag(self, token, src, stack, out, exception = False):
		engine = TemplatePyPPLEngine('')
		if exception:
			self.assertRaises(TemplatePyPPLSyntaxError, engine._parseTag, token, src, stack)
		else:
			engine._parseTag(token, src, stack)
			self.assertEqual(str(engine.code)[len(self.renderFunc_start + self.renderFunc_end):], out)

	def dataProvider_testParseLiteral(self):
		yield '', [("''", '')]
		yield 'ab', [("'ab'", '')]
		yield 'ab\n', [("'ab\\n'", ''), ("''", '')]
		yield 'ab\n\n', [("'ab\\n'", ''), ("'\\n'", ''), ("''", '')]
		yield 'ab\n\nx', [("'ab\\n'", ''), ("'\\n'", ''), ("'x'", '')]

	def testParseLiteral(self, tokenlines, buffer):
		engine = TemplatePyPPLEngine('')
		engine._parseLiteral(tokenlines.split('\n'), '')
		self.assertListEqual(engine.buffered, buffer)

	def dataProvider_testFlushOutput(self):
		yield [], ''
		yield [('a', '')], 'append_result(a)\n'
		yield [('a', ''), ('b', '')], 'extend_result([\n\ta,\n\tb,\n])\n'

	def testFlushOutput(self, buffers, out):
		engine = TemplatePyPPLEngine('')
		engine.buffered = buffers
		engine.flushOutput()
		self.assertListEqual(engine.buffered, [])
		self.assertEqual(str(engine.code)[len(self.renderFunc_start + self.renderFunc_end):], out)

	def dataProvider_testExprCode(self):
		yield 'a | b', 'c_b(c_a)'
		yield 'a | [0]', 'c_a[0]'
		yield 'a | .x', 'c_a.x'
		yield 'a | lambda x: x+1', '(lambda x: x+1)(c_a)'
		yield 'a.c', "do_dots(c_a, 'c')"
		yield 'a.c(d)', "do_dots(c_a, 'c')(d)"
		yield 'a.c[d]', "do_dots(c_a, 'c')[d]"
		yield 'a.c[d](e)', "do_dots(c_a, 'c')[d](e)"
		yield 'a.c(d)[e]', "do_dots(c_a, 'c')(d)[e]"
		yield 'a.c(d[e])', "do_dots(c_a, 'c')(d[e])"
		yield 'a.c[d(e)]', "do_dots(c_a, 'c')[d(e)]"
		yield 'a(b)', "c_a(b)"
		yield 'a[b]', "c_a[b]"
		yield 'a[b(c)]', "c_a[b(c)]"
		yield 'a(b[c])', "c_a(b[c])"
		yield 'a, b', "c_a, c_b"
		yield 'a.c, b.d', "do_dots(c_a, 'c'), do_dots(c_b, 'd')"
		yield 'a.c[d(e)], b(f)', "do_dots(c_a, 'c')[d(e)], c_b(f)"
		yield 'a("|"), b(".") | lambda x, y: x + y | .c(1)[0]', '(lambda x, y: x + y)(c_a("|"), c_b(".")).c(1)[0]'

	def testExprCode(self, expr, out):
		engine = TemplatePyPPLEngine('')
		code   = engine._exprCode(expr, '')
		self.assertEqual(code, out)

	def dataProvider_testVariable(self):
		vars_set = {}
		yield 'a', 'src_a', vars_set, {'a': 'src_a'}
		yield '1', 'src_1', vars_set, {'a': 'src_a'}, True
		yield 'a?', 'src_a?', vars_set, {'a': 'src_a'}, True
		yield '_b', 'src_b', vars_set, {'a': 'src_a', '_b': 'src_b'}

	def testVariable(self, name, src, vars_set, outs, exception = False):
		if exception:
			self.assertRaises(TemplatePyPPLSyntaxError, TemplatePyPPLEngine._variable, name, src, vars_set)
		else:
			TemplatePyPPLEngine._variable(name, src, vars_set)
		self.assertDictEqual(vars_set, outs)

	def dataProvider_testDoDots(self):
		e = "a"
		yield [e, 'join'], e.join
		yield ["a", 0], 'a'
		yield ["abc", 1], 'b'
		yield ["abc", '1'], 'b'
		e = {'a':1, 'b':2}
		yield [e, 'keys'], e.keys
		yield [e, 'a'], 1
		yield [e, 0], None, True
		yield [e, 'c'], None, True
		yield [e, []], None, True

	def testDoDots(self, dots, out, exception = False):
		if exception:
			self.assertRaises(TemplatePyPPLRenderError, TemplatePyPPLEngine._do_dots, *dots)
		else:
			v = TemplatePyPPLEngine._do_dots(*dots)
			self.assertEqual(v, out)

	def dataProvider_testRender(self):
		# 0
		yield '{{name}}', {'name': 'John'}, 'John'
		yield '{{names[0]}}', {'names': ['John', 'Tome']}, 'John'
		yield '{{names2.1}}', {'names2': ['John', 'Tome']}, 'Tome'
		yield '{{names3.1[:-1]}}', {'names3': ['John', 'Tome']}, 'Tom'
		yield '{{names4.1.upper()}}', {'names4': ['John', 'Tome']}, 'TOME'
		# 5
		yield '{{names5.1 | [:-1] | .upper()}}', {'names5': ['John', 'Tome']}, 'TOM'
		yield '{{names6 | [1][:-1] | .upper()}}', {'names6': ['John', 'Tome']}, 'TOM'
		yield '{{names7 | lambda x: x[1].upper()}}', {'names7': ['John', 'Tome']}, 'TOME'
		yield '{{v1, v2|concate}}', {'v1': 'hello', 'v2': 'world', 'concate': lambda x,y: x+y}, 'helloworld'
		yield '{{v3 | R}}', {'v3': 'false'}, "FALSE"
		# 10
		yield '{{v4|realpath}}', {'v4': __file__}, path.realpath(__file__)
		#yield ('{{v5|readlink}}', {'v5': path.join(path.dirname(path.realpath(path.abspath(__file__))), 'helpers.py')}, path.relpath(path.join(path.dirname(path.dirname(path.abspat(__file__))), bin', 'helpers.py'), start = path.dirname(__file__)))
		yield '{{v6|dirname}}', {'v6': '/a/b/c'}, '/a/b'
		yield '{{v7|basename}}{{v7|bn}}', {'v7': '/a/b/c.txt'}, 'c.txtc.txt'
		yield '{{v8|basename}}{{v8|bn}}', {'v8': '/a/b/c[1].txt'}, 'c.txtc.txt'
		yield '{{v9, v9b|basename}}{{v9, v9b|bn}}', {'v9': '/a/b/c.txt', 'v9b': True}, 'c.txtc.txt'
		# 15
		yield '{{v10, v10b|basename}}{{v10, v10b|bn}} {{v10|ext}}', {'v10': '/a/b/c[1].txt', 'v10b': True}, 'c[1].txtc[1].txt .txt'
		yield '{{v11|filename}}{{v11|fn}} {{v11|prefix}}', {'v11': '/a/b/a.txt'}, 'aa /a/b/a'
		yield '{{v12|filename}}{{v12|fn}}', {'v12': '/a/b/b[1].txt'}, 'bb'
		yield '{{v13, v13b|filename}}{{v13, v13b|fn}}', {'v13': '/a/b/d.txt', 'v13b': True}, 'dd'
		yield '{{v14, v14b|filename}}{{v14, v14b|fn}}', {'v14': '/a/b/c[1].txt', 'v14b': True}, 'c[1]c[1]'
		# 20
		yield '{{var1|R}}', {'var1': 'NULL'}, 'NULL'
		yield '{{var2|R}}', {'var2': 'abc'}, "'abc'"
		yield '{% for var in varlist %}{{var|R}}{% endfor %}', {'varlist': ['abc', 'True', 1, False, True, None, 'INF', '-INF', 'r:c()', [1,2,3]]}, "'abc'TRUE1FALSETRUENULLInf-Infc()c(1,2,3)"
		yield '{% if var3|bool %}1{% else %}0{% endif %}', {'var3': 'abc', 'bool': bool}, '1'
		yield '{% for k , v in data.items() %}{{k}}:{{v}}{% endfor %}', {'data': {'a':1, 'b':2}}, 'a:1b:2'
		# 25
		yield '{{x|R}}', {'x': OrderedDict([(u'key1', 'val1'), ('key2', u'val2')])}, "list(key1='val1',key2='val2')"
		yield '{{x|Rlist}}', {'x': OrderedDict([(u'key1', 'val1'), ('key2', u'val2')])}, "list(key1='val1',key2='val2')"
		yield '{{x|Rlist}}', {'x': [1,2,3]}, "as.list(c(1,2,3))"
		yield '{{a|quote}}', {'a':''}, '""'
		yield '{{b|asquote}}', {'b':[1,2]}, '"1" "2"'
		# 30
		yield '{{c|acquote}}', {'c':[1,2]}, '"1", "2"'
		yield '{{d|squote}}', {'d':"1"}, "'1'"
		yield '{{e.f|json}}', {'e':{'f':[1,2]}}, '[1, 2]'
		yield '{{g,h | os.path.join}}', {'g': 'a', 'h': 'b', 'os': __import__('os')}, 'a/b'
		yield """
		#!/usr/bin/env python
		{% if x %}
		{% for y in ylist %}
		{{y}}
		{% endfor %}
		{% endif %}
		""", {'x': True, 'ylist': [1,2,3,4,5]}, """
		#!/usr/bin/env python\n\t\t\n\t\t
		1\n\t\t
		2\n\t\t
		3\n\t\t
		4\n\t\t
		5\n\t\t
		\n\t\t"""
		yield '{{a|read}}', {'a': __file__}, helpers.readFile(__file__)
		file2read = path.join(path.dirname(__file__), 'helpers.py')
		yield '{{a|readlines|lambda x:"\\n".join(_ for _ in x if _)}}', {'a': file2read}, helpers.readFile(file2read, lambda x: '\n'.join(str(y) for y in x.splitlines() if y))

		yield '{{a.x, b.y | lambda x,y: x+y}}', {'a': {'x': 1}, 'b': {'y': 2}}, '3'
		yield '{{a.b["1"][0](",")}}', {'a': {'b': {"1": [lambda x: x]}}}, ','
		# python literals
		yield '{{1 | bool}}', {}, 'True'
		yield '{{True | int}}', {}, '1'

	def testRender(self, text, contexts, out):
		t  = TemplatePyPPL(text)
		helpers.assertTextEqual(self, t.render(contexts), out)

	def dataProvider_testRenderExceptions(self):
		yield '{{a}}', {}, TemplatePyPPLRenderError, "KeyError: 'a' in 'unknown template variable: \"a\" at Line 1: {{a}}'"
		yield '{% if a %}1{% endif %}', {}, TemplatePyPPLRenderError, "KeyError: 'a' in 'unknown template variable: \"a\" at Line 1: {% if a %}'"
		yield '{{a.b}}', {'a':1}, TemplatePyPPLRenderError, "TemplatePyPPLRenderError: No such attribute/index 'b' found for 1 in 'Line 1: {{a.b}}'"
		yield """
		{% if x %}
			{%for y in a%}
			{%endfor%}
		{% endif %}""", {'a':1, 'x':True}, TemplatePyPPLRenderError, "TypeError: 'int' object is not iterable in 'Line 3: {%for y in a%}'"
		yield """
		{% if x %}\n
			{%for y in a%}
			{%endfor%}
		{% endif %}""", {'a':1, 'x':True}, TemplatePyPPLRenderError, "TypeError: 'int' object is not iterable in 'Line 4: {%for y in a%}'"


	def testRenderExceptions(self, text, context, exception, msg):
		engine = TemplatePyPPLEngine(text)
		self.assertRaisesRegex(exception, msg, engine.render, context)

	def dataProvider_testStr(self):
		yield TemplatePyPPLEngine(''), ''
		yield TemplatePyPPLEngine('abcd\nwnfe'), \
		"""
			extend_result([
				'abcd\\n',
				'wnfe',
			])
		"""
	# kind of duplicated with testInit, so just 2 cases.
	def testStr(self, cb, renderfunc):
		renderfunc = renderfunc.lstrip('\n').split('\n')
		renderfunc = '\n'.join(line[2:] for line in renderfunc)
		helpers.assertTextEqual(self, str(cb)[len(self.str_prefix + self.renderFunc_start):-len(self.renderFunc_end)], renderfunc)

class TestTemplate (testly.TestCase):

	def dataProvider_testInit(self):
		yield '', {}
		yield '{{a}}', {'a': 1}

	def testInit(self, source, envs):
		tpl = Template(source, **envs)
		helpers.assertTextEqual(self, tpl.source, source)
		self.assertDictContains(Template.DEFAULT_ENVS, tpl.envs)
		self.assertDictContains(envs, tpl.envs)

	def dataProvider_testRegisterEnvs(self):
		yield '', {}, {}
		yield '{{a}}', {'a': 1}, {}
		yield '{{a}}', {'a': 1}, {'b': 2}

	def testRegisterEnvs(self, source, envs, newenvs):
		tpl = Template(source, **envs)
		tpl.registerEnvs(**newenvs)
		helpers.assertTextEqual(self, tpl.source, source)
		self.assertDictContains(Template.DEFAULT_ENVS, tpl.envs)
		self.assertDictContains(envs, tpl.envs)
		self.assertDictContains(newenvs, tpl.envs)

	def dataProvider_testStr(self):
		yield Template(''), 'Template <  >'

	def testStr(self, t, s):
		helpers.assertTextEqual(self, str(t), s)

	def dataProvider_testRepr(self):
		yield Template(''), 'Template <  >'

	def testRepr(self, t, s):
		helpers.assertTextEqual(self, repr(t), s)

	def testRender(self):
		self.assertRaises(NotImplementedError, Template('').render, {})


class TestTemplatePyPPL (testly.TestCase):

	def dataProvider_testInit(self):
		yield '', {}
		yield '{{a}}', {'a': 1}

	def testInit(self, source, envs):
		tpl = TemplatePyPPL(source, **envs)
		helpers.assertTextEqual(self, tpl.source, source)
		self.assertDictContains(Template.DEFAULT_ENVS, tpl.envs)
		self.assertDictContains(envs, tpl.envs)
		self.assertIsInstance(tpl.engine, TemplatePyPPLEngine)

	def dataProvider_testStr(self):
		yield '',
		yield 'a',
		yield '{{a}}',
		yield '{{a}}\n{{b}}',

	def testStr(self, source):
		tpl = TemplatePyPPL(source)
		lines = source.splitlines()
		if len(lines) <= 1:
			self.assertEqual(str(tpl), 'TemplatePyPPL < %s >' % ''.join(lines))
		else:
			helpers.assertTextEqual(self, str(tpl), '\n'.join(
				['TemplatePyPPL <<<'] +
				['\t' + line for line in tpl.source.splitlines()] +
				['>>>'])
			)

	def dataProvider_testRender(self):
		source = """
		whatever
		{% if a, b | lambda x, y: x in y %}
		{{a}}
		{% else %}
			{% for x in y %}
			{{x}}
			{% endfor %}
		{% endif %}
		"""
		data = {'b': 'abc', 'a': 'a', 'y': [1,2,3]}
		out  = """
		whatever
		\n\t\ta
		\n\t\t"""
		yield source, data, out

		data = {'b': 'abc', 'a': 'd', 'y': [1,2,3]}
		out  = """
		whatever
		\n\t\t\t1
		\n\t\t\t2
		\n\t\t\t3
		\n\t\t"""

	def testRender(self, source, data, out):
		tpl = TemplatePyPPL(source)
		helpers.assertTextEqual(self, tpl.render(data), out)

class TestTemplateJinja2(testly.TestCase):

	def dataProvider_testInit(self):
		yield '', {}
		yield '{{a}}', {'a': 1}

	@unittest.skipIf(not helpers.moduleInstalled('jinja2'), 'Jinja2 not installed.')
	def testInit(self, source, envs):
		import jinja2
		tpl = TemplateJinja2(source, **envs)
		helpers.assertTextEqual(self, tpl.source, source)
		self.assertDictContains(Template.DEFAULT_ENVS, tpl.envs)
		self.assertDictContains(envs, tpl.envs)
		self.assertIsInstance(tpl.engine, jinja2.Template)

	def dataProvider_testStr(self):
		yield '',
		yield 'a',
		yield '{{a}}',
		yield '{{a}}\n{{b}}',

	@unittest.skipIf(not helpers.moduleInstalled('jinja2'), 'Jinja2 not installed.')
	def testStr(self, source):
		tpl = TemplateJinja2(source)
		lines = source.splitlines()
		if len(lines) <= 1:
			self.assertEqual(str(tpl), 'TemplateJinja2 < %s >' % ''.join(lines))
		else:
			helpers.assertTextEqual(self, str(tpl), '\n'.join(
				['TemplateJinja2 <<<'] +
				['\t' + line for line in tpl.source.splitlines()] +
				['>>>'])
			)

	def dataProvider_testRender(self):
		# 0
		yield '{{name}}', {'name': 'John'}, 'John'
		yield '{{names[0]}}', {'names': ['John', 'Tom']}, 'John'
		yield '{{concate(v1, v2)}}', {'v1': 'hello', 'v2': 'world', 'concate': lambda x,y: x+y}, 'helloworld'
		yield '{{R(v23)}}', {'v23': '"FALSE"'}, '\'"FALSE"\''
		yield '{{R(v3)}}', {'v3': 'false'}, "FALSE"
		# 5
		yield '{{realpath(v4)}}', {'v4': __file__}, path.realpath(__file__)
		#yield ('{{readlink(v5)}}', {'v5': path.join(path.dirname(path.realpath(path.abspath(__file__))), 'helpers.py')yield , path.relpath(path.jo(path.dirname(path.dirname(path.abspath(__file__))), 'bin', 'helpers.py'))),
		yield '{{dirname(v6)}}', {'v6': '/a/b/c'}, '/a/b'
		yield '{{basename(v7)}}{{bn(v7)}}', {'v7': '/a/b/c.txt'}, 'c.txtc.txt'
		yield '{{basename(v8)}}{{bn(v8)}}', {'v8': '/a/b/c[1].txt'}, 'c.txtc.txt'
		yield '{{basename(v9, v9b)}}{{bn(v9, v9b)}}', {'v9': '/a/b/c.txt', 'v9b': True}, 'c.txtc.txt'
		# 10
		yield '{{basename(v10, v10b)}}{{bn(v10, v10b)}} {{ext(v10)}}', {'v10': '/a/b/c[1].txt', 'v10b': True}, 'c[1].txtc[1].txt .txt'
		yield '{{filename(v11)}}{{fn(v11)}} {{prefix(v11)}}', {'v11': '/a/b/a.txt'}, 'aa /a/b/a'
		yield '{{filename(v12)}}{{fn(v12)}}', {'v12': '/a/b/b[1].txt'}, 'bb'
		yield '{{filename(v13, v13b)}}{{fn(v13, v13b)}}', {'v13': '/a/b/d.txt', 'v13b': True}, 'dd'
		yield '{{filename(v14, v14b)}}{{fn(v14, v14b)}}', {'v14': '/a/b/c[1].txt', 'v14b': True}, 'c[1]c[1]'
		# 15
		yield '{{R(var1)}}', {'var1': 'NULL'}, 'NULL'
		yield '{{R(var2)}}', {'var2': 'abc'}, "'abc'"
		yield '{% for var in varlist %}{{R(var)}}{% endfor %}', {'varlist': ['abc', 'True', 1, False]}, "'abc'TRUE1FALSE"
		yield '{% if bool(var3) %}1{% else %}0{% endif %}', {'var3': 'abc', 'bool': bool}, '1'
		yield '{% for k,v in data.items() %}{{k}}:{{v}}{% endfor %}', {'data': {'a':1, 'b':2}}, 'a:1b:2'
		# 20
		yield '{{quote(a)}}', {'a':''}, '""'
		yield '{{R(x)}}', {'x': OrderedDict([(u'key1', 'val1'), ('key2', u'val2')])}, "list(key1='val1',key2='val2')"
		yield '{{asquote(b)}}', {'b':[1,2]}, '"1" "2"'
		yield '{{acquote(c)}}', {'c':[1,2]}, '"1", "2"'
		yield '{{squote(d)}}', {'d':'1'}, "'1'"
		# 25
		yield '{{json(e["f"])}}', {'e':{'f':[1,2]}}, '[1, 2]'
		yield '{{os.path.join(g,h)}}', {'g': 'a', 'h': 'b', 'os': __import__('os')}, 'a/b'
		yield """
		#!/usr/bin/env python
		{% if x %}
		{% for y in ylist %}
		{{y}}
		{% endfor %}
		{% endif %}
		""", {'x': True, 'ylist': [1,2,3,4,5]}, """
		#!/usr/bin/env python\n\t\t\n\t\t
		1\n\t\t
		2\n\t\t
		3\n\t\t
		4\n\t\t
		5\n\t\t
		\n\t\t"""
		yield '{{read(a)}}', {'a': __file__}, helpers.readFile(__file__)
		file2read = path.join(path.dirname(__file__), 'helpers.py')
		yield '{{"\\n".join(readlines(a))}}', {'a': file2read}, helpers.readFile(file2read, lambda x: '\n'.join(str(y) for y in x.splitlines() if y))

	@unittest.skipIf(not helpers.moduleInstalled('jinja2'), 'Jinja2 not installed.')
	def testRender(self, s, e, out):
		t = TemplateJinja2(s)
		helpers.assertTextEqual(self, t.render(e), out)

if __name__ == '__main__':
	testly.main(verbosity=2)
