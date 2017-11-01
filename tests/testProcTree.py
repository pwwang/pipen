import path, unittest

from collections import OrderedDict
from pyppl import Box
from pyppl.proctree import ProcTree, ProcNode

class Proc(object):
	def __init__(self, id, tag = 'notag'):
		self.depends = []
		self.id = id
		self.tag = tag
		ProcTree.register(self)

	def __str__(self):
		return '<Proc(id=%s,tag=%s) @ %s>' % (self.id, self.tag, hex(id(self)))

	def __repr__(self):
		return self.__str__()

	def name(self):
		return self.id if not self.tag or self.tag == 'notag' else self.id + '.' + self.tag

unittest.TestLoader.sortTestMethodsUsing = lambda _, a, b: (a > b) - (a < b)
class TestProcTree (unittest.TestCase):

	procs = Box()

	def test0Register(self):
		TestProcTree.procs.p1 = Proc('p1')
		TestProcTree.procs.p2 = Proc('p2')

		self.assertEqual(len(ProcTree.NODES), 2)
		n1 = ProcTree.NODES[id(TestProcTree.procs.p1)]
		n2 = ProcTree.NODES[id(TestProcTree.procs.p2)]
		self.assertIs(n1.proc, TestProcTree.procs.p1)
		self.assertIs(n2.proc, TestProcTree.procs.p2)
		self.assertEqual(n1.prev, [])
		self.assertEqual(n2.prev, [])
		self.assertEqual(n1.next, [])
		self.assertEqual(n2.next, [])
		self.assertFalse(n1.ran)
		self.assertFalse(n2.ran)
		self.assertFalse(n1.start)
		self.assertFalse(n2.start)

	def test1Check(self):
		p3 = Proc('p1', 'notag')
		#ProcTree.check(p3)
		self.assertRaises(ValueError, ProcTree.check, p3)
		TestProcTree.procs.p3 = Proc('p3')
		ProcTree.check(TestProcTree.procs.p3)

	def test2GetNode(self):
		p1 = ProcTree.getNode(TestProcTree.procs.p1).proc
		p2 = ProcTree.getNode(TestProcTree.procs.p2).proc
		p3 = ProcTree.getNode(TestProcTree.procs.p3).proc
		self.assertIs(p1, TestProcTree.procs.p1)
		self.assertIs(p2, TestProcTree.procs.p2)
		self.assertIs(p3, TestProcTree.procs.p3)

	def test3Init(self):
		TestProcTree.procs.p2.depends = [TestProcTree.procs.p1]
		TestProcTree.procs.p3.depends = [TestProcTree.procs.p2]
		pt = ProcTree()
		self.assertIsInstance(pt, ProcTree)
		self.assertEqual(len(ProcTree.NODES), 4)

		n1 = ProcTree.getNode(TestProcTree.procs.p1)
		n2 = ProcTree.getNode(TestProcTree.procs.p2)
		n3 = ProcTree.getNode(TestProcTree.procs.p3)

		self.assertEqual(n1.prev, [])
		self.assertEqual(n2.prev, [n1])
		self.assertEqual(n3.prev, [n2])
		self.assertEqual(n1.next, [n2])
		self.assertEqual(n2.next, [n3])
		self.assertEqual(n3.next, [])

	def test4SetGetStarts(self):
		pt = ProcTree()
		pt.setStarts([TestProcTree.procs.p1])
		n1 = ProcTree.getNode(TestProcTree.procs.p1)
		self.assertTrue(n1.start)
		self.assertEqual(pt.getStarts(), [TestProcTree.procs.p1])

	def test5GetEnds(self):
		n3 = ProcTree.getNode(TestProcTree.procs.p3)
		pt = ProcTree()
		pt.setStarts([TestProcTree.procs.p1])
		ends = pt.getEnds()
		self.assertEqual(ends, [TestProcTree.procs.p3])

	def test6GetNextToRun(self):
		pt = ProcTree()
		n1 = ProcTree.getNode(TestProcTree.procs.p1)
		n2 = ProcTree.getNode(TestProcTree.procs.p2)
		n3 = ProcTree.getNode(TestProcTree.procs.p3)
		pt.setStarts([TestProcTree.procs.p1])
		
		n2r = pt.getNextToRun()
		self.assertEqual(n2r, n1.proc)
		n2r = pt.getNextToRun()
		self.assertEqual(n2r, n2.proc)
		n2r = pt.getNextToRun()
		self.assertEqual(n2r, n3.proc)
		n2r = pt.getNextToRun()
		self.assertEqual(n2r, None)

	#@unittest.skip('')
	def test7GetPaths(self):
		ProcTree.NODES = OrderedDict()

		p1 = Proc('p1')
		p2 = Proc('p2')
		p3 = Proc('p3')
		p4 = Proc('p4')
		p5 = Proc('p5')
		p6 = Proc('p6')
		p7 = Proc('p7')
		p8 = Proc('p8')
		p9 = Proc('p9')
		p10 = Proc('p10')
		p11 = Proc('p11')
		"""
				   p1         p8
				/      \      /  \
			p2           p3        p10
				\      /
				   p4         p9
				/      \      /
			p5             p6 
				\      /
				   p7            p11(obsolete)
		"""
		p2.depends = [p1]
		p3.depends = [p1, p8]
		p4.depends = [p2, p3]
		p5.depends = [p4]
		p6.depends = [p4, p9]
		p7.depends = [p5, p6]
		p10.depends = [p8]

		n1 = ProcTree.getNode(p1)
		n2 = ProcTree.getNode(p2)
		n3 = ProcTree.getNode(p3)
		n4 = ProcTree.getNode(p4)
		n5 = ProcTree.getNode(p5)
		n6 = ProcTree.getNode(p6)
		n7 = ProcTree.getNode(p7)
		n8 = ProcTree.getNode(p8)
		n9 = ProcTree.getNode(p9)
		n10 = ProcTree.getNode(p10)

		self.assertEqual(len(ProcTree.NODES), 11)
		pt = ProcTree()
		self.assertRaises(ValueError, pt.getEnds)
		pt.setStarts([p1])
		self.assertEqual(pt.getStarts(), [p1])
		self.assertRaises(ValueError, pt.getEnds)
		pt.starts = []
		pt.setStarts([p1, p8, p9])
		self.assertEqual(len(pt.getEnds()), 2)
		self.assertIn(p7, pt.getEnds())
		self.assertIn(p10, pt.getEnds())

		self.assertEqual(pt.getNextToRun(), p1)
		self.assertEqual(pt.getNextToRun(), p2)
		self.assertEqual(pt.getNextToRun(), p8)
		self.assertEqual(pt.getNextToRun(), p3)
		self.assertEqual(pt.getNextToRun(), p4)
		self.assertEqual(pt.getNextToRun(), p5)
		self.assertEqual(pt.getNextToRun(), p9)
		self.assertEqual(pt.getNextToRun(), p6)
		self.assertEqual(pt.getNextToRun(), p7)
		self.assertEqual(pt.getNextToRun(), p10)
		self.assertEqual(pt.getNextToRun(), None)
		
		n1.start = False
		n8.start = False
		n9.start = False
		pt.starts = []
		self.assertEqual(pt.getStarts(), [])
		pt.ends  = []
		self.assertRaises(ValueError, pt.getEnds)
		pt.setStarts([p4, p9])
		self.assertEqual(pt.getEnds(), [p7])
		paths = pt.getPaths(p7)
		self.assertIn([p5, p4, p3, p1], paths)
		self.assertNotIn([p5, p4], paths)
		paths = pt.getPathsToStarts(p7)
		self.assertNotIn([p5, p4, p3, p1], paths)
		self.assertIn([p5, p4], paths)

	
	def test8Obsolete(self):
		ProcTree.NODES = OrderedDict()
		p1 = Proc('p1')
		p2 = Proc('p2')
		pt = ProcTree()
		pt.setStarts([p2])
		self.assertEqual(pt.getEnds(), [p2])

	def testLoop(self):
		ProcTree.NODES = OrderedDict()
		p1 = Proc('p1')
		p2 = Proc('p2')
		p3 = Proc('p3')
		p2.depends = [p1]
		p3.depends = [p2]
		p1.depends = [p3]
		pt = ProcTree()
		pt.setStarts([p1])
		#pt.getEnds()
		self.assertRaises(ValueError, pt.getEnds)



if __name__ == '__main__':
	unittest.main(verbosity=2, failfast=True)