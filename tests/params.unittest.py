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
		self.assertEquals (p._printName(), parameters.prefix + "c <int>")
		p.type = bool
		self.assertEquals (p._printName(), parameters.prefix + "c (bool)")
		
	def testParametersInit (self):
		ps = parameters()
		self.assertEquals(ps.props, {'_usage':'', '_example':'', '_desc':''})
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
		ps.a.setValue(1)
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
			'p3.desc': 'The p3 params'
		}
		self.assertEquals (ps._help(), """USAGE:
-----
  {} 

""".format(sys.argv[0]))
	
	def testParametersParse(self):
		pass
		
	
if __name__ == '__main__':
	unittest.main()