import sys, unittest, os, glob
rootdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, rootdir)
from pyppl import params
from pyppl.helpers.parameters import parameter
from pyppl.helpers.parameters import parameters

class TestParameters (unittest.TestCase):
	
	def testParameterInit(self):
		p = parameter('a', 1)
		
		self.assertIsInstance(p, parameter)
		self.assertEquals(p.desc, '')
		self.assertEquals(p.required, False)
		self.assertEquals(p.show, True)
		self.assertEquals(p.type, int)
		
		self.assertEquals(str(p), '1')
		
	def testParameterSetDesc(self):
		p = parameter('x', [1,2,3])
		p.desc = "abcd whatever"
		self.assertEquals(p.desc, "abcd whatever")
		
		p.setDesc('awlwaefwef')
		self.assertEquals(p.desc, "awlwaefwef")
		
	def testParameterSetRequired(self):
		p = parameter('a.e', 1.1)
		p.required = False
		self.assertEquals(p.required, False)
		p.setRequired(True)
		self.assertEquals(p.required, True)
		
	def testParameterSetType(self):
		p = parameter('A', 10)
		p.setType(bool)
		self.assertIs(p.value, True)
		self.assertIsNot(p.value, int)
		self.assertIs(p.type, bool)
		self.assertRaises(TypeError, p.setType, dict)
		p.type = int
		self.assertIs (p.type, int)
		self.assertIs (p.value, 1)
		self.assertIsNot (p.value, bool)
		
	def testParameterSetShow(self):
		p = parameter('x', 1)
		p.show = True
		self.assertIs(p.show, True)
		p.setShow(False)
		self.assertIs(p.show, False)
	
	def testParameterSetValue(self):
		p = parameter('a', 4)
		self.assertIs(p.value, 4)
		p.value = '3'
		self.assertIs(p.value, '3')
		p.setValue(2)
		self.assertIs(p.value, 2)
		
	def testParameterSetName(self):
		p = parameter('a', 4)
		self.assertIs(p.name, 'a')
		p.name = '3'
		self.assertIs(p.name, '3')
		p.setName('d')
		self.assertIs(p.name, 'd')
		
	def testParameterForceType(self):
		p = parameter('a', 4)
		p.type = str
		p._forceType()
		self.assertIs (p.value, '4')
		
	def testParameterPrintName(self):
		p = parameter('c', 9)
		self.assertEquals (p._printName('--param-'), "--param-c <int>")
		p.type = bool
		self.assertEquals (p._printName('--param-'), "--param-c (bool)")
		
	def testParametersInit (self):
		ps = parameters()
		self.assertEquals(ps.props, {
			'_usage':'', 
			'_example':'', 
			'_desc':'', 
			'_hopts': ['-h', '--help', '-H', '-?', ''],
			'_prefix': '--param-'})
		self.assertEquals(ps.params, {})
	
	def testParametersSetAttr(self):
		ps = parameters()
		ps.a = 'a'
		self.assertEquals(ps.a.name, 'a')
		self.assertEquals(ps.a.value, 'a')
		self.assertEquals(ps.a.type, str)
		self.assertEquals(ps.a.desc, '')
		self.assertEquals(ps.a.required, False)
		self.assertEquals(ps.a.show, True)
		
	def testParametersGetAttr(self):
		ps = parameters()
		ps.a
		self.assertEquals(ps.a.name, 'a')
		self.assertEquals(ps.a.value, '')
		self.assertEquals(ps.a.type, str)
		self.assertEquals(ps.a.desc, '')
		self.assertEquals(ps.a.required, False)
		self.assertEquals(ps.a.show, True)
		ps.a.setValue(1).setType(int)
		self.assertIs(ps.a.value, 1)
		self.assertEquals(ps.a.type, int)
		
	def testParametersProps(self):
		ps = parameters()
		ps.usage('Usage').example('Example').desc('Desc')
		self.assertEquals(ps.props['_usage'], 'Usage')
		self.assertEquals(ps.props['_example'], 'Example')
		self.assertEquals(ps.props['_desc'], 'Desc')
	
	def testParametersLoadDict(self):
		ps = parameters()
		d2load = {
			'p1': 1,
			'p1.required': True,
			'p2': [1,2,3],
			'p2.show': True,
			'p3': 2.3,
			'p3.desc': 'The p3 params'
		}
		ps.loadDict(d2load)
		self.assertIs (ps.p1.value, 1)
		self.assertIs (ps.p1.required, True)
		self.assertIs (ps.p1.show, False)
		self.assertEquals (ps.p2.value, [1,2,3])
		self.assertIs (ps.p2.show, True)
		self.assertIs (ps.p2.type, list)
		self.assertIs (ps.p3.value, 2.3)
		self.assertIs (ps.p3.type, float)
		self.assertIs (ps.p3.show, False)
	
	def testParametersHelp (self):
		ps = parameters()
		d2load = {
			'p1': 1,
			'p1.required': True,
			'p2': [1,2,3],
			'p2.show': True,
			'p3': 2.3,
			'p3.desc': 'The p3 params',
			'p3.required': True,
			'p3.show': True
		}
		ps.loadDict(d2load)
		self.assertEquals (ps._help().split("\n"), """\
USAGE:
-----
  {} --param-p3 <float> [OPTIONS]

REQUIRED OPTIONS:
----------------
  --param-p3 <float>                    The p3 params

OPTIONAL OPTIONS:
----------------
  --param-p2 <list>                     Default: [1, 2, 3]
  -h, --help, -H, -?                    Print this help information.

""".format(sys.argv[0]).split("\n"))
	
	def testParametersParse(self):
		sys.argv = [sys.argv[0], "--param-p3", "5.1", "--param-p2=4", "5", "6", "--param-bamdir", "/a/b/c/mm/pipeline/workdir/bam.2ITurpH4.0", "--param-test"]
		ps = parameters()
		d2load = {
			'p1': 1,
			'p1.required': True,
			'p2': [1,2,3],
			'p2.show': True,
			'p3': 2.3,
			'p3.desc': 'The p3 params',
			'p3.required': True,
			'p3.show': True
		}
		ps.loadDict(d2load)
		ps.bamdir.setRequired().setDesc('The temporary bam directory for this batch.')
		ps.test.setType(bool).setValue(False).setDesc('Run a test instance?')
		ps.parse()
		self.assertEquals(ps.p3.value, 5.1)
		self.assertEquals(ps.p2.value, ['4', '5', '6'])
		self.assertEquals(ps.bamdir.value, "/a/b/c/mm/pipeline/workdir/bam.2ITurpH4.0")
		self.assertEquals(ps.test.value, True)
		
		from tempfile import NamedTemporaryFile
		from json import dumps
		
		f = NamedTemporaryFile(delete = False, suffix='.json')
		f.write(dumps(d2load))
		f.close()
		ps1 = parameters()
		ps1.loadCfgfile(f.name)		
		sys.argv = [sys.argv[0], "--param-p3", "2", "--param-p2=4"]
		ps1.parse()
		self.assertEquals(ps1.p3.value, 2.0)
		self.assertEquals(ps1.p2.value, ['4'])
		try: 
			os.remove(f.name)
		except:
			pass
		
		f = NamedTemporaryFile(delete = False, suffix='.cfg')
		f.write('[Config]\n')
		for k,v in d2load.items():
			f.write(k + '=' + str(v) + '\n')
		f.write('p1.type: int\n')
		f.write('p2.type: list\n')
		f.write('p3.type: float\n')
		f.close()
		ps1 = parameters()
		ps1.loadCfgfile(f.name)	
		sys.argv = [sys.argv[0], "--param-p3", "10", "--param-p2", "9", "10"]
		ps1.parse()
		self.assertEquals(ps1.p3.value, 10.0)
		self.assertEquals(ps1.p2.value, ['9', '10'])
		try: 
			os.remove(f.name)
		except:
			pass
		
	def testSetPrefix (self):
		sys.argv = [sys.argv[0], "-p-p3", "5.1", "-p-p2=4", "5", "6"]
		ps = parameters()
		ps.prefix('-p-')
		d2load = {
			'p1': 1,
			'p1.required': True,
			'p2': [1,2,3],
			'p2.show': True,
			'p3': 2.3,
			'p3.desc': 'The p3 params',
			'p3.required': True,
			'p3.show': True
		}
		ps.loadDict(d2load)
		ps.parse()
		self.assertEquals(ps.p3.value, 5.1)
		self.assertEquals(ps.p2.value, ['4', '5', '6'])
	
if __name__ == '__main__':
	unittest.main()