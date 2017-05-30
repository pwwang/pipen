import os, sys, unittest
rootdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, rootdir)
from pyppl import proc
from pyppl import aggr
from pyppl import channel


class TestAggr (unittest.TestCase):

	def testInit (self):
		p1 = proc('aggr')
		p2 = proc('aggr')
		a  = aggr (p1, p2)
		self.assertTrue (isinstance(a, aggr))
		self.assertEqual (p2.depends, [p1])
		self.assertEqual (p1.aggr, 'a')
		self.assertEqual (p2.aggr, 'a')
		self.assertEqual (a.procs, [p1, p2])
		self.assertEqual (a.starts, [p1])
		self.assertEqual (a.ends, [p2])
		
		p3 = proc('aggr')
		p4 = proc('aggr')
		a2 = aggr (p3, p4, False)
		self.assertTrue (isinstance(a2, aggr))
		self.assertEqual (a2.procs, [p3, p4])
		self.assertEqual (p4.depends, [])
		self.assertEqual (p3.aggr, 'a2')
		self.assertEqual (p4.aggr, 'a2')
		self.assertEqual (a2.starts, [p3])
		self.assertEqual (a2.ends, [p4])
	
	def testCommprops (self):
		p1 = proc('commp')
		p2 = proc('commp')
		a  = aggr (p1, p2)
		a.forks = 10
		a.exportdir = './'
		for p in a.procs:
			self.assertEqual (p.forks, 10)
		self.assertEqual (p2.exportdir, './')
		
	def testInput (self):
		p1 = proc('commp')
		p2 = proc('commp')
		p1.input = "i11, i12"
		p2.input = "i21, i22"
		a  = aggr (p1, p2)
		self.assertRaisesRegexp(RuntimeError, r'Not enough data', a.__setattr__, 'input', [1])
		a.input = [(1,2)]
		
		#multiple starts
		p3 = proc('commp')
		p4 = proc('commp')
		p5 = proc('commp')
		p3.input = "i31, i32"
		p4.input = "i41, i42"
		a2 = aggr (p3, p4, p5, False)
		p5.depends = [p3, p4]
		a2.starts = [p3, p4]
		self.assertEqual (a2.starts, [p3, p4])
		self.assertEqual (a2.ends, [p5])
		self.assertRaisesRegexp(RuntimeError, r'Not enough data', a2.__setattr__, 'input', [(1,2,3)])
		self.assertRaisesRegexp(RuntimeError, r'Expect list or str for', a2.__setattr__, 'input', [(1,2,3,4)])
		a2.p3_commp.input = "i31, i32"
		a2.p4_commp.input = "i41, i42"
		a2.input = [(1,2,3,4)]
		self.assertEqual (p3.input["i31"], [(1,)])
		self.assertEqual (p3.input["i32"], [(2,)])
		self.assertEqual (p4.input["i41"], [(3,)])
		self.assertEqual (p4.input["i42"], [(4,)])
		
	def testDepends (self):
		p1 = proc('dep')
		p2 = proc('dep')
		p3 = proc('dep')
		p4 = proc('dep')
		a  = aggr (p1, p2)
		a.depends = [p3, p4]
		self.assertEqual (p1.depends, [p3, p4])
		
		p5 = proc('dep')
		p5.depends = a
		self.assertEqual (p5.depends, [p2])
		
	
	def testCopy (self):
		p1 = proc('copy')
		p2 = proc('copy')
		a  = aggr (p1, p2)
		a2 = a.copy()
		p3 = a2.procs[0]
		p4 = a2.procs[1]
		self.assertEqual (a.id, 'a')
		self.assertEqual (a2.id, 'a2')
		self.assertEqual (p3.id + '.' + p3.tag, 'p1.aggr')
		self.assertEqual (p4.id + '.' + p4.tag, 'p2.aggr')
		

if __name__ == '__main__':
	unittest.main()
