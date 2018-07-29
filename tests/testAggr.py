import testly

from collections import OrderedDict
from pyppl import Aggr, Proc, Box, utils, logger
from pyppl.aggr import _Proxy
from pyppl.exception import AggrAttributeError, AggrCopyError, AggrKeyError

class TestProxy(testly.TestCase):

	def testInit(self, aggr, procs, prefix, check):
		p = _Proxy(aggr, procs, prefix, check)
		self.assertEqual(p._prefix, prefix or [])
		self.assertListEqual(p._procs, procs)
		self.assertIs(p._aggr, aggr)
		self.assertEqual(p._check, check)

	def dataProvider_testInit(self):
		pInita = Proc()
		pInitb = Proc()
		pInitc = Proc()
		aggr = Aggr(pInita, pInitb, pInitc)
		yield aggr, [pInita, pInitb, pInitc], None, True
		yield aggr, [pInita, pInitb, pInitc], 'args', False

	def testGetattr(self, proxy, name):
		p = getattr(proxy, name)
		self.assertEqual(p._prefix, proxy._prefix + [name])
		self.assertListEqual(p._procs, proxy._procs)
		self.assertIs(p._aggr, proxy._aggr)
		self.assertEqual(p._check, proxy._check)
	
	def dataProvider_testGetattr(self):
		pGetattra = Proc()
		pGetattrb = Proc()
		pGetattrc = Proc()
		aggr = Aggr(pGetattra, pGetattrb, pGetattrc)
		proxy = _Proxy(aggr)
		yield proxy, ''
		yield proxy, 'args'

	def testSetattr(self, proxy, name, value, outvalues):
		setattr(proxy, name, value)
		if name.endswith('2'): 
			name = name[:-1]
		
		values = []
		prefix = proxy._prefix + [name]
		for proc in proxy._procs:
			val = proc
			for p in prefix:
				val = getattr(val, p)
			values.append(val)
		self.assertListEqual(values, outvalues)
		
	def dataProvider_testSetattr(self):
		pSetattra = Proc()
		pSetattra.args.a = Box()
		pSetattrb = Proc()
		pSetattrb.args.a = Box()
		pSetattrc = Proc()
		pSetattrc.args.a = Box(b=1)
		pSetattrd = Proc()
		pSetattre = Proc()
		aggr = Aggr(pSetattra, pSetattrb, pSetattrc, pSetattrd, pSetattre)
		aggr.delegate('forks', 'pSetattrb')
		aggr.delegate('tag', 'ends')
		proxy = _Proxy(aggr, check = True)
		yield proxy, 'forks', 10, [1, 10, 1, 1, 1]
		yield proxy, 'tag', 't', [aggr.pSetattra.tag, aggr.pSetattra.tag, aggr.pSetattra.tag, aggr.pSetattra.tag, 't']
		# depends and input
		aggr.starts = 'pSetattra, pSetattrb'
		yield proxy, 'depends', ['pSetattrc', 'pSetattrd'], [[aggr.pSetattrc], [aggr.pSetattrd], [aggr.pSetattrb], [aggr.pSetattrc], [aggr.pSetattrd]]
		yield proxy, 'depends2', ['pSetattrc', 'pSetattrd'], [[aggr.pSetattrc, aggr.pSetattrd], [aggr.pSetattrc, aggr.pSetattrd], [aggr.pSetattrb], [aggr.pSetattrc], [aggr.pSetattrd]]

		aggr1 = Aggr(pSetattra, pSetattrb, pSetattrc)
		aggr1.delegate('args.a.b', 'pSetattra, pSetattrb')
		aggr1.delegate('args.a', 'pSetattrb')
		proxy1 = _Proxy(aggr1, prefix = ['args', 'a'], check = True)
		yield proxy1, 'b', 3, [3, 3, 1]

'''			
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
'''

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

	def testDelegate(self, aggr, attrs, procs, outdelegates):
		aggr.delegate(attrs, procs)
		for attr in Aggr.ATTR_STARTS:
			outdelegates[attr] = ['starts']
		for attr in Aggr.ATTR_ENDS:
			outdelegates[attr] = ['ends']
		self.assertDictEqual(aggr._delegates, outdelegates)
	
	def dataProvider_testDelegate(self):
		pGetAttr1 = Proc()
		pGetAttr2 = Proc()
		pGetAttr3 = Proc()
		aggr1 = Aggr(pGetAttr1, pGetAttr2, pGetAttr3)
		aggr2 = Aggr(pGetAttr1, pGetAttr2, pGetAttr3)
		aggr3 = Aggr(pGetAttr1, pGetAttr2, pGetAttr3)
		aggr4 = Aggr(pGetAttr1, pGetAttr2, pGetAttr3)
		yield aggr1, 'aggrs.a', 'pGetAttr1', {'aggrs.a': [aggr1.pGetAttr1]}
		yield aggr2, 'aggrs.b, aggrs.c', 'pGetAttr1,pGetAttr2', {'aggrs.b': [aggr2.pGetAttr1, aggr2.pGetAttr2], 'aggrs.c': [aggr2.pGetAttr1, aggr2.pGetAttr2]}
		yield aggr3, 'aggrs.b, aggrs.c', 'starts', {'aggrs.b': ['starts'], 'aggrs.c': ['starts']}
		yield aggr4, 'aggrs.b, aggrs.c', 'ends', {'aggrs.b': ['ends'], 'aggrs.c': ['ends']}

	def testSelect(self, p, anything, forceList, out):
		self.assertEqual(p._select(anything, forceList), out)

	def dataProvider_testSelect(self):
		pSelecta = Proc()
		pSelectb = Proc()
		pSelectc = Proc()
		aggr = Aggr(pSelecta, pSelectb, pSelectc)
		yield aggr, 0, False, aggr.pSelecta
		yield aggr, 0, True, [aggr.pSelecta]
		yield aggr, 1, False, aggr.pSelectb
		yield aggr, 'pSelectb', False, aggr.pSelectb
		yield aggr, 'pSelectb', True, [aggr.pSelectb]
		yield aggr, aggr.pSelectb, False, aggr.pSelectb
		yield aggr, aggr.pSelectb, True, [aggr.pSelectb]
		yield aggr, slice(0,2), True, [aggr.pSelecta, aggr.pSelectb]
		yield aggr, (1,2), True, [aggr.pSelectb, aggr.pSelectc]
		yield aggr, 'starts', True, [aggr.pSelecta]
		yield aggr, 'ends', True, [aggr.pSelectc]
		yield aggr, 'pSelecta, pSelectc', True, [aggr.pSelecta, aggr.pSelectc]

	def testGetitem(self, aggr, key, type):
		self.assertIsInstance(aggr[key], type)
	
	def dataProvider_testGetitem(self):
		pSelecta = Proc()
		pSelectb = Proc()
		pSelectc = Proc()
		aggr = Aggr(pSelecta, pSelectb, pSelectc)
		yield aggr, 0, Proc
		yield aggr, 'pSelecta', Proc
		yield aggr, pSelecta, Proc
		yield aggr, slice(0,2), _Proxy
		yield aggr, (1,2), _Proxy
		yield aggr, 'starts', _Proxy
		yield aggr, 'ends', _Proxy
		yield aggr, 'pSelecta, pSelectc', _Proxy

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

	def testSetattr(self, aggr, name, value, outvalues):
		setattr(aggr, name, value)
		if name.endswith('2'): 
			name = name[:-1]
		
		values = []
		for proc in aggr._procs.values():
			val = getattr(proc, name)
			values.append(val)
		self.assertListEqual(values, outvalues)
		
	def dataProvider_testSetattr(self):
		pSetattra = Proc()
		pSetattra.args.a = Box()
		pSetattrb = Proc()
		pSetattrb.args.a = Box()
		pSetattrc = Proc()
		pSetattrc.args.a = Box(b=1)
		pSetattrd = Proc()
		pSetattre = Proc()
		aggr = Aggr(pSetattra, pSetattrb, pSetattrc, pSetattrd, pSetattre)
		aggr.delegate('forks', 'pSetattrb')
		aggr.delegate('tag', 'ends')
		yield aggr, 'forks', 10, [1, 10, 1, 1, 1]
		yield aggr, 'tag', 't', [aggr.pSetattra.tag, aggr.pSetattra.tag, aggr.pSetattra.tag, aggr.pSetattra.tag, 't']
		# depends and input
		aggr.starts = 'pSetattra, pSetattrb'
		yield aggr, 'depends', ['pSetattrc', 'pSetattrd'], [[aggr.pSetattrc], [aggr.pSetattrd], [aggr.pSetattrb], [aggr.pSetattrc], [aggr.pSetattrd]]
		yield aggr, 'depends2', ['pSetattrc', 'pSetattrd'], [[aggr.pSetattrc, aggr.pSetattrd], [aggr.pSetattrc, aggr.pSetattrd], [aggr.pSetattrb], [aggr.pSetattrc], [aggr.pSetattrd]]

		aggr1 = Aggr(pSetattra, pSetattrb, pSetattrc)
		aggr1.delegate('errntry', 'pSetattra, pSetattrb')
		aggr1.delegate('args.a', 'pSetattrb')
		yield aggr1, 'errntry', 8, [8, 8, 3]

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
			'input'  : ['starts'],
			'depends': ['starts'],
			'exdir'  : ['ends'],
			'exhow'  : ['ends'],
			'expart' : ['ends'],
			'exow'   : ['ends']
		}, aggr._delegates)
		# but when starts and ends changed
		aggr.starts = [aggr.pGetAttr1, aggr.pGetAttr2]
		aggr.ends   = [aggr.pGetAttr5]
		self.assertDictEqual({
			'input'  : ['starts'],
			'depends': ['starts'],
			'exdir'  : ['ends'],
			'exhow'  : ['ends'],
			'expart' : ['ends'],
			'exow'   : ['ends']
		}, aggr._delegates)

		# delegate a short attribute
		aggr.delegate('forks', [aggr.pGetAttr2, aggr.pGetAttr3])
		aggr.forks = 10
		# only 2, 3 changed
		self.assertListEqual([p.forks for p in aggr._procs.values()], [1, 10, 10, 1, 1])

		# change the specific procs
		aggr['pGetAttr2', 'pGetAttr4'].forks = 5
		self.assertListEqual([p.forks for p in aggr._procs.values()], [1, 10, 10, 5, 1])

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
		aggr[3].input = 'i3'
		self.assertListEqual([p.config['input'] for p in aggr._procs.values()], [[1,2], [1,2], '', 'i3', ''])
		# not suppose to do this
		# aggr.input2[2] = ['a', 'b']
		#self.assertListEqual([p.config['input'] for p in aggr._procs.values()], [[1,2], [1,2], ['a', 'b'], 'i3', ''])

		# similar for depends
		#self.assertRaises(AggrAttributeError, setattr, aggr, 'depends', 1)
		aggr.depends = [pGetAttr1, pGetAttr2]
		self.assertListEqual([p.depends for p in aggr._procs.values()], [[pGetAttr1], [pGetAttr2], [], [], []])
		# reverse it
		aggr.depends = [[], []]
		aggr.depends2 = [pGetAttr1, pGetAttr2]
		self.assertListEqual([p.depends for p in aggr._procs.values()], [[pGetAttr1, pGetAttr2], [pGetAttr1, pGetAttr2], [], [], []])

		# set attributes of certain processes
		aggr[0].args.params = Box(inopts = Box(a = 1))
		self.assertListEqual(
			[p.args for p in aggr._procs.values()], 
			[
				Box(params = Box(inopts = Box(a = 1))),
				Box(params = Box(inopts = Box())),
				Box(params = Box(inopts = Box())),
				Box(params = Box(inopts = Box())),
				Box(params = Box(inopts = Box())),
			])

		aggr[:2].args.params = Box(inopts = Box(b = 1))
		self.assertListEqual(
			[p.args for p in aggr._procs.values()], 
			[
				Box(params = Box(inopts = Box(b = 1))),
				Box(params = Box(inopts = Box(b = 1))),
				Box(params = Box(inopts = Box())),
				Box(params = Box(inopts = Box())),
				Box(params = Box(inopts = Box())),
			])

		aggr[1,2].args.params = Box(inopts = Box(c = 1))
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
		aggr['pGetAttr1'].args.params = Box(inopts = Box(d = 1))
		self.assertListEqual(
			[p.args for p in aggr._procs.values()], 
			[
				Box(params = Box(inopts = Box(d = 1))),
				Box(params = Box(inopts = Box(c = 1))),
				Box(params = Box(inopts = Box(c = 1))),
				Box(params = Box(inopts = Box())),
				Box(params = Box(inopts = Box())),
			])
		
		aggr['pGetAttr1', 'pGetAttr3'].args.params = Box(inopts = Box(e = 1))
		self.assertListEqual(
			[p.args for p in aggr._procs.values()], 
			[
				Box(params = Box(inopts = Box(e = 1))),
				Box(params = Box(inopts = Box(c = 1))),
				Box(params = Box(inopts = Box(e = 1))),
				Box(params = Box(inopts = Box())),
				Box(params = Box(inopts = Box())),
			])

		aggr['pGetAttr1, pGetAttr3'].args.params = Box(inopts = Box(f = 1))
		self.assertListEqual(
			[p.args for p in aggr._procs.values()], 
			[
				Box(params = Box(inopts = Box(f = 1))),
				Box(params = Box(inopts = Box(c = 1))),
				Box(params = Box(inopts = Box(f = 1))),
				Box(params = Box(inopts = Box())),
				Box(params = Box(inopts = Box())),
			])

		aggr['starts'].args.params = Box(inopts = Box(g = 1))
		self.assertListEqual(
			[p.args for p in aggr._procs.values()], 
			[
				Box(params = Box(inopts = Box(g = 1))),
				Box(params = Box(inopts = Box(g = 1))),
				Box(params = Box(inopts = Box(f = 1))),
				Box(params = Box(inopts = Box())),
				Box(params = Box(inopts = Box())),
			])

		aggr['ends'].args.params = Box(inopts = Box(h = 1))
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
			
		aggr[0].args.params.inopts = Box(z = 1)
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
		
	def testModuleFunc(self, aggr, name, on, off):
		aggr.moduleFunc(name, on, off)
		self.assertTrue(name in aggr._modules)
		self.assertIs(aggr._modules[name]['on'], on)
		self.assertIs(aggr._modules[name]['off'], off)
		self.assertIs(aggr._modules[name]['status'], 'off')

	def dataProvider_testModuleFunc(self):
		aggr = Aggr()
		yield aggr, 'qc', lambda a:True, lambda a:False

	def testOnOff(self, aggr, name, on, off, ons, offs):
		aggr.moduleFunc(name, on, off)
		aggr.on(name)
		self.assertTrue(ons(aggr))
		aggr.off(name)
		self.assertTrue(offs(aggr))

	def dataProvider_testOnOff(self):

		aggr = Aggr()
		def on(a):
			a.id = 'aggr'
		def off(a):
			a.id = None
		def ons(a):
			return a.id == 'aggr' and a._modules['qc']['status'] == 'on'
		def offs(a):
			return a.id == None and a._modules['qc']['status'] == 'off'
		yield aggr, 'qc', on, off, ons, offs
			

	
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
		aggr1.module('qc', lambda a: True, lambda a: False)
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
			self.assertEqual(newaggr._delegates, aggr._delegates)
			# self.assertDictEqual({
			# 	k: [aggr._procs[p.id] for p in v]
			# 	for k, v in newaggr._delegates.items()
			# }, aggr._delegates)

			# configs
			#if configs:
			self.assertDictEqual(newaggr._modules, aggr._modules)

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
		aggr1[:1].depends = [['pDepends3', 'pDepends5']]
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

	def testModule(self):
		pModule1 = Proc()
		pModule2 = Proc()
		pModule3 = Proc()
		pModule4 = Proc()
		pModule5 = Proc()
		pModule6 = Proc()
		aggr = Aggr(pModule1, pModule2, pModule3, pModule4, pModule5, pModule6, depends = False)
		aggr.module('m1', starts = 'pModule1, pModule2', ends = 'pModule4', depends = {
			'pModule3': 'starts',
			'pModule4': 'pModule3'
		}, ends_shared = {
			'pModule4': 'm2'
		}, depends_shared = {
			'pModule4': 'm2'
		})
		aggr.module('m2', starts = 'pModule3', ends = 'pModule4, pModule6', depends = {
			'pModule4': 'pModule3'
		}, ends_shared = {
			'pModule4': 'm1'
		}, depends_shared = {
			'pModule4': 'm1'
		})
		self.assertEqual(aggr.starts, [])
		self.assertEqual(aggr.ends, [])
		self.assertEqual(aggr.pModule3.depends, [])
		self.assertEqual(aggr.pModule4.depends, [])
		aggr.on('m1')
		self.assertEqual(aggr.starts, [aggr.pModule1, aggr.pModule2])
		self.assertEqual(aggr.ends, [aggr.pModule4])
		self.assertEqual(aggr.pModule3.depends, [aggr.pModule1, aggr.pModule2])
		self.assertEqual(aggr.pModule4.depends, [aggr.pModule3])
		aggr.off('m1')
		self.assertEqual(aggr.starts, [])
		self.assertEqual(aggr.ends, [])
		self.assertEqual(aggr.pModule3.depends, [])
		self.assertEqual(aggr.pModule4.depends, [])
		aggr.on('m2')
		self.assertEqual(aggr.starts, [aggr.pModule3])
		self.assertEqual(aggr.ends, [aggr.pModule4, aggr.pModule6])
		self.assertEqual(aggr.pModule4.depends, [aggr.pModule3])
		aggr.off('m2')
		self.assertEqual(aggr.starts, [])
		self.assertEqual(aggr.ends, [])
		self.assertEqual(aggr.pModule3.depends, [])
		aggr.on('m1, m2')
		aggr.off('m2')
		self.assertEqual(aggr.starts, [aggr.pModule1, aggr.pModule2])
		self.assertEqual(aggr.ends, [aggr.pModule4])
		self.assertEqual(aggr.pModule3.depends, [aggr.pModule1, aggr.pModule2])
		self.assertEqual(aggr.pModule4.depends, [aggr.pModule3])
		


if __name__ == '__main__':
	testly.main(verbosity=2)