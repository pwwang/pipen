import helpers, unittest

from collections import OrderedDict

from pyppl import Proc
from pyppl.proctree import ProcTree, ProcNode
from pyppl.exception import ProcTreeProcExists, ProcTreeParseError

class TestProcNode(helpers.TestCase):

	def testInit(self):
		proc = Proc()
		self.maxDiff = None
		pn = ProcNode(proc)
		self.assertIs(pn.proc, proc)
		self.assertListEqual(pn.prev, [])
		self.assertListEqual(pn.next, [])
		self.assertEqual(pn.ran, False)
		self.assertEqual(pn.start, False)
		self.assertIn('File ', pn.defs[0])

	def dataProvider_testSameIdTag(self):
		proc1 = Proc()
		pn1   = ProcNode(proc1)
		yield pn1, proc1, True

		proc2 = Proc()
		yield pn1, proc2, False

	def testSameIdTag(self, pn, proc, out):
		self.assertEqual(pn.sameIdTag(proc), out)

	def testRepr(self):
		proc = Proc()
		pn   = ProcNode(proc)
		self.assertEqual(repr(pn), '<ProcNode(<Proc(id=%s,tag=%s) @ %s>) @ %s>' % (proc.id, proc.tag, hex(id(proc)), hex(id(pn))))

class TestProcTree(helpers.TestCase):

	def setUp(self):
		# procs registered by Proc.__init__() are also removed!
		ProcTree.NODES = OrderedDict()
		
	def dataProvider_testRegister(self):
		proc_testRegister1 = Proc()
		yield proc_testRegister1, 1
		yield proc_testRegister1, 1
		proc_testRegister2 = Proc()
		yield proc_testRegister2, 2

	def testRegister(self, proc, l):
		ProcTree.register(proc)
		key = id(proc)
		self.assertIs(ProcTree.NODES[key].proc, proc)
		self.assertEqual(len(ProcTree.NODES), l)

	def dataProvider_testCheck(self):
		proc_testCheck1 = Proc()
		proc_testCheck2 = Proc()
		proc_testCheck3 = Proc(id = 'proc_testCheck1')
		yield proc_testCheck1, False
		yield proc_testCheck2, False
		yield proc_testCheck3, True

	def testCheck(self, proc, r):
		ProcTree.register(proc)
		if r:
			self.assertRaises(ProcTreeProcExists, ProcTree.check, proc)
		else:
			ProcTree.check(proc)

	def dataProvider_testGetNode(self):
		proc_testGetNode1 = Proc()
		proc_testGetNode2 = Proc()
		yield proc_testGetNode1,
		yield proc_testGetNode2,

	def testGetNode(self, proc):
		ProcTree.register(proc)
		self.assertIs(ProcTree.getNode(proc).proc, proc)

	def dataProvider_testGetPrevNextStr(self):
		proc_testGetPrevNextStr1 = Proc()
		proc_testGetPrevNextStr2 = Proc()
		proc_testGetPrevNextStr3 = Proc()
		proc_testGetPrevNextStr2.depends = proc_testGetPrevNextStr1
		proc_testGetPrevNextStr3.depends = proc_testGetPrevNextStr2
		ps = [proc_testGetPrevNextStr1, proc_testGetPrevNextStr2, proc_testGetPrevNextStr3]
		yield ps, proc_testGetPrevNextStr1, 'prev', 'START'
		yield ps, proc_testGetPrevNextStr2, 'prev', '[proc_testGetPrevNextStr1]'
		yield ps, proc_testGetPrevNextStr3, 'prev', '[proc_testGetPrevNextStr2]'
		yield ps, proc_testGetPrevNextStr1, 'next', '[proc_testGetPrevNextStr2]'
		yield ps, proc_testGetPrevNextStr2, 'next', '[proc_testGetPrevNextStr3]'
		yield ps, proc_testGetPrevNextStr3, 'next', 'END'

	def testGetPrevNextStr(self, procs, proc, which, out):
		for p in procs:
			ProcTree.register(p)
		ProcTree()
		if which == 'prev':
			self.assertEqual(ProcTree.getPrevStr(proc), out)
		else:
			self.assertEqual(ProcTree.getNextStr(proc), out)

	def dataProvider_testGetNext(self):
		proc_testGetNext1 = Proc()
		proc_testGetNext2 = Proc()
		proc_testGetNext3 = Proc()
		proc_testGetNext4 = Proc()
		proc_testGetNext2.depends = proc_testGetNext1
		proc_testGetNext3.depends = proc_testGetNext2
		proc_testGetNext4.depends = proc_testGetNext2
		ps = [proc_testGetNext1, proc_testGetNext2, proc_testGetNext3, proc_testGetNext4]
		yield ps, proc_testGetNext1, [proc_testGetNext2]
		yield ps, proc_testGetNext2, [proc_testGetNext3, proc_testGetNext4]
		yield ps, proc_testGetNext3, []
		yield ps, proc_testGetNext4, []

	def testGetNext(self, procs, proc, outs):
		for p in procs:
			ProcTree.register(p)
		ProcTree()
		nexts = ProcTree.getNext(proc)
		self.assertItemEqual(nexts, outs)

	def dataProvider_testReset(self):
		proc_testReset1 = Proc()
		proc_testReset2 = Proc()
		proc_testReset3 = Proc()
		proc_testReset4 = Proc()
		proc_testReset2.depends = proc_testReset1
		proc_testReset3.depends = proc_testReset2
		proc_testReset4.depends = proc_testReset2
		yield [proc_testReset1, proc_testReset2, proc_testReset3, proc_testReset4], 

	def testReset(self, procs):
		for p in procs:
			ProcTree.register(p)
		ProcTree()
		ProcTree.reset()
		for node in ProcTree.NODES.values():
			self.assertListEqual(node.prev, [])
			self.assertListEqual(node.next, [])
			self.assertFalse(node.ran)
			self.assertFalse(node.start)

	def dataProvider_testInit(self):
		proc_testInit1 = Proc()
		proc_testInit2 = Proc()
		proc_testInit3 = Proc()
		proc_testInit4 = Proc()
		proc_testInit2.depends = proc_testInit1
		proc_testInit3.depends = proc_testInit2
		proc_testInit4.depends = proc_testInit2
		yield [proc_testInit1, proc_testInit2, proc_testInit3, proc_testInit4], 
		yield [proc_testInit1, proc_testInit3], 

	def testInit(self, procs):
		for p in procs:
			ProcTree.register(p)
		pt = ProcTree()
		self.assertEqual(pt.starts, [])
		self.assertEqual(pt.ends, [])
		for proc in procs:
			depends = proc.depends
			for depend in depends:
				nproc   = ProcTree.getNode(proc)
				ndepend = ProcTree.getNode(depend)
				self.assertIn(nproc, ndepend.next)
				self.assertIn(ndepend, nproc.prev)

	def dataProvider_testSetGetStarts(self):
		proc_testSetGetStarts1 = Proc()
		proc_testSetGetStarts2 = Proc()
		proc_testSetGetStarts3 = Proc()
		proc_testSetGetStarts4 = Proc()
		proc_testSetGetStarts2.depends = proc_testSetGetStarts1
		proc_testSetGetStarts3.depends = proc_testSetGetStarts2
		proc_testSetGetStarts4.depends = proc_testSetGetStarts2
		yield [proc_testSetGetStarts1, proc_testSetGetStarts2, proc_testSetGetStarts3, proc_testSetGetStarts4], [proc_testSetGetStarts1]
		yield [proc_testSetGetStarts2, proc_testSetGetStarts3, proc_testSetGetStarts4], [proc_testSetGetStarts2]
		yield [proc_testSetGetStarts1, proc_testSetGetStarts2, proc_testSetGetStarts3, proc_testSetGetStarts4], [proc_testSetGetStarts1, proc_testSetGetStarts2]

	def testSetGetStarts(self, procs, starts):
		for p in procs:
			ProcTree.register(p)
		pt = ProcTree()
		pt.setStarts(starts)
		for proc in procs:
			if proc in starts:
				self.assertTrue(ProcTree.getNode(proc).start)
			else:
				self.assertFalse(ProcTree.getNode(proc).start)
		s = pt.getStarts()
		self.assertItemEqual(s, starts)
		self.assertItemEqual(pt.starts, starts)

	def dataProvider_testGetPaths(self):
		proc_testGetPaths1 = Proc()
		proc_testGetPaths2 = Proc()
		proc_testGetPaths3 = Proc()
		proc_testGetPaths4 = Proc()
		proc_testGetPaths5 = Proc()
		proc_testGetPaths2.depends = proc_testGetPaths1
		proc_testGetPaths3.depends = proc_testGetPaths2, proc_testGetPaths4
		proc_testGetPaths4.depends = proc_testGetPaths2
		proc_testGetPaths5.depends = proc_testGetPaths1
		"""
		proc1 -> proc2 -> proc3
			\        \    /
			  proc5  proc4
		"""
		ps = [proc_testGetPaths1, proc_testGetPaths2, proc_testGetPaths3, proc_testGetPaths4, proc_testGetPaths5]
		yield ps, proc_testGetPaths1, []
		yield ps, proc_testGetPaths2, [[proc_testGetPaths1]]
		yield ps, proc_testGetPaths3, [[proc_testGetPaths2, proc_testGetPaths1], [proc_testGetPaths4, proc_testGetPaths2, proc_testGetPaths1]]
		yield ps, proc_testGetPaths4, [[proc_testGetPaths2, proc_testGetPaths1]]
		yield ps, proc_testGetPaths5, [[proc_testGetPaths1]]

		proc_testGetPaths6 = Proc()
		proc_testGetPaths7 = Proc()
		proc_testGetPaths8 = Proc()
		proc_testGetPaths7.depends = proc_testGetPaths6
		proc_testGetPaths8.depends = proc_testGetPaths7
		proc_testGetPaths6.depends = proc_testGetPaths8
		ps2 = [proc_testGetPaths6, proc_testGetPaths7, proc_testGetPaths8]
		yield ps2, proc_testGetPaths6, [], True

		proc_testGetPaths10 = Proc()
		proc_testGetPaths11 = Proc()
		proc_testGetPaths12 = Proc()
		proc_testGetPaths11.depends = proc_testGetPaths10
		proc_testGetPaths12.depends = proc_testGetPaths11
		proc_testGetPaths10.depends = proc_testGetPaths11
		ps3 = [proc_testGetPaths10, proc_testGetPaths11, proc_testGetPaths12]
		yield ps3, proc_testGetPaths12, [], True

		# should be ok: 
		# 13 -> 15
		# 14 -> 15
		# 13 -> 14
		proc_testGetPaths13 = Proc()
		proc_testGetPaths14 = Proc()
		proc_testGetPaths15 = Proc()
		proc_testGetPaths15.depends = proc_testGetPaths13, proc_testGetPaths14
		proc_testGetPaths14.depends = proc_testGetPaths13
		ps4 = [proc_testGetPaths13, proc_testGetPaths14, proc_testGetPaths15]
		yield ps4, proc_testGetPaths15, [[proc_testGetPaths13], [proc_testGetPaths14, proc_testGetPaths13]]


	def testGetPaths(self, procs, proc, paths, exception = None):
		for p in procs:
			ProcTree.register(p)
		pt = ProcTree()
		if exception:
			self.assertRaises(ProcTreeParseError, pt.getPaths, proc)
		else:
			ps = pt.getPaths(proc)
			self.assertListEqual(ps, paths)

	def dataProvider_testGetPathsToStarts(self):
		proc_testGetPathsToStarts1 = Proc()
		proc_testGetPathsToStarts2 = Proc()
		proc_testGetPathsToStarts3 = Proc()
		proc_testGetPathsToStarts4 = Proc()
		proc_testGetPathsToStarts5 = Proc()
		proc_testGetPathsToStarts2.depends = proc_testGetPathsToStarts1
		proc_testGetPathsToStarts3.depends = proc_testGetPathsToStarts2, proc_testGetPathsToStarts4
		proc_testGetPathsToStarts4.depends = proc_testGetPathsToStarts2
		proc_testGetPathsToStarts5.depends = proc_testGetPathsToStarts1
		"""
		proc1 -> proc2 -> proc3
			\        \    /
			  proc5  proc4
		"""
		ps = [proc_testGetPathsToStarts1, proc_testGetPathsToStarts2, proc_testGetPathsToStarts3, proc_testGetPathsToStarts4, proc_testGetPathsToStarts5]
		yield ps, [proc_testGetPathsToStarts1], proc_testGetPathsToStarts1, []
		yield ps, [proc_testGetPathsToStarts1], proc_testGetPathsToStarts2, [[proc_testGetPathsToStarts1]]
		yield ps, [proc_testGetPathsToStarts2], proc_testGetPathsToStarts2, []
		yield ps, [proc_testGetPathsToStarts1], proc_testGetPathsToStarts3, [[proc_testGetPathsToStarts2, proc_testGetPathsToStarts1], [proc_testGetPathsToStarts4, proc_testGetPathsToStarts2, proc_testGetPathsToStarts1]]
		yield ps, [proc_testGetPathsToStarts1, proc_testGetPathsToStarts4], proc_testGetPathsToStarts3, [[proc_testGetPathsToStarts2, proc_testGetPathsToStarts1], [proc_testGetPathsToStarts4, proc_testGetPathsToStarts2, proc_testGetPathsToStarts1]]
		yield ps, [proc_testGetPathsToStarts2], proc_testGetPathsToStarts3, [[proc_testGetPathsToStarts2], [proc_testGetPathsToStarts4, proc_testGetPathsToStarts2]]
		yield ps, [proc_testGetPathsToStarts1], proc_testGetPathsToStarts4, [[proc_testGetPathsToStarts2, proc_testGetPathsToStarts1]]
		yield ps, [proc_testGetPathsToStarts1], proc_testGetPathsToStarts5, [[proc_testGetPathsToStarts1]]

	def testGetPathsToStarts(self, procs, starts, proc, paths):
		for p in procs:
			ProcTree.register(p)
		pt = ProcTree()
		pt.setStarts(starts)
		ps = pt.getPathsToStarts(proc)
		self.assertListEqual(ps, paths)

	def dataProvider_testCheckPath(self):
		proc_testCheckPath0 = Proc()
		proc_testCheckPath1 = Proc()
		proc_testCheckPath2 = Proc()
		proc_testCheckPath3 = Proc()
		proc_testCheckPath4 = Proc()
		proc_testCheckPath5 = Proc()
		proc_testCheckPath2.depends = proc_testCheckPath0, proc_testCheckPath1
		proc_testCheckPath3.depends = proc_testCheckPath2, proc_testCheckPath4
		proc_testCheckPath4.depends = proc_testCheckPath2
		proc_testCheckPath5.depends = proc_testCheckPath1
		"""
			proc0
				\
		proc1 -> proc2 -> proc3
			\        \    /
			  proc5  proc4
		"""
		ps = [proc_testCheckPath0, proc_testCheckPath1, proc_testCheckPath2, proc_testCheckPath3, proc_testCheckPath4, proc_testCheckPath5]
		yield ps, [proc_testCheckPath1], proc_testCheckPath1, True
		yield ps, [proc_testCheckPath1], proc_testCheckPath2, [proc_testCheckPath0]
		yield ps, [proc_testCheckPath0, proc_testCheckPath1], proc_testCheckPath2, True
		yield ps, [proc_testCheckPath0, proc_testCheckPath1], proc_testCheckPath3, True
		yield ps, [proc_testCheckPath0], proc_testCheckPath3, [proc_testCheckPath2, proc_testCheckPath1]

	def testCheckPath(self, procs, starts, proc, passed):
		for p in procs:
			ProcTree.register(p)
		pt = ProcTree()
		pt.setStarts(starts)
		if isinstance(passed, bool):
			self.assertEqual(pt.checkPath(proc), passed)
		else:
			self.assertListEqual(pt.checkPath(proc), passed)

	def dataProvider_testGetEnds(self):
		# check for loops
		proc_testGetEnds_loop0 = Proc()
		proc_testGetEnds_loop1 = Proc()
		proc_testGetEnds_loop2 = Proc()
		proc_testGetEnds_loop3 = Proc()
		proc_testGetEnds_loop1.depends = proc_testGetEnds_loop0
		proc_testGetEnds_loop2.depends = proc_testGetEnds_loop1
		proc_testGetEnds_loop3.depends = proc_testGetEnds_loop2
		proc_testGetEnds_loop0.depends = proc_testGetEnds_loop1
		"""
		0 -> 1 -> 2 -> 3
		|____|
		"""
		yield [proc_testGetEnds_loop0, proc_testGetEnds_loop1, proc_testGetEnds_loop2, proc_testGetEnds_loop3], [proc_testGetEnds_loop3], [], ProcTreeParseError, 'Loop dependency'

		proc_testGetEnds_loop4 = Proc()
		proc_testGetEnds_loop5 = Proc()
		proc_testGetEnds_loop6 = Proc()
		proc_testGetEnds_loop7 = Proc()
		proc_testGetEnds_loop5.depends = proc_testGetEnds_loop4
		proc_testGetEnds_loop6.depends = proc_testGetEnds_loop5
		proc_testGetEnds_loop7.depends = proc_testGetEnds_loop6
		proc_testGetEnds_loop4.depends = proc_testGetEnds_loop7
		"""
		4 -> 5 -> 6 -> 7
		|______________|
		"""
		yield [proc_testGetEnds_loop4, proc_testGetEnds_loop5, proc_testGetEnds_loop6, proc_testGetEnds_loop7], [proc_testGetEnds_loop7], [], ProcTreeParseError, 'Loop dependency'

		proc_testGetEnds0 = Proc()
		proc_testGetEnds1 = Proc()
		proc_testGetEnds2 = Proc()
		proc_testGetEnds3 = Proc()
		proc_testGetEnds4 = Proc()
		proc_testGetEnds5 = Proc()
		proc_testGetEnds2.depends = proc_testGetEnds0, proc_testGetEnds1
		proc_testGetEnds3.depends = proc_testGetEnds2, proc_testGetEnds4
		proc_testGetEnds4.depends = proc_testGetEnds2
		proc_testGetEnds5.depends = proc_testGetEnds1
		"""
			proc0
				\
		proc1 -> proc2 -> proc3
			\        \    /
			  proc5  proc4
		"""
		ps = [proc_testGetEnds0, proc_testGetEnds1, proc_testGetEnds2, proc_testGetEnds3, proc_testGetEnds4, proc_testGetEnds5]

		yield ps, [proc_testGetEnds5], [], ProcTreeParseError, 'one of the paths cannot go through'
		yield ps, [proc_testGetEnds1], [proc_testGetEnds5]
		yield ps, [proc_testGetEnds0, proc_testGetEnds1], [proc_testGetEnds3, proc_testGetEnds5]
		yield ps, [proc_testGetEnds0], [], ProcTreeParseError, 'one of the paths cannot go through'

		proc_testGetEnds6 = Proc()
		yield [proc_testGetEnds6], [proc_testGetEnds6], [proc_testGetEnds6]
		yield [proc_testGetEnds6], [], [], ProcTreeParseError, 'Failed to determine end processes by start processes'


	def testGetEnds(self, procs, starts, ends, exception = None, msg = None):
		for p in procs:
			ProcTree.register(p)
		pt = ProcTree()
		pt.setStarts(starts)
		if exception:
			self.assertRaisesStr(ProcTreeParseError, msg, pt.getEnds)
		else:
			self.assertItemEqual(pt.getEnds(), ends)

	def dataProvider_testGetAllPaths(self):
		proc_testGetAllPaths0 = Proc()
		proc_testGetAllPaths1 = Proc()
		proc_testGetAllPaths2 = Proc()
		proc_testGetAllPaths3 = Proc()
		proc_testGetAllPaths4 = Proc()
		proc_testGetAllPaths5 = Proc()
		proc_testGetAllPaths2.depends = proc_testGetAllPaths0, proc_testGetAllPaths1
		proc_testGetAllPaths3.depends = proc_testGetAllPaths2, proc_testGetAllPaths4
		proc_testGetAllPaths4.depends = proc_testGetAllPaths2
		proc_testGetAllPaths5.depends = proc_testGetAllPaths1
		"""
			proc0
				\
		proc1 -> proc2 -> proc3
			\        \    /
			  proc5  proc4
		"""
		ps = [proc_testGetAllPaths0, proc_testGetAllPaths1, proc_testGetAllPaths2, proc_testGetAllPaths3, proc_testGetAllPaths4, proc_testGetAllPaths5]
		yield ps, [proc_testGetAllPaths2], [[proc_testGetAllPaths3, proc_testGetAllPaths2], [proc_testGetAllPaths3, proc_testGetAllPaths4, proc_testGetAllPaths2]]
		yield ps, [proc_testGetAllPaths1], [[proc_testGetAllPaths5, proc_testGetAllPaths1]]
		yield ps, [proc_testGetAllPaths0, proc_testGetAllPaths1], [
			[proc_testGetAllPaths5, proc_testGetAllPaths1],
			[proc_testGetAllPaths3, proc_testGetAllPaths2, proc_testGetAllPaths0],
			[proc_testGetAllPaths3, proc_testGetAllPaths2, proc_testGetAllPaths1],
			[proc_testGetAllPaths3, proc_testGetAllPaths4, proc_testGetAllPaths2, proc_testGetAllPaths0],
			[proc_testGetAllPaths3, proc_testGetAllPaths4, proc_testGetAllPaths2, proc_testGetAllPaths1],
		]

		# obsolete
		proc_testGetAllPaths6 = Proc()
		yield [proc_testGetAllPaths6], [proc_testGetAllPaths6], [[proc_testGetAllPaths6]]

	def testGetAllPaths(self, procs, starts, paths):
		for p in procs:
			ProcTree.register(p)
		pt = ProcTree()
		pt.setStarts(starts)
		self.assertItemEqual(pt.getAllPaths(), paths)

	def dataProvider_testGetNextToRun(self):
		proc_testGetAllPaths0 = Proc()
		proc_testGetAllPaths1 = Proc()
		proc_testGetAllPaths2 = Proc()
		proc_testGetAllPaths3 = Proc()
		proc_testGetAllPaths4 = Proc()
		proc_testGetAllPaths5 = Proc()
		proc_testGetAllPaths2.depends = proc_testGetAllPaths0, proc_testGetAllPaths1
		proc_testGetAllPaths3.depends = proc_testGetAllPaths2, proc_testGetAllPaths4
		proc_testGetAllPaths4.depends = proc_testGetAllPaths2
		proc_testGetAllPaths5.depends = proc_testGetAllPaths1
		"""
			proc0
				\
		proc1 -> proc2 -> proc3
			\        \    /
			  proc5  proc4
		"""
		ps = [proc_testGetAllPaths0, proc_testGetAllPaths1, proc_testGetAllPaths2, proc_testGetAllPaths3, proc_testGetAllPaths4, proc_testGetAllPaths5]
		
		yield ps, [proc_testGetAllPaths0], [], [proc_testGetAllPaths0]
		
		yield ps, [proc_testGetAllPaths0, proc_testGetAllPaths1], [], [proc_testGetAllPaths0, proc_testGetAllPaths1]
		
		yield ps, [proc_testGetAllPaths0, proc_testGetAllPaths1], [proc_testGetAllPaths0, proc_testGetAllPaths1], [proc_testGetAllPaths2, proc_testGetAllPaths5]
		
		yield ps, [proc_testGetAllPaths0, proc_testGetAllPaths1], [proc_testGetAllPaths0, proc_testGetAllPaths1, proc_testGetAllPaths2, proc_testGetAllPaths5], [proc_testGetAllPaths4]
		
		yield ps, [proc_testGetAllPaths0, proc_testGetAllPaths1], [proc_testGetAllPaths0, proc_testGetAllPaths1, proc_testGetAllPaths2, proc_testGetAllPaths4, proc_testGetAllPaths5], [proc_testGetAllPaths3]
		
		yield ps, [proc_testGetAllPaths0, proc_testGetAllPaths1], [proc_testGetAllPaths0, proc_testGetAllPaths1, proc_testGetAllPaths2, proc_testGetAllPaths3, proc_testGetAllPaths4, proc_testGetAllPaths5], []

	def testGetNextToRun(self, procs, starts, haveran, out):
		for p in procs:
			ProcTree.register(p)
		pt = ProcTree()
		pt.setStarts(starts)
		for hr in haveran:
			ProcTree.getNode(hr).ran = True
		self.assertListEqual(pt.getNextToRun(), out)

	def dataProvider_testUnranProcs(self):
		proc_testUnranProcs0 = Proc()
		proc_testUnranProcs1 = Proc()
		proc_testUnranProcs2 = Proc()
		proc_testUnranProcs3 = Proc()
		proc_testUnranProcs4 = Proc()
		proc_testUnranProcs5 = Proc()
		proc_testUnranProcs6 = Proc()
		proc_testUnranProcs7 = Proc()
		proc_testUnranProcs2.depends = proc_testUnranProcs0, proc_testUnranProcs1
		proc_testUnranProcs3.depends = proc_testUnranProcs2, proc_testUnranProcs4
		proc_testUnranProcs4.depends = proc_testUnranProcs2
		proc_testUnranProcs5.depends = proc_testUnranProcs1
		proc_testUnranProcs6.depends = proc_testUnranProcs0
		"""
			proc0 -> proc6
				\
		proc1 -> proc2 -> proc3                   proc7
			\        \    /
			  proc5  proc4
		"""
		ps = [proc_testUnranProcs0, proc_testUnranProcs1, proc_testUnranProcs2, proc_testUnranProcs3, proc_testUnranProcs4, proc_testUnranProcs5, proc_testUnranProcs6, proc_testUnranProcs7]
		yield ps, [proc_testUnranProcs0], {
			'proc_testUnranProcs3': ['proc_testUnranProcs2', 'proc_testUnranProcs1']
		}
		yield ps, [proc_testUnranProcs1], {
			'proc_testUnranProcs3': ['proc_testUnranProcs2', 'proc_testUnranProcs0']
		}

	def testUnranProcs(self, procs, starts, outs):
		for p in procs:
			ProcTree.register(p)
		pt = ProcTree()
		pt.setStarts(starts)
		# run the pipeline
		ps = pt.getNextToRun()
		while ps:
			for p in ps:
				ProcTree.getNode(p).ran = True
			ps = pt.getNextToRun()
		self.assertDictEqual(pt.unranProcs(), outs)

if __name__ == '__main__':
	unittest.main(verbosity=2)