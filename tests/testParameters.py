import helpers, unittest

from os import path
from pyppl.parameters import Parameter, Parameters
from pyppl.exception import ParameterNameError, ParameterTypeError, ParametersParseError, ParametersLoadError

class TestParameter (helpers.TestCase):

	def dataProvider_testInit(self):
		yield '', '', str, 'Expect a string with alphabetics and underlines in length 1~32'
		yield '-', '', str, 'Expect a string with alphabetics and underlines in length 1~32'
		yield 'a?', '', str, 'Expect a string with alphabetics and underlines in length 1~32'
		yield int, '', str, 'Not a string'
		yield 'a', 1, int
		yield 'a', [], list
		yield 'a', '', str

	def testInit(self, name, value, t, excmsg = None):
		if excmsg:
			self.assertRaisesStr(ParameterNameError, excmsg, Parameter, name, value)
		else:
			param = Parameter(name, value)
			self.assertIsInstance(param, Parameter)
			self.assertEqual(param.desc, '')
			self.assertFalse(param.required, '')
			self.assertTrue(param.show, '')
			self.assertIs(param.type, t)
			self.assertEqual(param.name, name)
			self.assertEqual(param.value, value)

	def dataProvider_testSetGetAttr(self):
		yield 'a', '', 'desc', 'whatever description'
		yield 'a', '', 'required', True
		yield 'a', '', 'required', False
		yield 'a', True, 'required', True, ParameterTypeError, 'Bool option "a" cannot be set as required'
		yield 'a', '', 'show', True
		yield 'a', '', 'show', False
		yield 'a', '1', 'type', int
		yield 'a', 0, 'type', str
		yield 'a', 0, 'type', dict, ParameterTypeError, 'Unsupported type'
		yield 'a', '', 'value', 'a'
		yield 'a', '', 'value', 2
		yield 'a', '', 'name', 'a2'

	def testSetGetAttr(self, name, val, propname, propval, exception = None, msg = None):
		p = Parameter(name, val)
		if exception:
			self.assertRaisesStr(exception, msg, setattr, p, propname, propval)
		else:
			setattr(p, propname, propval)
			self.assertEqual(getattr(p, propname), propval)

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
		self.assertEqual(repr(p), '<Parameter({}) @ {}>'.format(','.join([key+'='+repr(val) for key, val in p.props.items()]), hex(id(p))))
		self.assertEqual(str(p), str(p.value))

	def dataProvider_testForceType(self):
		p1 = Parameter('a', 'a')
		yield p1, int, 0, ParameterTypeError

		p2 = Parameter('a', '')
		yield p2, int, 0, ParameterTypeError

		p3 = Parameter('a', '0')
		yield p3, list, ['0']

		p4 = Parameter('a', '0')
		yield p4, int, 0

	def testForceType(self, p, t, val, exception = None):
		if exception:
			self.assertRaises(exception, setattr, p, 'type', t)
		else:
			p.type = t
			self.assertEqual(p.value, val)

	def dataProvider_testPrintName(self):
		p1 = Parameter('a', 'a')
		yield p1, '-', 0, '-a <STR>'
		yield p1, '--param-', 0, '--param-a <STR>'
		yield p1, '--param-', 16, '--param-a        <STR>'
		p2 = Parameter('a', True)
		yield p2, '--param-', 16, '--param-a        (BOOL)'

	def testPrintName(self, p, prefix, keylen, out):
		self.assertEqual(p._printName(prefix, keylen), out)

class TestParameters(helpers.TestCase):

	def testInit(self):
		ps = Parameters()
		self.assertIsInstance(ps, Parameters)
		self.assertEqual(ps._props['usage'], '')
		self.assertEqual(ps._props['example'], '')
		self.assertEqual(ps._props['desc'], '')
		self.assertListEqual(ps._props['hopts'], ['-h', '--help', '-H', '-?', ''])
		self.assertEqual(ps._props['prefix'], '--param-')
		self.assertDictEqual(ps._props['params'], {})

	def dataProvider_testSetGetAttr(self):
		ps = Parameters()
		yield ps, '_props', None, ParameterNameError
		yield ps, 'a', 1

	def testSetGetAttr(self, ps, name, value, exception = None):
		if exception:
			self.assertRaises(exception, setattr, ps, name, value)
		else:
			setattr(ps, name, value)
			p = getattr(ps, name)
			self.assertIsInstance(p, Parameter)
			self.assertEqual(p.name, name)
			self.assertEqual(p.value, value)
			self.assertIn(name, ps._props['params'])
			del ps._props['params'][name]
			self.assertNotIn(name, ps._props['params'])
			p = getattr(ps, name)
			self.assertEqual(p.name, name)
			self.assertEqual(p.value, '')
			p.value = value
			self.assertEqual(p.value, value)

	def dataProvider_testPrefix(self):
		ps = Parameters()
		yield ps, ''
		yield ps, 'a'
		yield ps, '-'
		yield ps, '--'

	def testPrefix(self, ps, prefix):
		self.assertIs(ps.prefix(prefix), ps)
		self.assertEqual(ps._props['prefix'], prefix)

	def dataProvider_testHelpOpts(self):
		ps = Parameters()
		yield ps, '', ['']
		yield ps, 'a', ['a']
		yield ps, '-', ['-']
		yield ps, ' --, -h', ['--', '-h']
		yield ps, ['--help', '?'], ['--help', '?']

	def testHelpOpts(self, ps, h, out):
		self.assertIs(ps.helpOpts(h), ps)
		self.assertListEqual(ps._props['hopts'], out)

	def dataProvider_testUsage(self):
		ps = Parameters()
		yield ps, '', []
		yield ps, 'a', ['a']
		yield ps, 'a\nb', ['a', 'b']
		yield ps, '  a  \n\n  b \n', ['a', 'b']

	def testUsage(self, ps, u, out):
		self.assertIs(ps.usage(u), ps)
		self.assertListEqual(ps._props['usage'], out)

	def dataProvider_testExample(self):
		ps = Parameters()
		yield ps, '', []
		yield ps, 'a', ['a']
		yield ps, 'a\nb', ['a', 'b']
		yield ps, '  a  \n\n  b \n', ['a', 'b']

	def testExample(self, ps, e, out):
		self.assertIs(ps.example(e), ps)
		self.assertListEqual(ps._props['example'], out)

	def dataProvider_testDesc(self):
		ps = Parameters()
		yield ps, '', []
		yield ps, 'a', ['a']
		yield ps, 'a\nb', ['a', 'b']
		yield ps, '  a  \n\n  b \n', ['a', 'b']

	def testDesc(self, ps, d, out):
		self.assertIs(ps.desc(d), ps)
		self.assertListEqual(ps._props['desc'], out)

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
		d = ps.toDict()
		self.assertDictEqual(d, values)

	def dataProvider_testParse(self):
		ps = Parameters()
		yield ps, [], {}, 'USAGE', SystemExit
		
		ps1 = Parameters()
		ps1.helpOpts('-h')
		yield ps1, ['a', 'b', '-h'], {}, 'USAGE', SystemExit, None

		ps2 = Parameters()
		ps2.a
		yield ps2, ['--param-a=b'], {'a': 'b'}
		yield ps2, ['--param-d'], {'a': 'b'}, 'WARNING: Unknown option'

		ps3 = Parameters()
		ps3.e = True
		yield ps3, ['--param-e=False'], {'e': False}
		yield ps3, ['--param-e'], {'e': True}
		yield ps3, ['--param-e', 'Yes'], {'e': True}
		yield ps3, ['--param-e', 't'], {'e': True}
		yield ps3, ['--param-e', 'true'], {'e': True}
		yield ps3, ['--param-e', 'y'], {'e': True}
		yield ps3, ['--param-e', '1'], {'e': True}
		yield ps3, ['--param-e', 'on'], {'e': True}
		yield ps3, ['--param-e', 'f'], {'e': False}
		yield ps3, ['--param-e', 'false'], {'e': False}
		yield ps3, ['--param-e', 'no'], {'e': False}
		yield ps3, ['--param-e', 'n'], {'e': False}
		yield ps3, ['--param-e', '0'], {'e': False}
		yield ps3, ['--param-e', 'off'], {'e': False}
		yield ps3, ['--param-e', 'a'], {'e': False}, '', ParametersParseError, 'Cannot coerce value to bool'

		ps4 = Parameters()
		ps4.f = []
		yield ps4, ['--param-f=1'], {'f': ['1']}
		yield ps4, ['--param-f=1', '2', '3'], {'f': ['1', '2', '3']}

		ps5 = Parameters()
		ps5.g = ''
		yield ps5, ['--param-g'], {'g': ''}, 'No value assigned'
		yield ps5, ['--param-g', 'a', 'b'], {'g': 'a'}, 'Unused value found'

		ps6 = Parameters()
		ps6.helpOpts('-?')
		ps6.h.required = True
		yield ps6, [], {}, 'ERROR: Option --param-h is required.', SystemExit

		ps7 = Parameters()
		ps7.i = 1
		yield ps7, ['--param-i=a'], {}, None, ParameterTypeError, 'Unable to coerce'

		# mixed
		ps8 = Parameters()
		ps8.a
		ps8.b
		ps8.c
		yield ps8, ['--param-a=1', '--param-b', '2', '--param-c="3"'], {'a':'1', 'b':'2', 'c':'"3"'}

		ps9 = Parameters()
		ps9.a = []
		ps9.b = []
		ps9.c = []
		yield ps9, ['--param-a=1', '2', '--param-b', 'a', '--param-c'], {'a': ['1', '2'], 'b': ['a'], 'c': []}

		ps10 = Parameters()
		ps10.a = False
		ps10.b = False
		ps10.c = False
		yield ps10, ['--param-a', '--param-b', '1', '--param-c=yes'], {'a': True, 'b': True, 'c': True}

		ps11 = Parameters()
		ps11.a
		ps11.b = 'a'
		ps11.c = 1
		ps11.d = False
		ps11.e = []
		yield ps11, ['--param-d'], {'a':'', 'b':'a', 'c':1, 'd': True, 'e':[]}
		yield ps11, ['--param-d', 'no', '--param-c=100', '--param-e', '-1', '-2'], {'a':'', 'b':'a', 'c':100, 'd': False, 'e':['-1', '-2']}

	def testParse(self, ps, args, values, stderr = [], exception = None, msg = None):
		import sys
		sys.argv = [''] + args
		if exception:
			with helpers.captured_output() as (out, err):
				self.assertRaisesStr(exception, msg, ps.parse)
			if stderr:
				if not isinstance(stderr, list):
					stderr = [stderr]
				for stde in stderr:
					self.assertIn(stde, err.getvalue())
		else:
			with helpers.captured_output() as (out, err):
				d = ps.parse().toDict()

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
			'  progname',
			'',
			'OPTIONAL OPTIONS:',
			'  -h, --help, -H, -?                    - Print this help information.',
			''
		]
		
		ps1 = Parameters()
		ps1.helpOpts('-h')
		yield ps1, [
			'USAGE:',
			'  progname',
			'',
			'OPTIONAL OPTIONS:',
			'  -h                                    - Print this help information.',
			''
		]

		ps2 = Parameters()
		ps2.a
		yield ps2, [
			'USAGE:',
			'  progname [OPTIONS]',
			'',
			'OPTIONAL OPTIONS:',
			'  --param-a <STR>                       - DEFAULT: \'\'',
			'  -h, --help, -H, -?                    - Print this help information.',
			''
		]

		ps3 = Parameters()
		ps3.e = False
		yield ps3, [
			'USAGE:',
			'  progname [OPTIONS]',
			'',
			'OPTIONAL OPTIONS:',
			'  --param-e (BOOL)                      - DEFAULT: False',
			'  -h, --help, -H, -?                    - Print this help information.',
			''
		]

		ps4 = Parameters()
		ps4.ef.required = True
		ps4.ef.desc = 'This is a description of option ef. \n Option ef is required.'
		ps4.f = []
		ps4.f.desc = 'This is a description of option f. \n Option f is not required.'
		ps4.usage('{} User-defined usages\n{} User-defined another usage')
		ps4.desc('This program is doing: \n* 1. blahblah\n* 2. lalala')
		ps4.example('{} --param-f abc\n {} --param-f 22')
		yield ps4, [
			'DESCRIPTION:',
			'  This program is doing:',
			'  * 1. blahblah',
			'  * 2. lalala',
			'',
			'USAGE:',
			'  progname User-defined usages',
			'  progname User-defined another usage',
			'',
			'EXAMPLE:',
			'  progname --param-f abc',
			'  progname --param-f 22',
			'',
			'REQUIRED OPTIONS:',
			'  --param-ef <STR>                      - This is a description of option ef. ',
			'                                           Option ef is required.',
			'',
			'OPTIONAL OPTIONS:',
			'  --param-f  <LIST>                     - This is a description of option f. ',
			'                                           Option f is not required. DEFAULT: []',
			'  -h, --help, -H, -?                    - Print this help information.',
			''
		]

		# show = False, description
		ps5 = Parameters()
		ps5.g = ''
		ps5.g.show = False
		yield ps5, [
			'USAGE:',
			'  progname',
			'',
			'OPTIONAL OPTIONS:',
			'  -h, --help, -H, -?                    - Print this help information.',
			''
		]

	def testHelp(self, ps, out):
		self.maxDiff = None
		import sys
		sys.argv = ['progname']
		h = ps.help()
		self.assertTextEqual(h, '\n'.join(out) + '\n')
	
	def dataProvider_testLoadDict(self):
		yield {}, True
		yield {'a': ''}, True
		yield {'a': []}, False
		yield {'a': [], 'a.show': True}, True # can be different
		yield {'a': 1, 'a.type': bool}, False
		yield {'a': True, 'a.type': int, 'a.desc': 'hello'}, False
		yield {'a.type': ''}, True, ParametersLoadError, 'Cannot set attribute of an undefined option'
		yield {'a': 1, 'a.type2': ''}, True, ParametersLoadError, 'Unknown attribute name for option'
		yield {'a': 2, 'a.b.type': ''}, True, ParametersLoadError, 'Unknown attribute name for option'

	def testLoadDict(self, dictVar, show, exception = None, msg = None):
		ps = Parameters()
		if exception:
			self.assertRaisesStr(exception, msg, ps.loadDict, dictVar, show)
		else:
			ps.loadDict(dictVar, show)
			for dk, dv in dictVar.items():
				if '.' in dk: 
					pn, pa = dk.split('.', 2)
					p = getattr(ps, pn)
					self.assertIsInstance(p, Parameter)
					self.assertEqual(p.name, pn)
					self.assertEqual(getattr(p, pa), dv)
				else:
					p = getattr(ps, dk)
					self.assertIsInstance(p, Parameter)
					self.assertEqual(p.name, dk)
					self.assertEqual(p.value, dv)
					self.assertEqual(p.show, show)

	def dataProvider_testLoadFile(self, testdir):
		yield testdir, False, []

		jsonfile = path.join(testdir, 'testLoadFile.json')
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
			yamlfile = path.join(testdir, 'testLoadFile.yaml')
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

	def testLoadFile(self, cfgfile, show, params, exception = None, msg = None):
		ps = Parameters()
		if exception:
			self.assertRaisesStr(exception, msg, ps.loadFile, dictVar, cfgfile)
		else:
			ps.loadFile(cfgfile, show)
			for param in params:
				p = getattr(ps, param.name)
				self.assertDictEqual(param.props, p.props)
			

if __name__ == '__main__':
	unittest.main(verbosity=2)