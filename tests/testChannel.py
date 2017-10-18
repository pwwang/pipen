import path, unittest

import sys
import tempfile

from time import sleep
from os import path, makedirs, symlink
from pyppl.channel import Channel
from pyppl.utils import safeRemove
from pyppl.parameters import params

class TestChannel (unittest.TestCase):

	def testTuplize(self):
		data = [
			('abc',('abc', )),
			('',   ('', )),
			(1,    (1, )),
			([],   ([], )),
			((1,), (1,))
		]
		for d in data:
			self.assertEqual(Channel._tuplize(d[0]), d[1])
			
	def testCreate(self):
		data = [
			(1,     [(1, )]),
			("a,b", [("a,b", )]),
			(["a", "b"], [("a", ), ("b", )]),
			(("a", "b"), [("a", "b")]),
			([], []),
			([[]], [([], )]),
		]
		for d in data:
			self.assertEqual(Channel.create(d[0]), d[1])
		self.assertEqual(Channel.create(), [])
			
	def testInsert(self):
		ch1 = Channel.create([(1, 2), (3, 4)])
		ch2 = Channel.create([5, 6])
		self.assertEqual(ch1.insert(0, ch2), [(5, 1, 2), (6, 3, 4)])
		self.assertEqual(ch1.insert(1, ch2), [(1, 5, 2), (3, 6, 4)])
		self.assertEqual(ch1.insert(-1, ch2), [(1, 5, 2), (3, 6, 4)])
		self.assertEqual(ch1.insert(None, ch2), [(1, 2, 5), (3, 4, 6)])
		
		ch2 = Channel.create(5)
		self.assertEqual(ch1.insert(0, ch2), [(5, 1, 2), (5, 3, 4)])
		self.assertEqual(ch1.insert(1, ch2), [(1, 5, 2), (3, 5, 4)])
		self.assertEqual(ch1.insert(-1, ch2), [(1, 5, 2), (3, 5, 4)])
		self.assertEqual(ch1.insert(None, ch2), [(1, 2, 5), (3, 4, 5)])
		
		self.assertEqual(ch1.insert(0, [5, 6]), [(5, 1, 2), (6, 3, 4)])
		self.assertEqual(ch1.insert(1, [5, 6]), [(1, 5, 2), (3, 6, 4)])
		self.assertEqual(ch1.insert(-1, [5, 6]), [(1, 5, 2), (3, 6, 4)])
		self.assertEqual(ch1.insert(None, [5, 6]), [(1, 2, 5), (3, 4, 6)])
		self.assertEqual(ch1.insert(0, (5, 6)), [(5, 1, 2), (6, 3, 4)])
		self.assertEqual(ch1.insert(1, (5, 6)), [(1, 5, 2), (3, 6, 4)])
		self.assertEqual(ch1.insert(-1, (5, 6)), [(1, 5, 2), (3, 6, 4)])
		self.assertEqual(ch1.insert(None, (5, 6)), [(1, 2, 5), (3, 4, 6)])
		self.assertEqual(ch1.insert(0, "a"), [('a', 1, 2), ('a', 3, 4)])
		self.assertEqual(ch1.insert(1, "a"), [(1, 'a', 2), (3, 'a', 4)])
		self.assertEqual(ch1.insert(-1, "a"), [(1, 'a', 2), (3, 'a', 4)])
		self.assertEqual(ch1.insert(None, "a"), [(1, 2, 'a'), (3, 4, 'a')])
		
		self.assertEqual(ch1, [(1, 2), (3, 4)])
		
		ch1 = Channel.create()
		ch2 = Channel.create([21, 22])
		ch3 = 3
		ch4 = [41, 42]
		ch5 = (51, 52)
		ch6 = "a"
		self.assertRaises(ValueError, ch1.insert, 1, ch2)
		self.assertEqual(ch1.insert(0, ch2, ch3, ch4, ch5, ch6), [(21, 3, 41, 51, 'a'), (22, 3, 42, 52, 'a')])
		self.assertEqual(ch1, [])
		
	def testCbind(self):
		ch1 = Channel.create([(1, 2), (3, 4)])
		ch2 = Channel.create([5, 6])
		self.assertEqual(ch1.cbind(ch2), [(1, 2, 5), (3, 4, 6)])
		
		ch2 = Channel.create(5)
		self.assertEqual(ch1.cbind(ch2), [(1, 2, 5), (3, 4, 5)])
		self.assertEqual(ch1.cbind([5, 6]), [(1, 2, 5), (3, 4, 6)])
		self.assertEqual(ch1.cbind((5, 6)), [(1, 2, 5), (3, 4, 6)])
		self.assertEqual(ch1.cbind("a"), [(1, 2, 'a'), (3, 4, 'a')])
		
		ch1 = Channel.create()
		ch2 = Channel.create([21, 22])
		ch3 = 3
		ch4 = [41, 42]
		ch5 = (51, 52)
		ch6 = "a"
		
		self.assertEqual(ch1.cbind(ch2, ch3, ch4, ch5, ch6), [(21, 3, 41, 51, 'a'), (22, 3, 42, 52, 'a')])
		self.assertEqual(ch1, [])
		
		self.assertEqual(ch1.cbind(ch3).cbind(ch6), [(3, 'a')])
		
	def testFromChannels(self):
		ch1 = Channel.create([(1, 2), (3, 4)])
		ch2 = Channel.create('a')
		ch3 = Channel.create([5, 6])
		self.assertEqual(Channel.fromChannels(ch1, ch2, ch3), [(1, 2, 'a', 5), (3, 4, 'a', 6)])
		
	def testFilterFilterCol(self):
		ch1 = Channel.create([
			(1, 0, 0, 1),
			('a', '', 'b', '0'),
			(True, False, 0, 1),
			([], [1], [2], [0]),
		])
		self.assertEqual(ch1.filterCol(), ch1[:3])
		self.assertEqual(ch1.filterCol(col = 1), ch1[3:4])
		self.assertEqual(ch1.filterCol(col = 2), [ch1[1], ch1[3]])
		self.assertEqual(ch1.filterCol(col = 3), ch1)
		
		self.assertEqual(ch1.filter(lambda x: isinstance(x[2], int)), [ch1[0], ch1[2]])
	
	def testFromPatthernPairs(self):
		f1 = path.join(tempfile.gettempdir(), 'testFromPatthern1.txt')
		f2 = path.join(tempfile.gettempdir(), 'testFromPatthern2.txt')
		f3 = path.join(tempfile.gettempdir(), 'testFromPatthern3.txt')
		f4 = path.join(tempfile.gettempdir(), 'testFromPatthern4.txt')
		f5 = path.join(tempfile.gettempdir(), 'testFromPatthern5.txt')
		f6 = path.join(tempfile.gettempdir(), 'testFromPatthern6.txt')
		
		for f in [f1, f2, f3, f4, f5, f6]:
			safeRemove(f)
			
		
		pat = path.join(tempfile.gettempdir(), 'testFromPatthern?.txt')
		self.assertEqual(Channel.fromPattern(pat), [])
		
		byname   = Channel.create([f1, f2, f3, f4, f6])
		bynamer  = Channel.create([f6, f4, f3, f2, f1])
		bysize   = Channel.create([f4, f1, f3, f2, f6])
		bysizer  = Channel.create([f6, f2, f3, f1, f4])
		bymtime  = Channel.create([f4, f2, f3, f1, f6])
		bymtimer = Channel.create([f6, f1, f3, f2, f4])
		bylink   = Channel.create([f5])
		bydir    = Channel.create([f6])
		byfile   = Channel.create([f1, f2, f3, f4, f5])
		pairs    = Channel.create([(f1, f2), (f3, f4), (f5, f6)])
		
		open(f4, 'w').close()
		sleep(.1)
		with open(f2, 'w') as fout2:
			fout2.write('1111')
		sleep(.1)
		with open(f3, 'w') as fout3: 
			fout3.write('111')
		sleep(.1)
		with open(f1, 'w') as fout1:
			fout1.write('11')
		sleep(.1)
		makedirs(f6)
		sleep(.1)
		
		
		self.assertEqual(Channel.fromPattern(pat, reverse = False), byname)
		self.assertEqual(Channel.fromPattern(pat, reverse = True), bynamer)
		self.assertEqual(Channel.fromPattern(pat, sortby = 'size', reverse = False), bysize)
		self.assertEqual(Channel.fromPattern(pat, sortby = 'size', reverse = True), bysizer)
		self.assertEqual(Channel.fromPattern(pat, sortby = 'mtime', reverse = False), bymtime)
		self.assertEqual(Channel.fromPattern(pat, sortby = 'mtime', reverse = True), bymtimer)
		symlink(f1, f5)
		self.assertEqual(Channel.fromPattern(pat, t = 'link'), bylink)
		self.assertEqual(Channel.fromPattern(pat, t = 'dir'), bydir)
		self.assertEqual(Channel.fromPattern(pat, t = 'file'), byfile)
		self.assertEqual(Channel.fromPairs(pat), pairs)
		
		
		
	def testFromFile(self):
		f = path.join(tempfile.gettempdir(), 'testFromFile.txt')
		with open(f, 'w') as fout:
			fout.write("""
abc	basestring	callable
data	elif	f1
get	has_key	join
""")
		self.assertEqual(Channel.fromFile(f), [
			("abc", "basestring", "callable"), 
			("data", "elif", "f1"), 
			("get", "has_key", "join")
		])
		
		self.assertEqual(Channel.fromFile(f, skip = 2), [
			("data", "elif", "f1"), 
			("get", "has_key", "join")
		])

		self.assertEqual(Channel.fromFile(f, header = True), [
			("data", "elif", "f1"), 
			("get", "has_key", "join")
		])

		self.assertEqual(Channel.fromFile(f, header = True).basestring.flatten(), [
			"elif", "has_key"
		])
		
		with open(f, 'w') as fout:
			fout.write("""
abc|basestring|callable
data|elif|f1
get|has_key|join
""")
		self.assertEqual(Channel.fromFile(f, delimit = '|'), [
			("abc", "basestring", "callable"), 
			("data", "elif", "f1"), 
			("get", "has_key", "join")
		])
		
	def testFromArgv(self):
		sys.argv = ['proc']
		self.assertEqual(Channel.fromArgv(), [])
		
		sys.argv = ['proc', 'a', 'b']
		self.assertEqual(Channel.fromArgv(), [('a', ), ('b', )])
		
		sys.argv = ['proc', 'a,1', 'b,2']
		self.assertEqual(Channel.fromArgv(), [('a', '1'), ('b', '2')])
		
		sys.argv = ['proc', 'a', 'b,2']
		self.assertRaises(ValueError, Channel.fromArgv)
		
	def testFromParams(self):
		params.a = 'a'
		params.b = 2
		params.b.type = int
		params.c = [1, 2]
		params.c.type = list
		params.d = ['a', 'b']
		params.d.type = list
		params.e = []
		params.e.type = list
		
		self.assertRaises(ValueError, Channel.fromParams, 'c', 'e')
		self.assertEqual(Channel.fromParams('c', 'd'), [(1, 'a'), (2, 'b')])
		self.assertEqual(Channel.fromParams('a', 'b'), [('a', 2)])
		
	def testExpandCollapse(self):
		d  = path.join(tempfile.gettempdir(), 'testExpand')
		f1 = path.join(d, 'testExpand1.txt')
		f2 = path.join(d, 'testExpand2.txt')
		f3 = path.join(d, 'testExpand3.txt')
		f4 = path.join(d, 'testExpand4.txt')
		f5 = path.join(d, 'testExpand5.txt')
		f6 = path.join(d, 'testExpand6.txt')
		safeRemove(d)
		makedirs(d)
		for f in [f1, f2, f3, f4, f5, f6]:
			open(f, 'w').close()
			
		ch1 = Channel.create(d)
		self.assertEqual(ch1.expand(), Channel.create([f1, f2, f3, f4, f5, f6]))
		self.assertEqual(ch1.expand().collapse(), ch1)
		
		ch2 = Channel.create(tempfile.gettempdir())
		self.assertEqual(ch2.expand(pattern = 'testExpand/*.txt'), Channel.create([f1, f2, f3, f4, f5, f6]))
		self.assertEqual(ch2.expand(pattern = 'testExpand/*.txt').collapse(), ch1)
		
		
		ch3 = Channel.create((d, 1, 2))
		self.assertEqual(ch3.expand(), Channel.create([f1, f2, f3, f4, f5, f6]).cbind(1,2))
		self.assertEqual(ch3.expand().collapse(), ch3)
		
		ch4 = Channel.create((1, 2, d))
		self.assertEqual(ch4.expand(col = 2), Channel.create([f1, f2, f3, f4, f5, f6]).insert(0, 1, 2))
		self.assertEqual(ch4.expand(col = 2).collapse(col = 2), ch4)
		
	def testCopy(self):
		ch1 = Channel.create()
		ch2 = ch1.cbind(1).copy()
		self.assertEqual(ch1, [])
		self.assertEqual(ch2, [(1, )])
		
	def testWidth(self):
		data = [
			(1,     1),
			("a,b", 1),
			(["a", "b"], 1),
			(("a", "b"), 2),
			([], 0),
			([[]], 1),
		]
		for d in data:
			self.assertEqual(Channel.create(d[0]).width(), d[1])
		self.assertEqual(Channel.create().width(), 0)
		
	def testLength(self):
		data = [
			(1,     1),
			("a,b", 1),
			(["a", "b"], 2),
			(("a", "b"), 1),
			([], 0),
			([[]], 1),
		]
		for d in data:
			self.assertEqual(Channel.create(d[0]).length(), d[1])
		self.assertEqual(Channel.create().length(), 0)
	
	def testMapMapCol(self):
		ch1 = Channel.create()
		ch2 = Channel.create([1,2,3,4,5])
		ch3 = Channel.create([('a', 1), ('b', 2)])
		self.assertEqual(ch1.map(lambda x: (x[0]*x[0],)), [])
		self.assertEqual(ch2.map(lambda x: (x[0]*x[0],)), Channel.create([1,4,9,16,25]))
		self.assertEqual(ch3.map(lambda x: (x[0], x[1]*x[1])), Channel.create([('a', 1), ('b', 4)]))
		self.assertEqual(ch1.mapCol(lambda x: x*x), [])
		self.assertEqual(ch2.mapCol(lambda x: x*x), Channel.create([1,4,9,16,25]))
		self.assertEqual(ch3.mapCol(lambda x: x*x, 1), Channel.create([('a', 1), ('b', 4)]))
		
	def testReduceReduceCol(self):
		ch1 = Channel.create()
		self.assertRaises(TypeError, ch1.reduce, lambda x,y: x+y)
		ch1 = Channel.create([1,2,3,4,5])
		self.assertEqual(ch1.reduce(lambda x,y: x+y), (1, 2, 3, 4, 5))
		self.assertEqual(ch1.reduceCol(lambda x,y: x+y), 15)

	def testRbind(self):
		ch1 = Channel.create()
		ch2 = Channel.create((1,2,3))
		data = [
			(Channel.create(1), [(1, )], [(1,2,3),(1,1,1)]),
			(Channel.create((2,2,2)), [(2,2,2)], [(1,2,3), (2,2,2)]),
			([3], [(3,)],[(1,2,3),(3,3,3)]),
			((3,), [(3,)],[(1,2,3),(3,3,3)]),
			((4,4,4), [(4,4,4)],[(1,2,3),(4,4,4)]),
			([4,4,4], [(4,4,4)],[(1,2,3),(4,4,4)]),
			(5, [(5,)],[(1,2,3),(5,5,5)]),
		]
		for d in data:
			self.assertEqual(ch1.rbind(d[0]), d[1])
			self.assertEqual(ch2.rbind(d[0]), d[2])
			self.assertEqual(ch1, [])
			self.assertEqual(ch2, [(1,2,3)])
		self.assertRaises(ValueError, ch2.rbind, Channel.create((1,1)))
		self.assertRaises(ValueError, ch2.rbind, [1,2])
		self.assertRaises(ValueError, ch2.rbind, (1,2))

	def testSlice(self):
		ch = Channel.create((1,2,3,4,5))
		self.assertEqual(ch.slice(0), ch)
		self.assertEqual(ch.slice(1), Channel.create((2,3,4,5)))
		self.assertEqual(ch.slice(-1), Channel.create(5))
		self.assertEqual(ch.slice(1, 2), Channel.create((2,3)))
		self.assertEqual(ch.slice(5), [()])
		self.assertEqual(Channel.create().slice(1), [])

	def testColAt(self):
		ch = Channel.create((1,2,3,4,5))
		self.assertEqual(ch.colAt(1), Channel.create(2))
		self.assertEqual(ch.colAt(5), Channel.create([()]))
		self.assertEqual(Channel.create().colAt(0), [])

	def testRowAt(self):
		ch = Channel.create([1,2,3,4,5])
		self.assertEqual(ch.rowAt(1), Channel.create(2))
		self.assertEqual(ch.rowAt(4), Channel.create([(5)]))
		self.assertRaises(IndexError, Channel.create().rowAt, 0)

	def testFoldUnFold(self):
		ch = Channel.create((1,2,3,4,5,6))
		self.assertRaises(ValueError, ch.fold, 4)
		self.assertEqual(ch.fold(2), [(1,2),(3,4),(5,6)])
		self.assertEqual(ch.fold(3), [(1,2,3),(4,5,6)])
		self.assertRaises(ValueError, ch.fold(2).unfold)
		self.assertEqual(ch.fold(3).unfold(2), ch)
		self.assertEqual(Channel.create().fold(), [])
		self.assertEqual(Channel.create().unfold(), [])
	
	def testSplit(self):
		ch = Channel.create((1,2,3,4,5,6))
		self.assertEqual(ch.split(), [Channel.create(i) for i in (1,2,3,4,5,6)])
		self.assertEqual(ch.split(True), [[i] for i in (1,2,3,4,5,6)])
		self.assertEqual(Channel.create().split(), [])
		self.assertEqual(Channel.create().split(True), [])

	def testFlatten(self):
		ch = Channel.create([(1,2,3), (4,5,6)])
		self.assertEqual(ch.flatten(), [1,2,3,4,5,6])
		self.assertEqual(ch.flatten(1), [2,5])
		self.assertEqual(Channel.create().flatten(), [])
		self.assertEqual(Channel.create().flatten(1), [])

	def testAttach(self):
		ch = Channel.create([(1,2,3), (4,5,6)])
		self.assertRaises(IndexError, ch.attach)
		self.assertRaises(ValueError, ch.attach, "col1")
		self.assertRaises(ValueError, ch.attach, "col1", "attach", "col2")

		ch.attach ("col1", "col2", "col3")
		self.assertEqual(ch.col1, ch.colAt(0))
		self.assertEqual(ch.col2, ch.colAt(1))
		self.assertEqual(ch.col3, ch.colAt(2))

		ch.attach ("col1", "col2", "col3", True)
		self.assertEqual(ch.col1, ch.flatten(0))
		self.assertEqual(ch.col2, ch.flatten(1))
		self.assertEqual(ch.col3, ch.flatten(2))

	def testGet(self):
		ch = Channel.create([(1,2,3), (4,5,6)])
		self.assertEqual(ch.get(), 1)
		self.assertEqual(ch.get(2), 3)
		self.assertEqual(ch.get(5), 6)

	def testRepCol(self):
		ch = Channel.create([(1,2,3), (4,5,6)])
		self.assertEqual(ch.repCol(), [(1,2,3,1,2,3), (4,5,6,4,5,6)])
		self.assertEqual(ch.repCol(3), [(1,2,3,1,2,3,1,2,3), (4,5,6,4,5,6,4,5,6)])
		ch = Channel.create()
		self.assertEqual(ch.repCol(), [])

	def testRepRow(self):
		ch = Channel.create([(1,2,3), (4,5,6)])
		self.assertEqual(ch.repRow(), [(1,2,3), (4,5,6), (1,2,3), (4,5,6)])
		self.assertEqual(ch.repRow(3), [(1,2,3), (4,5,6), (1,2,3), (4,5,6), (1,2,3), (4,5,6)])
		ch = Channel.create()
		self.assertEqual(ch.repRow(), [])

if __name__ == '__main__':
	unittest.main(verbosity=2)