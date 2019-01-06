import helpers, testly, re, sys

from os import path, makedirs
from shutil import rmtree
from tempfile import gettempdir
from pyppl.parameters import Parameter, Parameters, HelpAssembler, Commands
from pyppl.exception import ParameterNameError, ParameterTypeError, ParametersParseError, ParametersLoadError

noANSI = lambda s: '\n'.join(line.rstrip() for line in re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', s).split('\n'))

class TestParameter (testly.TestCase):

	def dataProvider_testInit(self):
		yield '', '', None, None, ParameterNameError, 'Expect a string with alphabetics and underlines in length 1~32'
		yield '+', '', None, None, ParameterNameError, 'Expect a string with alphabetics and underlines in length 1~32'
		yield 'a?', '', None, None, ParameterNameError, 'Expect a string with alphabetics and underlines in length 1~32'
		yield int, '', None, None, ParameterNameError, 'Not a string'
		yield 'a', 1, 'int', ['Default: 1']
		yield 'a', [], 'list', ['Default: []']
		yield 'atuple', (), 'list', ['Default: []']
		yield 'a', u'a', 'str', ['Default: \'a\'']
		yield 'a', '', 'str', ["Default: ''"]
		yield 'a', {}, None, None, ParameterTypeError, 'Unsupported parameter type: dict'

	def testInit(self, name, value, t, desc = None, exc = None, excmsg = None):
		desc = desc or []
		if excmsg:
			self.assertRaisesRegex(exc, excmsg, Parameter, name, value)
		else:
			param = Parameter(name, value)
			self.assertIsInstance(param, Parameter)
			self.assertEqual(param.desc, desc)
			self.assertFalse(param.required)
			self.assertTrue(param.show)
			self.assertEqual(param.type, t)
			self.assertEqual(param.name, name)
			if t == 'list':
				self.assertListEqual(param.value, list(value))
			else:
				self.assertEqual(param.value, value)
			self.assertTrue(param == param)
			self.assertFalse(param != param)

	def dataProvider_testSetGetAttr(self):
		# 0
		yield 'a', '', 'desc', 'whatever description', ['whatever description', "Default: ''"]
		yield 'a', '', 'required', True
		yield 'a', '', 'required', False
		yield 'a', True, 'required', True, None, ParameterTypeError, 'Bool option "a" cannot be set as required'
		yield 'a', '', 'show', True
		# 5
		yield 'a', '', 'show', False
		yield 'a', '1', 'type', 'i', 'int'
		yield 'a', '1', 'type', 'int', 'int'
		yield 'a', '1', 'type', int, 'int'
		yield 'a', '1', 'type', 'b', 'bool'
		# 10
		yield 'a', '1', 'type', 'bool', 'bool'
		yield 'a', '1', 'type', bool, 'bool'
		yield 'a', '1', 'type', 'f', 'float'
		yield 'a', '1', 'type', 'float', 'float'
		yield 'a', '1', 'type', float, 'float'
		# 15
		yield 'a', 0, 'type', 's', 'str'
		yield 'a', 0, 'type', 'str', 'str'
		yield 'a', 0, 'type', str, 'str'
		yield 'a', 0, 'type', 'l', 'list'
		yield 'a', 0, 'type', 'list', 'list'
		# 20
		yield 'a', 0, 'type', list, 'list'
		yield 'a', 0, 'type', 'l:i', 'list:int'
		yield 'a', 0, 'type', 'l:int', 'list:int'
		yield 'a', 0, 'type', 'list:int', 'list:int'
		yield 'a', 0, 'type', 'l:b', 'list:bool'
		# 25
		yield 'a', 0, 'type', 'l:bool', 'list:bool'
		yield 'a', 0, 'type', 'list:bool', 'list:bool'
		yield 'a', 0, 'type', 'l:f', 'list:float'
		yield 'a', 0, 'type', 'l:float', 'list:float'
		yield 'a', 0, 'type', 'list:f', 'list:float'
		# 26
		yield 'a', 0, 'type', dict, None, ParameterTypeError, 'Unsupported type'
		yield 'a', '', 'value', 'a'
		yield 'a', '', 'value', 2
		yield 'a', '', 'name', 'a2'

		yield 'a', 1, '__dict__', {'_props': {'name': 'a', 'show': True, 'required': False, 'type': 'int', 'value': 1, 'desc': []}}

	def testSetGetAttr(self, name, val, propname, propval, exptval = None, exception = None, msg = None):
		exptval = exptval or propval
		p = Parameter(name, val)
		if exception:
			self.assertRaisesRegex(exception, msg, setattr, p, propname, propval)
		else:
			setattr(p, propname, propval)
			self.assertEqual(getattr(p, propname), exptval)

	def dataProvider_testReprStr(self):
		p1 = Parameter('a', 'a')
		p1.required = True
		yield p1,

		p2 = Parameter('b', 'b')
		p2.show = True
		yield p2,

		p3 = Parameter('c', 2)
		p3.desc = 'what'
		yield p3,

	def testReprStr(self, p):
		self.assertEqual(
			repr(p), 
			'<Parameter({}) @ {}>'.format(','.join([
				key + '=' + repr(val) 
				for key, val in p._props.items()
			]), hex(id(p)))
		)
		self.assertEqual(str(p), str(p.value))
	
	def dataProvider_testForceType(self):
		p1 = Parameter('a', 'a')
		yield p1, int, 0, ParameterTypeError

		p2 = Parameter('a', '')
		yield p2, int, 0, ParameterTypeError

		p3 = Parameter('a', '0')
		yield p3, 'list:str', ['0']
		yield p3, 'list:bool', [False]

		p4 = Parameter('aint', '0')
		yield p4, int, 0
		
		p5 = Parameter('a', 'False')
		yield p5, bool, 0

	def testForceType(self, p, t, val, exception = None):
		if exception:
			self.assertRaises(exception, setattr, p, 'type', t)
		else:
			p.type = t
			self.assertEqual(p.value, val)
	
class TestParameters(testly.TestCase):

	def setUpMeta(self):
		self.testdir = path.join(gettempdir(), 'PyPPL_unittest', 'TestParameters')
		if path.exists(self.testdir):
			rmtree(self.testdir)
		makedirs(self.testdir)

	def testInit(self):
		ps = Parameters()
		self.assertIsInstance(ps, Parameters)
		self.assertEqual(ps._props['usage'], [])
		self.assertEqual(ps._props['desc'], [])
		self.assertListEqual(ps._props['hopts'], ['-h', '--help', '-H', '-?'])
		self.assertEqual(ps._props['prefix'], '-')
		self.assertIsInstance(ps.__dict__['_assembler'], HelpAssembler)
		self.assertEqual(ps._assembler.theme, HelpAssembler.THEMES['default'])
		self.assertDictEqual(ps._params, {})
		self.assertTrue(ps == ps)
		self.assertFalse(ps != ps)

	def dataProvider_testSetGetAttr(self):
		ps = Parameters()
		#yield ps, '_props', None, ParameterNameError
		yield ps, 'a', 1
		
		ps1 = Parameters()
		ps1.a = 'a'
		yield ps1, 'a', 'a'

	def testSetGetAttr(self, ps, name, value, exception = None):
		if exception:
			self.assertRaises(exception, setattr, ps, name, value)
		else:
			setattr(ps, name, value)
			p = getattr(ps, name)
			self.assertIsInstance(p, Parameter)
			self.assertEqual(p.name, name)
			self.assertEqual(p.value, value)
			self.assertIn(name, ps._params)
			
			ps[name] = value
			p = ps[name]
			self.assertIsInstance(p, Parameter)
			self.assertEqual(p.name, name)
			self.assertEqual(p.value, value)
			self.assertIn(name, ps._params)

			del ps._params[name]
			self.assertNotIn(name, ps._params)
			p = getattr(ps, name)
			self.assertEqual(p.name, name)
			self.assertEqual(p.value, None)
			p.value = value
			self.assertEqual(p.value, value)

	def dataProvider_testSetTheme(self):
		yield 'default',
		yield 'blue',
		yield {},
		yield {'title': 'red'},

	def testSetTheme(self, theme):
		ps = Parameters()
		ps._setTheme(theme)
		self.assertEqual(ps._assembler.theme, HelpAssembler.THEMES.get(str(theme), theme))

	def testRepr(self):
		ps = Parameters()
		ps.a
		ps.b
		self.assertIn('<Parameters(a:None,b:None) @ ', repr(ps))
		self.assertIn('>', repr(ps))

	def dataProvider_testCall(self):
		ps = Parameters()
		yield ps, 'prefix', '', '', ParametersParseError
		yield ps, 'prefix', 'a', 'a'
		yield ps, 'prefix', '-', '-'
		yield ps, 'prefix', '--', '--'

		# 4, hopts
		yield ps, 'hopts', '', ['']
		yield ps, 'hopts', 'a', ['a']
		yield ps, 'hopts', '-', ['-']
		yield ps, 'hopts', ' --, -h', ['--', '-h']
		yield ps, 'hopts', ['--help', '?'], ['--help', '?']
		# cannot be tested solely
		yield ps, 'hopts', '?', ['?']

		# 10, usage
		yield ps, 'usage', '', ['']
		yield ps, 'usage', 'a', ['a']
		yield ps, 'usage', 'a\nb', ['a\nb']
		yield ps, 'usage', '  a  \n\n  b \n', ['  a  \n\n  b \n']

		# 14, desc
		yield ps, 'desc', '', ['']
		yield ps, 'desc', 'a', ['a']
		yield ps, 'desc', 'a\nb', ['a\nb']
		yield ps, 'desc', '  a  \n\n  b \n', ['  a  \n\n  b \n']
		#yield ps, 'Unknown', '', '', AttributeError


	def testCall(self, ps, option, value, outval, exception = None):
		self.assertTrue(callable(ps))
		if exception:
			self.assertRaises(exception, ps, option, value)
		else:
			ps(option, value)
			self.assertEqual(ps._props[option], outval)

	def dataProvider_testParseName(self):
		ps = Parameters()
		ps('prefix', '---')
		yield ps, '-a', None, 'auto', 'auto', None
		yield ps, '----a', None, 'auto', 'auto', None
		yield ps, '---a', 'a', 'auto', 'auto', None
		yield ps, '---a:i', 'a', 'int', 'auto', None
		yield ps, '---a:int', 'a', 'int', 'auto', None
		yield ps, '---a:s', 'a', 'str', 'auto', None
		yield ps, '---a:str', 'a', 'str', 'auto', None
		yield ps, '---a:b', 'a', 'bool', 'auto', None
		yield ps, '---a:bool', 'a', 'bool', 'auto', None
		yield ps, '---a:f', 'a', 'float', 'auto', None
		yield ps, '---a:float', 'a', 'float', 'auto', None
		yield ps, '---a:l', 'a', 'list', 'auto', None
		yield ps, '---a:list', 'a', 'list', 'auto', None
		yield ps, '---a:l:s', 'a', 'list', 'str', None
		yield ps, '---a:list:s', 'a', 'list', 'str', None
		yield ps, '---a:list:str', 'a', 'list', 'str', None
		yield ps, '---a:l:i', 'a', 'list', 'int', None
		yield ps, '---a:list:i', 'a', 'list', 'int', None
		yield ps, '---a:list:int', 'a', 'list', 'int', None
		yield ps, '---a:l:f', 'a', 'list', 'float', None
		yield ps, '---a:list:f', 'a', 'list', 'float', None
		yield ps, '---a:list:float', 'a', 'list', 'float', None
		yield ps, '---a:l:b', 'a', 'list', 'bool', None
		yield ps, '---a:list:b', 'a', 'list', 'bool', None
		yield ps, '---a:list:bool', 'a', 'list', 'bool', None
	
	def testParseName(self, ps, argname, an, at, st, av):
		an1, at1, st1, av1 = ps._parseName(argname)
		self.assertEqual(an1, an)
		self.assertEqual(at1, at)
		self.assertEqual(st1, st)
		self.assertEqual(av1, av)

	def dataProvider_testShouldPrintHelp(self):
		ps = Parameters()
		ps('hopts', '-h')
		yield ps, [], True
		yield ps, ['-h'], True
		ps1 = Parameters()
		ps1('hopts', ['--help'])
		yield ps1, [], True
		yield ps1, ['-h'], False
		ps2 = Parameters()
		ps2._hbald = False
		yield ps2, [], False

	def testShouldPrintHelp(self, ps, args, should):
		self.assertEqual(ps._shouldPrintHelp(args), should)

	def dataProvider_testCoerceValue(self):
		yield testly.Data('1', outval = 1)
		yield testly.Data('1.1', outval = 1.1)
		yield testly.Data('1.1E-2', outval = 0.011)
		yield testly.Data('TRUE', outval = True)
		yield testly.Data('py:[1,2]', outval = [1,2])
		yield testly.Data(True, outval = True)
		yield '1', 'int', 1
		yield '1.1', 'float', 1.1
		yield 'False', 'bool', False
		yield True, 'str', 'True'
		yield 'a', 'int', None, ParameterTypeError
		yield '{"a":1}', 'py', {"a": 1}
		yield '1', 'list', [1]
		yield '1', 'list:str', ['1']
		yield '1', 'list:bool', [True]
		yield 123, 'x', 123
		yield 1, 'list:one', [[1]]

	def testCoerceValue(self, value, t = 'auto', outval = None, exception = None):
		if exception:
			self.assertRaises(exception, Parameters._coerceValue, value, t)
		else:
			outval = outval is None and value or outval
			self.assertEqual(Parameters._coerceValue(value, t), outval)

	def dataProvider_testPutValue(self):
		ps = Parameters()
		yield ps, 'noSuchArgname', None, None, None, 'auto'
		ps.a.type = 'list'
		yield ps, 'a', 'auto', 1, 1, 'auto'
		yield ps, 'a', 'auto', '2', 2, 'auto'
		yield ps, 'a', 'auto', '', '', 'auto'
		yield ps, 'a', 'list', 3, ['3'], 'str'
		ps.b.type = 'bool'
		yield ps, 'b', 'auto', 'F', False, 'auto'
		ps.c.type = 'list'
		yield ps, 'c', 'list', 1, [[1]], 'one'
		yield ps, 'd', 'auto', '1', 1, 'auto', True
		ps.e.type = 'list'
		ps.e = [1,2,3]
		yield ps, 'e', 'list', '4', [1,2,3,4], 'auto', True
		ps.f = [1,2,3]
		yield ps, 'f', 'list', '4', [], None, True


	def testPutValue(self, ps, argname, argtype, argval, outval, subtype, arbi = False):
		with self.assertStdOE():
			ps._putValue(argname, argtype, subtype, argval, arbi)
		if argname in ps._params:
			self.assertEqual(ps._params[argname].value, outval)

	def dataProvider_testToDict(self):
		ps = Parameters()
		ps.a = 1
		ps.b = 2
		yield ps, {'a':1, 'b':2}

		ps2 = Parameters()
		yield ps2, {}

		ps3 = Parameters()
		ps3.x = True
		ps3.y = []
		yield ps3, {'x': True, 'y': []}

	def testToDict(self, ps, values):
		d = ps.asDict()
		self.assertDictEqual(d, values)

	def dataProvider_testParse(self):
		ps = Parameters()
		yield ps, [], {}, 'USAGE', SystemExit
		
		ps1 = Parameters()
		ps1('hopts', '-h')
		yield ps1, ['a', 'b', '-h'], {}, 'USAGE', SystemExit, None

		ps2 = Parameters()
		ps2('prefix', '--param-')
		ps2.a
		yield ps2, ['--param-a=b'], {'a': 'b', '_': []}
		yield ps2, ['--param-d'], {'a': 'b', '_': []}, 'Warning: No such option: --param-d'

		ps3 = Parameters()
		ps3('prefix', '--param-')
		ps3.e = True
		ps3.e.type = 'bool'
		yield ps3, ['--param-e=False'], {'e': False, '_': []}
		# 5
		yield ps3, ['--param-e'], {'e': True, '_': []}
		yield ps3, ['--param-e', 'Yes'], {'e': True, '_': []}
		yield ps3, ['--param-e', 't'], {'e': True, '_': []}
		yield ps3, ['--param-e', 'true'], {'e': True, '_': []}
		yield ps3, ['--param-e', 'y'], {'e': True, '_': []}
		# 10
		yield ps3, ['--param-e', '1'], {'e': True, '_': []}
		yield ps3, ['--param-e', 'on'], {'e': True, '_': []}
		yield ps3, ['--param-e', 'f'], {'e': False, '_': []}
		yield ps3, ['--param-e', 'false'], {'e': False, '_': []}
		yield ps3, ['--param-e', 'no'], {'e': False, '_': []}
		# 15
		yield ps3, ['--param-e', 'n'], {'e': False, '_': []}
		yield ps3, ['--param-e', '0'], {'e': False, '_': []}
		yield ps3, ['--param-e', 'off'], {'e': False, '_': []}
		yield ps3, ['--param-e', 'a'], {'e': True, '_': []}, None, ParameterTypeError, "Unable to coerce value 'a' to type: 'bool'"

		ps4 = Parameters()
		ps4('prefix', '--param-')
		ps4.f = []
		ps4.f.type = 'list:str'
		yield ps4, ['--param-f=1'], {'f': ['1'], '_': []}
		# 20
		yield ps4, ['--param-f=1', '2', '3'], {'f': ['1', '1', '2', '3'], '_': []}

		ps5 = Parameters()
		ps5('prefix', '--param-')
		ps5.g = ''
		yield ps5, ['--param-g'], {'g': '', '_': []}, ''
		yield ps5, ['--param-g', 'a', 'b'], {'g': 'a', '_': ['b']}

		ps6 = Parameters()
		ps6('prefix', '--param-')
		ps6('hbald', False)
		ps6.h.required = True
		# 23
		yield ps6, [], {}, 'Error: Option --param-h is required.', SystemExit

		ps7 = Parameters()
		ps7('prefix', '--param-')
		ps7.i = 1
		yield ps7, ['--param-i=a'], {}, None, ParameterTypeError, 'Unable to coerce'

		# mixed
		ps8 = Parameters()
		ps8('prefix', '--param-')
		ps8.a.type = 'str'
		ps8.b.type = 'str'
		ps8.c
		# 25
		yield ps8, ['--param-a=1', '--param-b', '2', '--param-c="3"'], {'a':'1', 'b':'2', 'c':'"3"', '_':[]}

		ps9 = Parameters()
		ps9('prefix', '--param-')
		ps9.a = []
		ps9.a.type = 'list:str'
		ps9.b = []
		ps9.c = []
		yield ps9, ['--param-a=1', '2', '--param-b', 'a', '--param-c'], {'a': ['1', '2'], 'b': ['a'], 'c': [], '_': []}

		ps10 = Parameters()
		ps10('prefix', '--param-')
		ps10.a = False
		ps10.b = False
		ps10.c = False
		yield ps10, ['--param-a', '--param-b', '1', '--param-c=yes'], {'a': True, 'b': True, 'c': True, '_':[]}

		ps11 = Parameters()
		ps11('prefix', '--param-')
		ps11.a
		ps11.b = 'a'
		ps11.c = 1
		ps11.d = False
		ps11.e = []
		yield ps11, ['--param-d'], {'a':None, 'b':'a', 'c':1, 'd': True, 'e':[], '_': []}
		yield ps11, ['a', '--param-d', 'no', 'b', '--param-c=100', '--param-e:l:s', '-1', '-2'], {'a': None, 'b':'a', 'c':100, 'd': False, 'e':['-1', '-2'], '_': ['a']}, 'Warning: Unexpected value(s): b.'

		# 30
		ps12 = Parameters()
		ps12.a
		ps12.b
		yield ps12, ['-a', '-b=1'], {'a':True, 'b':1, '_': []}

		ps13 = Parameters()
		ps13.a.type = list
		yield ps13, ['-a', '1', '-a', '-a', '2', '3'], {'a': [2,3], '_':[]}

	def testParse(self, ps, args, values, stderr = [], exception = None, msg = None):
		if exception:
			with helpers.captured_output() as (out, err):
				self.assertRaisesRegex(exception, msg, ps.parse, args)
			if stderr:
				if not isinstance(stderr, list):
					stderr = [stderr]
				for stde in stderr:
					self.assertIn(stde, err.getvalue())
		else:
			with helpers.captured_output() as (out, err):
				d = ps.parse(args)

			if stderr:
				if not isinstance(stderr, list):
					stderr = [stderr]
				for stde in stderr:
					self.assertIn(stde, err.getvalue())
			else:
				self.assertEqual(err.getvalue(), '')

			self.assertDictEqual(d, values)

	def dataProvider_testHelp(self):
		ps = Parameters()
		yield ps, [
			'USAGE:',
			'  testParameters.py',
			'',
			'OPTIONAL OPTIONS:',
			'  -h, --help, -H, -?                    - Print this help information',
			''
		]
		
		ps1 = Parameters()
		ps1('hopts', '-h')
		yield ps1, [
			'USAGE:',
			'  testParameters.py',
			'',
			'OPTIONAL OPTIONS:',
			'  -h                                    - Print this help information',
			''
		]

		ps2 = Parameters()
		ps2('prefix', '--param-')
		ps2.a
		yield ps2, [
			'USAGE:',
			'  testParameters.py [OPTIONS]',
			'',
			'OPTIONAL OPTIONS:',
			'  --param-a                             - Default: None',
			'  -h, --help, -H, -?                    - Print this help information',
			''
		]

		ps3            = Parameters()
		ps3.e          = False
		ps3.e.type     = 'bool'
		ps3._.required = True
		ps3._.desc     = 'positional options'
		yield ps3, [
			'USAGE:',
			'  testParameters.py [OPTIONS] POSITIONAL',
			'',
			'REQUIRED OPTIONS:',
			'  POSITIONAL                            - positional options',
			'',
			'OPTIONAL OPTIONS:',
			'  -e (BOOL)                             - Default: False',
			'  -h, --help, -H, -?                    - Print this help information',
			''
		]

		ps4             = Parameters()
		ps4('prefix', '--param-')
		ps4.ef.required = True
		ps4.ef.type     = 'str'
		ps4.ef.desc     = 'This is a description of option ef. \n Option ef is required.'
		ps4.f           = []
		ps4.f.type      = 'list'
		ps4.f.desc      = 'This is a description of option f. \n Option f is not required.'
		ps4.g           = ps4.f # alias
		ps4._.required  = False
		ps4._.desc      = 'positional options'
		ps4('usage', '{prog} User-defined usages\n{prog} User-defined another usage'.split('\n'))
		ps4('desc', 'This program is doing: \n* 1. blahblah\n* 2. lalala'.split('\n'))
		ps4._helpx = lambda items: items.update({'END': ['Bye!']}) or items
		yield ps4, [
			'DESCRIPTION:',
			'  This program is doing:',
			'  * 1. blahblah',
			'  * 2. lalala',
			'',
			'USAGE:',
			'  testParameters.py User-defined usages',
			'  testParameters.py User-defined another usage',
			'',
			'REQUIRED OPTIONS:',
			'  --param-ef <STR>                      - This is a description of option ef.',
			'                                           Option ef is required.',
			'',
			'OPTIONAL OPTIONS:',
			'  --param-f, --param-g <LIST>           - This is a description of option f.',
			'                                           Option f is not required.',
			'                                          Default: []',
			'  POSITIONAL                            - positional options',
			'                                          Default: None',
			'  -h, --help, -H, -?                    - Print this help information',
			'',
			'END:',
			'  Bye!',
			''
		]

		# show = False, description
		ps5 = Parameters()
		ps5.g = ''
		ps5.g.show = False
		yield ps5, [
			'Error: This is an error!',
			'USAGE:',
			'  testParameters.py',
			'',
			'OPTIONAL OPTIONS:',
			'  -h, --help, -H, -?                    - Print this help information',
			''
		], 'This is an error!'

	def testHelp(self, ps, out, error = ''):
		self.maxDiff     = 8000
		self.diffContext = None
		self.diffTheme   = 'contrast'
		import sys
		sys.argv = ['progname']
		h = ps.help(error)
		self.assertEqual(noANSI(h), '\n'.join(out) + '\n')
	
	def dataProvider_testLoadDict(self):
		yield {}, True
		yield {'a': ''}, True
		yield {'a': []}, False
		yield {'a': [], 'a.show': True}, True # can be different
		yield {'a': 1, 'a.type': 'bool'}, False
		yield {'a': True, 'a.type': 'int', 'a.desc': 'hello'}, False
		yield {'a.type': ''}, True, ParametersLoadError, 'Cannot set attribute of an undefined option'
		yield {'a': 1, 'a.type2': ''}, True, ParametersLoadError, 'Unknown attribute name for option'
		yield {'a': 2, 'a.b.type': ''}, True, ParametersLoadError, 'Unknown attribute name for option'

	def testLoadDict(self, dictVar, show, exception = None, msg = None):
		ps = Parameters()
		if exception:
			self.assertRaisesRegex(exception, msg, ps.loadDict, dictVar, show)
		else:
			ps.loadDict(dictVar, show)
			for dk, dv in dictVar.items():
				if '.' in dk: 
					pn, pa = dk.split('.', 2)
					p = getattr(ps, pn)
					self.assertIsInstance(p, Parameter)
					self.assertEqual(p.name, pn)
					if pa == 'desc':
						self.assertEqual(getattr(p, pa)[0], dv)
					else:
						self.assertEqual(getattr(p, pa), dv)
				else:
					p = getattr(ps, dk)
					self.assertIsInstance(p, Parameter)
					self.assertEqual(p.name, dk)
					self.assertEqual(p.value, dv)
					self.assertEqual(p.show, show)

	def dataProvider_testLoadFile(self):
		yield self.testdir, False, []

		jsonfile = path.join(self.testdir, 'testLoadFile.json')
		helpers.writeFile(jsonfile, '\n'.join([
			'{',
			'	"a": "2",',
			'	"a.desc": "Option a",',
			'	"a.type": "int",',
			'	"a.required": true',
			'}',
		]))
		p1 = Parameter('a', 2)
		p1.desc = "Option a"
		p1.required = True
		yield jsonfile, True, [p1]

		if helpers.moduleInstalled('yaml'):
			yamlfile = path.join(self.testdir, 'testLoadFile.yaml')
			helpers.writeFile(yamlfile, '\n'.join([
				'a: 2',
				'a.desc: Option a',
				'a.type: int',
				'a.required: false',
				'a.show: true',
				'',
			]))
			p2 = Parameter('a', 2)
			p2.desc = "Option a"
			p2.required = False
			p2.show = True
			yield yamlfile, False, [p2]
			
		conffile = path.join(self.testdir, 'testLoadFile.conf')
		helpers.writeFile(conffile, '\n'.join([
			'[PARAM1]',
			'a = 2',
			'a.desc = Option a',
			'a.type = int',
			'a.required = f',
			'[PARAM2]',
			'a.type = str',
			'b:',
			'	1',
			'	2',
			'b.type = list',
		]))
		p3 = Parameter('a', '2')
		p3.desc = "Option a"
		p3.required = False
		p4 = Parameter('b', ['1','2'])
		yield conffile, True, [p3, p4]

	def testLoadFile(self, cfgfile, show, params, exception = None, msg = None):
		ps = Parameters()
		if exception:
			self.assertRaisesRegex(exception, msg, ps.loadFile, dictVar, cfgfile)
		else:
			ps.loadFile(cfgfile, show)
			for param in params:
				p = getattr(ps, param.name)
				self.assertDictEqual(param._props, p._props)
	
class TestCommands(testly.TestCase):

	def testInit(self):
		cmds = Commands()
		self.assertEqual(cmds._desc, [])
		self.assertEqual(cmds._hcmd, 'help')
		self.assertEqual(cmds._cmds, {})
		self.assertIsInstance(cmds._assembler, HelpAssembler)
		self.assertEqual(cmds._assembler.theme, HelpAssembler.THEMES['default'])
		self.assertIsNone(cmds._helpx)
		cmds._helpx = lambda a: None
		self.assertTrue(callable(cmds._helpx))

	def test_setDesc(self, indesc, outdesc):
		cmds = Commands()
		cmds._setDesc(indesc)
		cmds._desc = indesc
		self.assertEqual(cmds._desc, outdesc)

	def dataProvider_test_setDesc(self):
		yield 'a', ['a']
		yield 'a\nb', ['a\nb']
		yield ['a', 'b'], ['a', 'b']

	def test_setHcmd(self, inhcmd, outhcmd):
		cmds = Commands()
		cmds._setHcmd(inhcmd)
		cmds._hcmd = inhcmd
		self.assertEqual(cmds._hcmd, outhcmd)

	def dataProvider_test_setHcmd(self):
		yield 'h', 'h'
		yield '?', '?'

	def test_setTheme(self, intheme, outtheme):
		cmds = Commands()
		cmds._setTheme(intheme)
		cmds._theme = intheme
		self.assertDictEqual(cmds._assembler.theme, outtheme)

	def dataProvider_test_setTheme(self):
		yield 'default', HelpAssembler.THEMES['default']
		yield 'blue', HelpAssembler.THEMES['blue']
		yield 'plain', HelpAssembler.THEMES['plain']

	def testSetGetattr(self):
		cmds = Commands()
		cmds['ps1'].a
		self.assertIsInstance(cmds.ps1, Parameters)
		self.assertIsInstance(cmds.ps1.a, Parameter)
		self.assertIsInstance(cmds.ps2, Parameters)

		cmds.ps3 = cmds.ps1
		self.assertEqual(cmds.ps3._prog, path.basename(sys.argv[0]) + ' ' + 'ps1|ps3')

		cmds.ps4 = 'command ps4'
		self.assertEqual(cmds.ps4._props['desc'], ['command ps4'])

	def testParse(self, cmds, args, retcmd, retps, arbi = False, exception = None):
		if exception:
			with self.assertStdOE():
				self.assertRaises(exception, cmds.parse, args, arbi)
		else:
			cmd, ps = cmds.parse(args, arbi)
			self.assertEqual(cmd, retcmd)
			self.assertDictEqual(ps, retps)

	def dataProvider_testParse(self):
		cmds1 = Commands()
		cmds1._cmds['None'] = None
		yield cmds1, [], '', {}, True

		args1 = ['1', '3', '-a', '1', '-b', '2', '-c:list', '4', '5', '-d']
		yield cmds1, args1, '1', {'_': [3], 'a': 1, 'b': 2, 'c': [4, 5], 'd': True}, True

		args2 = ['subcmd', '-a', '1', '-b', '2', '3', '-c:list', '4', '5', '-d']
		yield cmds1, args2, 'subcmd', {'a': 1, '_': [3], 'b': 2, 'c': [4, 5], 'd': True}, True

		args3 = ['None', '1', '2']
		yield cmds1, args3, 'None', {'_': ['1', '2']}, True

		cmds2 = Commands()
		cmds2.subcmd = 'A sub command.'
		yield cmds2, None, '', {}, False, SystemExit
		yield cmds2, ['help'], '', {}, False, SystemExit
		yield cmds2, ['help', 'x'], '', {}, False, SystemExit
		yield cmds2, ['help', 'subcmd'], '', {}, False, SystemExit
		yield cmds2, ['subcmd', '1'], 'subcmd', {'_': [1]}, False

	def dataProvider_testHelp(self):
		cmds = Commands()
		cmds._desc = 'Hello world!'
		yield cmds, [
			"DESCRIPTION:",
			"  Hello world!",
			"",
			"COMMANDS:",
			"  help <COMMAND>                        - Print help information for the command",
			""
		]
		yield cmds, [
			"DESCRIPTION:",
			"  Hello world!",
			"",
			"COMMANDS:",
			"  help <COMMAND>                        - Print help information for the command",
			"",
			"END:",
			"  -hello                                - world",
			"  -good <BYE>                           - world",
			""
		], '', lambda items: items.update({'end': [
			('-hello', '    ', 'world'),
			('-good', 'bye', 'world'),

		]}) or items

	def testHelp(self, cmds, outhelp, error = '', helpx = None):
		cmds._helpx = helpx
		self.assertEqual(noANSI(cmds.help(error)), '\n'.join(outhelp) + '\n')


if __name__ == '__main__':
	testly.main(verbosity=2)