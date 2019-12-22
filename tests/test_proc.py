import sys
from multiprocessing import cpu_count
from pathlib import Path
import pytest
import cmdy
from diot import Diot
from simpleconf import Config
from pyppl import _proc, proc
from pyppl.proc import Proc
from pyppl._proc import _require, _decache
from pyppl.config import config
from pyppl.channel import Channel
from pyppl.template import TemplateLiquid, TemplateJinja2
from pyppl.exception import ProcessAttributeError, ProcessInputError, ProcessOutputError, ProcessScriptError
from pyppl.jobmgr import STATES

class Jobmgr:
	def __init__(self, jobs):
		pass
	def start(self):
		pass

proc.Jobmgr = Jobmgr

def test_init():
	pProcInit = Proc()
	assert pProcInit._setcounter == {'cache': 0,
		'id'      : 1,
		'dirsig'  : 0,
		'errhow'  : 0,
		'errntry' : 0,
		'lang'    : 0,
		'runner'  : 0,
		'forks'   : 0,
		'tag'     : 0,
		'template': 0}
	assert pProcInit.id == 'pProcInit'
	assert pProcInit.tag == 'notag'
	assert pProcInit.desc == 'No description.'
	assert pProcInit.args == {}
	assert pProcInit.cache
	assert pProcInit.depends == []
	assert pProcInit.dirsig
	assert pProcInit.envs == {}
	assert pProcInit.errhow == config.errhow
	assert pProcInit.errntry == config.errntry
	assert pProcInit.forks == 1
	assert pProcInit.lang == cmdy.which(config.lang).strip()
	assert pProcInit.name == 'pProcInit.notag'
	assert pProcInit._ncjobids == []
	assert pProcInit.nexts == []
	assert pProcInit.nthread == config.nthread
	assert pProcInit.ppldir == Path(config.ppldir)
	assert pProcInit.procset == ''
	assert pProcInit.runtime_config == None
	assert pProcInit.shortname == 'pProcInit'
	assert pProcInit.template is TemplateLiquid

def test_init2():
	pProcInit2 = Proc(errhow = 'ignore')
	assert pProcInit2.errhow == 'ignore'

def test_id_setter():
	pIdSetter = Proc()
	with pytest.raises(ProcessAttributeError):
		pIdSetter.id = 'aa'

@pytest.mark.parametrize('value, expect, size, exlog', [
	({}, {}, 0, ''),
	({'a, b:file, ': ('1', 'infile')},
		{'a': ('var', ['1']), 'b': ('file', ['infile'])}, 1, ''),
	({'a:files, b:files, c': Channel.create([['infile1'], ['infile2']])},
		{'a': ('files', [['infile1'], ['infile2']]),
		 'b': ('files', [[], []]),
		 'c': ('var', ['', ''])}, 2,
		['No data found for input key "b"', 'No data found for input key "c"']),
	({'a,b': [(1,2,3), (4,5,6), (7,8,9)]},
		{'a': ('var', [1,4,7]),
		 'b': ('var', [2,5,8])}, 3,
		['Not all data are used as input, 1 column(s) wasted.']),
])
def test_input_and_size(request, caplog, value, expect, size, exlog):
	p = Proc(request.node.name)
	p.input = value
	p.runtime_config = {'dirsig': False}
	assert p.input == expect
	assert p.size == size
	if exlog:
		if not isinstance(exlog, list):
			exlog = [exlog]
		for exl in exlog:
			assert exl in caplog.text

def test_runtime_config():
	pRuntimeConfig = Proc()
	pRuntimeConfig.add_config('test_a')
	pRuntimeConfig.add_config('test_b', runtime = 'ignore')
	pRuntimeConfig.plugin_config.test_b = 3
	runtime_config = Config()
	runtime_config._load({'default': dict(
		tag      = 'uniformed_tag',
		cache    = False,
		dirsig   = False,
		envs     = Diot(a = 1),
		errhow   = 'retry',
		errntry  = 10,
		lang     = 'python',
		runner   = 'sge',
		template = 'jinja2',
		plugin_config = {'test_a': 1, 'test_b': 10}
	)})
	pRuntimeConfig.runtime_config = runtime_config
	assert pRuntimeConfig.runtime_config == runtime_config

	assert pRuntimeConfig.tag == 'uniformed_tag'
	assert pRuntimeConfig.cache == False
	assert pRuntimeConfig.dirsig == False
	assert pRuntimeConfig.envs == {'a': 1}
	assert pRuntimeConfig.errhow == 'retry'
	assert pRuntimeConfig.errntry == 10
	assert pRuntimeConfig.plugin_config.test_a == 1
	assert pRuntimeConfig.plugin_config.test_b == 3
	assert pRuntimeConfig.lang == cmdy.which('python').strip()
	assert pRuntimeConfig.runner == {'runner': 'sge'}
	assert pRuntimeConfig.template is TemplateJinja2

	pRuntimeConfig2 = Proc()
	pRuntimeConfig2.add_config('test_a')
	pRuntimeConfig2.add_config('test_b')
	pRuntimeConfig2.tag = 'mytag'
	pRuntimeConfig2.cache = True
	pRuntimeConfig2.dirsig = True
	pRuntimeConfig2.envs = Diot(a = 2, b = 3)
	pRuntimeConfig2.errhow = 'terminate'
	pRuntimeConfig2.errntry = 3
	pRuntimeConfig2.lang = 'bash'
	pRuntimeConfig2.runner = {'runner': 'ssh', 'ssh.servers': [1]}
	pRuntimeConfig2.template = None

	pRuntimeConfig2.runtime_config = runtime_config
	assert pRuntimeConfig2.tag == 'mytag'
	assert pRuntimeConfig2.cache == True
	assert pRuntimeConfig2.dirsig == True
	assert pRuntimeConfig2.envs == {'a': 1, 'b': 3}
	assert pRuntimeConfig2.errhow == 'terminate'
	assert pRuntimeConfig2.errntry == 3
	assert pRuntimeConfig2.lang == cmdy.which('bash').strip()
	assert pRuntimeConfig2.runner == {'runner': 'ssh', 'ssh.servers': [1]}
	assert pRuntimeConfig2.template is TemplateLiquid

def test_input_complex():
	runtime_config = Config()
	runtime_config._load({'default': {'dirsig': False}})

	pInputSeparate = Proc()
	pInputSeparate.input = 'a, b:file'
	pInputSeparate.input = '1', 'infile'
	pInputSeparate.runtime_config = runtime_config
	assert pInputSeparate.runtime_config == runtime_config
	assert pInputSeparate.input == {'a': ('var', ['1']), 'b': ('file', ['infile'])}

	# wrong type
	pInputSeparate.input = 'a:x:y'
	with pytest.raises(ProcessInputError):
		pInputSeparate.input

	pInputSeparate.input = {'a:var': [1, 2]}
	assert pInputSeparate.input == {'a': ('var', [1, 2])}
	pInputSeparate.output = 'out1:var:3, out2:var:4'

	# callback
	pInputSeparate2 = Proc()
	pInputSeparate2.depends = pInputSeparate
	pInputSeparate2.input = 'a, b, c'
	pInputSeparate2.input = lambda ch: ch.cbind(1)
	pInputSeparate2.runtime_config = runtime_config
	assert pInputSeparate2.input['a'] == ('var', ['3', '3'])
	assert pInputSeparate2.input['b'] == ('var', ['4', '4'])
	assert pInputSeparate2.input['c'] == ('var', [1, 1])

def test_output():
	pOutput = Proc()
	pOutput.output = 'a'
	with pytest.raises(ProcessOutputError):
		pOutput.output
	pOutput.output = 'a:b:c:d'
	with pytest.raises(ProcessOutputError):
		pOutput.output
	pOutput.output = {'a': '1', 'b': 2}
	with pytest.raises(ProcessOutputError):
		pOutput.output
	pOutput.output = 'a:b:c'
	with pytest.raises(ProcessOutputError):
		pOutput.output
	pOutput.output = '1not.identifier:file'
	with pytest.raises(ProcessOutputError):
		pOutput.output
	pOutput.output = 'a:1, b:file:infile'
	assert len(pOutput.output) == 2
	assert pOutput.output['a'][0] == 'var'
	assert pOutput.output['a'][1].render() == '1'
	assert pOutput.output['b'][0] == 'file'
	assert pOutput.output['b'][1].render() == 'infile'

def test_runner():
	pRunner = Proc()

	pRunner.runtime_config = Config()
	pRunner.runtime_config._load(config, {
		'default': {'runner': {'someconfig': 1}},
		'special_profile': {'runner': 'sge'},
		'profile2': {'runner': {'queue': '1-day'}}
	})
	pRunner.runner = 'special_profile'
	assert pRunner.runner == {'runner': 'sge', 'someconfig': 1}

	pRunner.runner = 'ssh'
	assert pRunner.runner == {'runner': 'ssh', 'someconfig': 1}

	pRunner.runner = 'profile2'
	assert pRunner.runner == {'runner': 'local', 'queue': '1-day', 'someconfig': 1}

	cfg = Config()
	cfg._load({'default': {'runner': {'defaultconfigs_for_runners': 1}}})
	pRunner.runtime_config = Config()
	pRunner.runtime_config._load(cfg)
	pRunner.runner = 'sge'
	assert pRunner.runner == {'runner': 'sge', 'defaultconfigs_for_runners': 1}

def test_script(caplog, tmp_path):
	pProcScript = Proc()
	pProcScript.script = ''
	assert pProcScript.script.source == '#!' + cmdy.which('bash').str()
	assert 'No script specified' in caplog.text
	caplog.clear()

	scriptfile = tmp_path / 'test_buildscript.txt'
	scriptfile.write_text('# script')
	pProcScript.script = 'file:%s' % scriptfile
	scriptfile.unlink()
	with pytest.raises(ProcessScriptError):
		pProcScript.script

	scriptfile.write_text('''# script
	# PYPPL INDENT REMOVE
	abs
	bin
	# PYPPL INDENT KEEP
	callable
	def''')
	caplog.clear()
	pProcScript.lang = 'python'
	assert pProcScript.script.render() == '''#!%s
# script
abs
bin
	callable
	def
'''%(cmdy.which('python').strip())
	assert 'Using template file: ' in caplog.text

def test_template():
	t = lambda: None
	pTemplate = Proc()
	pTemplate.template = t
	assert pTemplate.template is t
	pTemplate.template = None
	assert pTemplate.template is TemplateLiquid
	pTemplate.template = 'jinja2'
	assert pTemplate.template is TemplateJinja2

def test_require():
	with pytest.raises(ProcessAttributeError):
		_require(lambda: None, 'abc')

	p = Diot(a = '')
	with pytest.raises(ProcessAttributeError):
		_require(p, 'a')

def test_name_and_shortname():
	pName = Proc()
	assert pName.name == 'pName.notag'
	assert pName.shortname == 'pName'

	pName.tag = 'mytag@ps'
	assert pName.name == 'pName.mytag@ps'
	assert pName.procset == 'ps'

	pName.tag = 'new'
	assert pName.name == 'pName.new'
	assert pName.shortname == 'pName.new'

	pName.tag = 'notag@ps'
	assert pName.name == 'pName.notag@ps'
	assert pName.shortname == 'pName@ps'

def test_suffix():
	pSuffix = Proc()
	pSuffix.input = {'a': [1]}
	pSuffix.output = 'outfile:file:{{a}}.txt'
	pSuffix.runtime_config = {'dirsig': False}
	suffix0 = pSuffix.suffix
	assert len(suffix0) == 8

	pSuffix.input = {'a': [2]}
	suffix1 = pSuffix.suffix
	assert suffix1 != suffix0

	pSuffix.input = 'a'
	sys.argv = ['', '1']
	suffix2 = pSuffix.suffix
	assert suffix2 != suffix1 != suffix0

	sys.argv[0] = 'some_other_sys_argv_0'
	_decache(pSuffix, 'suffix')
	suffix3 = pSuffix.suffix
	assert suffix3 != suffix2 != suffix1 != suffix0

def test_workdir(tmp_path):
	pWorkdir = Proc()
	pWorkdir.input = 'x'
	pWorkdir.output = 'x:1'
	pWorkdir.runtime_config = {'dirsig': False}
	assert pWorkdir.workdir.resolve() == pWorkdir.ppldir.joinpath('PyPPL.{}.{}'.format(pWorkdir.name, pWorkdir.suffix)).resolve()
	assert pWorkdir.workdir.is_dir()

	_decache(pWorkdir, 'workdir')
	pWorkdir.workdir = 'pWorkdir'
	assert pWorkdir.workdir.resolve() == pWorkdir.ppldir.joinpath('pWorkdir').resolve()
	assert pWorkdir.workdir.is_dir()

	_decache(pWorkdir, 'workdir')
	pWorkdir.workdir = tmp_path.joinpath('pWorkdir')
	assert pWorkdir.workdir.resolve() == tmp_path.joinpath('pWorkdir').resolve()
	assert pWorkdir.workdir.is_dir()

def test_jobs():
	pJobs = Proc()
	pJobs.runtime_config = Config()
	pJobs.runtime_config._load({'default': {'dirsig': False}})
	assert pJobs.jobs == []

	pJobs.input = {'a': [1,2,3]}
	assert len(pJobs.jobs) == 3

def test_channel():

	pChannel = Proc()
	pChannel.runtime_config = Config()
	pChannel.runtime_config._load({'default': {'dirsig': False}})
	pChannel.channel = {'a': 1}
	assert pChannel.channel == {'a': 1}

### END of attribute tests

def test_runjobs():
	runtime_config = Config()
	runtime_config._load({'default': {'dirsig': False}})
	pRunJobs = Proc()
	pRunJobs.runtime_config = runtime_config
	pRunJobs.input = {'a': [1]}
	pRunJobs.output = 'outfile:file:{{a}}.txt'
	assert len(pRunJobs.jobs) == 1

	pRunJobs._run_jobs()
	assert pRunJobs.channel == [(pRunJobs.jobs[0].dir.joinpath('output/1.txt'),)]

def test_run(caplog):
	from pyppl.job import Job
	Job.state = None
	runtime_config = Config()
	runtime_config._load({'default': {'dirsig': False}})

	pRun = Proc()
	pRun.input = {'a': [1]}
	pRun.output = 'outfile:file:{{a}}.txt'
	with pytest.raises(SystemExit):
		pRun.run(runtime_config)
	assert pRun.channel == [(pRun.jobs[0].dir.joinpath('output/1.txt'),)]
	assert 'WORKDIR' in caplog.text
	assert 'pRun: Jobs [Cached: 0, Succ: 0, B.Fail: 0, S.Fail: 0, R.Fail: 0]' in caplog.text

def test_run2(caplog):
	from pyppl.job import Job
	from pyppl.jobmgr import STATES
	Job.state = STATES.BUILTFAILED
	runtime_config = Config()
	runtime_config._load({'default': {'dirsig': False}})

	pRunRun2 = Proc()
	pRunRun2.input = {'a': [1]}
	pRunRun2.output = 'outfile:file:{{a}}.txt'
	with pytest.raises(SystemExit):
		pRunRun2.run(runtime_config)
	assert 'pRunRun2: Jobs [Cached: 0, Succ: 0, B.Fail: 1, S.Fail: 0, R.Fail: 0]' in caplog.text

def test_run3(caplog):
	from pyppl.job import Job
	from pyppl.jobmgr import STATES
	Job.state = STATES.SUBMITFAILED
	runtime_config = Config()
	runtime_config._load({'default': {'dirsig': False}})

	pRunRun3 = Proc()
	pRunRun3.input = {'a': [1]}
	pRunRun3.output = 'outfile:file:{{a}}.txt'
	with pytest.raises(SystemExit):
		pRunRun3.run(runtime_config)
	assert 'pRunRun3: Jobs [Cached: 0, Succ: 0, B.Fail: 0, S.Fail: 1, R.Fail: 0]' in caplog.text

def test_run4(caplog):
	from pyppl.job import Job
	from pyppl.jobmgr import STATES
	Job.state = STATES.ENDFAILED
	runtime_config = Config()
	runtime_config._load({'default': {'dirsig': False}})

	pRunRun4 = Proc()
	pRunRun4.input = {'a': [1]}
	pRunRun4.output = 'outfile:file:{{a}}.txt'
	with pytest.raises(SystemExit):
		pRunRun4.run(runtime_config)
	assert 'pRunRun4: Jobs [Cached: 0, Succ: 0, B.Fail: 0, S.Fail: 0, R.Fail: 1]' in caplog.text

def test_defs():
	pDefs = Proc()
	assert 'pDefs = Proc()' in pDefs._defs

def test_depends():
	pDepends1 = Proc()
	pDepends2 = Proc()
	pDepends3 = Proc()

	pDepends2.depends = pDepends1
	assert pDepends2.depends == [pDepends1]
	assert pDepends1.nexts == [pDepends2]

	pDepends2.depends = pDepends3
	assert pDepends2.depends == [pDepends3]
	assert pDepends1.nexts == []
	assert pDepends3.nexts == [pDepends2]

def test_copy():
	pCopy = Proc()
	pNew1 = pCopy.copy('p6', tag = 'new', desc = 'desc')

	assert pNew1.id == 'p6'
	assert pNew1.tag == 'new'
	assert pNew1.desc == 'desc'

	pNew1.depends = pCopy
	pNew2 = pNew1.copy()
	assert pNew1.depends == [pCopy]
	assert pCopy.nexts == [pNew1]
	assert pNew2.depends == []
	assert pNew2._depends == []
	assert pNew2.nexts == []

	pNew3 = pCopy.copy()
	pNew2.depends = pNew3
	pnew4 = pNew3.copy()
	assert pnew4.depends == []
	assert pnew4._depends == []
	assert pnew4.nexts == []

