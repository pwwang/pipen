import helpers, testly

from shutil import rmtree
from tempfile import gettempdir
from copy import deepcopy
from pyppl.channel import Channel
from os import path, makedirs, symlink, utime
from time import time

class TestChannel (testly.TestCase):

	def setUpMeta(self):
		self.testdir = path.join(gettempdir(), 'PyPPL_unittest', 'TestChannel')
		if path.exists(self.testdir):
			rmtree(self.testdir)
		makedirs(self.testdir)

	def dataProvider_testTuplize(self):
		yield ('abc',('abc', ))
		yield ('',   ('', ))
		yield (1,    (1, ))
		yield ([],   ([], ))
		yield ((1,), (1,))

	def testTuplize(self, ins, outs):
		self.assertEqual(Channel._tuplize(ins), outs)

	def dataProvider_testCreate(self):
		yield 1,     [(1, )]
		yield "a,b", [("a,b", )]
		yield ["a", "b"], [("a", ), ("b", )]
		yield ("a", "b"), [("a", "b")]
		yield [], []
		yield [[]], [([], )]
		yield [("a", ), ("c", "d")], [], True
		# issue #29
		yield '', [('', )]
	
	def testCreate(self, ins, outs, exception = False):
		if exception:
			self.assertRaises(ValueError, Channel.create, ins)
		else:
			self.assertEqual(Channel.create(ins), outs)

	def dataProvider_testFromChannels(self):
		ch1  = Channel.create([(1, 2), (3, 4)])
		ch2  = Channel.create('a')
		ch3  = Channel.create([5, 6])
		outs = [(1, 2, 'a', 5), (3, 4, 'a', 6)]
		yield [ch1, ch2, ch3], outs

		ch1 = Channel.create([])
		ch2 = Channel.create([])
		yield [ch1, ch2], []
		
		ch1 = Channel.create([])
		ch2 = Channel.create(1)
		ch3 = Channel.create([1, 2])
		yield [ch1, ch2, ch3], [(1,1), (1,2)]

	def testFromChannels(self, chs, outs):
		self.assertEqual(Channel.fromChannels(*chs), outs)

	def dataProvider_testInsert(self):
		ch1 = Channel.create([(1, 2), (3, 4)])
		ch2 = Channel.create([5, 6])
		# 0-3
		yield 0, ch1, ch2, [(5, 1, 2), (6, 3, 4)]
		yield 1, ch1, ch2, [(1, 5, 2), (3, 6, 4)]
		yield -1, ch1, ch2, [(1, 5, 2), (3, 6, 4)]
		yield None, ch1, ch2, [(1, 2, 5), (3, 4, 6)]

		ch2 = Channel.create(5)
		# 4-7
		yield 0,    ch1, ch2, [(5, 1, 2), (5, 3, 4)]
		yield 1,    ch1, ch2, [(1, 5, 2), (3, 5, 4)]
		yield -1,   ch1, ch2, [(1, 5, 2), (3, 5, 4)]
		yield None, ch1, ch2, [(1, 2, 5), (3, 4, 5)]
		# 8-19
		yield 0,    ch1, [5, 6], [(5, 1, 2), (6, 3, 4)]
		yield 1,    ch1, [5, 6], [(1, 5, 2), (3, 6, 4)]
		yield -1,   ch1, [5, 6], [(1, 5, 2), (3, 6, 4)]
		yield None, ch1, [5, 6], [(1, 2, 5), (3, 4, 6)]
		yield 0,    ch1, (5, 6), [(5, 6, 1, 2), (5, 6, 3, 4)]
		yield 1,    ch1, (5, 6), [(1, 5, 6, 2), (3, 5, 6, 4)]
		yield -1,   ch1, (5, 6), [(1, 5, 6, 2), (3, 5, 6, 4)]
		yield None, ch1, (5, 6), [(1, 2, 5, 6), (3, 4, 5, 6)]
		yield 0,    ch1, "a",    [('a', 1, 2), ('a', 3, 4)]
		yield 1,    ch1, "a",    [(1, 'a', 2), (3, 'a', 4)]
		yield -1,   ch1, "a",    [(1, 'a', 2), (3, 'a', 4)]
		yield None, ch1, "a",    [(1, 2, 'a'), (3, 4, 'a')]

		# 20-23
		yield 0, ch1, [], ch1
		yield 1, ch1, [], ch1
		yield -1, ch1, [], ch1
		yield None, ch1, [], ch1

		ch1 = Channel.create()
		ch2 = Channel.create([21, 22])
		ch3 = 3
		ch4 = [41, 42]
		ch5 = (51, 52)
		ch6 = "a"

		# 24-25
		yield 1, ch1, ch2, ch2
		yield 0, ch1, [ch2, ch3, ch4, ch5, ch6], [(21, 3, 41, 51, 52, 'a'), (22, 3, 42, 51, 52, 'a')], True
		
		# 26-29
		yield 0, ch1, [], ch1
		yield 1, ch1, [], ch1
		yield -1, ch1, [], ch1
		yield None, ch1, [], ch1

		# 30-31
		yield None, ch1, [1, [1, 2]], [(1,1), (1,2)], True
		yield None, ch1, [Channel.create(1), Channel.create([1,2])], [(1,1), (1,2)], True

		# 32 Emptys
		yield 1, ch1, [[], 1, [], [2, 3]], [(1,2), (1,3)], True

		yield None, Channel.create(), [Channel.create([4,5]), Channel.create([1,2,3])], ValueError, True

		ch1 = Channel.create([(1,2), (3,4)])
		yield None, ch1, [1,2,3], ValueError

		# issue 29
		yield 0, Channel.create(), '', [('', )]
		
	def testInsert(self, pos, ch1, ch2, outs, ch2islist = False):
		if ch2islist:
			if not isinstance(outs, list):
				self.assertRaises(outs, ch1.insert, pos, *ch2)
			else:
				self.assertEqual(ch1.insert(pos, *ch2), outs)
		else:
			if not isinstance(outs, list):
				self.assertRaises(outs, ch1.insert, pos, ch2)
			else:
				self.assertEqual(ch1.insert(pos, ch2), outs)

	def dataProvider_testFromPattern(self):
		# create files
		testdir = path.join(self.testdir, 'testFromPattern')
		makedirs(testdir)
		file1 = path.join(testdir, 'testFromPattern1_File.ext1') # 1 file
		file2 = path.join(testdir, 'testFromPattern2_Link.ext1') # 2 link 1
		file3 = path.join(testdir, 'testFromPattern3_File.ext1') # 3 file
		file4 = path.join(testdir, 'testFromPattern4_Link.ext1') # 4 link 3
		file5 = path.join(testdir, 'testFromPattern5_FDir.ext1') # 5 dir
		file6 = path.join(testdir, 'testFromPattern6_FDir.ext2') # 6 dir
		file7 = path.join(testdir, 'testFromPattern7_Link.ext2') # 7 link 5
		file8 = path.join(testdir, 'testFromPattern8_Link.ext2') # 8 link 6
		file9 = path.join(testdir, 'testFromPattern9_File.ext2') # 9 file
		file0 = path.join(testdir, 'testFromPattern0_FDir.ext2') # 0 dir

		t = time() - 10
		helpers.writeFile(file9, '1')
		utime(file9, (t, t))
		helpers.writeFile(file3, '111')
		utime(file3, (t+1, t+1))
		helpers.writeFile(file1, '11')
		utime(file1, (t+2, t+2))
		makedirs(file0)
		utime(file0, (t+3, t+3))
		makedirs(file5)
		utime(file5, (t+4, t+4))
		makedirs(file6)
		utime(file6, (t+5, t+5))
		symlink(file5, file7)
		symlink(file6, file8)
		symlink(file3, file4)
		symlink(file1, file2)

		pattern = path.join(testdir, '*')
		yield pattern, Channel.create([file0, file1, file2, file3, file4, file5, file6, file7, file8, file9])

		pattern = path.join(testdir, '*.ext2')
		yield pattern, Channel.create([file0, file6, file7, file8, file9])

		pattern = path.join(testdir, '*')
		t       = 'file'
		yield pattern, Channel.create([file1, file3, file9]), t

		pattern = path.join(testdir, '*')
		t       = 'dir'
		yield pattern, Channel.create([file0, file5, file6]), t

		pattern = path.join(testdir, '*')
		t       = 'link'
		yield pattern, Channel.create([file2, file4, file7, file8]), t

		pattern = path.join(testdir, 'testFromPattern?_F*.*')
		sortby  = 'mtime'
		t       = 'any'
		yield pattern, Channel.create([file9, file3, file1, file0, file5, file6]), t, sortby

		pattern = path.join(testdir, 'testFromPattern?_F*.*')
		sortby  = 'size'
		t       = 'file'
		rev     = True
		yield pattern, Channel.create([file3, file1, file9]), t, sortby, rev
		
	def testFromPattern(self, pattern, outs, t = 'any', sortby = 'name', reverse = False):
		self.assertListEqual(Channel.fromPattern(pattern, t, sortby, reverse), outs)

	def dataProvider_testFromPairs(self):
		files1 = [path.join(self.testdir, 'testFromPairs1%s.txt' % i) for i in range(0, 4)]
		files2 = [path.join(self.testdir, 'testFromPairs2%s.txt' % i) for i in range(0, 4)]
		for f in files1 + files2:
			helpers.writeFile(f)

		yield path.join(self.testdir, 'testFromPairs1?.txt'), Channel.create([(files1[0], files1[1]), (files1[2], files1[3])])
		yield path.join(self.testdir, 'testFromPairs2?.txt'), Channel.create([(files2[0], files2[1]), (files2[2], files2[3])])

	def testFromPairs(self, pattern, outs):
		self.assertListEqual(Channel.fromPairs(pattern), outs)

	def dataProvider_testFromFile(self):
		file1 = path.join(self.testdir, 'testFromFile1.txt')
		helpers.writeFile(
			file1, 
			"a1\tb1\tc1\n" + 
			"a2\tb2\tc2"
		)
		outs = Channel.create([("a1", "b1", "c1"), ("a2", "b2", "c2")])
		yield file1, outs, False, 0, '\t'

		# head & delimit
		file2 = path.join(self.testdir, "testFromFile2.txt")
		helpers.writeFile(
			file2, 
			"a,b,c\n" + 
			"a1,b1,c1\n" + 
			"a2,b2,c2"
		)
		outs = Channel.create([("a1", "b1", "c1"), ("a2", "b2", "c2")])
		yield file2, outs, ['a', 'b', 'c'], 0, ','

		# skip
		file3 = path.join(self.testdir, "testFromFile3.txt")
		helpers.writeFile(
			file3, 
			"#a,b,c\n" + 
			"#a,b,c\n" + 
			"b,c\n" + 
			"a1,b1,c1\n" + 
			"a2,b2,c2"
		)
		outs = Channel.create([("a1", "b1", "c1"), ("a2", "b2", "c2")])
		yield file3, outs, ['RowNames', 'b', 'c'], 2, ','

		# error
		file4 = path.join(self.testdir, "testFromFile4.txt")
		helpers.writeFile(
			file4, 
			"#a,b,c\n" + 
			"b,c,d,e\n" + 
			"a1,b1,c1\n" + 
			"a2,b2,c2"
		)
		yield file4, [], ['a'], 1, ',', True

	def testFromFile(self, fn, outs, header = False, skip = 0, delimit = "\t", exception = False):
		headerFlag = bool(header)
		if exception:
			self.assertRaises(ValueError, Channel.fromFile, fn, header, skip, delimit)
		else:
			ch = Channel.fromFile(fn, header = headerFlag, skip = skip, delimit = delimit)
			self.assertListEqual(ch, outs)
			if headerFlag:
				for i, h in enumerate(header):
					self.assertListEqual(getattr(ch, h), outs.colAt(i))

	def dataProvider_testFromArgv(self):
		yield ["prog", "a", "b", "c"], [("a",), ("b",), ("c",)]
		yield ["prog", "a1,a2", "b1,b2", "c1,c2"], [("a1","a2"), ("b1","b2"), ("c1","c2")]
		yield ["prog", "a1,a2", "b1", "c1,c2"], [], True
		yield ["prog"], []

	def testFromArgv(self, args, outs, exception = False):
		import sys
		sys.argv = args
		if exception:
			self.assertRaises(ValueError, Channel.fromArgv)
		else:
			ch = Channel.fromArgv()
			self.assertListEqual(Channel.fromArgv(), outs)

	def dataProvider_testFromParams(self):
		from pyppl.parameters import Parameter
		p1 = Parameter('a', 'a1')
		p2 = Parameter('b', 'b1')
		p3 = Parameter('c', 'c1')
		ps = [p1, p2, p3]
		yield ps, [('a1', 'b1', 'c1')]

		p1 = Parameter('a', ['a1', 'a2'])
		p2 = Parameter('b', ['b1', 'b2'])
		p3 = Parameter('c', ['c1', 'c2'])
		ps = [p1, p2, p3]
		yield ps, [('a1', 'b1', 'c1'), ('a2', 'b2', 'c2')]

		p1 = Parameter('a', [])
		p2 = Parameter('b', [])
		p3 = Parameter('c', [])
		ps = [p1, p2, p3]
		yield ps, []

		p1 = Parameter('a', ['a1', 'a2'])
		p2 = Parameter('b', ['b1', 'b2'])
		p3 = Parameter('c', ['c1', 'c2', 'c3'])
		ps = [p1, p2, p3]
		yield ps, [], True

	def testFromParams(self, ps, outs = [], exception = False):
		from pyppl.parameters import Parameter, params
		outs = Channel.create(outs)
		for p in ps:
			params._props['params'][p.name] = p
		pnames = [p.name for  p in ps]
		if not exception:
			ch = Channel.fromParams(*pnames)
			self.assertListEqual(ch, outs)
			if ch:
				for i, p in enumerate(ps):
					self.assertListEqual(getattr(ch, p.name), outs.colAt(i))
		else:
			self.assertRaises(ValueError, Channel.fromParams, *pnames)

	def dataProvider_testExpand(self):
		# empty self
		yield Channel.create(), 0, []

		# defaults
		dir1  = path.join(self.testdir, 'testExpand')
		file1 = path.join(dir1, 'testExpand1.txt')
		file2 = path.join(dir1, 'testExpand2.txt')
		makedirs(dir1)
		helpers.writeFile(file1)
		helpers.writeFile(file2)
		yield Channel.create(dir1), 0, [file1, file2]

		# extra columns
		dir2  = path.join(self.testdir, 'testExpand2')
		file3 = path.join(dir2, 'testExpand3.txt')
		file4 = path.join(dir2, 'testExpand4.txt')
		makedirs(dir2)
		helpers.writeFile(file3)
		helpers.writeFile(file4)
		yield Channel.create(('a', 1, dir2)), 2, [('a', 1, file3), ('a', 1, file4)]

		# pattern not exists
		yield Channel.create(('a', 1, dir2)), 2, [], 'a.*'
		
		# expand respectively
		yield Channel.create([
			('a', 1, dir1),
			('b', 2, dir2)
		]), 2, Channel.create([
			('a', 1, file1),
			('a', 1, file2),
			('b', 2, file3),
			('b', 2, file4),
		])

	def testExpand(self, ch, col, outs, pattern = '*', t = 'any', sortby = 'name', reverse = False, exception = False):
		if exception:
			self.assertRaises(ValueError, ch.expand, col, pattern, t, sortby, reverse)
		else:
			c    = ch.expand(col, pattern, t, sortby, reverse)
			outs = Channel.create(outs)
			self.assertListEqual(c, outs)

	def dataProvider_testCollapse(self):
		# empty self
		yield Channel.create(), 0, [], True

		# defaults
		dir1  = path.join(self.testdir, 'testCollapse')
		file1 = path.join(dir1, 'testCollapse1.txt')
		file2 = path.join(dir1, 'testCollapse2.txt')
		makedirs(dir1)
		helpers.writeFile(file1)
		helpers.writeFile(file2)
		yield Channel.create([file1, file2]), 0, dir1

		# Extra cols
		yield Channel.create([('a1', file1, 'a2'), ('b1', file2, 'b2')]), 1, ('a1', dir1, 'a2')

		# No common prefix
		yield Channel.create([('a1', file1, 'a2'), ('b1', file2, 'b2')]), 0, ('', file1, 'a2')

	def testCollapse(self, ch, col, outs, exception = False):
		if exception:
			self.assertRaises(ValueError, ch.collapse, col)
		else:
			c    = ch.collapse(col)
			outs = Channel.create(outs)
			self.assertListEqual(c, outs)

	def dataProvider_testCopy(self):
		yield [], (1,)
		yield [(1,2)], (3,4)

	def testCopy(self, ch1, row):
		ch1 = Channel.create(ch1)
		ch2 = ch1.copy()
		ch1.append(row)
		self.assertNotEqual(ch1, ch2)
	
	def dataProvider_testWidth(self):
		yield [], 0
		yield (1,2), 2
		yield [1,2], 1

	def testWidth(self, ch, width):
		ch = Channel.create(ch)
		self.assertEqual(ch.width(), width)

	def dataProvider_testLength(self):
		yield [], 0
		yield (1,2), 1
		yield [1,2], 2

	def testLength(self, ch, length):
		ch = Channel.create(ch)
		self.assertEqual(ch.length(), length)
		self.assertEqual(len(ch), length)

	def dataProvider_testMap(self):
		yield [], lambda x: x*2, []
		yield [1,2,3,4,5], lambda x: x*2, [(1,1),(2,2),(3,3),(4,4),(5,5)]
		yield [(1,1),(2,2),(3,3),(4,4),(5,5)], lambda x: (x[0], x[1]*2,), [(1,2),(2,4),(3,6),(4,8),(5,10)]

	def testMap(self, ch, func, outs):
		ch   = Channel.create(ch)
		ch2  = ch.map(func)
		outs = Channel.create(outs)
		self.assertListEqual(ch2, outs)

	def dataProvider_testMapCol(self):
		yield [], lambda x: x*2, 0, []
		yield [1,2,3,4,5], lambda x: x*2, 0, [2,4,6,8,10]
		yield [(1,1),(2,2),(3,3),(4,4),(5,5)], lambda x: x*2, 1, [(1,2),(2,4),(3,6),(4,8),(5,10)]

	def testMapCol(self, ch, func, col, outs):
		ch   = Channel.create(ch)
		ch2  = ch.mapCol(func, col)
		outs = Channel.create(outs)
		self.assertListEqual(ch2, outs)
	
	def dataProvider_testFilter(self):
		yield [], None, []

		yield [
			(1, 0, 0, 1),
			('a', '', 'b', '0'),
			(True, False, 0, 1),
			([], [1], [2], [0]),
		], None, [
			(1, 0, 0, 1),
			('a', '', 'b', '0'),
			(True, False, 0, 1),
			([], [1], [2], [0]),
		]

		yield [
			(1, 0, 0, 1),
			('a', '', 'b', '0'),
			(True, False, 0, 1),
			([], [1], [2], [0]),
		], lambda x: all([isinstance(_, int) for _ in x]), [
			(1, 0, 0, 1),
			(True, False, 0, 1),
		]

	def testFilter(self, ch, func, outs):
		ch   = Channel.create(ch)
		ch2  = ch.filter(func)
		outs = Channel.create(outs)  
		self.assertListEqual(ch2, outs)

	def dataProvider_testFilterCol(self):
		yield [], None, 0, []

		yield [
			(1, 0, 0, 1),
			('a', '', 'b', '0'),
			(True, False, 0, 1),
			([], [1], [2], [0]),
		], None, 1, [
			([], [1], [2], [0]),
		]

		yield [
			(1, 0, 0, 1),
			('a', '', 'b', '0'),
			(True, False, 0, 1),
			([], [1], [2], [0]),
		], lambda x: bool(x), 2, [
			('a', '', 'b', '0'),
			([], [1], [2], [0]),
		]

	def testFilterCol(self, ch, func, col, outs):
		ch   = Channel.create(ch)
		ch2  = ch.filterCol(func, col)
		outs = Channel.create(outs)  
		self.assertListEqual(ch2, outs)

	def dataProvider_testReduce(self):
		yield [], None, [], True
		yield [1], None, (1,)
		yield [1,2,3,4,5], lambda x,y: x+y, (1,2,3,4,5)
		yield [2], lambda x,y: (x[0] * y[0], ), (2,)


	def testReduce(self, ch, func, outs, exception = False):
		ch   = Channel.create(ch)
		if not exception:
			ch2  = ch.reduce(func)
			self.assertTupleEqual(ch2, outs)
		else:
			self.assertRaises(TypeError, ch.reduce, func)

	def dataProvider_testReduceCol(self):
		yield [], None, 0, [], True

		yield [
			(1, 0, 0, 1),
			('a', '', 'b', '0'),
			(True, False, 0, 1),
			([], [1], [2], [0]),
		], lambda x,y: bool(x) and bool(y), 1, False
		
		yield [
			(1, 0, 0, 1),
			('a', '', 'b', '0'),
			(True, False, 0, 1),
			([], [1], [2], [0]),
		], lambda x, y: int(x[0] if isinstance(x, list) else x) + int(y[0] if isinstance(y, list) else y), 3, 2
		
	def testReduceCol(self, ch, func, col, outs, exception = False):
		ch   = Channel.create(ch)
		if not exception:
			ch2  = ch.reduceCol(func, col)
			self.assertEqual(ch2, outs)	
		else:
			self.assertRaises(TypeError, ch.reduceCol, func, col)

	def dataProvider_testRbind(self):
		yield [], [], []
		yield [], [[()]], []
		yield [], [1], [1]
		yield [], [1, (1,2)], [(1,1), (1,2)]
		yield (1,2,3), [1], [(1,2,3), (1,1,1)]
		yield (1,2,3), [(4,5,6)], [(1,2,3),(4,5,6)]
		yield (1,2,3), [(4,5)], [], True

	def testRbind(self, ch, rows, outs, exception = False):
		ch = Channel.create(ch)
		if not exception:
			ch2  = ch.rbind(*rows)
			outs = Channel.create(outs)
			self.assertListEqual(ch2, outs)
		else:
			self.assertRaises(ValueError, ch.rbind, *rows)

	def dataProvider_testCbind(self):
		yield [], [], []
		yield [(1,2), (3,4)], [5, 6], [(1,2,5,6), (3,4,5,6)]
		yield [(1,2), (3,4)], [(5, 6,)], [(1,2,5,6), (3,4,5,6)]
		yield [(1,2), (3,4)], [5], [(1,2,5), (3,4,5)]
		yield [7,8], [[5, 6], Channel.create(4)], [(7,5,4), (8,6,4)]
		yield [], [21, 22], [(21, 22)]
		yield [], [(21, 22, )], [(21, 22)]
		yield [], [[21, 22], (1, 2, 3)], [(21, 1, 2, 3), (22, 1,2,3)]
		yield [], [[21, 22], [1, 2, 3]], [], True

	def testCbind(self, ch, cols, outs, exception = False):
		ch   = Channel.create(ch)
		orgcols = deepcopy(cols)
		if not exception:
			ch2  = ch.cbind(*cols)
			outs = Channel.create(outs)
			self.assertListEqual(ch2, outs)
			for i, ocol in enumerate(orgcols):
				self.assertListEqual(Channel.create(ocol), Channel.create(cols[i]))
		else:
			self.assertRaises(ValueError, ch.cbind, *cols)

	def dataProvider_testColAt(self):
		#0
		yield [], 0, []
		yield [], 1, []
		# single index
		yield (1,2,3), 1, 2
		#3
		yield (1,2,3), -1, 3
		yield (1,2,3), [1, -1], (2,3)
		yield (1,2,3), [-1, 0], (3,1)
		#6
		yield [(1,2,3), (4,5,6)], 1, [2,5]
		yield [(1,2,3), (4,5,6)], -1, [3,6]
		yield [(1,2,3), (4,5,6)], [1, -2], [(2,2), (5,5)]
		#9
		yield [(1,2,3), (4,5,6)], [-1, -2], [(3,2), (6,5)]
		yield [(1,2,3), (4,5,6)], [2,1,0], [(3,2,1),(6,5,4)]

	
	def testColAt(self, ch, col, outs):
		ch   = Channel.create(ch)
		outs = Channel.create(outs)
		self.assertListEqual(ch.colAt(col), outs)

	def dataProvider_testRowAt(self):
		#0
		yield [], 0, []
		yield [], 1, []
		yield [1,2,3], 1, 2
		yield [1,2,3], -1, 3
		yield [1,2,3], [1,-1], [2,3]
		#5
		yield [1,2,3], [-1,0], [3,1]
		yield [(1,4),(2,5),(3,6)], 1, (2,5)
		yield [(1,4),(2,5),(3,6)], -1, (3,6)
		yield [(1,4),(2,5),(3,6)], [1, -2], [(2,5),(2,5)]

	def testRowAt(self, ch, row, outs):
		ch   = Channel.create(ch)
		outs = Channel.create(outs)
		self.assertListEqual(ch.rowAt(row), outs)

	def dataProvider_testUnique(self):
		yield [], []
		yield [1], [1]
		yield [1,2,3,4], [1,2,3,4]
		yield [1,2,2,4], [1,2,4]
		yield [1,2,3,1], [1,2,3]

	def testUnique(self, ch, outs):
		ch   = Channel.create(ch)
		outs = Channel.create(outs)
		self.assertListEqual(ch.unique(), outs)

	def dataProvider_testSlice(self):
		yield [], 0, None, []
		yield [], 1, None, []
		yield [], -1, None, []
		yield [1,2,3], 0, None, [1,2,3]
		yield (1,2,3), 1, None, (2,3)
		yield (1,2,3), -1, None, 3
		yield (1,2,3), -1, 1, 3
		yield [(1,2,3), (4,5,6)], -2, 1, [2,5]
		yield [(1,2,3), (4,5,6)], -2, 8, [(2,3), (5,6)]

	def testSlice(self, ch, start, length, outs):
		ch   = Channel.create(ch)
		outs = Channel.create(outs)
		self.assertListEqual(ch.slice(start, length), outs)

	def dataProvider_testFold(self):
		yield [], 0, [], True
		yield [(1,2,3,4)], 3, [], True
		yield [(1,2,3,4), (5,6,7,8)], 8, [(1,2,3,4,5,6,7,8)], True
		yield [(1,2,3,4)], 2, [(1,2),(3,4)]
		yield [(1,2,3,4), (5,6,7,8)], 2, [(1,2),(3,4),(5,6),(7,8)]
		yield [(1,2,3,4), (5,6,7,8)], 1, [1,2,3,4,5,6,7,8]
		yield [(1,2,3,4), (5,6,7,8)], 4, [(1,2,3,4), (5,6,7,8)]

	def testFold(self, ch, n, outs, exception = False):
		ch = Channel.create(ch)
		if exception:
			self.assertRaises(ValueError, ch.fold, n)
		else:
			outs = Channel.create(outs)
			self.assertListEqual(ch.fold(n), outs)

	def dataProvider_testUnfold(self):
		yield [], 0, [], True
		yield [], -1, [], True
		yield [1,2,3,4], 3, [], True

		yield [(1,2),(3,4),(5,6),(7,8)], 4, (1,2,3,4,5,6,7,8)
		yield [(1,2),(3,4),(5,6),(7,8)], 1, [(1,2),(3,4),(5,6),(7,8)]
		yield [1,2,3,4], 2, [(1,2), (3,4)]

	def testUnfold(self, ch, n, outs, exception = False):
		ch = Channel.create(ch)
		if exception:
			self.assertRaises(ValueError, ch.unfold, n)
		else:
			outs = Channel.create(outs)
			self.assertListEqual(ch.unfold(n), outs)

	def dataProvider_testSplit(self):
		yield [], True, []
		yield [], False, []
		yield [1,2,3], True, [[1, 2, 3]]
		yield [1,2,3], False, [Channel.create([1,2,3])]
		yield (1,2,3), True, [[1], [2], [3]]
		yield (1,2,3), False, [Channel.create(1), Channel.create(2), Channel.create(3)]
		yield [(1,4),(2,5),(3,6)], True, [[1, 2, 3], [4,5,6]]
		yield [(1,4),(2,5),(3,6)], False, [Channel.create([1,2,3]), Channel.create([4,5,6])]
	
	def testSplit(self, ch, flatten, outs):
		ch = Channel.create(ch)
		self.assertListEqual(ch.split(flatten), outs)

	def dataProvider_testAttach(self):
		yield [], []
		yield [], ['a'], False, ValueError
		yield (1,2), ['a', 'b', 'c'], False, ValueError
		yield (1,2), ['attach', 'attach1'], False, AttributeError
		yield (1,2,3), ['a', 'b'], False
		yield [1,2], ['a'], False
		yield [(1,2,3), (4,5,6)], ['a', 'b'], True

	def testAttach(self, ch, names, flatten = False, exception = None):
		ch = Channel.create(ch)
		if exception:
			self.assertRaises(exception, ch.attach, *names, **{'flatten': flatten})
		else:
			ch.attach(*names, **{'flatten': flatten})
			for i, name in enumerate(names):
				self.assertListEqual(ch.colAt(i) if not flatten else ch.flatten(i), getattr(ch, name))

	def dataProvider_testGet(self):
		yield [], 0, [], IndexError
		yield [1,2,3], 4, [], IndexError
		yield [1,2,3], 1, 2
		yield [1,2,3], 0, 1
		yield (1,2,3), 0, 1
		yield (1,2,3), -1, 3

	def testGet(self, ch, idx, outs, exception = None):
		ch = Channel.create(ch)
		if exception:
			self.assertRaises(exception, ch.get, idx)
		else:
			self.assertEqual(ch.get(idx), outs)

	def dataProvider_testRepCol(self):
		yield [], 1, []
		yield [], 2, []
		yield [], 0, []
		yield [1], 2, (1,1)
		yield [1, 2], 2, [(1,1), (2,2)]
		yield (1,2), 2, [(1,2, 1,2)]
		yield [(1,2), (3,4)], 2, [(1,2,1,2),(3,4,3,4)]

	def testRepCol(self, ch, n, outs):
		ch   = Channel.create(ch)
		outs = Channel.create(outs)
		self.assertListEqual(ch.repCol(n), outs)

	def dataProvider_testRepRow(self):
		yield [], 1, []
		yield [], 2, []
		yield [], 0, []
		yield [1], 2, [1,1]
		yield [1, 2], 2, [1,2,1,2]
		yield (1,2), 2, [(1,2), (1,2)]
		yield [(1,2), (3,4)], 2, [(1,2),(3,4),(1,2),(3,4)]

	def testRepRow(self, ch, n, outs):
		ch   = Channel.create(ch)
		outs = Channel.create(outs)
		self.assertListEqual(ch.repRow(n), outs)

	def dataProvider_testFlatten(self):
		yield [], None, []
		yield [], 0, []
		yield [], 1, []
		yield [], -1, []
		yield [1,2,3], 1, [], IndexError
		yield [1,2,3], -1, [1,2,3]
		yield [1,2,3], None, [1,2,3]
		yield (1,2,3), None, [1,2,3]
		yield [1,2,3], 0, [1,2,3]
		yield (1,2,3), 0, [1]
		yield (1,2,3), 1, [2]
		yield (1,2,3), -1, [3]

	def testFlatten(self, ch, col, outs, exception = None):
		ch = Channel.create(ch)
		if exception:
			self.assertRaises(exception, ch.flatten, col)
		else:
			self.assertListEqual(ch.flatten(col), outs)

if __name__ == '__main__':
	testly.main(verbosity=2)