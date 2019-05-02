# pylint: disable=invalid-name,missing-docstring

import testly

from pyppl import Proc, Box
from pyppl.aggr import _Proxy, Aggr

class TestProxy(testly.TestCase):

	def testGetAttr(self):
		self.assertEqual(_Proxy([1,2,1]).count(1), 2)
		self.assertEqual(_Proxy([
			Box(a=1),
			Box(a=2),
			Box(a=3),
		]).a, [1,2,3])
		self.assertEqual(_Proxy([
			Box(a=Box(b=1)),
			Box(a=Box(b=2)),
			Box(a=Box(b=3)),
		])['a']['b'], [1,2,3])

	def testSetAttr(self):
		a = _Proxy([1,2,3])
		a.__dict__['__doc__'] = 'proxy'
		self.assertEqual(a.__doc__, 'proxy')

		a = _Proxy([
			Box(a=1),
			Box(a=2),
			Box(a=3),
		])
		a.a = 4
		self.assertEqual(a, [
			Box(a=4),
			Box(a=4),
			Box(a=4),
		])
		a.a = (4,5,6)
		self.assertEqual(a, [
			Box(a=4),
			Box(a=5),
			Box(a=6),
		])

		a = _Proxy([
			Box(a=Box(b=1)),
			Box(a=Box(b=2)),
			Box(a=Box(b=3)),
		])
		a.a.b = 4
		self.assertEqual(a, [
			Box(a=Box(b=4)),
			Box(a=Box(b=4)),
			Box(a=Box(b=4)),
		])
		a['a']['b'] = (4,5,6)
		self.assertEqual(a, [
			Box(a=Box(b=4)),
			Box(a=Box(b=5)),
			Box(a=Box(b=6)),
		])

class TestAggr(testly.TestCase):
	def testInit(self):
		a = Aggr()
		self.assertIsInstance(a, (Box, Aggr))

		p1 = Proc()
		p2 = Proc()
		p3 = Proc()
		p4 = Proc()
		a = Aggr(p1, p2, p3, p4, copy = False)
		self.assertEqual({k:v for k,v in a.items() if k.startswith('p')}, Box(p1 = p1, p2 = p2, p3 = p3, p4 = p4))

		a = Aggr(p1, p2, p3, p4)
		self.assertEqual([k for k in a.keys() if k.startswith('p')], ['p1', 'p2', 'p3', 'p4'])

		self.assertRaises(AssertionError, Aggr, 1)

		self.assertEqual(a.p1.id, 'p1')
		self.assertEqual(a.p1.tag, 'notag@a')

		a = Aggr(p1, p2, p3, p4, id = 'b', tag = 'tag')
		self.assertEqual(a.p1.id, 'p1')
		self.assertEqual(a.p1.tag, 'tag@b')

		self.assertEqual(a.p2.depends, [a.p1])

		self.assertEqual(a.starts, [a.p1])
		self.assertEqual(a.ends, [a.p4])

		self.assertIs(a.groups.starts, a.starts)
		self.assertIs(a.groups.ends, a.ends)

	def testGetItem(self):

		# it's ok to define multiple p1 without tag, because we haven't run yet
		p1 = Proc()
		p2 = Proc()
		p3 = Proc()
		p4 = Proc()

		a = Aggr(p1, p2, p3, p4, copy = False)
		self.assertEqual(a.starts, [a.p1])

		self.assertEqual(a[0], a.p1)
		self.assertEqual(a[:1], [a.p1])
		self.assertEqual(a[(0,1)], [a.p1, a.p2])
		self.assertEqual(a[("p1", "p2")], [a.p1, a.p2])
		self.assertEqual(a["p*"], [a.p1, a.p2, a.p3, a.p4])

	def testSetGroup(self):
		px1 = Proc()
		px2 = Proc()
		py1 = Proc()
		py2 = Proc()
		a = Aggr(px1, px2, py1, py2)
		a.setGroup('g1', 'p?1')
		a.setGroup('g2', 'p?2')
		a.setGroup('gx', 'px?')
		a.setGroup('gy', 'py?')
		self.assertEqual(a.g1, [a.px1, a.py1])
		self.assertEqual(a.g2, [a.px2, a.py2])
		self.assertEqual(a.gx, [a.px1, a.px2])
		self.assertEqual(a.gy, [a.py1, a.py2])

	def testCopy(self):
		px1 = Proc()
		px2 = Proc()
		py1 = Proc()
		py2 = Proc()
		a = Aggr(px1, px2, py1, py2)
		a.setGroup('g1', 'p?1')
		a.setGroup('g2', 'p?2')
		a.setGroup('gx', 'px?')
		a.setGroup('gy', 'py?')

		b = a.copy()
		self.assertEqual(b.id, 'b')
		self.assertEqual(b.py2.depends, [b.py1])
		self.assertEqual(b.py1.depends, [b.px2])
		self.assertEqual(b.px2.depends, [b.px1])
		self.assertEqual(b.starts, [b.px1])
		self.assertEqual(b.ends, [b.py2])
		self.assertEqual(b.g1, [b.px1, b.py1])
		self.assertEqual(b.g2, [b.px2, b.py2])
		self.assertEqual(b.gx, [b.px1, b.px2])
		self.assertEqual(b.gy, [b.py1, b.py2])

if __name__ == '__main__':
	testly.main(verbosity=2)
