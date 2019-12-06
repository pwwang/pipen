import pytest
import inspect
import json
from pathlib import Path
from glob import glob
from os import path, readlink
from liquid import Liquid, LiquidRenderError
from collections import OrderedDict
from pyppl.template import Template, TemplateJinja2, TemplateLiquid
from diot import Diot, OrderedDiot

HERE = Path(__file__).resolve().parent

class _TemplateFilter(object):
	"""
	A set of builtin filters
	"""

	@staticmethod
	def read(var):
		"""Read the contents from a file"""
		with open(var) as fvar:
			return fvar.read()

	@staticmethod
	def readlines(var, skip_empty_lines = True):
		"""Read the lines from a file"""
		ret = []
		with open(var) as fvar:
			for line in fvar:
				line = line.rstrip('\n\r')
				if not line and skip_empty_lines:
					continue
				ret.append(line)
		return ret

	@staticmethod
	def basename(var, orig = False):
		"""Get the basename of a path"""
		bname = path.basename(var)
		if orig or not bname.startswith('['):
			return bname

		return bname[bname.find(']')+1:]

	@staticmethod
	def filename(var, orig = False, dot = -1):
		"""
		Return the stem of the basename (stripping extension(s))
		@params:
			`var`: The path
			`orig`: If the path is a renamed file (like: `origin[1].txt`),
				- whether return its original filename or the parsed filename (`origin.txt`)
			`dot`: Strip to which dot.
				- `-1`: the last one
				- `-2`: the 2nd last one ...
				- `1` : remove all dots.
		"""
		bname = _TemplateFilter.basename(var, orig)
		if '.' not in bname:
			return bname
		return '.'.join(bname.split('.')[0:dot])

	@staticmethod
	def prefix(var, orig = False, dot = -1):
		"""Get the prefix part of a path"""
		return path.join(path.dirname(var), _TemplateFilter.filename(var, orig, dot))

	# pylint: disable=invalid-name,too-many-return-statements
	@staticmethod
	def R(var, ignoreintkey = True):
		"""Convert a value into R values"""
		if var is True:
			return 'TRUE'
		if var is False:
			return 'FALSE'
		if var is None:
			return 'NULL'
		if isinstance(var, str):
			if var.upper() in ['+INF', 'INF']:
				return 'Inf'
			if var.upper() == '-INF':
				return '-Inf'
			if var.upper() == 'TRUE':
				return 'TRUE'
			if var.upper() == 'FALSE':
				return 'FALSE'
			if var.upper() == 'NA' or var.upper() == 'NULL':
				return var
			if var.startswith('r:') or var.startswith('R:'):
				return str(var)[2:]
			return repr(str(var))
		if isinstance(var, Path):
			return repr(str(var))
		if isinstance(var, (list, tuple, set)):
			return 'c({})'.format(','.join([_TemplateFilter.R(i) for i in var]))
		if isinstance(var, dict):
			# list allow repeated names
			return 'list({})'.format(','.join([
				'`{0}`={1}'.format(
					k,
					_TemplateFilter.R(v)) if isinstance(k, int) and not ignoreintkey else \
					_TemplateFilter.R(v) if isinstance(k, int) and ignoreintkey else \
					'`{0}`={1}'.format(str(k).split('#')[0], _TemplateFilter.R(v))
				for k, v in sorted(var.items())]))
		return repr(var)

	@staticmethod
	def Rlist(var, ignoreintkey = True): # pylint: disable=invalid-name
		"""Convert a dict into an R list"""
		assert isinstance(var, (list, tuple, set, dict))
		if isinstance(var, dict):
			return _TemplateFilter.R(var, ignoreintkey)
		return 'as.list({})'.format(_TemplateFilter.R(var, ignoreintkey))

	@staticmethod
	def render(var, data = None):
		"""
		Render a template variable, using the shared environment
		"""
		if not isinstance(var, str):
			return var
		frames = inspect.getouterframes(inspect.currentframe())
		data   = data or {}
		for frame in frames:
			lvars = frame[0].f_locals
			if lvars.get('__engine') == 'liquid':
				evars = lvars.get('_liquid_context', {})
				if 'true' in evars:
					del evars['true']
				if 'false' in evars:
					del evars['false']
				if 'nil' in evars:
					del evars['nil']
				if '_liquid_liquid_filters' in evars:
					del evars['_liquid_liquid_filters']
				break
			if '_Context__self' in lvars:
				evars = dict(lvars['_Context__self'])
				break

		engine = evars.get('__engine')
		if not engine:
			raise RuntimeError(
				"I don't know which template engine to use to render {}...".format(var[:10]))

		engine = TemplateJinja2 if engine == 'jinja2' else TemplateLiquid
		return engine(var, **evars).render(data)

	@staticmethod
	def diot(var):
		"""
		Turn a dict into a Diot object
		"""
		if not isinstance(var, dict):
			raise TypeError('Cannot coerce non-dict object to Diot.')
		return 'Diot(%r)' % var.items()

	@staticmethod
	def odiot(var):
		"""
		Turn a dict into an ordered Diot object
		"""
		if not isinstance(var, dict):
			raise TypeError('Cannot coerce non-dict object to OrderedDiot.')
		return 'OrderedDiot(%r)' % var.items()

	@staticmethod
	def glob1(*paths, first = True):
		"""
		Return the paths matches the paths
		"""
		ret = glob(path.join(*paths))
		if ret and first:
			return ret[0]
		if not ret and first:
			return '__NoNeXiStFiLe__'
		return ret

@pytest.fixture
def default_envs():
	return {
		'Diot'      : Diot,
		'ODiot'     : OrderedDiot,
		'R'        : _TemplateFilter.R,
		'Rvec'     : _TemplateFilter.R, # will be deprecated!
		'Rlist'    : _TemplateFilter.Rlist,
		'realpath' : path.realpath,
		'readlink' : readlink,
		'dirname'  : path.dirname,
		# /a/b/c[1].txt => c.txt
		'basename' : _TemplateFilter.basename,
		'bn'       : _TemplateFilter.basename,
		'diot'      : _TemplateFilter.diot,
		'odiot'     : _TemplateFilter.odiot,
		'stem'     : _TemplateFilter.filename,
		'filename' : _TemplateFilter.filename,
		'fn'       : _TemplateFilter.filename,
		# /a/b/c.d.e.txt => c
		'filename2': lambda var, orig = False, dot = 1: _TemplateFilter.filename(var, orig, dot),
		'fn2'      : lambda var, orig = False, dot = 1: _TemplateFilter.filename(var, orig, dot),
		# /a/b/c.txt => .txt
		'ext'      : lambda var: path.splitext(var)[1],
		'glob1'    : _TemplateFilter.glob1,
		# /a/b/c[1].txt => /a/b/c
		'prefix'   : _TemplateFilter.prefix,
		# /a/b/c.d.e.txt => /a/b/c
		'prefix2'  : lambda var, orig = False, dot = 1: _TemplateFilter.prefix(var, orig, dot),
		'quote'    : lambda var: json.dumps(str(var)),
		'squote'   : repr,
		'json'     : json.dumps,
		'read'     : _TemplateFilter.read,
		'readlines': _TemplateFilter.readlines,
		'render'   : _TemplateFilter.render,
		# single quote of all elements of an array
		'asquote'  : lambda var: '''%s''' % (" " .join([json.dumps(str(e)) for e in var])),
		# double quote of all elements of an array
		'acquote'  : lambda var: """%s""" % (", ".join([json.dumps(str(e)) for e in var]))
	}

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
		("""{% mode compact %}
		whatever
		{%- if a in b -%}
		{{a}}
		{%- else -%}
			{% for x in y %}
			{{x-}}
			{% endfor %}
		{% endif %}
		""", {'b': 'abc', 'a': 'd', 'y': [1,2,3]}, """		whatever123"""),

		('{% python from pathlib import Path %}{{Path("/a/b/c") | R}}', {}, "'/a/b/c'"),
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
		#('{{x | lambda a, render = render:render(a[0])}}', {'x': ('{{i}}', 1), 'i': 2}, '2'),
		('{{glob1(here, "test_template.py")}}', {'here': HERE}, str(Path(__file__).resolve())),
		('{{glob1(here, "test_template_not_exists.py")}}', {'here': HERE}, '__NoNeXiStFiLe__'),
		('{{glob1(here, "test_template.py", first = False)[0]}}', {'here': HERE}, str(Path(__file__).resolve())),
	])
	def testRender(self, source, data, out, default_envs):
		tpl = TemplateLiquid(source, **default_envs)
		assert tpl.render(data) == out

	def test_readlines_skip_empty(self, tmp_path, default_envs):
		tmpfile = tmp_path / 'test_readlines_skip_empty.txt'
		tmpfile.write_text("a\n\nb\n")
		assert TemplateLiquid('{{readlines(a) | @join: "."}}', **default_envs).render({'a': tmpfile}) == "a.b"
		assert TemplateLiquid('{{readlines(a, False) | @join: "."}}', **default_envs).render({'a': tmpfile}) == "a..b"

	def test_filename_no_ext(self, default_envs):
		assert TemplateLiquid('{{a|fn}}', **default_envs).render({'a': 'abc'}) == "abc"

	def test_render_func(self, default_envs):
		assert TemplateLiquid('{{x | render}}', **default_envs).render({'x': '{{i}}', 'i': 2}) == '2'
		assert TemplateLiquid('{{x | render}}', **default_envs).render({'x': [], 'i': 2}) == '[]'
		liquid = TemplateLiquid('{{x | render}}', **default_envs)
		with pytest.raises(LiquidRenderError):
			liquid.render({'x': '', '__engine': None})

	def test_diot(self, default_envs):
		with pytest.raises(LiquidRenderError):
			TemplateLiquid('{{x|diot}}', **default_envs).render({'x': []})
		with pytest.raises(LiquidRenderError):
			TemplateLiquid('{{x|odiot}}', **default_envs).render({'x': []})
		TemplateLiquid('{{x|diot}}', **default_envs).render({'x': {}}) == {}
		TemplateLiquid('{{x|odiot}}', **default_envs).render({'x': {}}) == {}


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
	def testRender(self, s, e, out, default_envs):
		t = TemplateJinja2(s, **default_envs)
		assert t.render(e) == out

