import testly

from collections import OrderedDict
from pyppl import Aggr, Proc, Box, utils, logger
from pyppl.aggr import DotProxy
from pyppl.exception import AggrAttributeError, AggrCopyError

class TestDotProxy(testly.TestCase):
	
	def dataProvider_testInit(self):
		aggr = Aggr()
		yield aggr, ''
		yield aggr, 'prefix1.prefix2'
	
	def testInit(self, aggr, prefix):
		dp = DotProxy(aggr, prefix)
		self.assertIsInstance(dp, DotProxy)
		self.assertIsInstance(dp._aggr, Aggr)
		self.assertIsInstance(aggr, Aggr)
		self.assertIs(dp._aggr, aggr)
		self.assertEqual(dp._prefix, prefix)
	
	def dataProvider_testGetAttr(self):
		aggr = Aggr()
		yield DotProxy(aggr, ''), 'a1'
	
	def testGetAttr(self, dp, name):
		dp1 = getattr(dp, name)
		self.assertIsInstance(dp1, DotProxy)
		self.assertIsInstance(dp._aggr, Aggr)
		self.assertIsInstance(dp1._aggr, Aggr)
		self.assertIs(dp1._aggr, dp._aggr)
		self.assertEqual(dp1._prefix, (dp._prefix if not dp._prefix else dp._prefix + '.') + name)
		
		dp2 = dp[name]
		self.assertIsInstance(dp2, DotProxy)
		self.assertIsInstance(dp2._aggr, Aggr)
		self.assertIs(dp2._aggr, dp._aggr)
		self.assertEqual(dp2._prefix, (dp._prefix if not dp._prefix else dp._prefix + '.') + name)
	
	def dataProvider_testIsDelegated(self):
		yield 'a.b', {'c': (lambda a: [], 'c')}, False
		yield 'a.bb', {'a.b': (lambda a: [], 'a.b')}, False
		yield 'args', {'args': (lambda a: [], 'args')}, ([], ['args'])
		yield 'args.a', {'args.a': (lambda a: [], 'args.a')}, ([], ['args', 'a'])
		yield 'a.b.c.d', {'a.b': (lambda a: [], 'x.y')}, ([], ['x', 'y', 'c', 'd'])
	
	def testIsDelegated(self, prefix, delegates, ret):
		r = DotProxy._isDelegated(Aggr(), prefix, delegates)
		if isinstance(r, bool):
			self.assertEqual(r, ret)
		else:
			self.assertTupleEqual(r, ret)
		
	def dataProvider_testSetAttr(self):
		pSetAttr1 = Proc()
		pSetAttr2 = Proc()
		pSetAttr3 = Proc()
		aggr = Aggr(pSetAttr1, pSetAttr2, pSetAttr3)
		dp = DotProxy(aggr, '')
		yield aggr, 'a', None, None, aggr, AggrAttributeError, 'Attribute is not delegated: \'a\''
		
		pSetAttr3.args.b = Box(c = 3)
		aggr1 = Aggr(pSetAttr1, pSetAttr2, pSetAttr3)
		aggr1.delegate('args', 'ends')
		dp1 = DotProxy(aggr1, 'args')
		yield dp1, 'a', 1, lambda: aggr1.pSetAttr3.args.a, aggr1
		
		dp2 = DotProxy(aggr1, 'args.b')
		yield dp2, 'c', 2, lambda: aggr1.pSetAttr3.args.b.c, aggr1
		
	def testSetAttr(self, dp, name, value, expval, aggr, exception = None, msg = None):
		if exception:
			self.assertRaisesRegex(exception, msg, setattr, dp, name, value)
		else:
			setattr(dp, name, value)
			self.assertEqual(expval(), value)
			
			dp[name] = value
			self.assertEqual(expval(), value)

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
				# delegates
				self.assertDictContains({
					'depends2': ([list(aggr._procs.values())[0]], 'depends2'),
					'depends' : ([list(aggr._procs.values())[0]], 'depends'),
					'input' :   ([list(aggr._procs.values())[0]], 'input'),
					'exdir' :   ([list(aggr._procs.values())[-1]], 'exdir'),
					'exhow' :   ([list(aggr._procs.values())[-1]], 'exhow'),
					'exow' :    ([list(aggr._procs.values())[-1]], 'exow'),
					'expart' :  ([list(aggr._procs.values())[-1]], 'expart'),
				}, {
					k: (v[0](aggr), v[1]) for k, v in aggr._delegates.items()
				})
			else:
				self.assertListEqual(aggr.starts, [])
				self.assertListEqual(aggr.ends  , [])
				for i, proc in enumerate(aggr._procs.values()):
					if i == 0: continue
					self.assertListEqual(proc.depends, [])
				# delegates
				self.assertDictContains({
					'depends2': ([], 'depends2'),
					'depends' : ([], 'depends'),
					'input' :   ([], 'input'),
					'exdir' :   ([], 'exdir'),
					'exhow' :   ([], 'exhow'),
					'exow' :    ([], 'exow'),
					'expart' :  ([], 'expart'),
				}, {
					k: (v[0](aggr), v[1]) for k, v in aggr._delegates.items()
				})
	
	def dataProvider_testDelegate(self):
		pDelegate1 = Proc()
		pDelegate2 = Proc()
		pDelegate3 = Proc()
		aggr = Aggr(pDelegate1, pDelegate2, pDelegate3)
		yield aggr, 'starts', None, None, None, AggrAttributeError, 'Cannot delegate Proc attribute to an existing Aggr attribute: \'starts\''
		yield aggr, 'pDelegate1', None, None, None, AggrAttributeError, 'Cannot delegate Proc attribute to an existing Aggr attribute: \'pDelegate1\''
		yield aggr, 'args', 'starts', None, {
			'args': ([aggr.pDelegate1], 'args')
		}
		yield aggr, 'args', 'ends', None, {
			'args': ([aggr.pDelegate3], 'args')
		}
		yield aggr, 'args', 'both', None, {
			'args': ([aggr.pDelegate1, aggr.pDelegate3], 'args')
		}
		yield aggr, 'args', 'neither', None, {
			'args': ([aggr.pDelegate2], 'args')
		}
		yield aggr, 'args', 'pDelegate2', None, {
			'args': ([aggr.pDelegate2], 'args')
		}
		yield aggr, 'args.a', None, 'a', {
			'args.a': ([aggr.pDelegate1, aggr.pDelegate2, aggr.pDelegate3], 'a')
		}
		
				
	def testDelegate(self, aggr, attr, procs, pattr, delegates, exception = None, msg = None):
		pattr = pattr or attr
		if exception:
			self.assertRaisesRegex(exception, msg, aggr.delegate, attr, procs, pattr)
		else:
			aggr.delegate(attr, procs, pattr)
			for k, v in delegates.items():
				self.assertListEqual(list(aggr._delegates[k][0](aggr)), v[0])
				self.assertEqual(aggr._delegates[k][1], v[1])
			
	def dataProvider_testGetAttr(self):
		pGetAttr1 = Proc()
		pGetAttr2 = Proc()
		pGetAttr3 = Proc()
		aggr = Aggr(pGetAttr1, pGetAttr2, pGetAttr3)
		yield aggr, '_props', aggr._props
		yield aggr, '_delegates', aggr._delegates
		yield aggr, '_procs', aggr._procs
		yield aggr, 'starts', aggr.starts
		yield aggr, 'ends', aggr.ends
		yield aggr, 'id', aggr.id
		yield aggr, 'pGetAttr1', aggr.pGetAttr1
		yield aggr, 'pGetAttr2', aggr.pGetAttr2
		yield aggr, 'pGetAttr3', aggr.pGetAttr3
		# not raised, because we have to allow:
		# aggr.delegate('args.a')
		# when we do aggr.args.a no error should be raised for aggr.args
		#yield aggr, 'a', None, False, AggrAttributeError, 'Attribute not delegated: \'a\''
		
		aggr1 = Aggr(pGetAttr1, pGetAttr2, pGetAttr3)
		aggr1.delegate('args', 'starts')
		yield aggr1, 'args', None, True
		
			
	def testGetAttr(self, aggr, name, value, isDotProxy = False, exception = None, msg = None):
		if exception:
			self.assertRaisesRegex(exception, msg, getattr, aggr, name)
		elif isDotProxy:
			self.assertIsInstance(getattr(aggr, name), DotProxy)
		else:
			self.assertEqual(getattr(aggr, name), value)
			
	def dataProvider_testSetAttr(self):
		pSetAttr1 = Proc()
		pSetAttr2 = Proc()
		pSetAttr3 = Proc()
		pSetAttr3.args.p = 1
		aggr = Aggr(pSetAttr1, pSetAttr2, pSetAttr3)
		aggr.delegate('args', 'ends')
		#aggr.delegate('envs.p1', 'pSetAttr3', 'envs.p')
		yield aggr, 'id', 'whatever', lambda: aggr.id
		yield aggr, 'starts', (aggr.pSetAttr1, aggr.pSetAttr2), lambda: tuple(aggr.starts)
		yield aggr, 'ends', aggr.pSetAttr3, lambda: aggr.ends[0]
		yield aggr, '_procs', None, None, AggrAttributeError, 'Built-in attribute is not allowed to be modified'
		yield aggr, 'a', None, None, AggrAttributeError, 'Attribute is not delegated: \'a\''
		yield aggr, 'args', {'a': 1}, lambda: aggr.pSetAttr3.args
		#yield aggr, 'envs.p1', 2, lambda: aggr.pSetAttr3.envs
			
	def testSetAttr(self, aggr, name, value, expval, exception = None, msg = None):
		if exception:
			self.assertRaisesRegex(exception, msg, setattr, aggr, name, value)
		else:
			setattr(aggr, name, value)
			self.assertEqual(expval(), value)
	
	def dataProvider_testChain(self):
		pChain1 = Proc()
		pChain2 = Proc()
		pChain3 = Proc()
		pChain1.args.params = Box(c = 1, d = 2)
		pChain3.args.b = 1
		aggr = Aggr(pChain1, pChain2, pChain3)
		aggr.delegate('a.p', 'starts', 'args.params')
		aggr.delegate('args.b1', 'pChain3', 'args.b')
		aggr.delegate('runner', 'pChain3')
		aggr.delegate('a', 'ends', 'args')
		aggr.delegate('f', 'neither', 'forks')
		def attr_setaggr():
			aggr.a.b = 2
		def attr_setaggr1():
			aggr.a.p.c = 2
		def attr_setaggr2():
			aggr.a.p['d'] = 3
		def attr_setaggr3():
			aggr.a.p.e = 4
		def attr_setaggr4():
			aggr.f = 10
		def attr_setaggr5():
			aggr.args.b1 = 11
		def attr_setaggr6():
			aggr.runner = 'sge'
		yield attr_setaggr, 2, lambda: aggr.pChain3.args.b
		yield attr_setaggr1, 2, lambda: aggr.pChain1.args.params.c
		yield attr_setaggr2, 3, lambda: aggr.pChain1.args.params.d
		yield attr_setaggr3, 4, lambda: 4
		yield attr_setaggr4, 10, lambda: aggr.pChain2.forks
		yield attr_setaggr5, 11, lambda: aggr.pChain3.args.b
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
		aggr.depends = pCopy4
		aggr.delegate('a', None, 'args')
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
			# delegates
			self.assertDictEqual(newaggr._delegates, aggr._delegates)
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
		for p in aggr.starts:
			self.assertListEqual(p.depends, depends)
		
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
		for i, p in enumerate(aggr.starts):
			self.assertListEqual(p.depends, [depends[i]])

	# issue #31
	def testIssue31(self):
		p = Proc()
		#p.runner = 'local'
		a = Aggr(p)
		a.runner = 'sge'
		with self.assertLogs(logger.getLogger()):
			a.p.run()
		self.assertEqual(a.p.runner, 'sge')
		
if __name__ == '__main__':
	testly.main(verbosity=2, failfast = True)