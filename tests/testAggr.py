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
		yield FakeProc('a'), {}, []
		yield [FakeProc('a'), FakeProc('b'), FakeProc('c')], {'args': [FakeProc('a'), FakeProc('b')]}, ['args']
	
	def testInit(self, procs, delegates, prefix):
		dp = _DotProxy(procs, delegates, prefix)
		self.assertIsInstance(dp, _DotProxy)
		self.assertIsInstance(dp._DotProxy_procs, list)
		self.assertListEqual(dp._DotProxy_procs, procs if isinstance(procs, list) else [procs])
		self.assertDictEqual(dp._DotProxy_delegates, delegates)
		self.assertListEqual(dp._DotProxy_prefix, prefix)

	def dataProvider_testSetProcsAttr(self):
		procs = [FakeProc('a'), FakeProc('b'), FakeProc('c')]
		yield procs, ['args', 'inopts'], 'b', 1
		yield procs, ['args'], 'inopts', 2

	def testSetProcsAttr(self, procs, prefix, name, value):
		_DotProxy._setProcsAttr(procs, prefix, name, value)
		for proc in procs:
			obj = proc
			for p in prefix:
				obj = getattr(obj, p)
			self.assertEqual(getattr(obj, name), value)

	def dataProvider_testSetProcsItem(self):
		procs = [FakeProc('a'), FakeProc('b'), FakeProc('c')]
		yield procs, ['args', 'inopts'], 'b', 1
		yield procs, ['args'], 'inopts', 2

	def testSetProcsItem(self, procs, prefix, name, value):
		_DotProxy._setProcsItem(procs, prefix, name, value)
		for proc in procs:
			obj = proc
			for p in prefix:
				obj = getattr(obj, p)
			self.assertEqual(obj[name], value)

	def testGetattr(self, procs, delegates, prefix, name, outprocs):
		dp = _DotProxy(procs, delegates, prefix)
		self.assertListEqual(dp.__getattr__(name)._DotProxy_procs, outprocs)

	def dataProvider_testGetattr(self):
		yield FakeProc('a'), {}, [], 'forks', [FakeProc('a')]
		yield [FakeProc('a'), FakeProc('b'), FakeProc('c')], {'args.inopts': [FakeProc('a')]}, ['args'], 'id', [FakeProc('a'), FakeProc('b'), FakeProc('c')]
		yield [FakeProc('a'), FakeProc('b'), FakeProc('c')], {'args.inopts': [FakeProc('a')]}, ['args'], 'inopts', [FakeProc('a')]

	def testSetattr(self, procs, delegates, prefix, name, value, outvalues):
		dp = _DotProxy(procs, delegates, prefix)
		dp.__setattr__(name, value)
		
		for i, proc in enumerate(dp._DotProxy_procs):
			obj = proc
			for p in prefix:
				obj = getattr(obj, p)
			self.assertEqual(getattr(obj, name), outvalues[i])

	def dataProvider_testSetattr(self):
		yield FakeProc('a'), {}, [], 'forks', 10, [10]
		procs = [FakeProc('a'), FakeProc('b'), FakeProc('c')]
		yield procs, {'args.inopts': [procs[0]]}, ['args'], 'id', 'x', ['x']*3
		yield procs, {'args.inopts': [procs[0]]}, ['args'], 'inopts', 'onlya', ['onlya', Box(), Box()]

	def testGetitem(self, procs, delegates, prefix, name, outprocs):
		dp = _DotProxy(procs, delegates, prefix)
		self.assertListEqual(dp.__getitem__(name)._DotProxy_procs, outprocs)

	def dataProvider_testGetitem(self):
		yield FakeProc('a'), {}, [], 'forks', [FakeProc('a')]
		yield [FakeProc('a'), FakeProc('b'), FakeProc('c')], {'args.inopts': [FakeProc('a')]}, ['args'], 'id', [FakeProc('a'), FakeProc('b'), FakeProc('c')]
		yield [FakeProc('a'), FakeProc('b'), FakeProc('c')], {'args.inopts': [FakeProc('a')]}, ['args'], 'inopts', [FakeProc('a')]

	def testSetitem(self, procs, delegates, prefix, name, value, outvalues):
		dp = _DotProxy(procs, delegates, prefix)
		dp.__setitem__(name, value)
		for i, proc in enumerate(dp._DotProxy_procs):
			obj = proc
			for p in prefix:
				obj = getattr(obj, p)
			self.assertEqual(obj[name], outvalues[i])

	def dataProvider_testSetitem(self):
		yield FakeProc('a'), {}, ['args'], 'id', 'newa', ['newa']
		procs = [FakeProc('a'), FakeProc('b'), FakeProc('c')]
		yield procs, {'args.inopts.x': [procs[0]]}, ['args', 'inopts'], 'y', 'yvalue', ['yvalue']*3
		procs2 = [FakeProc('a'), FakeProc('b'), FakeProc('c')]
		yield procs2, {'args.inopts': [procs2[0]]}, ['args'], 'inopts', 'onlya', ['onlya', Box(), Box()]

class TestProxy(testly.TestCase):

	def testInit(self, name, procs, starts, ends, delegates):
		p = _Proxy(name, procs, starts, ends, delegates)
		self.assertListEqual(p._ids, [proc.id for proc in procs.values()])
		self.assertListEqual(p._starts, [proc.id for proc in starts])
		self.assertListEqual(p._ends, [proc.id for proc in ends])
		self.assertListEqual(p._procs, list(procs.values()))
		self.assertEqual(p._attr, name)
		self.assertDictEqual(p._delegates, delegates)

	def dataProvider_testInit(self):
		yield 'forks', OrderedDict([('a', FakeProc('a')), ('b', FakeProc('b')), ('c', FakeProc('c'))]), [FakeProc('a')], [FakeProc('c')], {}

	def testAny2index(self, p, anything, out):
		self.assertEqual(p._any2index(anything), out)

	def dataProvider_testAny2index(self):
		procs = OrderedDict([('a', FakeProc('a')), ('b', FakeProc('b')), ('c', FakeProc('c'))])
		p = _Proxy('args', procs, [procs['a']], [procs['c']], {})
		yield p, 0, 0
		yield p, 1, 1
		yield p, slice(0,1), slice(0,1)
		yield p, [0,2], [0,2]
		yield p, (1,2), [1,2]
		yield p, 'a', 0
		yield p, 'c', 2
		yield p, 'a, c', [0,2]
		yield p, ['a', 'b'], [0, 1]

	def testGetattr(self, p, name, outprocs):
		dp = p.__getattr__(name)
		self.assertListEqual(dp._DotProxy_procs, outprocs)
		self.assertListEqual(dp._DotProxy_prefix, [p._attr, name])

	def dataProvider_testGetattr(self):
		procs = OrderedDict([('a', FakeProc('a')), ('b', FakeProc('b')), ('c', FakeProc('c'))])
		p = _Proxy('args', procs, [procs['a']], [procs['c']], {})
		yield p, 'id', list(procs.values())
		p2 = _Proxy('args', procs, [procs['a']], [procs['c']], {'args.id': [procs['b']]})
		yield p2, 'id', [FakeProc('b')]

	def testSetattr(self, p, name, value, outvalues):
		p.__setattr__(name, value)
		for i, proc in enumerate(p._procs):
			obj = getattr(proc, p._attr)
			self.assertEqual(getattr(obj, name), outvalues[i])
	
	def dataProvider_testSetattr(self):
		procs = OrderedDict([('a', FakeProc('a')), ('b', FakeProc('b')), ('c', FakeProc('c'))])
		p = _Proxy('args', procs, [procs['a']], [procs['c']], {'args.inopts': [procs['b']]})
		yield p, 'id', 'x', ['x']*3
		yield p, 'inopts', Box(b=1), [Box(), Box(b=1), Box()]

	def testGetitem(self, p, index, outprocs):
		self.assertEqual(p[index]._DotProxy_procs, outprocs)

	def dataProvider_testGetitem(self):
		procs = OrderedDict([('a', FakeProc('a')), ('b', FakeProc('b')), ('c', FakeProc('c'))])
		p = _Proxy('args', procs, [procs['a']], [procs['c']], {'args.inopts': [procs['b']]})
		yield p, 'a,c', [procs['a'], procs['c']]
		yield p, (0,2), [procs['a'], procs['c']]
		yield p, [0,2], [procs['a'], procs['c']]
		yield p, ['a', 'c'], [procs['a'], procs['c']]
		yield p, 'starts', [procs['a']]
		yield p, 'ends', [procs['c']]
		yield p, 'inopts', [procs['b']]
	
	def testSetitem(self, p, index, value, outvalues):
		p[index] = value
		self.assertListEqual([getattr(proc, p._attr) for proc in p._procs], outvalues)
	
	def dataProvider_testSetitem(self):
		procs0 = OrderedDict([('a', FakeProc('a')), ('b', FakeProc('b')), ('c', FakeProc('c'))])
		procs1 = OrderedDict([('a', FakeProc('a')), ('b', FakeProc('b')), ('c', FakeProc('c'))])
		procs2 = OrderedDict([('a', FakeProc('a')), ('b', FakeProc('b')), ('c', FakeProc('c'))])
		procs3 = OrderedDict([('a', FakeProc('a')), ('b', FakeProc('b')), ('c', FakeProc('c'))])
		procs4 = OrderedDict([('a', FakeProc('a')), ('b', FakeProc('b')), ('c', FakeProc('c'))])
		procs5 = OrderedDict([('a', FakeProc('a')), ('b', FakeProc('b')), ('c', FakeProc('c'))])
		procs6 = OrderedDict([('a', FakeProc('a')), ('b', FakeProc('b')), ('c', FakeProc('c'))])
		p0 = _Proxy('forks', procs0, [procs0['a']], [procs0['c']], {'args.inopts': [procs0['b']]})
		p1 = _Proxy('forks', procs1, [procs1['a']], [procs1['c']], {'args.inopts': [procs1['b']]})
		p2 = _Proxy('forks', procs2, [procs2['a']], [procs2['c']], {'args.inopts': [procs2['b']]})
		p3 = _Proxy('forks', procs3, [procs3['a']], [procs3['c']], {'args.inopts': [procs3['b']]})
		p4 = _Proxy('forks', procs4, [procs4['a']], [procs4['c']], {'args.inopts': [procs4['b']]})
		p5 = _Proxy('forks', procs5, [procs5['a']], [procs5['c']], {'args.inopts': [procs5['b']]})
		p6 = _Proxy('args',  procs6, [procs6['a']], [procs6['c']], {'args.inopts': [procs6['b']]})
		yield p0, 'a,c', 10, [10, 1, 10]
		yield p1, (0,2), 10, [10, 1, 10]
		yield p2, [0,2], 10, [10, 1, 10]
		yield p3, ['a', 'c'], 10, [10, 1, 10]
		yield p4, 'starts', 4, [4, 1, 1]
		yield p5, 'ends', 4, [1, 1, 4]
		yield p6, 'inopts', 1, [Box([('inopts', Box()), ('id', 'a')]), Box([('inopts', 1), ('id', 'b')]), Box([('inopts', Box()), ('id', 'c')])]

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

	def testDelegate(self, aggr, attrs, procs, outdelegates, outdelstarts, outdelends):
		aggr.delegate(attrs, procs)
		for attr in Aggr.ATTR_STARTS:
			outdelegates[attr] = aggr.starts
			outdelstarts.append(attr)
		for attr in Aggr.ATTR_ENDS:
			outdelegates[attr] = aggr.ends
			outdelends.append(attr)
		self.assertDictEqual(aggr._delegates, outdelegates)
		self.assertCountEqual(aggr._delegates_starts, outdelstarts)
		self.assertCountEqual(aggr._delegates_ends, outdelends)
	
	def dataProvider_testDelegate(self):
		pGetAttr1 = Proc()
		pGetAttr2 = Proc()
		pGetAttr3 = Proc()
		aggr1 = Aggr(pGetAttr1, pGetAttr2, pGetAttr3)
		aggr2 = Aggr(pGetAttr1, pGetAttr2, pGetAttr3)
		aggr3 = Aggr(pGetAttr1, pGetAttr2, pGetAttr3)
		aggr4 = Aggr(pGetAttr1, pGetAttr2, pGetAttr3)
		yield aggr1, 'aggrs.a', 'pGetAttr1', {'aggrs.a': [aggr1.pGetAttr1]}, [], []
		yield aggr2, 'aggrs.b, aggrs.c', 'pGetAttr1,pGetAttr2', {'aggrs.b': [aggr2.pGetAttr1, aggr2.pGetAttr2], 'aggrs.c': [aggr2.pGetAttr1, aggr2.pGetAttr2]}, [], []
		yield aggr3, 'aggrs.b, aggrs.c', 'starts', {'aggrs.b': [aggr3.pGetAttr1], 'aggrs.c': [aggr3.pGetAttr1]}, ['aggrs.b', 'aggrs.c'], []
		yield aggr4, 'aggrs.b, aggrs.c', 'ends', {'aggrs.b': [aggr4.pGetAttr3], 'aggrs.c': [aggr4.pGetAttr3]}, [], ['aggrs.b', 'aggrs.c']


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

	def testSetattr(self, aggr, name, value, values):
		# make sure setattr is not called
		aggr.id = aggr.id
		aggr.__setattr__(name, value)
		for i, proc in enumerate(aggr._procs.values()):
			self.assertEqual(getattr(proc, name), values[i])
			self.assertNotEqual(proc.id, aggr.id)

	def dataProvider_testSetattr(self):
		pGetAttr1 = Proc()
		pGetAttr2 = Proc()
		pGetAttr3 = Proc()
		aggr1 = Aggr(pGetAttr1, pGetAttr2, pGetAttr3)
		aggr2 = Aggr(pGetAttr1, pGetAttr2, pGetAttr3)
		yield aggr1, 'forks', 10, [10] * 3
		aggr2.delegate('forks', 'pGetAttr2')
		yield aggr2, 'forks', 10, [1, 10, 1]

	def testSetGetAttr(self):
		pGetAttr1 = Proc()
		pGetAttr2 = Proc()
		pGetAttr3 = Proc()
		pGetAttr4 = Proc()
		pGetAttr5 = Proc()
		pGetAttr1.args.params = Box(inopts = Box())
		pGetAttr2.args.params = Box(inopts = Box())
		pGetAttr3.args.params = Box(inopts = Box())
		pGetAttr4.args.params = Box(inopts = Box())
		pGetAttr5.args.params = Box(inopts = Box())
		aggr = Aggr(pGetAttr1, pGetAttr2, pGetAttr3, pGetAttr4, pGetAttr5, depends = False)
		# nothing delegated yet
		self.assertDictEqual({
			'input'  : [],
			'depends': [],
			'exdir'  : [],
			'exhow'  : [],
			'expart' : [],
			'exow'   : []
		}, aggr._delegates)
		# but when starts and ends changed
		aggr.starts = [aggr.pGetAttr1, aggr.pGetAttr2]
		aggr.ends   = [aggr.pGetAttr5]
		self.assertDictEqual({
			'input'  : [aggr.pGetAttr1, aggr.pGetAttr2],
			'depends': [aggr.pGetAttr1, aggr.pGetAttr2],
			'exdir'  : [aggr.pGetAttr5],
			'exhow'  : [aggr.pGetAttr5],
			'expart' : [aggr.pGetAttr5],
			'exow'   : [aggr.pGetAttr5]
		}, aggr._delegates)

		# delegate a short attribute
		aggr.delegate('forks', [aggr.pGetAttr2, aggr.pGetAttr3])
		aggr.forks = 10
		# only 2, 3 changed
		self.assertListEqual([p.forks for p in aggr._procs.values()], [1, 10, 10, 1, 1])

		# change the specific procs
		aggr.forks['pGetAttr2', 'pGetAttr4'] = 5
		self.assertListEqual([p.forks for p in aggr._procs.values()], [1, 5, 10, 5, 1])

		# fix an attribute
		aggr.pGetAttr3.runner = 'dry'
		aggr.runner = 'sge'
		self.assertListEqual([p.config['runner'] for p in aggr._procs.values()], ['sge', 'sge', 'dry', 'sge', 'sge'])

		# set input
		self.assertRaises(AggrAttributeError, setattr, aggr, 'input', 1)
		aggr.input = [1,2]
		self.assertListEqual([p.config['input'] for p in aggr._procs.values()], [1, 2, '', '', ''])
		# reverse it
		aggr.input = ['', '']
		aggr.input2 = [1,2]
		self.assertListEqual([p.config['input'] for p in aggr._procs.values()], [[1,2], [1,2], '', '', ''])
		aggr.input[3] = 'i3'
		self.assertListEqual([p.config['input'] for p in aggr._procs.values()], [[1,2], [1,2], '', 'i3', ''])
		# not suppose to do this
		# aggr.input2[2] = ['a', 'b']
		#self.assertListEqual([p.config['input'] for p in aggr._procs.values()], [[1,2], [1,2], ['a', 'b'], 'i3', ''])

		# similar for depends
		self.assertRaises(AggrAttributeError, setattr, aggr, 'depends', 1)
		aggr.depends = [pGetAttr1, pGetAttr2]
		self.assertListEqual([p.depends for p in aggr._procs.values()], [[pGetAttr1], [pGetAttr2], [], [], []])
		# reverse it
		aggr.depends = [[], []]
		aggr.depends2 = [pGetAttr1, pGetAttr2]
		self.assertListEqual([p.depends for p in aggr._procs.values()], [[pGetAttr1, pGetAttr2], [pGetAttr1, pGetAttr2], [], [], []])

		# set attributes of certain processes
		aggr.args[0].params = Box(inopts = Box(a = 1))
		self.assertListEqual(
			[p.args for p in aggr._procs.values()], 
			[
				Box(params = Box(inopts = Box(a = 1))),
				Box(params = Box(inopts = Box())),
				Box(params = Box(inopts = Box())),
				Box(params = Box(inopts = Box())),
				Box(params = Box(inopts = Box())),
			])

		aggr.args[:2].params = Box(inopts = Box(b = 1))
		self.assertListEqual(
			[p.args for p in aggr._procs.values()], 
			[
				Box(params = Box(inopts = Box(b = 1))),
				Box(params = Box(inopts = Box(b = 1))),
				Box(params = Box(inopts = Box())),
				Box(params = Box(inopts = Box())),
				Box(params = Box(inopts = Box())),
			])

		aggr.args[1,2].params = Box(inopts = Box(c = 1))
		self.assertListEqual(
			[p.args for p in aggr._procs.values()], 
			[
				Box(params = Box(inopts = Box(b = 1))),
				Box(params = Box(inopts = Box(c = 1))),
				Box(params = Box(inopts = Box(c = 1))),
				Box(params = Box(inopts = Box())),
				Box(params = Box(inopts = Box())),
			])
		
		# using proc ids
		aggr.args['pGetAttr1'].params = Box(inopts = Box(d = 1))
		self.assertListEqual(
			[p.args for p in aggr._procs.values()], 
			[
				Box(params = Box(inopts = Box(d = 1))),
				Box(params = Box(inopts = Box(c = 1))),
				Box(params = Box(inopts = Box(c = 1))),
				Box(params = Box(inopts = Box())),
				Box(params = Box(inopts = Box())),
			])
		
		aggr.args['pGetAttr1', 'pGetAttr3'].params = Box(inopts = Box(e = 1))
		self.assertListEqual(
			[p.args for p in aggr._procs.values()], 
			[
				Box(params = Box(inopts = Box(e = 1))),
				Box(params = Box(inopts = Box(c = 1))),
				Box(params = Box(inopts = Box(e = 1))),
				Box(params = Box(inopts = Box())),
				Box(params = Box(inopts = Box())),
			])

		aggr.args['pGetAttr1, pGetAttr3'].params = Box(inopts = Box(f = 1))
		self.assertListEqual(
			[p.args for p in aggr._procs.values()], 
			[
				Box(params = Box(inopts = Box(f = 1))),
				Box(params = Box(inopts = Box(c = 1))),
				Box(params = Box(inopts = Box(f = 1))),
				Box(params = Box(inopts = Box())),
				Box(params = Box(inopts = Box())),
			])

		aggr.args['starts'].params = Box(inopts = Box(g = 1))
		self.assertListEqual(
			[p.args for p in aggr._procs.values()], 
			[
				Box(params = Box(inopts = Box(g = 1))),
				Box(params = Box(inopts = Box(g = 1))),
				Box(params = Box(inopts = Box(f = 1))),
				Box(params = Box(inopts = Box())),
				Box(params = Box(inopts = Box())),
			])

		aggr.args['ends'].params = Box(inopts = Box(h = 1))
		self.assertListEqual(
			[p.args for p in aggr._procs.values()], 
			[
				Box(params = Box(inopts = Box(g = 1))),
				Box(params = Box(inopts = Box(g = 1))),
				Box(params = Box(inopts = Box(f = 1))),
				Box(params = Box(inopts = Box())),
				Box(params = Box(inopts = Box(h = 1))),
			])

		aggr.delegate('args.params.inopts', 'pGetAttr3')
		aggr.args['params'].inopts = Box(n = 1)
		self.assertListEqual(
			[p.args for p in aggr._procs.values()], 
			[
				Box(params = Box(inopts = Box(g = 1))),
				Box(params = Box(inopts = Box(g = 1))),
				Box(params = Box(inopts = Box(n = 1))),
				Box(params = Box(inopts = Box())),
				Box(params = Box(inopts = Box(h = 1))),
			])

		aggr.args.params['inopts'] = Box(m = 1)
		self.assertListEqual(
			[p.args for p in aggr._procs.values()], 
			[
				Box(params = Box(inopts = Box(g = 1))),
				Box(params = Box(inopts = Box(g = 1))),
				Box(params = Box(inopts = Box(m = 1))),
				Box(params = Box(inopts = Box())),
				Box(params = Box(inopts = Box(h = 1))),
			])
			
		aggr.args[0].params.inopts = Box(z = 1)
		# remeber at line 453, inopts refers to the same Box() object, so both pGetAttr1 and 3 will change
		self.assertListEqual(
			[p.args for p in aggr._procs.values()], 
			[
				Box(params = Box(inopts = Box(z = 1))),
				Box(params = Box(inopts = Box(z = 1))), # <-- not g
				Box(params = Box(inopts = Box(m = 1))),
				Box(params = Box(inopts = Box())),
				Box(params = Box(inopts = Box(h = 1))),
			])

		aggr.args.params.inopts.cnames = True
		self.assertListEqual(
			[p.args.params.inopts for p in aggr._procs.values()], 
			[
				Box(z = 1),
				Box(z = 1),
				Box(m = 1, cnames = True),
				Box(),
				Box(h = 1),
			])
		
		# something undelegated
		aggr.tag = 'abc'
		self.assertListEqual(
			[p.tag for p in aggr._procs.values()],
			['abc'] * 5
		)

		del aggr._delegates['args.params.inopts']
		aggr.delegate('args', 'pGetAttr4')
		aggr.args.params.inopts.rnames = True
		self.assertListEqual(
			[p.args.params.inopts for p in aggr._procs.values()], 
			[
				Box(z = 1),
				Box(z = 1),
				Box(m = 1, cnames = True),
				Box(rnames = True),
				Box(h = 1),
			])
		
	def testConfig(self, aggr, name, on, off):
		aggr.config(name, on, off)
		self.assertTrue(name in aggr._config)
		self.assertIs(aggr._config[name]['on'], on)
		self.assertIs(aggr._config[name]['off'], off)

	def dataProvider_testConfig(self):
		aggr = Aggr()
		yield aggr, 'qc', lambda a:True, lambda a:False

	def testOnOff(self, aggr, name, on, off, ons, offs):
		aggr.config(name, on, off)
		aggr.on(name)
		self.assertTrue(ons(aggr))
		aggr.off(name)
		self.assertTrue(offs(aggr))

	def dataProvider_testOnOff(self):
		aggr = Aggr()
		def on(a):
			a.starts = [1]
		def off(a):
			a.starts = []
		def ons(a):
			return a.starts == [1]
		def offs(a):
			return a.starts == []
		yield aggr, 'qc', on, off, ons, offs
			
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
		yield aggr, aggr.pCopy1.tag, False, None, False, False, AggrCopyError, 'Cannot copy process with same id and tag: \'pCopy1.%s\'' % aggr.pCopy1.tag
		
		aggr1 = Aggr(pCopy1, pCopy2, pCopy3, depends = False)
		aggr1.starts = [aggr1.pCopy1, aggr1.pCopy2]
		aggr1.pCopy3.depends = aggr1.starts
		aggr1.config('qc', lambda a: True, lambda a: False)
		yield aggr1, None, True, None, True, True


			
	def testCopy(self, aggr, tag, deps, id, delegates = False, configs = False, exception = None, msg = None):
		self.maxDiff = None
		if exception:
			self.assertRaisesRegex(exception, msg, aggr.copy, tag, deps, id, delegates, configs)
		else:
			newaggr = aggr.copy(tag, deps, id, delegates, configs)
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

			# delegates
			#if delegates:
			self.assertNotEqual(newaggr._delegates, aggr._delegates)
			self.assertDictEqual({
				k: [aggr._procs[p.id] for p in v]
				for k, v in newaggr._delegates.items()
			}, aggr._delegates)

			# configs
			#if configs:
			self.assertDictEqual(newaggr._config, aggr._config)

	def testAddStart(self, aggr, args, starts):
		aggr.addStart(*args)
		self.assertListEqual(aggr.starts, starts)

	def dataProvider_testAddStart(self):
		p1 = Proc()
		p2 = Proc()
		p3 = Proc()
		aggr = Aggr(p1, p2, p3, depends = False)
		yield aggr, [aggr.p1], [aggr.p1]
		yield aggr, [aggr.p2], [aggr.p1, aggr.p2]
		yield aggr, ['p1', 'p2'], [aggr.p1, aggr.p2]
		yield aggr, ['p1, p2'], [aggr.p1, aggr.p2]

	def testDelStart(self, aggr, args, starts):
		aggr.delStart(*args)
		self.assertListEqual(aggr.starts, starts)

	def dataProvider_testDelStart(self):
		p1 = Proc()
		p2 = Proc()
		p3 = Proc()
		aggr = Aggr(p1, p2, p3, depends = False)
		aggr.starts = 'p1, p2'
		yield aggr, [aggr.p1], [aggr.p2]
		yield aggr, ['p1, p2'], []
	
	def testAddEnd(self, aggr, args, ends):
		aggr.addEnd(*args)
		self.assertListEqual(aggr.ends, ends)

	def dataProvider_testAddEnd(self):
		p1 = Proc()
		p2 = Proc()
		p3 = Proc()
		aggr = Aggr(p1, p2, p3, depends = False)
		yield aggr, [aggr.p1], [aggr.p1]
		yield aggr, [aggr.p2], [aggr.p1, aggr.p2]
		yield aggr, ['p1', 'p2'], [aggr.p1, aggr.p2]
		yield aggr, ['p1, p2'], [aggr.p1, aggr.p2]

	def testDelEnd(self, aggr, args, ends):
		aggr.delEnd(*args)
		self.assertListEqual(aggr.ends, ends)

	def dataProvider_testDelEnd(self):
		p1 = Proc()
		p2 = Proc()
		p3 = Proc()
		aggr = Aggr(p1, p2, p3, depends = False)
		aggr.ends = 'p1, p2'
		yield aggr, [aggr.p1], [aggr.p2]
		yield aggr, ['p1, p2'], []

	def dataProvider_testDepends(self):
		pDepends1 = Proc()
		pDepends2 = Proc()
		pDepends3 = Proc()
		pDepends4 = Proc()
		pDepends5 = Proc()
		aggr = Aggr(pDepends1, pDepends2, pDepends3)
		aggr.starts = 'pDepends1, pDepends2'
		aggr.depends = [aggr.pDepends2, aggr.pDepends3]
		yield aggr, [[aggr.pDepends2], [aggr.pDepends3]]

		aggr1 = Aggr(pDepends1, pDepends2, pDepends3, pDepends4, pDepends5)
		aggr1.starts = 'pDepends1'
		aggr1.depends['pDepends1'] = 'pDepends3, pDepends5'
		yield aggr1, [[aggr1.pDepends3, aggr1.pDepends5]]

	def testDepends(self, aggr, depends):
		for i, p in enumerate(aggr.starts):
			self.assertListEqual(p.depends, depends[i])
		
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