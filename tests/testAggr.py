import path, unittest

from contextlib import contextmanager
from six import StringIO

from pyppl import Proc, Aggr, utils, Channel, Box
from pyppl.aggr import _Proxy

@contextmanager
def captured_output():
	new_out, new_err = StringIO(), StringIO()
	old_out, old_err = sys.stdout, sys.stderr
	try:
		sys.stdout, sys.stderr = new_out, new_err
		yield sys.stdout, sys.stderr
	finally:
		sys.stdout, sys.stderr = old_out, old_err

class TestAggr (unittest.TestCase):
	
	def testInit(self):
		p1 = Proc()
		p2 = Proc()
		a = Aggr(p1, p2)
		self.assertIsInstance(a, Aggr)
		self.assertIsNot(a.starts[0], p1)
		self.assertIsNot(a.ends[0], p2)
		self.assertEqual(a.starts[0].id, 'p1')
		self.assertEqual(a.ends[0].id, 'p2')
		self.assertIn(a.p1, a.p2.depends)

		b = Aggr(p1, p2, depends = False)
		self.assertEqual(b.starts, [])
		self.assertEqual(b.ends, [])

		self.assertRaises(AttributeError, Aggr, p1.copy(newid = 'id'))
		self.assertRaises(AttributeError, Aggr, p1.copy(newid = 'starts'))
		self.assertRaises(AttributeError, Aggr, p1.copy(newid = 'ends'))
		self.assertRaises(AttributeError, Aggr, p1.copy(newid = 'delegate'))
		self.assertRaises(AttributeError, Aggr, p1.copy(newid = 'addProc'))
		self.assertRaises(AttributeError, Aggr, p1.copy(newid = 'copy'))

	def testProxy(self):
		a = Aggr()
		p = _Proxy(a, 'args', 'a')
		self.assertIsInstance(a, Aggr)
		self.assertIsInstance(p, _Proxy)
		p.addsub('b')
		self.assertEqual(p.__dict__['_subs'], ['a', 'b'])
		self.assertRaises(AttributeError, p.__setattr__, 'x', 1)
		p.a = 1
		p.b = 2

	def testGetAttr(self):
		p = Proc()
		a = Aggr(p)
		a.delegate('args.x')
		a.delegate('args.y')
		self.assertEqual(a.starts, [a.p])
		self.assertEqual(a.ends, [a.p])
		self.assertEqual(a.id, 'a')
		self.assertIsInstance(a.args, _Proxy)
		self.assertEqual(a.args._subs, ['x', 'y'])
		self.assertIsInstance(a.p, Proc)
		self.assertIsNot(a.p, p)
		self.assertEqual(a._procs, {'p': a.p})

		a.args.x = 1
		a.args.y = 2
		self.assertEqual(a.p.args.x, 1)
		self.assertEqual(a.p.args.y, 2)

		a.delegate('a.*', None, 'args.*')
		a.a.x = 3
		a.a.y = 4
		self.assertEqual(a.p.args.x, 3)
		self.assertEqual(a.p.args.y, 4)

	def testDelegate(self):
		p1 = Proc()
		p2 = Proc()
		p1.args.args1 = Box()
		a = Aggr(p1, p2)
		self.assertRaises(AttributeError, a.delegate, 'starts')
		self.assertRaises(AttributeError, a.delegate, 'x.a.b')
		self.assertRaises(AttributeError, a.delegate, 'id.b')
		#self.assertRaises(AttributeError, a.delegate, 'args.*', None, 'x.*')
		

		a.delegate('a')
		a.delegate('b', 'starts')
		a.delegate('c', 'ends')
		a.delegate('d', 'both')
		a.delegate('a', 'p1', 'args.x') # overwrite
		a.delegate('tplenvs.a', pattr = 'desc')
		a.delegate('a.*', None, 'args.*')
		a.delegate('f.*', 'p1', 'args.args1.*')
		self.assertEqual(a._delegates, {
			'a': ('p1', 'args.x'),
			'a.*': (None, 'args.*'),
			'b': ('starts', 'b'),
			'c': ('ends', 'c'),
			'd': ('both', 'd'),
			'depends': ('starts', 'depends'),
			'depends2': ('starts', 'depends2'),
			'exdir': ('ends', 'exdir'),
			'exhow': ('ends', 'exhow'),
			'exow': ('ends', 'exow'),
			'expart': ('ends', 'expart'),
			'input': ('starts', 'input'),
			'tplenvs.a': (None, 'desc'),
			'f.*': ('p1', 'args.args1.*')
		})
		a.f.j = 2
		a.tplenvs.a = 'hahahah'
		a.a.a = 'aaa'
		self.assertEqual(a.p1.args.args1.j, 2)
		self.assertEqual(a.p2.desc, 'hahahah')
		self.assertEqual(a.p2.args.a, 'aaa')

	def testSet(self):
		p1 = Proc()
		p2 = Proc()
		a = Aggr(p1, p2)
		a.forks = 20
		self.assertEqual(a.p1.forks, 20)
		self.assertEqual(a.p2.forks, 20)
		a.delegate('errhow', 'p2')
		a.errhow = 'retry'
		self.assertEqual(a.p2.errhow, 'retry')
		self.assertEqual(a.p1.errhow, 'terminate')
		a.delegate('args.*')
		a.args.a = 2
		self.assertEqual(a.p1.args, {'a':2})
		self.assertEqual(a.p2.args, {'a':2})
		a.args.a = 1
		self.assertEqual(a.p1.args, {'a':1})
		self.assertEqual(a.p2.args, {'a':1})
		a.delegate('tplenvs.*')
		a.tplenvs.x = 1
		self.assertEqual(a.p1.tplenvs, {'x':1})
		self.assertEqual(a.p2.tplenvs, {'x':1})
				
		a.p1.tplenvs.b = Box()
		a.delegate('tb', 'starts', 'tplenvs.b.c')
		a.tb = 'h'
		self.assertEqual(a.p1.tplenvs, {'x':1, 'b': {
			'c': 'h'
		}})


		a.delegate('forks', 'starts')
		a.forks = 10
		self.assertEqual(a.p1.forks, 10)
		self.assertEqual(a.p2.forks, 20)
		a.delegate('forks', 'ends')
		a.forks = 5
		self.assertEqual(a.p1.forks, 10)
		self.assertEqual(a.p2.forks, 5)

	def testSetInput(self):
		p1 = Proc()
		p2 = Proc()
		p3 = Proc()
		p1.input = "in1, in2"
		p2.input = "in1, in2"
		a = Aggr(p1, p2, p3)
		a.starts = [a.p1, a.p2]
		a.p2.depends = []

		a.input = [lambda x: x]*2
		self.assertTrue(callable(a.p1.config['input']['in1, in2']))
		self.assertTrue(callable(a.p2.config['input']['in1, in2']))

		a.p1.input = "in1, in2"
		a.p2.input = "in1, in2"
		ch = Channel.create([(1,'a', 3, 'c'), (2, 'b', 4, 'd')])
		a.input = [ch.slice(0, 2), ch.slice(2)]
		
		self.assertEqual(a.p1.config['input']['in1, in2'], [(1, 'a'), (2, 'b')])
		self.assertEqual(a.p2.config['input']['in1, in2'], [(3, 'c'), (4, 'd')])

	def testAddproc(self):
		p1 = Proc()
		p2 = Proc()
		p3 = Proc()
		a = Aggr(p1, p2)
		b = Aggr(p1, p2)
		c = Aggr(p1, p2)
		d = Aggr(p1, p2)
		a.addProc(p3)
		b.addProc(p3, where = 'starts')
		c.addProc(p3, where = 'ends')
		d.addProc(p3, where = 'both')
		self.assertIn(a.p3, a.__dict__['_procs'].values())
		self.assertIn(b.p3, b.__dict__['_procs'].values())
		self.assertIn(c.p3, c.__dict__['_procs'].values())
		self.assertIn(d.p3, d.__dict__['_procs'].values())
		self.assertNotIn(a.p3, a.starts)
		self.assertNotIn(a.p3, a.ends)
		self.assertIn(b.p3, b.starts)
		self.assertNotIn(b.p3, b.ends)
		self.assertNotIn(c.p3, c.starts)
		self.assertIn(c.p3, c.ends)
		self.assertIn(d.p3, d.starts)
		self.assertIn(d.p3, d.ends)

	def testCopy(self):
		p1 = Proc()
		p2 = Proc()
		p3 = Proc()
		a = Aggr(p1, p2)
		a.delegate('args.*')
		b = a.copy()
		self.assertEqual(b.id, 'b')
		self.assertEqual(b.p1.tag, utils.uid('b', 4))
		self.assertEqual(b.p2.tag, utils.uid('b', 4))
		self.assertEqual(b.starts, [b.p1])
		self.assertEqual(b.ends, [b.p2])
		self.assertIn(b.p1, b.p2.depends)

		self.assertRaises(ValueError, a.copy, tag = utils.uid('a', 4))
		a.p2.depends = p3
		self.assertRaises(ValueError, a.copy, deps = True)

		a.args.a = 1
		self.assertEqual(a.p1.args.a, 1)

		b.args.a = 2
		self.assertEqual(b.p1.args.a, 2)
		self.assertEqual(a.p1.args.a, 1)

if __name__ == '__main__':
	unittest.main(verbosity=2)