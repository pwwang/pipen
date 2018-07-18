import testly

from collections import OrderedDict
from pyppl import Aggr, Proc, Box, utils, logger
from pyppl.aggr import _DotProxy, _Proxy
from pyppl.exception import AggrAttributeError, AggrCopyError

class FakeProc(object):
	def __init__(self, id):
		self.id    = id
		self.args  = Box(inopts = Box(), id = id)
		self.forks = 1

	def __eq__(self, other):
		return self.id == other.id
	
	def __ne__(self, other):
		return not self.__eq__(other)

class TestDotProxy(testly.TestCase):
	
	def dataProvider_testInit(self):
		yield Box(),
		yield [Box(), Box(), Box()],
	
	def testInit(self, objs):
		dp = _DotProxy(objs)
		self.assertIsInstance(dp, _DotProxy)
		self.assertIsInstance(dp._DotProxy_objs, list)
		self.assertListEqual(dp._DotProxy_objs, objs if isinstance(objs, list) else [objs])
	
	def testGetattr(self, objs, name, outobjs):
		dp = _DotProxy(objs)
		self.assertListEqual(dp.__getattr__(name)._DotProxy_objs, outobjs)

	def dataProvider_testGetattr(self):
		yield Box(a = 1), 'a', [1]
		yield [Box(a=1), Box(a=2), Box(a=3)], 'a', [1,2,3]
		yield [Box(a=Box()), Box(a=Box(b=1)), Box(a=Box(c=2))], 'a', [Box(),Box(b=1),Box(c=2)]

	def testSetattr(self, objs, name, value, outvalue):
		dp = _DotProxy(objs)
		dp.__setattr__(name, value)
		self.assertListEqual(dp.__getattr__(name)._DotProxy_objs, outvalue)

	def dataProvider_testSetattr(self):
		yield Box(a = 1), 'a', 2, [2]
		yield [Box(a=1), Box(a=2), Box(a=4)], 'a', 3, [3,3,3]
		yield [Box(a=Box()), Box(a=Box()), Box(a=Box())], 'a', Box(b=1), [Box(b=1)]*3

	def testGetitem(self, objs, name, outobjs):
		dp = _DotProxy(objs)
		self.assertListEqual(dp[name]._DotProxy_objs, outobjs)

	def dataProvider_testGetitem(self):
		yield Box(a = 1), 'a', [1]
		yield [Box(a=1), Box(a=2), Box(a=3)], 'a', [1,2,3]
		yield [Box(a=Box()), Box(a=Box(b=1)), Box(a=Box(c=2))], 'a', [Box(),Box(b=1),Box(c=2)]

	def testSetitem(self, objs, name, value, outvalue):
		dp = _DotProxy(objs)
		dp[name] = value
		self.assertListEqual(dp[name]._DotProxy_objs, outvalue)

	def dataProvider_testSetitem(self):
		yield Box(a = 1), 'a', 2, [2]
		yield [Box(a=1), Box(a=2), Box(a=4)], 'a', 3, [3,3,3]
		yield [Box(a=Box()), Box(a=Box()), Box(a=Box())], 'a', Box(b=1), [Box(b=1)]*3

class TestProxy(testly.TestCase):

	def testInit(self, name, procs, starts, ends):
		p = _Proxy(name, procs, starts, ends)
		self.assertListEqual(p._ids, [proc.id for proc in procs.values()])
		self.assertListEqual(p._starts, [proc.id for proc in starts])
		self.assertListEqual(p._ends, [proc.id for proc in ends])
		self.assertListEqual(p._procs, list(procs.values()))
		self.assertEqual(p._attr, name)

	def dataProvider_testInit(self):
		yield 'forks', OrderedDict([('a', FakeProc('a')), ('b', FakeProc('b')), ('c', FakeProc('c'))]), [FakeProc('a')], [FakeProc('c')]

	def testAny2index(self, p, anything, out):
		self.assertEqual(p._any2index(anything), out)

	def dataProvider_testAny2index(self):
		procs = OrderedDict([('a', FakeProc('a')), ('b', FakeProc('b')), ('c', FakeProc('c'))])
		p = _Proxy('args', procs, [procs['a']], [procs['c']])
		yield p, 0, 0
		yield p, 1, 1
		yield p, slice(0,1), slice(0,1)
		yield p, [0,2], [0,2]
		yield p, (1,2), [1,2]
		yield p, 'a', 0
		yield p, 'c', 2
		yield p, 'a, c', [0,2]
		yield p, ['a', 'b'], [0, 1]

	def testGetitem(self, p, index, outobjs):
		self.assertEqual(p[index]._DotProxy_objs, outobjs)

	def dataProvider_testGetitem(self):
		procs = OrderedDict([('a', FakeProc('a')), ('b', FakeProc('b')), ('c', FakeProc('c'))])
		p = _Proxy('args', procs, [procs['a']], [procs['c']])
		yield p, 'a,c', [Box(inopts = Box(), id = 'a'), Box(inopts = Box(), id = 'c')]
		yield p, (0,2), [Box(inopts = Box(), id = 'a'), Box(inopts = Box(), id = 'c')]
		yield p, [0,2], [Box(inopts = Box(), id = 'a'), Box(inopts = Box(), id = 'c')]
		yield p, ['a', 'c'], [Box(inopts = Box(), id = 'a'), Box(inopts = Box(), id = 'c')]
		yield p, 'starts', [Box(inopts = Box(), id = 'a')]
		yield p, 'ends', [Box(inopts = Box(), id = 'c')]
	
	def testSetitem(self, p, index, value, outvalue):
		p[index] = value
		self.assertEqual(p[index]._DotProxy_objs, outvalue)
	
	def dataProvider_testSetitem(self):
		procs = OrderedDict([('a', FakeProc('a')), ('b', FakeProc('b')), ('c', FakeProc('c'))])
		p = _Proxy('forks', procs, [procs['a']], [procs['c']])
		yield p, 'a,c', 10, [10, 10]
		yield p, (0,2), 10, [10, 10]
		yield p, [0,2], 10, [10, 10]
		yield p, ['a', 'c'], 10, [10, 10]
		yield p, 'starts', 4, [4]
		yield p, 'ends', 4, [4]

class TestAggr(testly.TestCase):

	def dataProvider_testInit(self):
		pInit1 = Proc()
		pInit2 = Proc()
		pInit3 = Proc()
		pInit4 = Proc()
		pInit5 = Proc()
		
		yield [pInit1.copy(id = 'starts'), pInit2, pInit3, pInit4, pInit5], {}, AggrAttributeError, 'Use a different process id, attribute name is already taken: \'starts\''
		yield [pInit1.copy(id = '_procs'), pInit2, pInit3, pInit4, pInit5], {}, AggrAttributeError, 'Use a different process id, attribute name is already taken: \'_procs\''
		yield [pInit1, pInit2.copy(id = 'pInit1'), pInit3, pInit4, pInit5], {}, AggrAttributeError, 'Use a different process id, attribute name is already taken: \'pInit1\''
		yield [pInit1.copy(tag = '1st'), pInit2, pInit3, pInit4, pInit5], {}
		yield [pInit1.copy(tag = '1st'), pInit2, pInit3, pInit4, pInit5], {'tag': 'aggr'}
		yield [pInit1, pInit2, pInit3, pInit4, pInit5], {'depends': False}
		yield [pInit1, pInit2, pInit3, pInit4, pInit5], {}
		yield [pInit1], {}
		yield [pInit1, pInit2, pInit3, pInit4, pInit5], {'id': 'aggr2'}
		
	def testInit(self, args, kwargs, exception = None, msg = None):
		self.maxDiff = None
		if exception:
			self.assertRaisesRegex(exception, msg, Aggr, *args, **kwargs)
		else:
			aggr = Aggr(*args, **kwargs)
			self.assertEqual(aggr.id, 'aggr' if 'id' not in kwargs else kwargs['id'])
			for i, p in enumerate(aggr._procs.values()):
				self.assertEqual(p.tag, kwargs['tag'] if 'tag' in kwargs else utils.uid(args[i].tag + '@' + aggr.id, 4))
				self.assertEqual(p.aggr, aggr.id)
				self.assertIs(aggr._procs[p.id], p)
			if ('depends' not in kwargs or kwargs['depends']) and len(args) > 0:
				self.assertListEqual(aggr.starts, [list(aggr._procs.values())[0]])
				self.assertListEqual(aggr.ends  , [list(aggr._procs.values())[-1]])
				for i, proc in enumerate(aggr._procs.values()):
					if i == 0: continue
					self.assertIs(proc.depends[0], list(aggr._procs.values())[i - 1])
			else:
				self.assertListEqual(aggr.starts, [])
				self.assertListEqual(aggr.ends  , [])
				for i, proc in enumerate(aggr._procs.values()):
					if i == 0: continue
					self.assertListEqual(proc.depends, [])

	def testGetattr(self, aggr, name, outtype):
		# make sure getattr is not called for starts,ends,_procs
		self.assertIsInstance(aggr.starts, list)
		self.assertIsInstance(aggr.ends, list)
		self.assertIsInstance(aggr._procs, dict)
		self.assertIsInstance(aggr.__getattr__(name), outtype)

	def dataProvider_testGetattr(self):
		pGetAttr1 = Proc()
		pGetAttr2 = Proc()
		pGetAttr3 = Proc()
		aggr = Aggr(pGetAttr1, pGetAttr2, pGetAttr3)
		# yield aggr, 'starts', list
		# yield aggr, 'ends', list
		# yield aggr, '_procs', dict
		yield aggr, 'pGetAttr1', Proc
		yield aggr, 'pGetAttr2', Proc
		yield aggr, 'pGetAttr3', Proc
		yield aggr, 'a', _Proxy
		yield aggr, 'b', _Proxy
		yield aggr, 'aggrs', _Proxy

	def testSetattr(self, aggr, name, value):
		# make sure setattr is not called
		aggr.id = aggr.id
		aggr.__setattr__(name, value)
		for proc in aggr._procs.values():
			self.assertEqual(getattr(proc, name), value)
			self.assertNotEqual(proc.id, aggr.id)

	def dataProvider_testSetattr(self):
		pGetAttr1 = Proc()
		pGetAttr2 = Proc()
		pGetAttr3 = Proc()
		aggr = Aggr(pGetAttr1, pGetAttr2, pGetAttr3)
		yield aggr, 'forks', 10
			
	def dataProvider_testChain(self):
		pChain1 = Proc()
		pChain2 = Proc()
		pChain3 = Proc()
		pChain1.args.params = Box(c = 1, d = 2)
		pChain3.args.b = 1
		aggr = Aggr(pChain1, pChain2, pChain3)
		def attr_setaggr():
			aggr.args[2].b = 2
		def attr_setaggr1():
			aggr.args['starts'].params.c = 2
		def attr_setaggr2():
			aggr.args[0:1].params.d = 3
		def attr_setaggr3():
			aggr.args.x = 4
		def attr_setaggr4():
			aggr.forks = 10
		def attr_setaggr5():
			aggr.args['pChain3'].b1 = 11
		def attr_setaggr6():
			aggr.runner = 'sge'
		yield attr_setaggr, 2, lambda: aggr.pChain3.args.b
		yield attr_setaggr1, 2, lambda: aggr.pChain1.args.params.c
		yield attr_setaggr2, 3, lambda: aggr.pChain1.args.params.d
		yield attr_setaggr3, 4, lambda: 4
		yield attr_setaggr4, 10, lambda: aggr.pChain2.forks
		yield attr_setaggr5, 11, lambda: aggr.pChain3.args.b1
		yield attr_setaggr6, 'sge', lambda: aggr.pChain3.config['runner']
	
	def testChain(self, attr_setaggr, value, attr_getproc):
		attr_setaggr()
		self.assertEqual(attr_getproc(), value)
	
	def dataProvider_testAddProc(self):
		pAddProc1 = Proc()
		pAddProc2 = Proc()
		pAddProc3 = Proc()
		pAddProc4 = Proc(tag = 'new')
		pAddProc5 = Proc(tag = 'new')
		pAddProc6 = Proc(tag = 'new')
		aggr = Aggr(pAddProc1, pAddProc2, pAddProc3)
		yield aggr, pAddProc4, 'starts', None, True, utils.uid(pAddProc4.tag + '@' + aggr.id, 4)
		yield aggr, pAddProc5, 'ends', None, True, utils.uid(pAddProc5.tag + '@' + aggr.id, 4)
		yield aggr, pAddProc6, None, None, False, utils.uid(pAddProc6.tag + '@' + aggr.id, 4)
	
	def testAddProc(self, aggr, p, where, tag, copy, newtag):
		self.assertIs(aggr.addProc(p, tag, where, copy), aggr)
		if not copy:
			self.assertIs(aggr._procs[p.id], p)
		self.assertEqual(aggr._procs[p.id].id, p.id)
		self.assertEqual(aggr._procs[p.id].tag, newtag)
		if where == 'starts':
			self.assertIn(aggr._procs[p.id], aggr.starts)
		elif where == 'ends':
			self.assertIn(aggr._procs[p.id], aggr.ends)
		else:
			self.assertNotIn(aggr._procs[p.id], aggr.starts)
			self.assertNotIn(aggr._procs[p.id], aggr.ends)
			
	def dataProvider_testCopy(self):
		pCopy1 = Proc()
		pCopy2 = Proc()
		pCopy3 = Proc()
		pCopy4 = Proc()
		aggr = Aggr(pCopy1, pCopy2, pCopy3)
		aggr.depends = [pCopy4]
		yield aggr, 'newtag', True, 'newid'
		yield aggr, None, True, None
		yield aggr, None, False, None
		yield aggr, aggr.pCopy1.tag, False, None, AggrCopyError, 'Cannot copy process with same id and tag: \'pCopy1.%s\'' % aggr.pCopy1.tag
		
		aggr1 = Aggr(pCopy1, pCopy2, pCopy3, depends = False)
		aggr1.starts = [aggr1.pCopy1, aggr1.pCopy2]
		aggr1.pCopy3.depends = aggr1.starts
		yield aggr1, None, True, None
			
	def testCopy(self, aggr, tag, deps, id, exception = None, msg = None):
		self.maxDiff = None
		if exception:
			self.assertRaisesRegex(exception, msg, aggr.copy, tag, deps, id)
		else:
			newaggr = aggr.copy(tag, deps, id)
			# id
			if id is None:
				self.assertEqual(newaggr.id, 'newaggr')
			else:
				self.assertEqual(newaggr.id, id)
			# tag
			if tag is None:
				for k, proc in newaggr._procs.items():
					self.assertEqual(proc.tag, newaggr._procs[k].tag)
			else:
				for k, proc in newaggr._procs.items():
					self.assertEqual(proc.tag, tag)
			# procs
			self.assertDictEqual(newaggr._procs, {k:newaggr._procs[k] for k in aggr._procs.keys()})
			# starts, ends
			self.assertListEqual(newaggr.starts, [newaggr._procs[p.id] for p in aggr.starts])
			self.assertListEqual(newaggr.ends, [newaggr._procs[p.id] for p in aggr.ends])
			# depends
			if deps:
				for k, p in newaggr._procs.items():
					self.assertListEqual(
						list(p.depends),
						[
							p if not p in aggr._procs.values() else \
							newaggr._procs[p.id] \
							for p in aggr._procs[k].depends
						]
					)
			else:
				for k, p in newaggr._procs.items():
					self.assertListEqual(p.depends, [])
	
	def dataProvider_testDepends(self):
		pDepends1 = Proc()
		pDepends2 = Proc()
		pDepends3 = Proc()
		pDepends4 = Proc()
		pDepends5 = Proc()
		aggr = Aggr(pDepends1, pDepends2, pDepends3)
		aggr.starts = [pDepends1, pDepends2]
		yield aggr, [pDepends4, pDepends5]		
	
	def testDepends(self, aggr, depends):
		aggr.depends = depends
		for i, p in enumerate(aggr.starts):
			self.assertListEqual(p.depends, [depends[i]])
		
	def dataProvider_testDepends2(self):
		pDepends21 = Proc()
		pDepends22 = Proc()
		pDepends23 = Proc()
		pDepends24 = Proc()
		pDepends25 = Proc()
		aggr = Aggr(pDepends21, pDepends22, pDepends23)
		aggr.starts = [pDepends21, pDepends22]
		yield aggr, [pDepends24, pDepends25]		
	
	def testDepends2(self, aggr, depends):
		aggr.depends2 = depends
		for p in aggr.starts:
			self.assertListEqual(p.depends, depends)

	def testIssue31(self):
		p = Proc()
		#p.runner = 'local'
		a = Aggr(p)
		a.runner = 'sge'
		a.p._readConfig(None, None)
		self.assertEqual(a.p.runner, 'sge')

		a2 = Aggr(p.copy(id = 'p2'))
		a2.p2.runner = 'local'
		a2.runner = 'sge' # make sure it's not  overwriting
		a2.p2._readConfig(None, None)
		self.assertEqual(a2.p2.runner, 'local')
		
if __name__ == '__main__':
	testly.main(verbosity=2)