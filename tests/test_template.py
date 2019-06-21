import pytest
from pathlib import Path
from liquid import Liquid, LiquidRenderError
from collections import OrderedDict
from pyppl.template import Template, TemplateJinja2, TemplateLiquid

def installed(module):
	try:
		__import__(module)
		return True
	except ImportError:
		return False

def assertDictContains(subdict, totaldict):
	total = totaldict.copy()
	total.update(subdict)
	assert total == totaldict

class TestTemplate:

	@pytest.mark.parametrize('source, envs', [
		('', {}),
		('{{a}}', {'a': 1})
	])
	def test_Init(self, source, envs):
		tpl = Template(source, **envs)
		assert tpl.source == source

		assertDictContains(Template.DEFAULT_ENVS, tpl.envs)
		assertDictContains(envs, tpl.envs)

	@pytest.mark.parametrize('source, envs, newenvs', [
		('', {}, {}),
		('{{a}}', {'a': 1}, {}),
		('{{a}}', {'a': 1}, {'b': 2}),
	])
	def testRegisterEnvs(self, source, envs, newenvs):
		tpl = Template(source, **envs)
		tpl.registerEnvs(**newenvs)
		assert tpl.source == source
		assertDictContains(Template.DEFAULT_ENVS, tpl.envs)
		assertDictContains(envs, tpl.envs)
		assertDictContains(newenvs, tpl.envs)

	@pytest.mark.parametrize('t,s', [
		(Template(''), 'Template <  >')
	])
	def testStr(self, t, s):
		assert str(t) == s

	@pytest.mark.parametrize('t,s', [
		(Template(''), 'Template <  >')
	])
	def testRepr(self, t, s):
		assert repr(t) == s

	def testRender(self):
		with pytest.raises(NotImplementedError):
			Template('').render({})


class TestTemplateLiquid:

	@pytest.mark.parametrize('source, envs', [
		('', {}),
		('{{a}}', {'a': 1})
	])
	def testInit(self, source, envs):
		tpl = TemplateLiquid(source, **envs)
		assert tpl.source == source
		assertDictContains(Template.DEFAULT_ENVS, tpl.envs)
		assertDictContains(envs, tpl.envs)
		assert isinstance(tpl.engine, Liquid)

	@pytest.mark.parametrize('source', [
		'',
		'a',
		'{{a}}',
		'{{a}}\n{{b}}',
	])
	def testStr(self, source):
		tpl = TemplateLiquid(source)
		lines = source.splitlines()
		if len(lines) <= 1:
			assert str(tpl) == 'TemplateLiquid < %s >' % ''.join(lines)
		else:
			assert str(tpl) == '\n'.join(
				['TemplateLiquid <<<'] +
				['\t' + line for line in tpl.source.splitlines()] +
				['>>>'])

	@pytest.mark.parametrize('source, data, out', [
		("""
		whatever
		{% if a in b %}
		{{a}}
		{% else %}
			{% for x in y %}
			{{x}}
			{% endfor %}
		{% endif %}
		""", {'b': 'abc', 'a': 'd', 'y': [1,2,3]}, """
		whatever
			1
			2
			3
		"""),

		('{{True | R}}', {}, 'TRUE'),
		('{{None | R}}', {}, 'NULL'),
		('{{"+INF" | R}}', {}, 'Inf'),
		('{{"-inf" | R}}', {}, '-Inf'),
		('{{"r:list(1,2,3)" | R}}', {}, 'list(1,2,3)'),
		('{{[1,2,3] | R}}', {}, 'c(1,2,3)'),
		('{{[1,2,3] | Rlist}}', {}, 'as.list(c(1,2,3))'),
		('{{ {0:1} | Rlist}}', {}, 'list(1)'),
		('{{ {0:1} | Rlist: False}}', {}, 'list(`0`=1)'),
		('{{x | render}}', {'x': '{{i}}', 'i': 2}, '2'),
		('{{x | lambda a, render = render:render(a[0])}}', {'x': ('{{i}}', 1), 'i': 2}, '2'),
	])
	def testRender(self, source, data, out):
		tpl = TemplateLiquid(source)
		assert tpl.render(data) == out

	def test_readlines_skip_empty(self, tmp_path):
		tmpfile = tmp_path / 'test_readlines_skip_empty.txt'
		tmpfile.write_text("a\n\nb\n")
		assert TemplateLiquid('{{readlines(a) | @join: "."}}').render({'a': tmpfile}) == "a.b"
		assert TemplateLiquid('{{readlines(a, False) | @join: "."}}').render({'a': tmpfile}) == "a..b"

	def test_filename_no_ext(self):
		assert TemplateLiquid('{{a|fn}}').render({'a': 'abc'}) == "abc"

	def test_render_func(self):
		assert TemplateLiquid('{{x | render}}').render({'x': '{{i}}', 'i': 2}) == '2'
		assert TemplateLiquid('{{x | render}}').render({'x': [], 'i': 2}) == '[]'
		liquid = TemplateLiquid('{{x | render}}')
		with pytest.raises(LiquidRenderError):
			liquid.render({'x': '', '__engine': None})

	def test_box(self):
		with pytest.raises(LiquidRenderError):
			TemplateLiquid('{{x|box}}').render({'x': []})
		with pytest.raises(LiquidRenderError):
			TemplateLiquid('{{x|obox}}').render({'x': []})
		TemplateLiquid('{{x|box}}').render({'x': {}}) == {}
		TemplateLiquid('{{x|obox}}').render({'x': {}}) == {}


@pytest.mark.skipif(not installed('jinja2'), reason = 'Jinja2 is not installed')
class TestTemplateJinja2:

	@pytest.mark.parametrize('source, envs', [
		('', {}),
		('{{a}}', {'a': 1})
	])
	def testInit(self, source, envs):
		import jinja2
		tpl = TemplateJinja2(source, **envs)
		assert tpl.source == source
		assertDictContains(Template.DEFAULT_ENVS, tpl.envs)
		assertDictContains(envs, tpl.envs)
		assert isinstance(tpl.engine, jinja2.Template)

	@pytest.mark.parametrize('source', [
		'',
		'a',
		'{{a}}',
		'{{a}}\n{{b}}',

	])
	def testStr(self, source):
		tpl = TemplateJinja2(source)
		lines = source.splitlines()
		if len(lines) <= 1:
			assert str(tpl) == 'TemplateJinja2 < %s >' % ''.join(lines)
		else:
			assert str(tpl) == '\n'.join(
				['TemplateJinja2 <<<'] +
				['\t' + line for line in tpl.source.splitlines()] +
				['>>>'])

	@pytest.mark.parametrize('s,e,out', [
		# 0
		('{{name}}', {'name': 'John'}, 'John'),
		('{{names[0]}}', {'names': ['John', 'Tom']}, 'John'),
		('{{concate(v1, v2)}}', {'v1': 'hello', 'v2': 'world', 'concate': lambda x,y: x+y}, 'helloworld'),
		('{{R(v23)}}', {'v23': '"FALSE"'}, '\'"FALSE"\''),
		('{{R(v3)}}', {'v3': 'false'}, "FALSE"),
		# 5
		('{{realpath(v4)}}', {'v4': __file__}, str(Path(__file__).resolve())),
		#(('{{readlink(v5)}}', {'v5': path.join(path.dirname(path.realpath(path.abspath(__file__))),), 'helpers.py')(, path.relpath(path.jo(path.dirname(path.dirname(path.abspath(__file__))), ),'bin', 'helpers.py'))),
		('{{dirname(v6)}}', {'v6': '/a/b/c'}, '/a/b'),
		('{{basename(v7)}}{{bn(v7)}}', {'v7': '/a/b/c.txt'}, 'c.txtc.txt'),
		('{{basename(v8)}}{{bn(v8)}}', {'v8': '/a/b/[1]c.txt'}, 'c.txtc.txt'),
		('{{basename(v9, v9b)}}{{bn(v9, v9b)}}', {'v9': '/a/b/c.txt', 'v9b': True}, 'c.txtc.txt'),
		# 10
		('{{basename(v10, v10b)}}{{bn(v10, v10b)}} {{ext(v10)}}', {'v10': '/a/b/c[1].txt', 'v10b': True}, 'c[1].txtc[1].txt .txt'),
		('{{filename(v11)}}{{fn(v11)}} {{prefix(v11)}}', {'v11': '/a/b/a.txt'}, 'aa /a/b/a'),
		('{{filename(v12)}}{{fn(v12)}}', {'v12': '/a/b/[1]b.txt'}, 'bb'),
		('{{filename(v13, v13b)}}{{fn(v13, v13b)}}', {'v13': '/a/b/d.txt', 'v13b': True}, 'dd'),
		('{{filename(v14, v14b)}}{{fn(v14, v14b)}}', {'v14': '/a/b/[1]c.txt', 'v14b': True}, '[1]c[1]c'),
		# 15
		('{{R(var1)}}', {'var1': 'NULL'}, 'NULL'),
		('{{R(var2)}}', {'var2': 'abc'}, "'abc'"),
		('{% for var in varlist %}{{R(var)}}{% endfor %}', {'varlist': ['abc', 'True', 1, False]}, "'abc'TRUE1FALSE"),
		('{% if bool(var3) %}1{% else %}0{% endif %}', {'var3': 'abc', 'bool': bool}, '1'),
		('{% for k,v in data.items() %}{{k}}:{{v}}{% endfor %}', {'data': OrderedDict([('a', 1), ('b', 2)])}, 'a:1b:2'),
		# 20
		('{{quote(a)}}', {'a':''}, '""'),
		('{{R(x)}}', {'x': OrderedDict([(u'key1', 'val1'), ('key2', u'val2')])}, "list(`key1`='val1',`key2`='val2')"),
		('{{asquote(b)}}', {'b':[1,2]}, '"1" "2"'),
		('{{acquote(c)}}', {'c':[1,2]}, '"1", "2"'),
		('{{squote(d)}}', {'d':'1'}, "'1'"),
		# 25
		('{{json(e["f"])}}', {'e':{'f':[1,2]}}, '[1, 2]'),
		('{{os.path.join(g,h)}}', {'g': 'a', 'h': 'b', 'os': __import__('os')}, 'a/b'),
		("""
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
		\n\t\t"""),
		(
			'{{read(a).strip()}}',
			{'a': Path(__file__).parent / 'mocks' / 'srun'},
			(Path(__file__).parent / 'mocks' / 'srun').read_text().strip()),
		(
			'{{"\\n".join(readlines(a)).strip()}}',
			{'a': Path(__file__).parent / 'mocks' / 'srun'},
			(Path(__file__).parent / 'mocks' / 'srun').read_text().strip()),
		('{{render(x)}}', {'x': '{{i}}', 'i': 2}, '2'),
		('{{render(x[0])}}', {'x': ('{{i}}', 1), 'i': 2}, '2'),
	])
	def testRender(self, s, e, out):
		t = TemplateJinja2(s)
		assert t.render(e) == out

