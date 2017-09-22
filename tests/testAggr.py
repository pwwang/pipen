import path, unittest

from contextlib import contextmanager
from six import StringIO

from pyppl import Proc, Aggr, utils

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

		b = Aggr(p1, p2, False)
		self.assertEqual(b.starts, [])
		self.assertEqual(b.ends, [])

		self.assertRaises(AttributeError, Aggr, p1.copy(newid = 'set'))
		self.assertRaises(AttributeError, Aggr, p1.copy(newid = 'id'))
		self.assertRaises(AttributeError, Aggr, p1.copy(newid = 'starts'))
		self.assertRaises(AttributeError, Aggr, p1.copy(newid = 'ends'))
		self.assertRaises(AttributeError, Aggr, p1.copy(newid = 'procs'))
		self.assertRaises(AttributeError, Aggr, p1.copy(newid = 'addProc'))
		self.assertRaises(AttributeError, Aggr, p1.copy(newid = 'copy'))

	def testSet(self):
		p1 = Proc()
		p2 = Proc()
		a = Aggr(p1, p2)
		a.set('forks', 20)
		self.assertEqual(a.p1.forks, 20)
		self.assertEqual(a.p2.forks, 20)
		a.set('errhow', 'retry', 'p2')
		self.assertEqual(a.p2.errhow, 'retry')
		self.assertEqual(a.p1.errhow, 'terminate')
		a.set('args', {'a': 2})
		self.assertEqual(a.p1.args, {'a':2})
		self.assertEqual(a.p2.args, {'a':2})
		a.set('args.a', 1)
		self.assertEqual(a.p1.args, {'a':1})
		self.assertEqual(a.p2.args, {'a':1})
		a.set('tplenvs.x', 1)
		self.assertEqual(a.p1.tplenvs, {'x':1})
		self.assertEqual(a.p2.tplenvs, {'x':1})

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
		self.assertIn(a.p3, a.procs)
		self.assertIn(b.p3, b.procs)
		self.assertIn(c.p3, c.procs)
		self.assertIn(d.p3, d.procs)
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




		

if __name__ == '__main__':
	unittest.main(verbosity=2)