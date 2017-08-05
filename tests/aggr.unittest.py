import os, sys, unittest
rootdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, rootdir)
from pyppl import proc
from pyppl import aggr
from pyppl import channel
from pyppl import utils


class TestAggr (unittest.TestCase):

	def testInit (self):
		p1 = proc('aggr')
		p2 = proc('aggr')
		a  = aggr (p1, p2)
		self.assertTrue (isinstance(a, aggr))
		self.assertEqual (a.p2.depends, [a.p1])
		self.assertEqual (a.p1.aggr, 'a')
		self.assertEqual (a.p2.aggr, 'a')
		self.assertEqual (a.procs, [a.p1, a.p2])
		self.assertEqual (a.starts, [a.p1])
		self.assertEqual (a.ends, [a.p2])
		
		p3 = proc('aggr')
		p4 = proc('aggr')
		a2 = aggr (p3, p4, False)
		self.assertTrue (isinstance(a2, aggr))
		self.assertEqual (a2.procs, [a2.p3, a2.p4])
		self.assertEqual (a2.p4.depends, [])
		self.assertEqual (a2.p3.aggr, 'a2')
		self.assertEqual (a2.p4.aggr, 'a2')
		self.assertEqual (a2.starts, [])
		self.assertEqual (a2.ends, [])
	
	def testCommprops (self):
		p1 = proc('commp')
		p2 = proc('commp')
		a  = aggr (p1, p2)
		a.forks = 10
		a.exportdir = './'
		for p in a.procs:
			self.assertEqual (p.forks, 10)
		self.assertEqual (a.p2.exportdir, './')
		
	def testInput (self):
		p1 = proc('commp')
		p2 = proc('commp')
		p1.input = "i11, i12"
		p2.input = "i21, i22"
		a  = aggr (p1, p2)
		a.input = [(1,2)]
		self.assertEqual (a.p1.input, {"i11, i12": [(1,2)]})
		
		#multiple starts
		p3 = proc('commp')
		p4 = proc('commp')
		p5 = proc('commp')
		p3.input = "i31, i32"
		p4.input = "i41, i42"
		a2 = aggr (p3, p4, p5, False)
		p5.depends = [a2.p3, a2.p4]
		a2.starts = [a2.p3, a2.p4]
		self.assertEqual (a2.starts, [a2.p3, a2.p4])
		self.assertEqual (a2.ends, [])
		a2.p3.input = {a2.p3.input: []}
		self.assertNotEqual (p3, a2.p3)
		#self.assertRaisesRegexp(RuntimeError, r'Not enough data', a2.__setattr__, 'input', [(1,2,3)])
		self.assertRaises(RuntimeError, a2.__setattr__, 'input', [(1,2,3,4)])
		a2.p3.input = "i31, i32"
		a2.p4.input = "i41, i42"
		a2.input = [(1,2,3,4)]
		self.assertEqual (a2.p3.input["i31, i32"], [(1,2)])
		self.assertEqual (a2.p4.input["i41, i42"], [(3,4)])
		
	def testDepends (self):
		p1 = proc('dep')
		p2 = proc('dep')
		p3 = proc('dep')
		p4 = proc('dep')
		a  = aggr (p1, p2)
		a.depends = [p3, p4]
		self.assertEqual (a.p1.depends, [p3, p4])
		
		p5 = proc('dep')
		p5.depends = a
		self.assertEqual (p5.depends, [a.p2])
		
	
	def testCopy (self):
		p1 = proc('copy')
		p2 = proc('copy')
		a  = aggr (p1, p2)
		a2 = a.copy()
		p3 = a2.procs[0]
		p4 = a2.procs[1]
		self.assertEqual (a.id, 'a')
		self.assertEqual (a2.id, 'a2')
		self.assertEqual (p3.id + '.' + p3.tag, 'p1.' + utils.uid(a2.id, 4))
		self.assertEqual (p4.id + '.' + p4.tag, 'p2.' + utils.uid(a2.id, 4))
		

if __name__ == '__main__':
	unittest.main()
