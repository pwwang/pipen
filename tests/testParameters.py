import helpers, unittest

from pyppl.parameters import Parameter, Parameters
from pyppl.exception import ParameterNameError

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


'''
import sys, tempfile
from os import path
from contextlib import contextmanager
from six import StringIO



	def testParameter(self):
		p = Parameter('a', [])
		self.assertTrue(isinstance(p, Parameter))
		self.assertEqual(p.desc, '')
		self.assertEqual(p.required, False)
		self.assertEqual(p.show, True)
		self.assertEqual(p.type, list)
		self.assertEqual(p.name, 'a')
		self.assertEqual(p.value, [])
		self.assertEqual(repr(p), 'Parameter({})[{}]'.format(','.join([key+'='+str(val) for key, val in p.props.items()]), hex(id(p))))
		
		self.assertEqual(p._printName('-P'), '-Pa <LIST>')
		p.setDesc('some description')
		self.assertEqual(p.desc, 'some description')
		p.setRequired()
		self.assertTrue(p.required)
		self.assertRaises(TypeError, p.setType, dict)
		p.setType(str)
		self.assertEqual(p.type, str)
		self.assertEqual(p.value, '[]')
		p.setValue([1,2])
		self.assertEqual(p.value, [1,2])
		self.assertEqual(p.type, str)
		p.setShow(False)
		self.assertFalse(p.show)
		p.setName('name2')
		self.assertEqual(p.name, 'name2')
		self.assertEqual(p._printName('-P'), '-Pname2 <STR>')
		p._forceType()
		self.assertEqual(p.value, '[1, 2]')

		p = Parameter('a', True)
		self.assertRaises(ValueError, p.setRequired)

		p = Parameter('a', 'a')
		self.assertRaises(TypeError, p.setType, int)
		
	def testParametersInit(self):
		ps = Parameters()
		self.assertIsInstance(ps, Parameters)
		self.assertEqual(ps._props, {
			'usage': '',
			'example': '',
			'desc': '',
			'hopts': ['-h', '--help', '-H', '-?', ''],
			'prefix': '--param-',
			'params': {}
		})
	
	def testParametersPrefix(self):
		ps = Parameters()
		ps.prefix('-x')
		self.assertEqual(ps._props['prefix'], '-x')
		self.assertRaises(ValueError, ps.prefix, 'x')
	
	def testParametersHopts(self):
		ps = Parameters()
		ps.helpOpts('-h, --help')
		self.assertEqual(ps._props['hopts'], ['-h', '--help'])
		ps.helpOpts(['-?'])
		self.assertEqual(ps._props['hopts'], ['-?'])
		
	def testParametersProps(self):
		ps = Parameters()
		ps.usage("-a <list> -b")
		self.assertEqual(ps._props['usage'], ['-a <list> -b'])
		ps.usage("-a <list> -b\n -c -d")
		self.assertEqual(ps._props['usage'], ['-a <list> -b', '-c -d'])
		ps.example("example")
		self.assertEqual(ps._props['example'], ["example"])
		ps.example("example\n example2")
		self.assertEqual(ps._props['example'], ["example", "example2"])
		ps.desc("desc")
		self.assertEqual(ps._props['desc'], ["desc"])
		ps.desc("desc\n desc2")
		self.assertEqual(ps._props['desc'], ["desc", "desc2"])
		
	def testSetGetAttr(self):
		ps = Parameters()
		ps.b = 'a'
		self.assertEqual(ps.b.name, 'b')
		self.assertEqual(ps.b.value, 'a')
		self.assertEqual(ps.b.type, str)
		self.assertEqual(ps.b.desc, '')
		self.assertEqual(ps.b.required, False)
		self.assertEqual(ps.b.show, True)

		ps.a
		self.assertEqual(ps.a.name, 'a')
		self.assertEqual(ps.a.value, '')
		self.assertEqual(ps.a.type, str)
		self.assertEqual(ps.a.desc, '')
		self.assertEqual(ps.a.required, False)
		self.assertEqual(ps.a.show, True)
		ps.a.setValue(1).setType(int)
		self.assertIs(ps.a.value, 1)
		self.assertEqual(ps.a.type, int)
		
	def testHelp(self):
		self.maxDiff = None
		
		ps = Parameters()
		ps.desc('A test program.\n The test description.')
		ps.example('prog -a A -b B\n prog -c C')
		ps.a.setValue('a')
		ps.b.setValue(2).setType(int).setRequired().setDesc('Option b')
		ps.c.setValue([]).setType(list).setShow(False)
		self.assertEqual(ps.help().splitlines(), ("""DESCRIPTION:
  A test program.
  The test description.

USAGE:
  %s --param-b <INT> [OPTIONS]

EXAMPLE:
  prog -a A -b B
  prog -c C

REQUIRED OPTIONS:
  --param-b <INT>                       - Option b

OPTIONAL OPTIONS:
  --param-a <STR>                       - DEFAULT: a
  -h, --help, -H, -?                    - Print this help information.

""" % sys.argv[0]).splitlines())

	def testParseAndToDict(self):
		ps = Parameters()
		ps.desc('A test program.\n The test description.')
		ps.example('prog -a A -b B\n prog -c C')
		ps.a.setValue('a')
		ps.b.setValue(2).setType(int).setRequired().setDesc('Option b')
		ps.c.setValue([]).setType(list).setShow(False)
		ps.d.setValue(0).setType(bool).setDesc('A switch')
		
		sys.argv = ['-h']
		with captured_output():
			self.assertRaises(SystemExit, ps.parse)

		sys.argv = ['prog', '--param-a', 'b', '--param-b', '3', '--param-c', 'a', 'b', '--param-d=x']
		self.assertRaises(ValueError, ps.parse)

		sys.argv = ['prog', '--param-a', 'b', '--param-b', 'a', '--param-c', 'a', 'b']
		self.assertRaises(TypeError, ps.parse)

		sys.argv = ['prog', '--param-a', 'b', '--param-b', '3', '--param-c', 'a', 'b', '--param-d=f']
		ps.parse()
		self.assertEqual(ps.a.value, 'b')
		self.assertEqual(ps.b.value, 3)
		self.assertEqual(ps.c.value, ['a', 'b'])
		self.assertEqual(ps.d.value, False)
		psdict = ps.toDict()
		self.assertEqual(psdict, {
			'a': 'b',
			'b': 3,
			'c': ['a', 'b'],
			'd': False
		})
		self.assertEqual(psdict.a, 'b')
		self.assertEqual(psdict.b, 3)
		self.assertEqual(psdict.c, ['a', 'b'])
		self.assertEqual(psdict.d, False)
		
		ps.b.value = ''
		sys.argv = ['prog', '--param-a=b', '--param-c=a', '--param-c', 'b', '--param-d=1', 'unused']
		with captured_output() as (out,err):
			self.assertRaises(SystemExit, ps.parse)

		sys.argv = ['prog', '--param-a=b', '--param-b=3', '--param-c=a', '--param-c', 'b', '--param-d=1', 'unused']
		with captured_output() as (out,err):
			ps.parse()
		self.assertEqual('WARNING: Unused value found: unused.\n', err.getvalue())
		self.assertEqual(ps.a.value, 'b')
		self.assertEqual(ps.b.value, 3)
		self.assertEqual(ps.c.value, ['a', 'b'])
		self.assertEqual(ps.d.value, True)
		psdict = ps.toDict()
		self.assertEqual(psdict, {
			'a': 'b',
			'b': 3,
			'c': ['a', 'b'],
			'd': True
		})
		self.assertEqual(psdict.a, 'b')
		self.assertEqual(psdict.b, 3)
		self.assertEqual(psdict.c, ['a', 'b'])
		self.assertEqual(psdict.d, True)
	
	def testLoadDict(self):
		self.maxDiff = None
		ps = Parameters()
		ps.desc('A test program.\n The test description.')
		ps.example('prog -a A -b B\n prog -c C')
		ps.loadDict({
			'a': 'b',
			'b': 3,
			'b.type': int,
			'b.required': True,
			'b.desc': 'Option b',
			'b.show': True,
			'c': ['a', 'b'],
			'c.type': list,
			'c.show': False,
			'd': False,
			'd.desc': 'A switch',
		})
		self.assertEqual(ps.toDict(), {
			'a': 'b',
			'b': 3,
			'c': ['a', 'b'],
			'd': False
		})
		self.assertEqual(ps.help().splitlines(), ("""DESCRIPTION:
  A test program.
  The test description.

USAGE:
  %s --param-b <INT>

EXAMPLE:
  prog -a A -b B
  prog -c C

REQUIRED OPTIONS:
  --param-b <INT>                       - Option b

OPTIONAL OPTIONS:
  -h, --help, -H, -?                    - Print this help information.

""" % sys.argv[0]).splitlines())
	
	def testLoadFile(self):
		f1 = path.join(tempfile.gettempdir(), 'testLoadFile.json') 
		f2 = path.join(tempfile.gettempdir(), 'testLoadFile.conf') 
		with open(f1, 'w') as f:
			f.write("""
{
	"a": "b",
	"b": 3,
	"b.type": "int",
	"b.required": true,
	"b.desc": "Option b",
	"c": ["a", "b"],
	"c.type": "list",
	"c.show": false,
	"D": false,
	"D.desc": "A switch"
}			
""")
		
		ps = Parameters()
		ps.loadFile(f1)
		self.assertEqual(ps.toDict(), {
			'a': 'b',
			'b': 3,
			'c': ['a', 'b'],
			'D': False
		})
		
		with open(f2, 'w') as f:
			f.write("""
[Params]
a: b
b: 3
b.type: int
b.required: True
b.desc: Option b
c: 1
  aa
  bb
c.type: list
c.show: False
D: False
D.type: bool
D.desc: A switch
""")	
		ps = Parameters()
		ps.loadFile(f2)
		self.assertEqual(ps.toDict(), {
			'a': 'b',
			'b': 3,
			'c': ['1', 'aa', 'bb'],
			'D': False
		})
'''	
if __name__ == '__main__':
	unittest.main(verbosity=2)