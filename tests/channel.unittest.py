import sys, unittest, os, glob
rootdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, rootdir)
from pyppl import channel

class TestChannel (unittest.TestCase):

	def testCreate (self):
		c1 = channel.create([("abc", "def"), ("ghi", "opq")])
		c2 = channel([("abc", "def"), ("ghi", "opq")])

		self.assertTrue (isinstance(c1, channel))
		self.assertTrue (isinstance(c2, channel))

		c3 = channel()
		self.assertEqual (c3, [])

	def testFromPath (self):
		c = channel.fromPath (os.path.join(rootdir, 'tests', '*.py'))
		self.assertEqual (sorted(c), sorted(map(channel._tuplize, glob.glob(os.path.join(rootdir, 'tests', '*.py')))))
	
	def testFromPairs (self):
		files = [
			os.path.join (rootdir, 'tests', 'a_1.txt'),
			os.path.join (rootdir, 'tests', 'a_2.txt'),
			os.path.join (rootdir, 'tests', 'b_1.txt'),
			os.path.join (rootdir, 'tests', 'b_2.txt'),
			os.path.join (rootdir, 'tests', 'c_1.txt'),
			os.path.join (rootdir, 'tests', 'c_2.txt'),
		]
		for file in files:
			open(file, 'w').close()

		c = channel.fromPairs ( os.path.join(rootdir, 'tests', '*_*.txt') )
	
		self.assertEqual (sorted(c), sorted([
			(os.path.join (rootdir, 'tests', 'a_1.txt'), os.path.join (rootdir, 'tests', 'a_2.txt')),
			(os.path.join (rootdir, 'tests', 'b_1.txt'), os.path.join (rootdir, 'tests', 'b_2.txt')),
			(os.path.join (rootdir, 'tests', 'c_1.txt'), os.path.join (rootdir, 'tests', 'c_2.txt')),

		]))

		for file in files:
			os.remove(file)
	
	def testFromArgv (self):
		sys.argv = ["0", "11", "22", "33", "44"]
		c = channel.fromArgv()
		self.assertEqual (c, [("11",), ("22",), ("33",), ("44",)])
		sys.argv = ["0", "11,22", "33,44"]
		c = channel.fromArgv()
		self.assertEqual (c, [("11", "22"), ("33", "44")])
		sys.argv = ["0", "11,22", "33"]
		self.assertRaises (ValueError, channel.fromArgv)

	def testFromChannels (self):
		c1 = channel.create([("abc", "def"), ("ghi", "opq")])
		c2 = channel.create([("abc", "def"), ("ghi", "opq")])
		c3 = channel.fromChannels (c1, c2)
		self.assertEqual (c3, [("abc", "def", "abc", "def"), ("ghi", "opq", "ghi", "opq")])
		
	def testFromFile (self):
		testfile = "/tmp/chan.txt"
		with open (testfile, "w") as f:
			f.write ("""
			1	2	4
			a	b	c
			4	1	0
			""")
		c = channel.fromFile (testfile)
		self.assertEqual (c, [("1", "2", "4"), ("a", "b", "c"), ("4", "1", "0")])

	def testTuplize (self):
		data = [
			(1, (1,)),
			((1, ), (1,)),
			("abc", ("abc", )),
			(("abc", ), ("abc", )),
		]
		for d in data:
			self.assertEqual (channel._tuplize(d[0]), d[1])

	def testMap (self):
		c1 = channel.create([("abc", "def"), ("ghi", "opq")])
		c2 = channel([("abc", "def"), ("ghi", "opq")])
		c1 = c1.map (lambda x: (x[0] + '.c1', x[1]))
		c2 = c2.map (lambda x: len(x[0]) + len(x[1]))
		self.assertEqual (c1, [("abc.c1", "def"), ("ghi.c1", "opq")])
		self.assertEqual (c2, [(6, ), (6, )])

	def testFilter (self):
		c = channel.create([1,2,3,4,5]).filter(lambda x: x[0]<3)
		self.assertEqual (c, [(1, ), (2, )])
	
	def testReduce (self):
		c = channel.create([("abc", "def"), ("ghi", "opq")]).reduce(lambda x,y: (x[0]+y[0], x[1]+y[1]))
		self.assertEqual (c, [('abcghi', ), ('defopq',)])

	def testMerge(self):
		c1 = channel.create ([("abc", "def"), ("ghi", "opq")])
		c2 = channel.create (["abc", "def", "ghi", "opq"])
		self.assertRaises (Exception, c1.merge, c2)

		c3 = channel.create(["1", '2', '3', '4'])	
		c4 = c2.copy().merge(c3)
		self.assertEqual (c4, [("abc", "1"), ("def", '2'), ("ghi", '3'), ("opq", '4')])

		c5 = [5,6,7,8]
		self.assertEqual (c2.copy().merge(c3,c5), [("abc", "1", 5), ("def", '2', 6), ("ghi", '3', 7), ("opq", '4', 8)])
		self.assertEqual (c4.copy().merge(c5), [("abc", "1", 5), ("def", '2', 6), ("ghi", '3', 7), ("opq", '4', 8)])
		c6 = channel.create()
		c6.merge (c2, c3 ,c5)
		self.assertEqual (c6, [("abc", "1", 5), ("def", '2', 6), ("ghi", '3', 7), ("opq", '4', 8)])
		
		c = channel.create()
		cd = {"c":c}
		c.merge (c2, c3, c5)
		self.assertEqual (cd['c'], [("abc", "1", 5), ("def", '2', 6), ("ghi", '3', 7), ("opq", '4', 8)])
		self.assertEqual (c, [("abc", "1", 5), ("def", '2', 6), ("ghi", '3', 7), ("opq", '4', 8)])

		cc = channel()
		ccs = channel([(1, 2, 3), (4, 5, 6), (7, 8, 9), (10, 11, 12)])
		for cs in ccs.split():
			cc.merge(cs)
		self.assertEqual(cc, ccs)
	
	def testMergeList (self):
		c1 = channel.create(["1", '2', '3', '4'])
		c2 = channel.create (["abc", "def", "ghi", ["opq", 1]])
		self.assertEqual (c2.merge(c1), [("abc", "1"), ("def", '2'), ("ghi", '3'), (["opq", 1], '4')])
	
	def testSplit(self):
		
		c4 = channel.create( [("abc", "1", 5), ("def", '2', 6), ("ghi", '3', 7), ("opq", '4', 8)] )

		c6,c7,c8 = c4.split()
		self.assertEqual (c6, [("abc",), ("def",), ("ghi",), ("opq",)])
		self.assertEqual (c7, [("1",), ('2',), ('3',), ('4',)])
		self.assertEqual (c8, [(5,), (6,), (7,), (8,)])

		c11 = channel.create ([("abc",), ("def",), ("ghi",), ("opq",)])
		self.assertEqual (c11.split(), [c11])
		
		c13 = channel.create ([("abc", "def", "ghi", "opq",)])
		self.assertEqual (c13.split(), [[("abc",)], [("def",)], [("ghi",)], [("opq",)]])


	def testLengthAndWidth (self):
		c2 = channel.create (["abc", "def", "ghi", "opq"])
		c3 = channel.create(["1", '2', '3', '4'])
		c4 = c2.copy().merge(c3)

		self.assertEqual (c2.width(), 1)
		self.assertEqual (c3.width(), 1)
		self.assertEqual (c4.width(), 2)
		self.assertEqual (c2.length(), 4)
		self.assertEqual (c3.length(), 4)
		self.assertEqual (c4.length(), 4)

	def testCopy(self):
		c1 = channel.create([("a", "b", "c")])
		c2 = c1.copy()
		c2[0] = ("x", "y", "z")
		self.assertEqual (c1, [("a", "b", "c")])		
		self.assertEqual (c2, [("x", "y", "z")])

	def testToList (self):
		l = ["abc", "def", "ghi", "opq"]
		c1 = channel.create (["abc", "def", "ghi", "opq"])
		self.assertEqual (c1.toList(), l)
		
		c2 = channel.create([("abc", "1", 5), ("def", '2', 6), ("ghi", '3', 7), ("opq", '4', 8)])
		self.assertRaises (Exception, c2.toList)
	
	def testExpand (self):
		import glob
		ch1 = channel.create (["./"])
		ch1.expand()
		self.assertEqual (sorted(ch1), channel.create(sorted(glob.glob("./*"))))
		
		ch2 = channel.create ([(1, "./", 2)])
		ch2.expand(1, "channel.*")
		self.assertEqual (ch2, [(1, "./channel.unittest.py", 2)])

	def textCollapse (self):
		ch1 = channel.fromPath("./*.py")
		ch1.collapse()
		self.assertEqual (ch1, [("./", )])
		
		ch2 = channel.fromPath("./*.py")
		for i, c in enumerate(ch2):
			c = tuple (1, c[0], 2)
		ch1.collapse(1)
		self.assertEqual (ch1, [(1, "./", 2)])

		ch = channel.create ([(1, "/a/b/x/c.1.txt", 2), (1, "/a/b/y/c.2.txt", 2)])
		ch.collapse(1)
		self.assertEqual(ch, [(1, "/a/b", 2)])
	
	def testInsert (self):
		self.maxDiff = None
		import glob
		ch1 = channel.fromPath("./*.py")
		ch1.insert (0, 1)
		ret = [(1, x) for x in sorted(glob.glob("./*.py"))]
		self.assertEqual (sorted(ch1), ret)
		
		#print channel.create(ret).insert(None, [1])
		ch1.insert (None, [1])
		ret = [(1, x, 1) for x in sorted(glob.glob("./*.py"))]
		self.assertEqual (sorted(ch1), ret)
		
		ch1.insert (None, range(ch1.length()))
		ret = [(1, x, 1, i) for i,x in enumerate(sorted(glob.glob("./*.py")))]
		self.assertEqual (sorted(ch1), ret)
		
	def testCbind (self):
		
		chan  = channel.create ([1,2,3,4,5])
		col1 = [2,4,6,8,10]
		chan.cbind (col1)
		self.assertEqual (chan, [(1,2), (2,4), (3,6), (4,8), (5,10)])
		col2 = [5,4,3,2,1]
		chan.cbindMany (col1, col2)
		self.assertEqual (chan, [(1,2,2,5), (2,4,4,4), (3,6,6,3), (4,8,8,2), (5,10,10,1)])
		chan.cbind(0)
		self.assertEqual (chan, [(1,2,2,5,0), (2,4,4,4,0), (3,6,6,3,0), (4,8,8,2,0), (5,10,10,1,0)])
		
		self.assertEqual (channel.create([(),(),(),(),()]).cbind(1), [(1,), (1,), (1,), (1,), (1,)])
		
	def testSlice (self):
		chan = channel.create([(1,2,2,5), (2,4,4,4), (3,6,6,3), (4,8,8,2), (5,10,10,1)])
		self.assertEqual (chan.slice(0,0), [])
		self.assertEqual (chan.slice(0,1), [(1,),(2,),(3,),(4,),(5,)])
		self.assertEqual (chan.slice(0), chan)
		self.assertEqual (chan.slice(2), [(2,5),(4,4),(6,3),(8,2),(10,1)])
		self.assertEqual (chan.slice(-2), [(2,5),(4,4),(6,3),(8,2),(10,1)])
		self.assertEqual (chan.colAt(-2), [(2,),(4,),(6,),(8,),(10,)])
		
	def testFold (self):
		chan  = channel.create([(1,2,2,5), (2,4,4,4), (3,6,6,3), (4,8,8,2), (5,10,10,1)])
		chan1 = chan.fold(1)
		self.assertEqual (chan1, channel.create([1,2,2,5,2,4,4,4,3,6,6,3,4,8,8,2,5,10,10,1]))
		chan2 = chan1.unfold (4)
		self.assertEqual (chan2, chan)
		self.assertRaises (ValueError, chan1.unfold, 8)
		chan3 = chan1.unfold(5)
		self.assertEqual (chan3, [(1,2,2,5,2), (4,4,4,3,6), (6,3,4,8,8), (2,5,10,10,1)])
		chan  = channel.create([(1,), (2,)])
		chan2 = chan.unfold(2)
		self.assertEqual (chan2, [(1,2)])
		
if __name__ == '__main__':
	unittest.main()
