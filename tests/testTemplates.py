import path, six, unittest
from os import path
from pyppl.templates import Template, TemplatePyPPL, template_pyppl
from pyppl.templates.template_jinja2 import TemplateJinja2
from pyppl.templates.template_pyppl import TemplatePyPPLCodeBuilder, TemplatePyPPLSyntaxError, TemplatePyPPLRenderError

def moduleInstalled(mod):
	try:
		__import__(mod)
		return True
	except ImportError:
		return False

class TestTemplatePyPPLCodeBuilder(unittest.TestCase):

	def testInit(self):
		cb = TemplatePyPPLCodeBuilder()
		self.assertIsInstance(cb, TemplatePyPPLCodeBuilder)
		self.assertEqual(cb.code, [])
		self.assertEqual(cb.nIndent, 0)
		self.assertEqual(str(cb), "")
	
	def testAddLine(self):
		cb = TemplatePyPPLCodeBuilder()
		cb.addLine("Hello\nWhatever")
		self.assertEqual(str(cb), "Hello\nWhatever\n")

	def testAddSection(self):
		cb = TemplatePyPPLCodeBuilder()
		cb.addLine("line1")
		sec = cb.addSection()
		cb.addLine("line2")
		sec.addLine("line1.5")
		self.assertEqual(str(cb), "line1\nline1.5\nline2\n")

	def testInDedent(self):
		cb = TemplatePyPPLCodeBuilder(8)
		cb.indent()
		cb.addLine("abc")
		self.assertEqual(str(cb), ("\t" * 9) + "abc\n")
		self.assertEqual(cb.nIndent, 9)
		cb.dedent()
		self.assertEqual(cb.nIndent, 8)
		
	def testGetGlobals(self):
		cb = TemplatePyPPLCodeBuilder()
		cb.addLine('def func():')
		cb.indent()
		sec = cb.addSection()
		sec.addLine('a = 1')
		sec.addLine('b = 2')
		cb.addLine('return a + b')
		cb.dedent()
		func = cb.getGlobals()['func']
		self.assertEqual(func(), 3)
		



class TestTemplatePyPPL (unittest.TestCase):
	
	
	
	def testPyPPLInit(self):
		t = TemplatePyPPL('')
		self.assertIsInstance(t, Template)
		self.assertIsInstance(t, TemplatePyPPL)
		self.assertEqual(t.envs, Template.DEFAULT_ENVS)
		self.assertIsInstance(t.engine, template_pyppl.TemplatePyPPLEngine)

	@unittest.skipIf(not moduleInstalled('jinja2'), 'Jinja2 not installed.')
	def testJinja2Init(self):
		import jinja2
		t = TemplateJinja2('')
		self.assertIsInstance(t, TemplateJinja2)
		self.assertIsInstance(t.engine, jinja2.Template)
		
	data = [
		('{{name}}', {'name': 'John'}, 'John'),	
		('{{names[0]}}', {'names': ['John', 'Tome']}, 'John'),
		('{{names2.1}}', {'names2': ['John', 'Tome']}, 'Tome'),
		('{{names3.1[:-1]}}', {'names3': ['John', 'Tome']}, 'Tom'),
		('{{names4.1.upper()}}', {'names4': ['John', 'Tome']}, 'TOME'),
		('{{names5.1 | [:-1] | .upper()}}', {'names5': ['John', 'Tome']}, 'TOM'),
		('{{names6 | [1][:-1] | .upper()}}', {'names6': ['John', 'Tome']}, 'TOM'),
		('{{names7 | lambda x: x[1].upper()}}', {'names7': ['John', 'Tome']}, 'TOME'),
		('{{v1, v2|concate}}', {'v1': 'hello', 'v2': 'world', 'concate': lambda x,y: x+y}, 'helloworld'),
		('{{v3 | R}}', {'v3': 'false'}, 'FALSE'),
		('{{v4|realpath}}', {'v4': __file__}, path.realpath(__file__)),
		('{{v5|readlink}}', {'v5': path.join(path.dirname(path.realpath(path.abspath(__file__))), 'path.py')}, path.relpath(path.join(path.dirname(path.dirname(path.abspath(__file__))), 'bin', 'path.py'), start = path.dirname(__file__))),
		('{{v6|dirname}}', {'v6': '/a/b/c'}, '/a/b'),
		('{{v7|basename}}{{v7|bn}}', {'v7': '/a/b/c.txt'}, 'c.txtc.txt'),
		('{{v8|basename}}{{v8|bn}}', {'v8': '/a/b/c[1].txt'}, 'c.txtc.txt'),
		('{{v9, v9b|basename}}{{v9, v9b|bn}}', {'v9': '/a/b/c.txt', 'v9b': True}, 'c.txtc.txt'),
		('{{v10, v10b|basename}}{{v10, v10b|bn}} {{v10|ext}}', {'v10': '/a/b/c[1].txt', 'v10b': True}, 'c[1].txtc[1].txt .txt'),
		('{{v11|filename}}{{v11|fn}} {{v11|prefix}}', {'v11': '/a/b/a.txt'}, 'aa /a/b/a'),
		('{{v12|filename}}{{v12|fn}}', {'v12': '/a/b/b[1].txt'}, 'bb'),
		('{{v13, v13b|filename}}{{v13, v13b|fn}}', {'v13': '/a/b/d.txt', 'v13b': True}, 'dd'),
		('{{v14, v14b|filename}}{{v14, v14b|fn}}', {'v14': '/a/b/c[1].txt', 'v14b': True}, 'c[1]c[1]'),
		('{{var1|R}}', {'var1': 'NULL'}, 'NULL'),
		('{{var2|R}}', {'var2': 'abc'}, '"abc"'),
		('{% for var in varlist %}{{var|R}}{% endfor %}', {'varlist': ['abc', 'True', 1, False]}, '"abc"TRUE1FALSE'),
		('{% if var3|bool %}1{% else %}0{% endif %}', {'var3': 'abc', 'bool': bool}, '1'),
		('{% for k , v in data.items() %}{{k}}:{{v}}{% endfor %}', {'data': {'a':1, 'b':2}}, 'a:1b:2'),
		('{{a|quote}}', {'a':''}, '""'),
		('{{b|asquote}}', {'b':[1,2]}, '"1" "2"'),
		('{{c|acquote}}', {'c':[1,2]}, '"1", "2"'),
		('{{d|squote}}', {'d':1}, "'1'"),
		('{{e.f|json}}', {'e':{'f':[1,2]}}, '[1, 2]'),
		('{{g,h | os.path.join}}', {'g': 'a', 'h': 'b', 'os': __import__('os')}, 'a/b'),
	]
	
	def testPyPPLRender(self):
		for d in self.data:
			d0, d1, d2 = d
			t  = TemplatePyPPL(d0)
			self.assertEqual(t.render(d1), d2)
		
		t  = TemplatePyPPL('{{a|read}}')
		self.assertIn('{{a|read}}', t.render({'a': __file__}))
		t  = TemplatePyPPL('{{a|readlines}}')
		self.assertIn("import path, unittest", t.render({'a': __file__}))
		t = TemplatePyPPL('{{a.x, b.y | lambda x,y: x+y}}')
		self.assertEqual(t.render({'a': {'x': 1}, 'b': {'y': 2}}), '3')
		t = TemplatePyPPL('{{a.x, b.y | lambda x,y: x+y}}')
		self.assertEqual(t.render({'a': {'x': 1}, 'b': {'y': 2}}), '3')
		t = TemplatePyPPL('{{a.b["1"][0](",")}}')
		self.assertEqual(t.render({'a': {'b': {"1": [lambda x: x]}}}), ',')
		
	def testExceptions(self):
		# unmatched tag
		src = '{% if True %} {% if False %} {% endif %}'
		six.assertRaisesRegex(
			self,
			TemplatePyPPLSyntaxError,
			r'line 1: \{% if True %\}',
			TemplatePyPPL,
			src
		)
		
	def testExceptions1(self):
		# expression
		src = '{{ a }}'
		t   = TemplatePyPPL(src)
		six.assertRaisesRegex(
			self,
			TemplatePyPPLRenderError,
			r'unknown template variable: a',
			t.render
		)
	
	def testExceptions2(self):
		# don't understand if
		src = '{% if %}'
		six.assertRaisesRegex(
			self,
			TemplatePyPPLSyntaxError,
			r'Don\'t understand if\/elif: \'in template line 1: \{% if %\}\'',
			TemplatePyPPL,
			src
		)
		
		# if error
		src = '{% if a %}1{% endif %}'
		t   = TemplatePyPPL(src)
		six.assertRaisesRegex(
			self,
			TemplatePyPPLRenderError,
			r"KeyError: 'a', unknown template variable: a, in template line 1: \{% if a %\}",
			t.render
		)
		
		# don't understand else
		src = '{% else a %}'
		six.assertRaisesRegex(
			self,
			TemplatePyPPLSyntaxError,
			r'Don\'t understand else: \'in template line 1: \{% else a %\}\'',
			TemplatePyPPL,
			src
		)
		
		# don't understand for
		src = '{% for a %}'
		six.assertRaisesRegex(
			self,
			TemplatePyPPLSyntaxError,
			r'Don\'t understand for: \'in template line 1: \{% for a %\}\'',
			TemplatePyPPL,
			src
		)
		
		# don't understand end
		src = '{% endx %}'
		six.assertRaisesRegex(
			self,
			TemplatePyPPLSyntaxError,
			r'Too many ends: \'in template line 1: \{% endx %\}\'',
			TemplatePyPPL,
			src
		)
		
		# literal error
		src = """
{% if x %}

{{a.b}}
{% endif %}
"""
		t   = TemplatePyPPL(src)
		six.assertRaisesRegex(
			self,
			TemplatePyPPLRenderError,
			r"TypeError: 'int' object has no attribute '__getitem__', in template line 4: \{\{a.b\}\}",
			t.render,
			{'a': 1, 'x': True}
		)

	@unittest.skipIf(not moduleInstalled('jinja2'), 'Jinja2 not installed.')
	def testJinja2Render(self):
		data = [
			('{{name}}', {'name': 'John'}, 'John'),
			('{{names[0]}}', {'names': ['John', 'Tom']}, 'John'),
			('{{concate(v1, v2)}}', {'v1': 'hello', 'v2': 'world', 'concate': lambda x,y: x+y}, 'helloworld'),
			('{{R(v3)}}', {'v3': 'false'}, 'FALSE'),
			('{{realpath(v4)}}', {'v4': __file__}, path.realpath(__file__)),
			('{{readlink(v5)}}', {'v5': path.join(path.dirname(path.realpath(path.abspath(__file__))), 'path.py')}, path.relpath(path.join(path.dirname(path.dirname(path.abspath(__file__))), 'bin', 'path.py'))),
			('{{dirname(v6)}}', {'v6': '/a/b/c'}, '/a/b'),
			('{{basename(v7)}}{{bn(v7)}}', {'v7': '/a/b/c.txt'}, 'c.txtc.txt'),
			('{{basename(v8)}}{{bn(v8)}}', {'v8': '/a/b/c[1].txt'}, 'c.txtc.txt'),
			('{{basename(v9, v9b)}}{{bn(v9, v9b)}}', {'v9': '/a/b/c.txt', 'v9b': True}, 'c.txtc.txt'),
			('{{basename(v10, v10b)}}{{bn(v10, v10b)}} {{ext(v10)}}', {'v10': '/a/b/c[1].txt', 'v10b': True}, 'c[1].txtc[1].txt .txt'),
			('{{filename(v11)}}{{fn(v11)}} {{prefix(v11)}}', {'v11': '/a/b/a.txt'}, 'aa /a/b/a'),
			('{{filename(v12)}}{{fn(v12)}}', {'v12': '/a/b/b[1].txt'}, 'bb'),
			('{{filename(v13, v13b)}}{{fn(v13, v13b)}}', {'v13': '/a/b/d.txt', 'v13b': True}, 'dd'),
			('{{filename(v14, v14b)}}{{fn(v14, v14b)}}', {'v14': '/a/b/c[1].txt', 'v14b': True}, 'c[1]c[1]'),
			('{{R(var1)}}', {'var1': 'NULL'}, 'NULL'),
			('{{R(var2)}}', {'var2': 'abc'}, '"abc"'),
			('{% for var in varlist %}{{R(var)}}{% endfor %}', {'varlist': ['abc', 'True', 1, False]}, '"abc"TRUE1FALSE'),
			('{% if bool(var3) %}1{% else %}0{% endif %}', {'var3': 'abc', 'bool': bool}, '1'),
			('{% for k,v in data.items() %}{{k}}:{{v}}{% endfor %}', {'data': {'a':1, 'b':2}}, 'a:1b:2'),
			('{{quote(a)}}', {'a':''}, '""'),
			('{{asquote(b)}}', {'b':[1,2]}, '"1" "2"'),
			('{{acquote(c)}}', {'c':[1,2]}, '"1", "2"'),
			('{{squote(d)}}', {'d':1}, "'1'"),
			('{{json(e["f"])}}', {'e':{'f':[1,2]}}, '[1, 2]'),
		]
		d0 = ''
		d1 = {}
		d2 = ''
		for d in data:
			d0 += d[0]
			d1.update(d[1])
			d2 += d[2]
			t = TemplateJinja2(d[0])
			self.assertEqual(t.render(d[1]), d[2])
		t  = TemplateJinja2(d0)
		self.assertEqual(t.render(d1), d2)
		t  = TemplateJinja2('{{read(a)}}')
		self.assertIn('{{read(a)}}', t.render({'a': __file__}))
		t  = TemplateJinja2('{{readlines(a)}}')
		self.assertIn("import path, unittest", t.render({'a': __file__}))

	def testStr(self):
		t = TemplatePyPPL('')
		self.assertIn('TemplatePyPPL with source:', str(t))
		if moduleInstalled('jinja2'):
			t = TemplateJinja2('')
			self.assertIn('TemplateJinja2 with source:', str(t))

	def testRenderFile(self):
		t = TemplatePyPPL('{{name}}')
		t.registerEnvs(name = 'a')
		self.assertEqual(t.render(), 'a')

if __name__ == '__main__':
	unittest.main(verbosity=2)
