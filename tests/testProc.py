import helpers, testly, json, sys
import copy as pycopy

import yaml
from os import path, makedirs
from box import Box
from shutil import rmtree
from tempfile import gettempdir
from collections import OrderedDict
from multiprocessing import cpu_count
from pyppl import Proc, Box, Aggr, utils, ProcTree, Channel, Job, logger
from pyppl.exception import ProcTagError, ProcAttributeError, ProcTreeProcExists, ProcInputError, ProcOutputError, ProcScriptError, ProcRunCmdError
from pyppl.template import TemplateLiquid
if helpers.moduleInstalled('jinja2'):
	from pyppl.template import TemplateJinja2
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
			'ncjobids': [],
			'output': Box(ordered_box = True),
			'origin': 'p',
			'procvars': {},
			'rc': [0],
			'runner': 'local',
			'script': None,
			'sets': set(),
			'timer': None,
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
			'acache': False,
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
			#'iftype': 'indir',
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
			'ncjobids': [],
			'lock': None,
			'origin': 'someId',
			'output': Box(ordered_box = True),
			'procvars': {},
			'rc': [0],
			'lock': None,
			'origin': 'someId',
			'runner': 'local',
			'script': None,
			'sets': set(),
			'size': 0,
			'suffix': '',
			'template': None,
			'timer': None,
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
			'acache': False,
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
			#'iftype': 'indir',
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
		
	
	def testInit(self, tag, desc, id, props, cfg, exception = None):
		self.maxDiff = None
		if exception:
			self.assertRaises(exception, Proc, tag = tag, desc = desc, id = id)
		else:
			p = Proc(tag = tag, desc = desc, id = id)
			self.assertDictEqual(p.props, props)
			self.assertDictEqual({k:v for k,v in p.config.items() if not k.startswith('_')}, cfg)
			config2 = cfg.copy()
			del config2['tag']
			del config2['desc']
			del config2['id']
			p2 = Proc(cfg['id'], tag, desc, **config2)
			#props['sets'] = list(sorted(['runner', 'echo', 'depends', 'expect', 'callfront', 'script', 'cache', 'nthread', 'beforeCmd', 'template', 'rc', 'input', 'forks', 'acache', 'workdir', 'resume', 'exhow', 'args', 'exow', 'dirsig', 'ppldir', 'errhow', 'lang', 'tplenvs', 'exdir', 'expart', 'afterCmd', 'callback', 'aggr', 'output', 'errntry']))
			p2.props['sets'] = set()
			self.assertDictEqual(p2.props, props)
			self.assertDictEqual({k:v for k,v in p2.config.items() if not k.startswith('_')}, cfg)

			
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
		#yield pSetAttr, 'profile', 'sge', 'local', None, None, ['WARNING', 'Attribute "profile" is deprecated']
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
		yield pSetAttr, 'input', OrderedDict([('inkey1:var', 'inval1'), ('inkey2:file', 'inval2')])
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
		pRepr2 = Proc(tag = 'aggr@aggr')
		pRepr2.aggr = 'aggr'
		yield pRepr2, '<Proc(pRepr2.aggr@aggr) @ %s>' % hex(id(pRepr2))
		
	def testRepr(self, p, r):
		self.assertEqual(repr(p), r)
			
	def dataProvider_testCopy(self):
		pCopy = Proc()
		pCopy.workdir = path.join(self.testdir, 'pCopy')
		yield pCopy, None, 'DESCRIPTION', None, { # oprops
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
			'ncjobids': [],
			'output': Box(ordered_box = True),
			'procvars': {},
			'rc': [0],
			'runner': 'local',
			'script': None,
			'sets': {'workdir'},
			'size': 0,
			'suffix': '',
			'template': None,
			'timer': None,
			'workdir': ''
		}, { # oconfig
			'afterCmd': '',
			'aggr': None,
			'args': Box(),
			#'iftype': 'indir',
			'beforeCmd': '',
			# 'brings': {},
			'cache': True,
			'callback': None,
			'callfront': None,
			'acache': False,
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
		}, { # nprops
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
			'ncjobids': [],
			'output': Box(ordered_box = True),
			'procvars': {},
			'rc': [0],
			'runner': 'local',
			'script': None,
			'sets': {'workdir', 'desc'},
			'timer': None,
			'size': 0,
			'suffix': '',
			'template': None,
			'workdir': ''
		}, { # nconfig
			'afterCmd': '',
			'aggr': None,
			'args': Box(),
			'beforeCmd': '',
			# 'brings': {},
			'cache': True,
			'callback': None,
			'callfront': None,
			'acache': False,
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
			#'iftype': 'indir',
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
		self.assertDictEqual({k:v for k,v in p.config.items() if not k.startswith('_')}, nconfig)
		p.args.a = 1
		p.props['output']['a:var'] = 'outputa'
		p.tplenvs.b = 2
		p.tag = 'newtag'
		self.assertEqual(orgp.tag, 'notag')
		self.assertEqual(orgp.output, {})
		self.assertEqual(orgp.envs, {})
		self.assertEqual(p.envs.b, 2)
		self.assertEqual(orgp.args, {})
		self.assertEqual(orgp.sets, {'workdir'})
		self.assertIsInstance(p.args, Box)
		self.assertEqual(p.args, {'a': 1})
		self.assertEqual(p.output, {'a:var': 'outputa'})
		self.assertEqual(p.envs, {'b': 2})
		self.assertEqual(p.tag, 'newtag')
		# original process keeps intact
		self.assertDictEqual(orgp.props, oprops)
		orgp.config['tplenvs'] = Box()
		self.assertDictEqual({k:v for k,v in orgp.config.items() if not k.startswith('_')}, oconfig)
		
	def dataProvider_testSuffix(self):
		pSuffix = Proc()
		pSuffix.props['suffix'] = '23lhsaf'
		yield pSuffix, '23lhsaf'
		
		pSuffix1 = Proc()
		pSuffix1.input = {'in': lambda ch: ch}
		pSuffix1.depends = pSuffix
		sigs = Box(ordered_box = True)
		sigs.argv0 = path.realpath(sys.argv[0])
		sigs.id    = pSuffix1.id
		sigs.tag   = pSuffix1.tag

		if isinstance(pSuffix1.config.input, dict):
			sigs.input = pycopy.copy(pSuffix1.config.input)
			for key, val in pSuffix1.config.input.items():
				sigs.input[key] = utils.funcsig(val) if callable(val) else val
		sigs['depends'] = [pSuffix.name(True) + '#' + pSuffix._suffix()]
		yield pSuffix1, utils.uid(sigs.to_json())
		
	def testSuffix(self, p, suffix):
		s = p._suffix()
		self.assertEqual(s, suffix)
		
	def dataProvider_testName(self):
		pName = Proc()
		pName.tag = 'tag@aggr'
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
		yield pBuildProps2, {}, {'template': TemplateLiquid}
		yield pBuildProps2, {'template': ''}, {'template': TemplateLiquid}
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
		
		# 5
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
		#with helpers.log2str():
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
			'P_PROPS',
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
			'P_PROPS',
			'ppldir => %s' % repr(self.testdir),
			'runner => ssh',
			'size   => 0',
			'P_ARGS',
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
			'Repeat1',
			'',
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
			'Repeat1',
			'Repeat2',
			'',
			'Repeat3',
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
		yield pSaveSettings, {
			'origin'  : 'pSaveSettings',
			'jobs'    : [],
			'runner'  : 'local',
			'lock'    : None,
			'sets'    : set(['ppldir']),
			'echo'    : {'jobs': [], 'type': {'stderr': None, 'stdout': None}},
			'depends' : [],
			'expect'  : 'TemplateLiquid <  >',
			'input'   : OrderedDict(),
			'size'    : 0,
			'script'  : 'TemplateLiquid < #!/usr/bin/env bash >',
			'expart'  : ['TemplateLiquid <  >'],
			'timer'   : None,
			'procvars': {},
			'ncjobids': [],
			'template': 'TemplateLiquid',
			'rc'      : [0],
			'output'  : {},
			'channel' : []
		}
		
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
		#pSaveSettings1.brings   = {'b': '{{fn(i.b)}}.br'}
		pSaveSettings1.output   = 'out:file:{{fn(i.b)}}-{{i.a}}.out'
		pSaveSettings1.echo     = {'jobs': [0,1]}
		pSaveSettings1.expart   = '*-1.out'
		pSaveSettings1.expect   = 'grep 1 {{o.out}}'
		pSaveSettings1.args.a   = 'a'
		pSaveSettings1.rc       = '0,1'
		pSaveSettings1.script   = 'echo {{i.a}} > {{o.out}}'
		pSaveSettings1.template = 'jinja2'
		if helpers.moduleInstalled('jinja2'):
			yield pSaveSettings1, {
				'origin'  : 'pSaveSettings1',
				'jobs'    : [None, None],
				'runner'  : 'local',
				'lock'    : None,
				'sets'    : set(['ppldir', 'script', 'expart', 'output', 'expect', 'template', 'rc', 'input', 'echo', ]),
				'echo'    : {'jobs': [0, 1], 'type': {'stderr': None, 'stdout': None}},
				'depends' : [],
				'expect'  : 'TemplateJinja2 < grep 1 {{o.out}} >',
				'input'   : OrderedDict([('a', {'data': [1, 1], 'type': 'var'}), ('b', {'data': [infile1, infile2], 'type': 'file'}), ('c', {'data': [[infile1, infile2], [infile1, infile2]], 'type': 'files'})]),
				'size'    : 2,
				'script'  : "TemplateJinja2 <<<\n\t#!/usr/bin/env bash\n\techo {{i.a}} > {{o.out}}\n>>>",
				'expart'  : ['TemplateJinja2 < *-1.out >'],
				'timer'   : None,
				'procvars': {},
				'ncjobids': [],
				'template': 'TemplateJinja2',
				'rc'      : [0, 1],
				'output'  : OrderedDict([('out', "('file', TemplateJinja2 < {{fn(i.b)}}-{{i.a}}.out >)")]),
				'channel' : []
			}

		
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
		psettings = helpers.readFile(path.join(p.workdir, 'proc.settings.yaml'), yaml.load)
		for key, val in settings.items():
			self.assertEqual({key:psettings[key]}, {key:val})
	
	def dataProvider_testBuildJobs(self):
		pBuildJobs = Proc()
		pBuildJobs.input = {}
		pBuildJobs1 = Proc()
		pBuildJobs1.input = {'a':[1,2,3]}
		yield pBuildJobs, 0
		yield pBuildJobs1, 3
		
	def testBuildJobs(self, p, size):
		p._buildInput()
		p._buildJobs()
		self.assertEqual(p.size, size)
		self.assertEqual(len(p.jobs), size)
		for job in p.jobs:
			self.assertIsInstance(job, Job)

	
	def dataProvider_testTidyBeforeRun(self):
		pTidyBeforeRun= Proc()
		pTidyBeforeRun.ppldir = self.testdir
		yield pTidyBeforeRun, []
		pTidyBeforeRun1 = Proc()
		pTidyBeforeRun1.ppldir = self.testdir
		pTidyBeforeRun1.props['callfront'] = lambda p: logger.info('hello')
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
		yield pRunCmd1, 'preCmd', None, None, [
			'INFO',
			'Running <preCmd> ...',
			'CMDERR',
			'123',
			'CMDOUT',
			'456',
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
		yield 't2', 'sge', None, 'sge', {'runner': None}
		yield 't3', 'default1', {'default1': {'runner': 'sge'}}, 'sge', {'runner': 'default1'}
		yield 't4', 'xxx', {'xxx': {}, 'default': {}}, 'local', {'runner': 'xxx'}
		yield 't5', 'xxx', {'xxx': {}}, 'local', {'runner': 'xxx'}
		yield 't6', 'xxx', {'yyy': {}}, 'local', {'runner': 'xxx'}
		yield 't7', 'sge1d', {'sge1d': {'runner': 'sge', 'nthread': 10, 'forks': 4, 'ppldir': self.testdir}}, 'sge', {'runner': 'sge1d', 'forks': 4, 'nthread': 10, 'ppldir': self.testdir}
		yield 't8', {'forks': 10}, {'default': {'forks': 20}}, 'local', {'forks': 10, 'runner': '__tmp__'}
		yield 't9', {'forks': 10}, {'default': {'envs': {'a': 1}}}, 'local', {'forks': 10}
		
	def testReadConfig(self, tag, profile, inconfig, runner, outconfig):
		pReadConfig = Proc(tag = tag)
		pReadConfig._readConfig(profile, inconfig)
		self.assertEqual(pReadConfig.runner, runner)
		self.assertDictContains(outconfig, pReadConfig.config)
		
	def dataProvider_testTidyAfterRun(self):
		pTidyAfterRun = Proc()
		pTidyAfterRun.props['callback'] = lambda p: logger.info('goodbye')
		yield pTidyAfterRun, 'terminate', 'skip+', None, [
			'DEBUG',
			'Calling callback ...',
			'INFO',
			'goodbye'
		]
		
		pTidyAfterRun1 = Proc()
		pTidyAfterRun1.ppldir = self.testdir
		pTidyAfterRun1.input = {'in': [1,2]}
		pTidyAfterRun1.props['callback'] = lambda p: logger.info('goodbye')
		pTidyAfterRun1._tidyBeforeRun()
		# write rc to job.rc
		#for job in pTidyAfterRun1.jobs:
		#	helpers.writeFile(job.rcfile, 0)
		yield pTidyAfterRun1, 'terminate', '', None, [
			'DEBUG',
			'pTidyAfterRun1: Successful       : 0, 1',
			'INFO',
			'goodbye'
		]
		
		pTidyAfterRun2 = Proc()
		pTidyAfterRun2.ppldir = self.testdir
		pTidyAfterRun2.input = {'in': [1,2]}
		pTidyAfterRun2._tidyBeforeRun()
		# write rc to job.rc
		#helpers.writeFile(pTidyAfterRun2.jobs[0].rcfile, 0)
		#helpers.writeFile(pTidyAfterRun2.jobs[1].rcfile, 1)
		yield pTidyAfterRun2, 'terminate', '', SystemExit, [
			'ERROR',
			'failed (totally 1). Return code: 1 (Script error).',
			'[2/2] Script:',
			'[2/2] Stdout:',
			'[2/2] Stderr:',
			'[2/2] check STDERR below:',
			'<EMPTY STDERR>',
		], False
		yield pTidyAfterRun2, 'ignore', '', None, [
			'WARNING',
			'pTidyAfterRun2: [1/2] Failed (totally 2)',
		], False
		
	def testTidyAfterRun(self, p, errhow, resume, exception = None, errs = [], done = True):
		p.props['errhow'] = errhow
		p.props['resume'] = resume
		for job in p.jobs:
			job.build()
			job.status = Job.STATUS_DONE if done else Job.STATUS_ENDFAILED
		if exception:
			self.assertRaises(exception, p._tidyAfterRun)
		else:
			with helpers.log2str(levels = 'all') as (out, err):
				p._tidyAfterRun()
			stderr = err.getvalue()
			for err in errs:
				self.assertIn(err, stderr)
				stderr = stderr[(stderr.find(err) + len(err)):]

	def dataProvider_testRunJobs(self):
		pRunJobs = Proc()
		pRunJobs.ppldir = self.testdir
		pRunJobs.input  = {'a': [1,2]}
		yield pRunJobs, 
		pRunJobs2 = Proc()
		pRunJobs2.ppldir = self.testdir
		pRunJobs2.input  = {'a': [1,2]}
		pRunJobs2.props['runner'] = 'NoSuchRunner'
		yield pRunJobs2, ProcAttributeError
	
	def testRunJobs(self, p, exception = None):
		if exception:
			self.assertRaises(exception, p._tidyBeforeRun)
		else:
			p._tidyBeforeRun()
			self.assertIsNone(p._runJobs())
		
	def dataProvider_testRun(self):
		pRun = Proc()
		pRun.ppldir = self.testdir
		pRun.input  = {'a': [1,2]}
		with helpers.log2str():
			pRun._tidyBeforeRun()
		yield pRun, {'runner': 'dry'}, False, [
			pRun.workdir,
			'P_PROPS',
			'RUNNING',
			'P_DONE',
			'Time:'
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
		pRun3.script = 'echo {{i.a}}'
		with helpers.log2str():
			pRun3._tidyBeforeRun()
		for job in pRun3.jobs:
			job.build()
			job.cache()
		yield pRun3, {}, True, [
			pRun3.workdir,
			'CACHED',
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
			pRun4.workdir,
			'RESUMED',
		]
		
		
	def testRun(self, p, cfg, cache, errs = []):
		RunnerLocal.INTERVAL = .1
		with helpers.log2str(levels = 'all') as (out, err):
			p.run(cfg)
		self.assertEqual(p.cache, cache)
		stderr = err.getvalue()
		# print out.getvalue()
		# print stderr
		for err in errs:
			self.assertIn(err, stderr)
			stderr = stderr[(stderr.find(err) + len(err)):]
	
if __name__ == '__main__':
	testly.main(verbosity=2, failfast = True)