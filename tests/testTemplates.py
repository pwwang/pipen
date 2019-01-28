import testly, helpers, unittest
from os import path
from liquid import Liquid
from collections import OrderedDict
from pyppl.template import Template, TemplateJinja2, TemplateLiquid

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


class TestTemplateLiquid (testly.TestCase):

	def dataProvider_testInit(self):
		yield '', {}
		yield '{{a}}', {'a': 1}

	def testInit(self, source, envs):
		tpl = TemplateLiquid(source, **envs)
		helpers.assertTextEqual(self, tpl.source, source)
		self.assertDictContains(Template.DEFAULT_ENVS, tpl.envs)
		self.assertDictContains(envs, tpl.envs)
		self.assertIsInstance(tpl.engine, Liquid)

	def dataProvider_testStr(self):
		yield '',
		yield 'a',
		yield '{{a}}',
		yield '{{a}}\n{{b}}',

	def testStr(self, source):
		tpl = TemplateLiquid(source)
		lines = source.splitlines()
		if len(lines) <= 1:
			self.assertEqual(str(tpl), 'TemplateLiquid < %s >' % ''.join(lines))
		else:
			helpers.assertTextEqual(self, str(tpl), '\n'.join(
				['TemplateLiquid <<<'] +
				['\t' + line for line in tpl.source.splitlines()] +
				['>>>'])
			)

	def dataProvider_testRender(self):
		source = """
		whatever
		{% if a in b %}
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
		a
		"""
		yield source, data, out

		data = {'b': 'abc', 'a': 'd', 'y': [1,2,3]}
		out  = """
		whatever
		\n\t\t\t1
		\n\t\t\t2
		\n\t\t\t3
		\n\t\t"""

		yield '{{True | R}}', {}, 'TRUE'
		yield '{{None | R}}', {}, 'NULL'
		yield '{{"+INF" | R}}', {}, 'Inf'
		yield '{{"-inf" | R}}', {}, '-Inf'
		yield '{{"r:list(1,2,3)" | R}}', {}, 'list(1,2,3)'
		yield '{{[1,2,3] | R}}', {}, 'c(1,2,3)'
		yield '{{[1,2,3] | Rlist}}', {}, 'as.list(c(1,2,3))'
		yield '{{ {0:1} | Rlist}}', {}, 'list(1)'
		yield '{{ {0:1} | Rlist: False}}', {}, 'list(`0`=1)'
		yield '{{x | render}}', {'x': '{{i}}', 'i': 2}, '2'
		yield '{{x | lambda a, render = render:render(a[0])}}', {'x': ('{{i}}', 1), 'i': 2}, '2'

	def testRender(self, source, data, out):
		tpl = TemplateLiquid(source)
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
		yield '{{basename(v8)}}{{bn(v8)}}', {'v8': '/a/b/[1]c.txt'}, 'c.txtc.txt'
		yield '{{basename(v9, v9b)}}{{bn(v9, v9b)}}', {'v9': '/a/b/c.txt', 'v9b': True}, 'c.txtc.txt'
		# 10
		yield '{{basename(v10, v10b)}}{{bn(v10, v10b)}} {{ext(v10)}}', {'v10': '/a/b/c[1].txt', 'v10b': True}, 'c[1].txtc[1].txt .txt'
		yield '{{filename(v11)}}{{fn(v11)}} {{prefix(v11)}}', {'v11': '/a/b/a.txt'}, 'aa /a/b/a'
		yield '{{filename(v12)}}{{fn(v12)}}', {'v12': '/a/b/[1]b.txt'}, 'bb'
		yield '{{filename(v13, v13b)}}{{fn(v13, v13b)}}', {'v13': '/a/b/d.txt', 'v13b': True}, 'dd'
		yield '{{filename(v14, v14b)}}{{fn(v14, v14b)}}', {'v14': '/a/b/[1]c.txt', 'v14b': True}, '[1]c[1]c'
		# 15
		yield '{{R(var1)}}', {'var1': 'NULL'}, 'NULL'
		yield '{{R(var2)}}', {'var2': 'abc'}, "'abc'"
		yield '{% for var in varlist %}{{R(var)}}{% endfor %}', {'varlist': ['abc', 'True', 1, False]}, "'abc'TRUE1FALSE"
		yield '{% if bool(var3) %}1{% else %}0{% endif %}', {'var3': 'abc', 'bool': bool}, '1'
		yield '{% for k,v in data.items() %}{{k}}:{{v}}{% endfor %}', {'data': OrderedDict([('a', 1), ('b', 2)])}, 'a:1b:2'
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
		yield '{{render(x)}}', {'x': '{{i}}', 'i': 2}, '2'
		yield '{{render(x[0])}}', {'x': ('{{i}}', 1), 'i': 2}, '2'

	@unittest.skipIf(not helpers.moduleInstalled('jinja2'), 'Jinja2 not installed.')
	def testRender(self, s, e, out):
		t = TemplateJinja2(s)
		helpers.assertTextEqual(self, t.render(e), out)

if __name__ == '__main__':
	testly.main(verbosity=2)
