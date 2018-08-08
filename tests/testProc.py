import helpers, testly, json, sys
import copy as pycopy

from os import path, makedirs
from shutil import rmtree
from tempfile import gettempdir
from collections import OrderedDict
from multiprocessing import cpu_count
from pyppl import Proc, Box, Aggr, utils, ProcTree, Channel
from pyppl.exception import ProcTagError, ProcAttributeError, ProcTreeProcExists, ProcInputError, ProcOutputError, ProcScriptError, ProcRunCmdError
from pyppl.templates import TemplatePyPPL
if helpers.moduleInstalled('jinja2'):
	from pyppl.templates import TemplateJinja2
from pyppl.runners import RunnerLocal

__folder__ = path.realpath(path.dirname(__file__))

class TestProc(testly.TestCase):

	def setUpMeta(self):
		self.testdir = path.join(gettempdir(), 'PyPPL_unittest', 'TestProc')
		if path.exists(self.testdir):
			rmtree(self.testdir)
		makedirs(self.testdir)
	
	def dataProvider_testInit(self):
		yield 'notag', 'No description', None, {
			# 'brings': {},
			'channel': [],
			'depends': [],
			'echo': {},
			'expart': [],
			'expect': None,
			'input': {},
			'jobs': [],
			'lock': None,
			'logs': {},
			'ncjobids': [],
			'output': OrderedDict(),
			'origin': 'p',
			'procvars': {},
			'rc': [0],
			'runner': 'local',
			'script': None,
			'sets': [],
			'size': 0,
			'suffix': '',
			'template': None,
			'workdir': ''
		}, {
			'afterCmd': '',
			'aggr': None,
			'args': Box(),
			'beforeCmd': '',
			# 'brings': {},
			'cache': True,
			'callback': None,
			'callfront': None,
			'cclean': False,
			'depends': [],
			'desc': 'No description',
			'dirsig': True,
			'echo': False,
			'errhow': 'terminate',
			'errntry': 3,
			'exdir': '',
			'exhow': 'move',
			'exow': True,
			'expart': '',
			'expect': '',
			'forks': 1,
			'id': 'p',
			'infile': 'indir',
			'input': '',
			'lang': 'bash',
			'nthread': min(int(cpu_count() / 2), 16),
			'output': '',
			'ppldir': path.realpath('./workdir'),
			'rc': 0,
			'resume': '',
			'runner': 'local',
			'script': '',
			'tag': 'notag',
			'template': '',
			'tplenvs': Box(),
			'workdir': ''
		}
		
		yield 'atag', 'A different description', 'someId', {
			# 'brings': {},
			'channel': [],
			'depends': [],
			'echo': {},
			'expart': [],
			'expect': None,
			'input': {},
			'jobs': [],
			'logs': {},
			'ncjobids': [],
			'lock': None,
			'origin': 'someId',
			'output': OrderedDict(),
			'procvars': {},
			'rc': [0],
			'lock': None,
			'origin': 'someId',
			'runner': 'local',
			'script': None,
			'sets': [],
			'size': 0,
			'suffix': '',
			'template': None,
			'workdir': ''
		}, {
			'afterCmd': '',
			'aggr': None,
			'args': Box(),
			'beforeCmd': '',
			# 'brings': {},
			'cache': True,
			'callback': None,
			'callfront': None,
			'cclean': False,
			'depends': [],
			'desc': 'A different description',
			'dirsig': True,
			'echo': False,
			'errhow': 'terminate',
			'errntry': 3,
			'exdir': '',
			'exhow': 'move',
			'exow': True,
			'expart': '',
			'expect': '',
			'forks': 1,
			'id': 'someId',
			'infile': 'indir',
			'input': '',
			'lang': 'bash',
			'nthread': min(int(cpu_count() / 2), 16),
			'output': '',
			'ppldir': path.realpath('./workdir'),
			'rc': 0,
			'resume': '',
			'runner': 'local',
			'script': '',
			'tag': 'atag',
			'template': '',
			'tplenvs': Box(),
			'workdir': ''
		}
		
		yield 'tag no allowed', '', None, {}, {}, ProcTagError
		
	
	def testInit(self, tag, desc, id, props, config, exception = None):
		self.maxDiff = None
		if exception:
			self.assertRaises(exception, Proc, tag = tag, desc = desc, id = id)
		else:
			p = Proc(tag = tag, desc = desc, id = id)
			self.assertDictEqual(p.props, props)
			self.assertDictEqual(p.config, config)
			config2 = config.copy()
			del config2['tag']
			del config2['desc']
			del config2['id']
			p2 = Proc(tag, desc, id = config['id'], **config2)
			props['sets'] = list(sorted(['runner', 'echo', 'depends', 'expect', 'callfront', 'script', 'cache', 'nthread', 'beforeCmd', 'template', 'rc', 'input', 'forks', 'infile', 'cclean', 'workdir', 'resume', 'exhow', 'args', 'exow', 'dirsig', 'ppldir', 'errhow', 'lang', 'tplenvs', 'exdir', 'expart', 'afterCmd', 'callback', 'aggr', 'output', 'errntry']))
			p2.props['sets'] = list(sorted(p2.sets))
			self.assertDictEqual(p2.props, props)
			self.assertDictEqual(p2.config, config)

			
	def dataProvider_testGetAttr(self):
		pGetAttr = Proc()
		yield pGetAttr, '__keynotexists__', None, ProcAttributeError
		yield pGetAttr, 'envs', {}
		yield pGetAttr, 'script', None
		yield pGetAttr, 'suffix', ''
		
	def testGetAttr(self, p, name, val, exception = None):
		if exception:
			self.assertRaises(exception, p.__getattr__, name)
		else:
			v = p.__getattr__(name)
			if isinstance(val, list):
				self.assertListEqual(v, val)
			elif isinstance(val, dict):
				self.assertDictEqual(v, val)
			else:
				self.assertEqual(v, val)
				
	def dataProvider_testSetAttr(self):
		pSetAttr = Proc()
		pSetAttrDepends = Proc()
		pSetAttrAggr = Proc()
		aSetAttr = Aggr(pSetAttrAggr)
		aSetAttr.ends = [aSetAttr.pSetAttrAggr]
		yield pSetAttr, '__nosuchattr__', None, None, ProcAttributeError, 'Cannot set attribute for process'
		yield pSetAttr, 'profile', 'sge', 'local', None, None, ['WARNING', 'Attribute "profile" is deprecated']
		yield pSetAttr, 'envs', {'a': 1}
		yield pSetAttr, 'depends', pSetAttr, None, ProcAttributeError, 'Process depends on itself'
		yield pSetAttr, 'depends', 1, None, ProcAttributeError, "Process dependents should be 'Proc/Aggr', not: 'int'"
		#5
		yield pSetAttr, 'depends', pSetAttrDepends, [pSetAttrDepends]
		yield pSetAttr, 'depends', aSetAttr, [aSetAttr.pSetAttrAggr]
		yield pSetAttr, 'depends', (aSetAttr, pSetAttrDepends), [aSetAttr.pSetAttrAggr, pSetAttrDepends]
		yield pSetAttr, 'script', 'file:' + path.abspath(__file__)
		yield pSetAttr, 'script', 'file:' + path.relpath(__file__, __folder__), 'file:' + path.abspath(__file__)
		#10
		yield pSetAttr, 'args', {'a':1}, Box({'a':1})
		yield pSetAttr, 'envs', {'a':1}, Box({'a':1})
		yield pSetAttr, 'input', 'inkey1:var, inkey2:file'
		yield pSetAttr, 'input', [('inval1', 'inval2')], {'inkey1:var, inkey2:file': [('inval1', 'inval2')]}
		yield pSetAttr, 'input', {'inkey1:var, inkey2:file': [('inval1', 'inval2')]}
		yield pSetAttr, 'input', [('inval3', 'inval4')], {'inkey1:var, inkey2:file': [('inval3', 'inval4')]}
		yield pSetAttr, 'input', ['inkey3:var', 'inkey4:file'], {'inkey1:var, inkey2:file': ['inkey3:var', 'inkey4:file']}
		yield pSetAttr, 'input', {'inkey1:var': 'inval1', 'inkey2:file': 'inval2'}
		yield pSetAttr, 'input', [('inval3', 'inval4')], {'inkey1:var, inkey2:file': [('inval3', 'inval4')]}
				
	def testSetAttr(self, p, name, val, expect = None, exception = None, msg = None, errs = []):
		if exception:
			self.assertRaisesRegex(exception, msg, p.__setattr__, name, val)
		else:
			if expect is None:
				expect = val
			with helpers.log2str() as (out, err):
				p.__setattr__(name, val)
			stderr = err.getvalue()
			v = p.__getattr__(name)
			if not v:
				v = p.config[name]
			if isinstance(expect, list):
				self.assertListEqual(v, expect)
			elif isinstance(expect, dict):
				self.assertDictEqual(v, expect)
			else:
				self.assertEqual(v, expect)
			for err in errs:
				self.assertIn(err, stderr)
			setname = name if name not in Proc.ALIAS else Proc.ALIAS[name]
			self.assertIn(setname, p.props['sets'])
			
	def dataProvider_testRepr(self):
		pRepr = Proc()
		yield pRepr, '<Proc(pRepr) @ %s>' % hex(id(pRepr))
		pRepr1 = Proc(tag = 'atag')
		yield pRepr1, '<Proc(pRepr1.atag) @ %s>' % hex(id(pRepr1))
		pRepr2 = Proc(tag = 'aggr')
		pRepr2.aggr = 'aggr'
		yield pRepr2, '<Proc(pRepr2.aggr@aggr) @ %s>' % hex(id(pRepr2))
		
	def testRepr(self, p, r):
		self.assertEqual(repr(p), r)
	
	def dataProvider_testLog(self):
		pLog = Proc()
		pLog.props['size'] = 2
		Proc.LOG_NLINE['CACHE_SCRIPT_NEWER'] = -3
		yield pLog, 'hello', 'info', '', ['INFO', 'hello']
		yield pLog, 'hello', 'info', '', ['INFO', 'hello']
		yield pLog, 'script newer1', 'warning', 'CACHE_SCRIPT_NEWER', [], ['WARNING', 'DEBUG', 'script newer1']
		yield pLog, 'script newer2', 'warning', 'CACHE_SCRIPT_NEWER', [], ['WARNING', 'script newer1', 'script newer2', 'DEBUG']
		
		pLog1 = Proc()
		pLog1.props['size'] = 100
		yield pLog1, 'script newer1', 'warning', 'CACHE_SCRIPT_NEWER', [], ['WARNING', 'DEBUG', 'script newer1']
		yield pLog1, 'script newer2', 'warning', 'CACHE_SCRIPT_NEWER', [], ['WARNING', 'script newer1', 'script newer2', 'DEBUG']
		yield pLog1, 'script newer3', 'warning', 'CACHE_SCRIPT_NEWER', ['WARNING', 'script newer1', 'script newer2', 'DEBUG', 'max=3']
		yield pLog1, 'script newer4', 'warning', 'CACHE_SCRIPT_NEWER', [], ['WARNING', 'script newer1', 'script newer2', 'DEBUG', 'max=3', 'script newer4']
		
	# note: single test will not work, e.g: python testProc.py TestProc.testLog_6 	
	def testLog(self, p, msg, level, key, expects, noexpects = []):
		with helpers.log2str(levels = 'all') as (out, err):
			p.log(msg, level, key)
		stderr = err.getvalue()
		if not isinstance(expects, list):
			expects = [expects]
		if not isinstance(noexpects, list):
			noexpect = [noexpects]
		for ex in expects:
			self.assertIn(ex, stderr)
		for ex in noexpects:
			self.assertNotIn(ex, stderr)
			
	def dataProvider_testCopy(self):
		pCopy = Proc()
		pCopy.workdir = path.join(self.testdir, 'pCopy')
		yield pCopy, None, 'DESCRIPTION', None, {
			# 'brings': {},
			'channel': [],
			'depends': [],
			'echo': {},
			'expart': [],
			'expect': None,
			'lock': None,
			'origin': 'pCopy',
			'input': {},
			'jobs': [],
			'logs': {},
			'ncjobids': [],
			'output': OrderedDict(),
			'procvars': {},
			'rc': [0],
			'runner': 'local',
			'script': None,
			'sets': ['workdir'],
			'size': 0,
			'suffix': '',
			'template': None,
			'workdir': ''
		}, {
			'afterCmd': '',
			'aggr': None,
			'args': Box(),
			'infile': 'indir',
			'beforeCmd': '',
			# 'brings': {},
			'cache': True,
			'callback': None,
			'callfront': None,
			'cclean': False,
			'depends': [],
			'desc': 'No description.',
			'dirsig': True,
			'echo': False,
			'errhow': 'terminate',
			'errntry': 3,
			'exdir': '',
			'exhow': 'move',
			'exow': True,
			'expart': '',
			'expect': '',
			'forks': 1,
			'id': 'pCopy',
			'input': '',
			'lang': 'bash',
			'nthread': min(int(cpu_count() / 2), 16),
			'output': '',
			'ppldir': path.realpath('./workdir'),
			'rc': 0,
			'resume': '',
			'runner': 'local',
			'script': '',
			'tag': 'notag',
			'template': '',
			'tplenvs': Box(),
			'workdir': path.join(self.testdir, 'pCopy')
		}, {
			# 'brings': {},
			'channel': [],
			'depends': [],
			'echo': {},
			'expart': [],
			'expect': None,
			'lock': None,
			'origin': 'pCopy',
			'input': {},
			'jobs': [],
			'logs': {},
			'ncjobids': [],
			'output': OrderedDict(),
			'procvars': {},
			'rc': [0],
			'runner': 'local',
			'script': None,
			'sets': ['workdir'],
			'size': 0,
			'suffix': '',
			'template': None,
			'workdir': ''
		}, {
			'afterCmd': '',
			'aggr': None,
			'args': Box(),
			'beforeCmd': '',
			# 'brings': {},
			'cache': True,
			'callback': None,
			'callfront': None,
			'cclean': False,
			'depends': [],
			'desc': 'DESCRIPTION',
			'dirsig': True,
			'echo': False,
			'errhow': 'terminate',
			'errntry': 3,
			'exdir': '',
			'exhow': 'move',
			'exow': True,
			'expart': '',
			'expect': '',
			'forks': 1,
			'id': 'p',
			'infile': 'indir',
			'input': '',
			'lang': 'bash',
			'nthread': min(int(cpu_count() / 2), 16),
			'output': '',
			'ppldir': path.realpath('./workdir'),
			'rc': 0,
			'resume': '',
			'runner': 'local',
			'script': '',
			'tag': 'notag',
			'template': '',
			'tplenvs': Box(),
			'workdir': ''
		}
			
	def testCopy(self, orgp, tag, desc, newid, oprops, oconfig, nprops, nconfig):
		self.maxDiff = None
		p = orgp.copy(tag = tag, desc = desc, id = newid)
		self.assertDictEqual(p.props, nprops)
		self.assertDictEqual(p.config, nconfig)
		p.args.a = 1
		p.props['output']['a:var'] = 'outputa'
		p.tplenvs.b = 2
		p.tag = 'newtag'
		self.assertEqual(orgp.tag, 'notag')
		self.assertEqual(orgp.output, {})
		self.assertEqual(orgp.envs, {})
		self.assertEqual(orgp.args, {})
		self.assertEqual(orgp.sets, ['workdir'])
		self.assertIsInstance(p.args, Box)
		self.assertEqual(p.args, {'a': 1})
		self.assertEqual(p.output, {'a:var': 'outputa'})
		self.assertEqual(p.envs, {'b': 2})
		self.assertEqual(p.tag, 'newtag')
		# original process keeps intact
		self.assertDictEqual(orgp.props, oprops)
		self.assertDictEqual(orgp.config, oconfig)
		
	def dataProvider_testSuffix(self):
		pSuffix = Proc()
		pSuffix.props['suffix'] = '23lhsaf'
		yield pSuffix, '23lhsaf'
		
		pSuffix1 = Proc()
		pSuffix1.input = {'in': lambda ch: ch}
		pSuffix1.depends = pSuffix
		config = {key:val for key, val in pSuffix1.config.items() if key in [
			'id', 'tag', 'input'
		]}
		config['argv0'] = path.realpath(sys.argv[0])
		if isinstance(config['input'], dict):
			config['input'] = pycopy.copy(config['input'])
			for key, val in config['input'].items():
				config['input'][key] = utils.funcsig(val) if callable(val) else val
		config['depends'] = [pSuffix.name(True) + '#' + pSuffix._suffix()]
		yield pSuffix1, utils.uid(json.dumps(config, sort_keys = True))
		
	def testSuffix(self, p, suffix):
		s = p._suffix()
		self.assertEqual(s, suffix)
		
	def dataProvider_testName(self):
		pName = Proc()
		pName.tag = 'tag'
		pName.aggr = 'aggr'
		yield pName, True, 'pName.tag@aggr'
		yield pName, False, 'pName.tag'
		
		pName1 = Proc()
		yield pName1, True, 'pName1'
		yield pName1, False, 'pName1'
		
	def testName(self, p, aggr, name):
		n = p.name(aggr)
		self.assertEqual(n, name)
		
	def dataProvider_testBuildProps(self):
		testdir = self.testdir
		# 0
		pBuildProps = Proc()
		pBuildProps.ppldir = testdir
		yield pBuildProps, {}, {}, ProcTreeProcExists, 'There are two processes with id\(pBuildProps\) and tag\(notag\)'
		# 1
		pBuildProps1 = Proc(id = 'pBuildProps')
		pBuildProps1.ppldir = testdir
		yield pBuildProps1, {}, {}, ProcTreeProcExists, 'There are two processes with id\(pBuildProps\) and tag\(notag\)'
		# 2-9
		pBuildProps2 = Proc()
		pBuildProps2.ppldir = testdir
		yield pBuildProps2, {}, {'template': TemplatePyPPL}
		yield pBuildProps2, {'template': ''}, {'template': TemplatePyPPL}
		if helpers.moduleInstalled('jinja2'):
			yield pBuildProps2, {'template': TemplateJinja2}, {'template': TemplateJinja2}
			yield pBuildProps2, {'template': 'jinja2'}, {'template': TemplateJinja2}
		yield pBuildProps2, {'rc': ' 0, 1, '}, {'rc': [0,1]}
		yield pBuildProps2, {'rc': 2}, {'rc': [2]}
		yield pBuildProps2, {'rc': [0, 1]}, {'rc': [0, 1]}
		yield pBuildProps2, {'workdir': path.join(testdir, 'pBuildProps2')}, {'workdir': path.join(testdir, 'pBuildProps2')}
		# 10
		pBuildProps3 = Proc()
		pBuildProps3.ppldir = testdir
		yield pBuildProps3, {}, {'workdir': path.join(testdir, 'PyPPL.pBuildProps3.notag.%s' % pBuildProps3._suffix())}, None, None, [lambda p: path.isdir(p.workdir)]
		
		# 11
		pBuildProps4 = Proc()
		pBuildProps4.ppldir = testdir
		yield pBuildProps4, {'resume': 'skip+'}, {}, ProcAttributeError, 'Cannot skip process, as workdir not exists'
		
		# 12
		pBuildProps5 = Proc()
		pBuildProps5.ppldir = testdir
		# exdir
		yield pBuildProps5, {'exdir': path.relpath(path.join(testdir, 'exports'))}, {'exdir': path.abspath(path.join(testdir, 'exports'))}, None, None, [lambda p: path.isdir(p.exdir)]
		# echo
		# 13-20
		yield pBuildProps5, {'echo': True}, {'echo': {'jobs': [0], 'type': {'stderr': None, 'stdout': None}}}
		yield pBuildProps5, {'echo': False}, {'echo': {'jobs': [], 'type': {'stderr': None, 'stdout': None}}}
		yield pBuildProps5, {'echo': 'stderr'}, {'echo': {'jobs': [0], 'type': {'stderr': None}}}
		yield pBuildProps5, {'echo': 'stdout'}, {'echo': {'jobs': [0], 'type': {'stdout': None}}}
		yield pBuildProps5, {'echo': {'type': 'all'}}, {'echo': {'jobs': [0], 'type': {'stderr': None, 'stdout': None}}}
		yield pBuildProps5, {'echo': {'jobs': ' 0, 1 ', 'type': 'all'}}, {'echo': {'jobs': [0, 1], 'type': {'stderr': None, 'stdout': None}}}
		yield pBuildProps5, {'echo': {'jobs': range(2), 'type': 'all'}}, {'echo': {'jobs': [0, 1], 'type': {'stderr': None, 'stdout': None}}}
		yield pBuildProps5, {'echo': {'type': 'stderr'}}, {'echo': {'jobs': [0], 'type': {'stderr': None}}}
		yield pBuildProps5, {'echo': {'type': {'all': r'^a'}}}, {'echo': {'jobs': [0], 'type': {'stderr': r'^a', 'stdout': r'^a'}}}
		# expect
		# 21
		yield pBuildProps5, {'expect': 'expect template'}, {}, None, None, [lambda p: p.expect.source == 'expect template']
		# expart
		# 22
		yield pBuildProps5, {'expart': 'a,b,c,d,"e,f"'}, {}, None, None, [
			(lambda p: p.expart[i].source == v) for i,v in enumerate(['a', 'b', 'c', 'd', '"e,f"'])
		]
		
	def testBuildProps(self, p, attrs = {}, props = {}, exception = None, msg = None, expects = []):
		for k,v in attrs.items():
			setattr(p, k, v)
		if exception:
			self.assertRaisesRegex(exception, msg, p._buildProps)
		else:
			p._buildProps()
			for k, v in props.items():
				if isinstance(v, dict):
					self.assertDictEqual(v, getattr(p, k))
				elif isinstance(v, list):
					self.assertListEqual(v, getattr(p, k))
				else:
					self.assertEqual(v, getattr(p, k))
			for expect in expects:
				self.assertTrue(expect(p))
				
	def dataProvider_testBuildInput(self):
		pBuildInputDep = Proc()
		pBuildInputDep.props['channel'] = []
		
		pBuildInput = Proc()
		pBuildInput.depends = pBuildInputDep
		yield pBuildInput, {}, {}
		yield pBuildInput, 'a,b', {'a': {'data': [], 'type': 'var'}, 'b': {'data': [], 'type': 'var'}}
		yield pBuildInput, 'a:unknowntype', {}, ProcInputError, 'Unknown input type'
		
		pBuildInputDep1 = Proc()
		pBuildInputDep1.props['channel'] = Channel.create([1,2])
		pBuildInputDep2 = Proc()
		pBuildInputDep2.props['channel'] = Channel.create([3,4])
		pBuildInput1 = Proc()
		pBuildInput1.depends = pBuildInputDep1, pBuildInputDep2
		yield pBuildInput1, 'a,b', {'a': {'data': [1,2], 'type': 'var'}, 'b': {'data': [3,4], 'type': 'var'}}
		
		pBuildInput2 = Proc()
		pBuildInput2.depends = pBuildInputDep1, pBuildInputDep2
		yield pBuildInput2, 'a', {'a': {'data': [1,2], 'type': 'var'}}, None, None, ['Not all data are used as input, 1 column(s) wasted.']
		
		pBuildInput3 = Proc()
		pBuildInput3.depends = pBuildInputDep1, pBuildInputDep2
		yield pBuildInput2, {'a,b,c': lambda ch1, ch2: ch1.cbind(ch2)}, {'a': {'data': [1,2], 'type': 'var'}, 'b': {'data': [3,4], 'type': 'var'}, 'c': {'data': ['',''], 'type': 'var'}}, None, None, ['No data found for input key "c", use empty strings/lists instead.']
		
		pBuildInput4 = Proc()
		yield pBuildInput4, {'a': [1], 'b': 2, 'c': [1,2], 'd:files':[[self.testdir, self.testdir]]}, {
			'a': {'data': [1,1], 'type': 'var'},
			'b': {'data': [2,2], 'type': 'var'},
			'c': {'data': [1,2], 'type': 'var'},
			'd': {'data': [[self.testdir,self.testdir], [self.testdir,self.testdir]], 'type': 'files'},
		}
		
		pBuildInput5 = Proc()
		pBuildInput5.ppldir = self.testdir
		pBuildInput5.input  = {'a': ['h"i\'nihao'], 'b': 2, 'c': [1,2], 'd:files':[[self.testdir, self.testdir]]}
		with helpers.log2str():
			pBuildInput5._buildInput()
			pBuildInput5._buildProps()
			pBuildInput5._saveSettings()
		pBuildInput5.props['resume'] = 'skip+'
		yield pBuildInput5, {}, {
			'a': {'data': ['h"i\'nihao','h"i\'nihao'], 'type': 'var'},
			'b': {'data': [2,2], 'type': 'var'},
			'c': {'data': [1,2], 'type': 'var'},
			'd': {'data': [[self.testdir,self.testdir], [self.testdir,self.testdir]], 'type': 'files'},
		}
		
		pBuildInput6 = Proc()
		pBuildInput6.ppldir = self.testdir
		pBuildInput6.props['resume'] = 'skip+'
		yield pBuildInput6, {}, {}, ProcInputError, 'Cannot parse input for skip\+/resume process, no such file:'
				
	def testBuildInput(self, p, cin, pin, exception = None, msg = None, errs = []):
		self.maxDiff = None
		p.input = cin
		if exception:
			self.assertRaisesRegex(exception, msg, p._buildInput)
		else:
			with helpers.log2str(levels = 'all') as (out, err):
				#p._buildInput()
				pass
			p._buildInput()
			stderr = err.getvalue()
			self.assertDictEqual(p.input, pin)
			for err in errs:
				self.assertIn(err, stderr)
				
	def dataProvider_testBuildProcVars(self):
		pBuildProcVars = Proc()
		pBuildProcVars.ppldir = self.testdir
		yield pBuildProcVars, {}, {'size': 0, 'ppldir': self.testdir}, [
			'P.PROPS',
			'ppldir => %s' % repr(self.testdir),
			'size   => 0',
		]
		
		pBuildProcVars1 = Proc()
		pBuildProcVars1.ppldir = self.testdir
		pBuildProcVars1.args.a = 1
		pBuildProcVars1.props['runner'] = 'ssh'
		# pBuildProcVars1.props['runner'] will still be 'local'
		# because the runner closes in proc.run
		#pBuildProcVars1.runner = 'ssh'  
		yield pBuildProcVars1, {'a': 1}, {'size': 0, 'ppldir': self.testdir, 'runner': 'ssh'}, [
			'P.PROPS',
			'ppldir => %s' % repr(self.testdir),
			'runner => ssh',
			'size   => 0',
			'P.ARGS',
			'a      => 1'
		]
		
	def testBuildProcVars(self, p, procargs, procvars, errs = []):
		with helpers.log2str(levels = 'all') as (out, err):
			p._buildProps()
			p._buildProcVars()
		stderr = err.getvalue()
		self.assertDictContains(procargs, p.procvars['args'])
		self.assertDictContains(procvars, p.procvars['proc'])
		for err in errs:
			self.assertIn(err, stderr)
		
	def dataProvider_testBuildOutput(self):
		pBuildOutput = Proc()
		pBuildOutput.ppldir = self.testdir
		pBuildOutput.output = ''
		yield pBuildOutput, '', {}
		yield pBuildOutput, {}, {}, ProcOutputError, 'Process output should be str/list/OrderedDict, not: \'dict\''
		yield pBuildOutput, 'a', {}, ProcOutputError, 'One of <key>:<type>:<value> missed for process output in: \'a\''
		yield pBuildOutput, ['a:b:c:d'], {}, ProcOutputError, 'Too many parts for process output in: \'a:b:c:d\''
		yield pBuildOutput, OrderedDict([('a:b:c', 'd')]), {}, ProcOutputError, 'Too many parts for process output key in: \'a:b:c\''
		yield pBuildOutput, 'a:b:c', {}, ProcOutputError, 'Unknown output type: \'b\''
		yield pBuildOutput, 'a:c, b:file:d, e:dir:f', OrderedDict([
			('a', ('var', 'c')),
			('b', ('file', 'd')),
			('e', ('dir', 'f')),
		])
		yield pBuildOutput, 'a:c, b:file:d, e:dir:f, g:stdout:h, i:stderr:j', OrderedDict([
			('a', ('var', 'c')),
			('b', ('file', 'd')),
			('e', ('dir', 'f')),
			('g', ('stdout', 'h')),
			('i', ('stderr', 'j')),
		])

	def testBuildOutput(self, p, inout, outout, exception = None, msg = None):
		p.output = inout
		if exception:
			self.assertRaisesRegex(exception, msg, p._buildOutput)
		else:
			p._buildProps()
			p._buildOutput()
			for k, v in outout.items():
				t, o = p.output[k]
				o = o.source
				self.assertEqual(t, v[0])
				self.assertEqual(o, v[1])
				
	def dataProvider_testBuildScript(self):
		pBuildScript = Proc()
		pBuildScript.ppldir = self.testdir
		yield pBuildScript, '', '#!/usr/bin/env bash\n', None, None, [
			'WARNING',
			'No script specified'
		]
		
		tplfile = path.join(self.testdir, 'scriptTpl.txt')
		helpers.writeFile(tplfile, [
			'A',
			'B',
			'## PYPPL REPEAT START: repeat  #',
			'Repeat1',
			'## PYPPL REPEAT END: repeat',
			'',
			'## PYPPL REPEAT START: repeat #',
			'Repeat2',
			'## PYPPL REPEAT END: repeat',
			'C',
			'  ### PYPPL INDENT REMOVE',
			'  D',
			'    E',
			'  # PYPPL INDENT KEEP ###',
			'  F'
		])
		yield pBuildScript, 'file:' + tplfile, [
			'#!/usr/bin/env bash',
			'A',
			'B',
			'Repeat1',
			'',
			'C',
			'D',
			'  E',
			'  F',
			''
		]
		
		tplfile1 = path.join(self.testdir, 'scriptTpl1.txt')
		helpers.writeFile(tplfile1, [
			'A',
			'B',
			'## PYPPL REPEAT START: repeat #',
			'Repeat1',
			'# PYPPL REPEAT START: repeat2',
			'Repeat2',
			'### PYPPL REPEAT END: repeat2',
			'',
			'## PYPPL REPEAT START: repeat #',
			'Repeat3',
			'# PYPPL REPEAT START: repeat2',
			'Repeat2'
			'## PYPPL REPEAT END: repeat2',
			'## PYPPL REPEAT END: repeat',
			'C',
			'  ### PYPPL INDENT REMOVE',
			'  D',
			'    # PYPPL INDENT REMOVE',
			'    E',
			'  # PYPPL INDENT KEEP ###',
			'  F',
		])
		yield pBuildScript, 'file:' + tplfile1, [
			'#!/usr/bin/env bash',
			'A',
			'B',
			'Repeat1',
			'Repeat2',
			'',
			'Repeat3',
			'C',
			'D',
			'E',
			'  F',
			''
		]
		
		tplfile = path.join(self.testdir, 'nosuchtpl')
		yield pBuildScript, 'file:' + tplfile, '', ProcScriptError, 'No such template file:'
				
	def testBuildScript(self, p, inscript, outscript, exception = None, msg = None, errs = []):
		p.script = inscript
		if exception:
			self.assertRaisesRegex(exception, msg, p._buildScript)
		else:
			with helpers.log2str(levels = 'all') as (out, err):
				p._buildProps()
				p._buildScript()
			helpers.assertTextEqual(self, p.script.source, outscript)
			stderr = err.getvalue()
			for err in errs:
				self.assertIn(err, stderr)
				
	def dataProvider_testSaveSettings(self):
		pSaveSettings = Proc()
		pSaveSettings.ppldir = self.testdir
		yield pSaveSettings, [
			# '[brings]',
			'[channel]',
			'value: []',
			'[depends]',
			'procs: []',
			'[echo]',
			'jobs: []',
			'type: {"stderr": null, "stdout": null}',
			'[expart]',
			'value_0: TemplatePyPPL <  >',
			'[expect]',
			'value: TemplatePyPPL <  >',
			'[input]',
			'[output]',
			'[procvars]',
			'args: {}',
			'proc: {',
			'[rc]',
			'value: [0]',
			'[runner]',
			'value: local',
			'[script]',
			'value:',
			'	"TemplatePyPPL < #!/usr/bin/env bash >"',
			'[sets]',
			'value: [\'ppldir\']',
			'[size]',
			'value: %s' % (len(sys.argv) - 1), 
			'[suffix]',
			'value: ',
			'[template]',
			'name: TemplatePyPPL',
			'[workdir]',
			'value: ',
		]
		
		pSaveSettings1 = Proc()
		pSaveSettings1.ppldir = self.testdir
		infile1 = path.join(self.testdir, 'pSaveSettings1-in1.txt')
		infile2 = path.join(self.testdir, 'pSaveSettings1-in2.txt')
		brfile1 = path.join(self.testdir, 'pSaveSettings1-in1.br')
		brfile2 = path.join(self.testdir, 'pSaveSettings1-in2.br')
		helpers.writeFile(infile1)
		helpers.writeFile(infile2)
		helpers.writeFile(brfile1)
		helpers.writeFile(brfile2)
		pSaveSettings1.input    = {'a': 1, 'b:file': [infile1, infile2], 'c:files': [[infile1, infile2]]}
		#pSaveSettings1.brings   = {'b': '{{fn(in.b)}}.br'}
		pSaveSettings1.output   = 'out:file:{{fn(in.b)}}-{{in.a}}.out'
		pSaveSettings1.echo     = {'jobs': [0,1]}
		pSaveSettings1.expart   = '*-1.out'
		pSaveSettings1.expect   = 'grep 1 {{out.out}}'
		pSaveSettings1.args.a   = 'a'
		pSaveSettings1.rc       = '0,1'
		pSaveSettings1.script   = 'echo {{in.a}} > {{out.out}}'
		pSaveSettings1.template = 'jinja2'
		if helpers.moduleInstalled('jinja2'):
			yield pSaveSettings1, [
				#'[brings]',
				#'b: [\'TemplateJinja2 < {{fn(in.b)}}.br >\']',
				'[channel]',
				'value: []',
				'[depends]',
				'procs: []',
				'[echo]',
				'jobs: [0, 1]',
				'type: {"stderr": null, "stdout": null}',
				'[expart]',
				'value_0: TemplateJinja2 < *-1.out >',
				'[expect]',
				'value: TemplateJinja2 < grep 1 {{out.out}} >',
				'[input]',
				'a.type: var',
				'a.data#0',
				'	1',
				'a.data#1',
				'	1',
				'b.type: file',
				'b.data#0',
				'pSaveSettings1-in1.txt',
				'b.data#1',
				'pSaveSettings1-in2.txt',
				'[output]',
				'out.type: file',
				'out.data: TemplateJinja2 < {{fn(in.b)}}-{{in.a}}.out >',
				'[procvars]',
				'args: {"a": "a"}',
				'proc: {',
				'[rc]',
				'value: [0, 1]',
				'[runner]',
				'value: local',
				'[script]',
				'value:',
				'	"TemplateJinja2 <<<"',
				'	"\\t#!/usr/bin/env bash"',
				'	"\\techo {{in.a}} > {{out.out}}"',
				'	">>>"',
				'[sets]',
				'value: [\'ppldir\', \'input\', \'output\', \'echo\', \'expart\', \'expect\', \'rc\', \'script\', \'template\']',
				'[size]',
				'value: 2',
				'[suffix]',
				'value: ',
				'[template]',
				'name: TemplateJinja2',
				'[workdir]',
				'value: ',
			]
		
	def testSaveSettings(self, p, settings):
		self.maxDiff = None
		with helpers.log2str() as (out, err):
			p._buildInput()
			p._buildProcVars ()
			p._buildProps()
			# p._buildBrings()
			p._buildOutput()
			p._buildScript()
			p._saveSettings()
		psettings = helpers.readFile(path.join(p.workdir, 'proc.settings'), str)
		for setting in settings:
			self.assertIn(setting, psettings)
			psettings = psettings[(psettings.find(setting) + len(setting)):]
	
	def dataProvider_testBuildJobs(self):
		pBuildJobs = Proc()
		pBuildJobs.ppldir = self.testdir
		infile1 = path.join(self.testdir, 'pBuildJobs-in1.txt')
		infile2 = path.join(self.testdir, 'pBuildJobs-in2.txt')
		helpers.writeFile(infile1)
		helpers.writeFile(infile2)
		pBuildJobs.input    = {'a': 1, 'b:file': [infile1, infile2], 'c:files': [[infile1, infile2]]}
		pBuildJobs.output   = 'out:file:{{in.b | fn}}-{{in.a}}.out'
		pBuildJobs.script   = 'echo {{in.a}} > {{out.out}}'
		with helpers.log2str(levels = 'all') as (out, err):
			pBuildJobs._buildProps ()
			pBuildJobs._buildInput ()
			pBuildJobs._buildProcVars ()
			#pBuildJobs._buildBrings ()
			pBuildJobs._buildOutput()
			pBuildJobs._buildScript()
		yield pBuildJobs, 2, [
			path.join(pBuildJobs.workdir, '1', 'output', 'pBuildJobs-in1-1.out'),
			path.join(pBuildJobs.workdir, '2', 'output', 'pBuildJobs-in2-1.out')
		], ['out'], [
			'INPUT',
			'/2] a   => 1',
			'/2] b   => %s' % pBuildJobs.workdir,
			# '/2] _b  => %s' % testdir,
			'/2] c   => [ %s' % pBuildJobs.workdir,
			'/2]          %s' % pBuildJobs.workdir,
			# '/2] _c  => [%s' % testdir,
			# '/2]         %s' % testdir,
			'OUTPUT',
			'/2] out => %s' % pBuildJobs.workdir
		]
		
		pBuildJobs1 = Proc()
		pBuildJobs1.ppldir = self.testdir
		yield pBuildJobs1, 0, [], [], [
			'WARNING', 
			'No data found for jobs, process will be skipped.'
		]
		
	def testBuildJobs(self, p, size, channel, chkeys, errs = []):
		with helpers.log2str(levels = 'all') as (out, err):
			p._buildJobs ()
		stderr = err.getvalue()
		self.assertEqual(len(p.jobs), size)
		channel = Channel.create(channel)
		self.assertListEqual(p.channel, channel)
		for i, key in enumerate(chkeys):
			self.assertListEqual(getattr(p.channel, key), channel.colAt(i))
		for err in errs:
			self.assertIn(err, stderr)
			stderr = stderr[(stderr.find(err) + len(err)):]
	
	def dataProvider_testTidyBeforeRun(self):
		pTidyBeforeRun= Proc()
		pTidyBeforeRun.ppldir = self.testdir
		yield pTidyBeforeRun, []
		pTidyBeforeRun1 = Proc()
		pTidyBeforeRun1.ppldir = self.testdir
		pTidyBeforeRun1.props['callfront'] = lambda p: p.log('hello')
		yield pTidyBeforeRun1, ['DEBUG', 'Calling callfront ...', 'INFO', 'hello']
	
	def testTidyBeforeRun(self, p, errs = []):
		with helpers.log2str(levels = 'all') as (out, err):
			p._tidyBeforeRun()
		stderr = err.getvalue()
		for err in errs:
			self.assertIn(err, stderr)
			stderr = stderr[(stderr.find(err) + len(err)):]
			
	def dataProvider_testRunCmd(self):
		pRunCmd = Proc()
		pRunCmd.ppldir = self.testdir
		yield pRunCmd, 'beforeCmd'
		pRunCmd1 = Proc()
		pRunCmd1.ppldir = self.testdir
		pRunCmd1.beforeCmd = "echo 456; echo 123 >&2"
		yield pRunCmd1, 'beforeCmd', None, None, [
			'INFO',
			'Running <beforeCmd> ...',
			'CMDOUT',
			'456',
			'CMDERR',
			'123'
		]
		pRunCmd2 = Proc()
		pRunCmd2.ppldir = self.testdir
		pRunCmd2.beforeCmd = "xxx 123 >&2"
		yield pRunCmd2, 'beforeCmd', ProcRunCmdError, 'Failed to run <beforeCmd>:'
		pRunCmd3 = Proc()
		pRunCmd3.ppldir = self.testdir
		pRunCmd3.afterCmd = "xxx 123 >&2"
		yield pRunCmd3, 'beforeCmd'
		pRunCmd4 = Proc()
		pRunCmd4.ppldir = self.testdir
		pRunCmd4.afterCmd = "exit 1"
		yield pRunCmd4, 'afterCmd', ProcRunCmdError, 'Failed to run <afterCmd>:'
		
	def testRunCmd(self, p, key, exception = None, msg = None, errs = []):
		p._buildProps()
		if exception:
			self.assertRaisesRegex(exception, msg, p._runCmd, key)
		else:
			with helpers.log2str() as (out, err):
				p._runCmd(key)
			stderr = err.getvalue()
			for err in errs:
				self.assertIn(err, stderr)
				stderr = stderr[(stderr.find(err) + len(err)):]
	
	def dataProvider_testReadConfig(self):
		pReadConfig = Proc()
		yield 't1', None, None, 'local', {'runner': 'local'}
		yield 't2', 'sge', None, 'sge', {'runner': 'sge'}
		yield 't3', 'default', {'default': {'runner': 'sge'}}, 'sge', {'runner': 'default'}
		yield 't4', 'xxx', {'xxx': {}, 'default': {}}, 'xxx', {'runner': 'xxx'}
		yield 't5', 'xxx', {'xxx': {}}, 'local', {'runner': 'xxx'}
		yield 't6', 'xxx', {'yyy': {}}, 'xxx', {'runner': 'xxx'}
		yield 't7', 'sge1d', {'sge1d': {'runner': 'sge', 'nthread': 10, 'forks': 4, 'ppldir': self.testdir}}, 'sge', {'runner': 'sge1d', 'forks': 4, 'nthread': 10, 'ppldir': self.testdir}
		
	def testReadConfig(self, tag, profile, inconfig, runner, outconfig):
		pReadConfig = Proc(tag = tag)
		pReadConfig._readConfig(profile, inconfig)
		self.assertEqual(pReadConfig.runner, runner)
		self.assertDictContains(outconfig, pReadConfig.config)
		
	def dataProvider_testTidyAfterRun(self):
		pTidyAfterRun = Proc()
		pTidyAfterRun.props['callback'] = lambda p: p.log('goodbye')
		yield pTidyAfterRun, 'terminate', 'skip+', None, [
			'DEBUG',
			'Calling callback ...',
			'INFO',
			'goodbye'
		]
		
		pTidyAfterRun1 = Proc()
		pTidyAfterRun1.ppldir = self.testdir
		pTidyAfterRun1.input = {'in': [1,2]}
		pTidyAfterRun1.props['callback'] = lambda p: p.log('goodbye')
		pTidyAfterRun1._tidyBeforeRun()
		# write rc to job.rc
		for job in pTidyAfterRun1.jobs:
			helpers.writeFile(job.rcfile, 0)
		yield pTidyAfterRun1, 'terminate', '', None, [
			'DEBUG',
			'Successful jobs: ALL',
			'INFO',
			'goodbye'
		]
		
		pTidyAfterRun2 = Proc()
		pTidyAfterRun2.ppldir = self.testdir
		pTidyAfterRun2.input = {'in': [1,2]}
		pTidyAfterRun2._tidyBeforeRun()
		# write rc to job.rc
		helpers.writeFile(pTidyAfterRun2.jobs[0].rcfile, 0)
		helpers.writeFile(pTidyAfterRun2.jobs[1].rcfile, 1)
		yield pTidyAfterRun2, 'terminate', '', SystemExit, [
			'ERROR',
			'failed (totally 1). Return code: 1 (Script error).',
			'[2/2] Script:',
			'[2/2] Stdout:',
			'[2/2] Stderr:',
			'[2/2] check STDERR below:',
			'<EMPTY STDERR>',
		]
		yield pTidyAfterRun2, 'ignore', '', None, [
			'WARNING',
			'[2/2] failed but ignored (totally 1). Return code: 1 (Script error).',
		]
		
	def testTidyAfterRun(self, p, errhow, resume, exception = None, errs = []):
		p.props['errhow'] = errhow
		p.props['resume'] = resume
		if exception:
			self.assertRaises(exception, p._tidyAfterRun)
		else:
			with helpers.log2str(levels = 'all') as (out, err):
				p._tidyAfterRun()
			stderr = err.getvalue()
			for err in errs:
				self.assertIn(err, stderr)
				stderr = stderr[(stderr.find(err) + len(err)):]
				
	def dataProvider_testCheckCached(self):
		pCheckCached = Proc()
		pCheckCached.props['cache'] = False
		yield pCheckCached, False, [
			'DEBUG',
			'Not cached, because proc.cache is False'
		]
		
		# 1 all cached
		pCheckCached1 = Proc()
		pCheckCached1.ppldir = self.testdir
		pCheckCached1.input  = {'a': [1,2]}
		with helpers.log2str():
			pCheckCached1._tidyBeforeRun()
		for job in pCheckCached1.jobs:
			job.cache()
		yield pCheckCached1, True, [
			'INFO',
			'Truly cached jobs : ALL',
			'Export-cached jobs: []'
		]
	
		# 2 all export cached
		pCheckCached2 = Proc()
		pCheckCached2.ppldir = self.testdir
		pCheckCached2.input  = {'a': [1,2]}
		pCheckCached2.output = 'a:file:{{in.a}}.txt'
		pCheckCached2.cache  = 'export'
		pCheckCached2.exdir  = self.testdir 
		with helpers.log2str():
			pCheckCached2._tidyBeforeRun()
		for i, job in enumerate(pCheckCached2.jobs):
			helpers.writeFile(job.rcfile, 0)
			helpers.writeFile(path.join(job.outdir, str(i+1) + '.txt'))
			helpers.writeFile(path.join(self.testdir, str(i+1) + '.txt'))
			
		yield pCheckCached2, True, [
			'INFO',
			'Truly cached jobs : []',
			'Export-cached jobs: ALL'
		]
		
		# partially cached
		pCheckCached3 = Proc()
		pCheckCached3.ppldir = self.testdir
		pCheckCached3.input  = {'a': [1,2]}
		with helpers.log2str():
			pCheckCached3._tidyBeforeRun()
		pCheckCached3.jobs[0].cache()
		yield pCheckCached3, False, [
			'INFO',
			'Truly cached jobs : 0',
			'Export-cached jobs: []',
			'Partly cached, only run non-cached 1 job(s).',
			'DEBUG',
			'Jobs to run: 1'
		]
		
		# no jobs cached
		pCheckCached4 = Proc()
		pCheckCached4.ppldir = self.testdir
		pCheckCached4.input  = {'a': [1,2]}
		with helpers.log2str():
			pCheckCached4._tidyBeforeRun()
		yield pCheckCached4, False, [
			'DEBUG',
			'Not cached, none of the jobs are cached.',
		]
		
	def testCheckCached(self, p, ret, errs):
		with helpers.log2str(levels = 'all') as (out, err):
			r = p._checkCached()
		self.assertEqual(r, ret)
		stderr = err.getvalue()
		for err in errs:
			self.assertIn(err, stderr)
			stderr = stderr[(stderr.find(err) + len(err)):]
	
	def dataProvider_testRunJobs(self):
		pRunJobs = Proc()
		pRunJobs.ppldir = self.testdir
		pRunJobs.input  = {'a': [1,2]}
		with helpers.log2str():
			pRunJobs._tidyBeforeRun()
		yield pRunJobs,
	
	def testRunJobs(self, p):
		self.assertIsNone(p._runJobs())
		
	def dataProvider_testRun(self):
		pRun = Proc()
		pRun.ppldir = self.testdir
		pRun.input  = {'a': [1,2]}
		with helpers.log2str():
			pRun._tidyBeforeRun()
		yield pRun, {'runner': 'dry'}, False, [
			'RUNNING',
			pRun.workdir,
			'INFO',
			'Done (time: '
		]
		pRun1 = Proc()
		pRun1.ppldir = self.testdir
		pRun1.props['resume'] = 'skip'
		
		yield pRun1, {}, True, [
			'SKIPPED',
			'Pipeline will resume from future processes.'
		]
		pRun2 = Proc()
		pRun2.ppldir = self.testdir
		pRun2.input  = {'a': [1,2]}
		with helpers.log2str():
			pRun2._tidyBeforeRun()
		pRun2.props['resume'] = 'skip+'
		yield pRun2, {}, True, [
			'SKIPPED',
			'Data loaded, pipeline will resume from future processes.'
		]
		
		pRun3 = Proc()
		pRun3.ppldir = self.testdir
		pRun3.input  = {'a': [1,2]}
		with helpers.log2str():
			pRun3._tidyBeforeRun()
		for job in pRun3.jobs:
			job.cache()
		yield pRun3, {}, True, [
			'CACHED',
			pRun3.workdir
		]
		pRun4 = Proc()
		pRun4.ppldir = self.testdir
		pRun4.input  = {'a': [1,2]}
		with helpers.log2str():
			pRun4._tidyBeforeRun()
		for job in pRun4.jobs:
			job.cache()
		pRun4.props['resume'] = 'resume'		
		yield pRun4, {}, True, [
			'RESUMED',
			pRun4.workdir
		]
		
		
	def testRun(self, p, config, cache, errs = []):
		RunnerLocal.INTERVAL = .1
		#with helpers.log2str(levels = 'all') as (out, err):
		p.run(config)
		self.assertEqual(p.cache, cache)
		# stderr = err.getvalue()
		# print out.getvalue()
		# print stderr
		# for err in errs:
		# 	self.assertIn(err, stderr)
		# 	stderr = stderr[(stderr.find(err) + len(err)):]
	
if __name__ == '__main__':
	testly.main(verbosity=2, failfast = True)