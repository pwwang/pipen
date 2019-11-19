import os
os.environ['PYPPL_default__log'] = 'py:{"levels": "all"}'
import sys
import logging
import pytest
from pathlib import Path
from simpleconf import Config
from pyppl import PyPPL
from pyppl.utils import config, uid, Box, OBox, fs
from pyppl.proc import Proc
from pyppl.template import TemplateLiquid
from pyppl.channel import Channel
from pyppl.jobmgr import STATES
from pyppl.procset import ProcSet
from pyppl.exception import ProcTagError, ProcAttributeError, ProcTreeProcExists, \
	ProcInputError, ProcOutputError, ProcScriptError, ProcRunCmdError

@pytest.fixture
def tmpdir(tmpdir):
	config.ppldir = tmpdir / 'test_proc_workdir'
	return Path(tmpdir)

def test_proc_init(tmpdir):
	p1 = Proc(id = 'p1', tag = 'tag', desc = 'desc', preCmd = 'ls')
	assert p1.config.id == 'p1'
	assert p1.config.args == {}
	assert p1.config.callfront == None
	assert p1.config.callback == None
	assert p1.props.channel == []
	assert p1.config.depends == []
	assert p1.props.depends == []
	assert p1.props.echo == {}
	assert p1.props.expart == []
	assert p1.props.expect == None
	#assert p1.config.hide == False
	assert p1.config.input == ''
	assert p1.props.input == {}
	assert p1.props.jobs == []
	assert p1.props.lock == None
	assert p1.props.ncjobids == []
	assert p1.props.origin == 'p1'
	assert p1.config.output == ''
	assert p1.props.output == {}
	assert p1.props.procvars == {}
	assert p1.props.rc == [0]
	assert p1.config.resume == ''
	assert p1.props.runner == 'local'
	assert p1.props.script == None
	assert p1.props._suffix == ''
	assert p1.props.template == None
	assert p1.props.timer == None
	assert p1.config.envs == {}
	assert p1.props.workdir == ''
	assert p1.props.sets == set(['beforeCmd'])

	with pytest.raises(ProcTagError):
		Proc(tag = 'a b')

	with pytest.raises(ProcAttributeError):
		Proc(depends = 1)

def test_proc_getattr(tmpdir):
	p2 = Proc()

	with pytest.raises(ProcAttributeError):
		p2.x

	# alias
	p2.afterCmd = 'after cmd'

	assert p2.postCmd == 'after cmd'

	assert p2.id == 'p2'
	assert p2.envs == {}

def test_proc_setattr(tmpdir, caplog):
	p3 = Proc()
	with pytest.raises(ProcAttributeError):
		p3.x = 1
	p3.preCmd = 'ls'
	assert 'beforeCmd' in p3.sets

	p4 = Proc()
	ps = ProcSet(p4)
	p3.depends = p4
	assert p3.depends == [p4]
	p3.depends = [p4], ps
	assert p3.depends == [p4, ps.p4]
	assert p4.tag == 'notag'
	assert ps.p4.tag == 'notag@ps'

	with pytest.raises(ProcAttributeError):
		p3.depends = p3

	with pytest.raises(ProcAttributeError):
		p3.depends = object()

	p3.script = 'file:%s' % Path(__file__).name
	assert p3.config.script == 'file:%s' % Path(__file__).resolve()

	with pytest.raises(ProcAttributeError):
		p3.script = 'file:nosuchfile'

	p3.args = {'a': 1}
	assert p3.args.a == 1

	p3.input = 'a, b'
	p3.input = [1, 2]
	assert p3.config.input == {'a, b': [1, 2]}

	p3.input = {'a': [1], 'b': [2]}
	caplog.clear()
	p3.input = [3,4]
	assert 'Previous input is a dict with multiple keys and key order may be changed.' in caplog.text
	assert 'Now the key order is:' in caplog.text

	p3.runner = 'sge'
	assert p3.config.runner == 'sge'
	assert p3.props.runner == 'sge'

	with pytest.raises(ProcAttributeError):
		p3.tag = 'a@b'

def test_repr(tmpdir):
	p4 = Proc()
	assert p4.id == 'p4'
	assert p4.tag == 'notag'
	assert repr(p4).startswith('<Proc(p4) @')

def test_copy(tmpdir):
	p5 = Proc()
	p6 = p5.copy(id = 'p6', tag = 'new', desc = 'desc')
	assert p6.sets == {'id', 'tag', 'desc'}
	assert p6.id == 'p6'
	assert p6.tag == 'new'
	assert p6.desc == 'desc'
	assert p6.workdir == ''
	assert p6.resume == ''
	assert p6.config.args == {}
	assert p6.config.args is not p5.config.args
	assert p6.envs == {}
	assert p6.envs is not p5.envs

	assert p6.depends == []
	assert p6.jobs == []
	assert p6.ncjobids == []
	assert p6.origin == 'p5'
	assert p6.props._suffix == ''
	assert p6.channel == []
	assert p6.procvars == {}
	assert p6.procvars is not p5.procvars

def test_name():
	p61 = Proc()
	assert p61.name() == 'p61'
	ps = ProcSet(p61)
	assert ps.p61.tag == 'notag@ps'
	assert ps.p61.name(True) == 'p61@ps'

def test_procset():
	p62 = Proc()
	assert p62.procset is None
	p62.config.tag = 'notag@ps'
	assert p62.procset == 'ps'

def test_size(tmpdir):
	p7 = Proc()
	assert p7.size == 0
	p7.props.jobs = [1,2,3]
	assert p7.size == 3

def test_suffix_preset(tmpdir):
	p75 = Proc()
	p8 = Proc()
	p8.depends = p75
	p8.props._suffix = '123'
	assert p8.suffix == '123'

def test_suffix_compute(tmpdir):
	p76 = Proc()
	p81 = Proc()
	p81.depends = p76
	p81.input = 'a'
	sigs = OBox()
	sigs.argv0 = str(Path(sys.argv[0]).resolve())
	sigs.id = 'p81'
	sigs.tag = 'notag'
	sigs.input = 'a'
	sigs.depends = ['p76#' + p76.suffix]
	assert p81.suffix == uid(sigs.to_json())

def test_suffix_input(tmpdir):
	p82 = Proc()
	p82.input = 'a'
	p82.input = [1]
	sigs = OBox()
	sigs.argv0 = str(Path(sys.argv[0]).resolve())
	sigs.id = 'p82'
	sigs.tag = 'notag'
	assert p82.config.input == {'a': [1]}
	sigs.input = {'a': "[1]"}
	assert p82.suffix == uid(sigs.to_json())

def test_buildprops(tmpdir):
	from pyppl import ProcTree
	p9 = Proc()
	p91 = Proc(id = 'p9')
	ProcTree.register(p9)
	ProcTree.register(p91)
	with pytest.raises(ProcTreeProcExists):
		p91._buildProps()

	p9.id = 'p89'
	p9.template = TemplateLiquid
	p9.ppldir = Path(tmpdir / 'test_buildprops')
	p9.rc = '0,1'
	p9.workdir = tmpdir / 'p8'
	p9.exdir = tmpdir / 'p8.exdir'
	p9.echo = True
	p9.expect = 'ls'
	p9.expart = 'outfile'
	p9._buildProps()
	assert p9.template is TemplateLiquid
	assert p9.rc == [0, 1]
	assert p9.workdir.exists()
	assert fs.exists(p9.exdir)
	assert p9.echo == dict(jobs=[0], type=dict(stderr=None, stdout=None))
	assert p9.expect.render() == 'ls'
	assert len(p9.expart) == 1
	assert p9.expart[0].render() == 'outfile'

	p9.template = None
	p9.rc = 1
	p9.sets.remove('workdir')
	p9.props.workdir = None
	p9.echo = False
	p9._buildProps()
	assert p9.template is TemplateLiquid
	assert p9.rc == [1]
	assert Path(p9.workdir) == Path(p9.ppldir) / ('PyPPL.p89.notag.%s' % p9.suffix)
	assert p9.echo == dict(jobs=[], type=dict(stderr=None, stdout=None))

	p9.template = 'liquid'
	p9.rc = [0,1,2]
	p9.echo = 'stderr'
	p9._buildProps()
	assert p9.template is TemplateLiquid
	assert p9.rc == [0,1,2]
	assert p9.echo == dict(jobs=[0], type=dict(stderr=None))

	fs.remove(p9.workdir)
	p9.resume = 'resume'
	with pytest.raises(ProcAttributeError):
		p9._buildProps()

	p9.echo = dict(type='stderr')
	p9.resume = ''
	p9._buildProps()
	assert p9.echo == dict(jobs=[0], type=dict(stderr=None))

	p9.echo = dict(jobs='0,1')
	p9._buildProps()
	assert p9.echo == dict(jobs=[0,1], type=dict(stderr=None, stdout=None))

	p9.echo = dict(jobs='0,1', type=dict(all=r'^log'))
	p9._buildProps()
	assert p9.echo == dict(jobs=[0,1], type=dict(stderr=r'^log', stdout=r'^log'))

def test_buildinput(tmpdir, caplog):
	p10 = Proc()
	p10.input = 'a, b:file, '
	p10.input = ('1', 'infile')
	p10._buildInput()
	assert len(p10.input) == 2
	assert p10.input['a'] == ('var', ['1'])
	assert p10.input['b'] == ('file', ['infile'])
	assert p10.size == 1

	p10.input = 'a:x:y'
	with pytest.raises(ProcInputError):
		p10._buildInput()

	p101 = Proc()
	p101.props.channel = Channel.create([(1,3), (2,4)])
	p10.depends = p101
	p10.input = 'a, b, c'
	p10.input = lambda ch: ch.cbind(1).cbind(2)
	caplog.clear()
	p10._buildInput()
	assert 'Not all data are used as input' in caplog.text
	assert len(p10.input) == 3
	assert p10.size == 2
	assert p10.input['a'] == ('var', [1,2])
	assert p10.input['b'] == ('var', [3,4])
	assert p10.input['c'] == ('var', [1,1])

	p10.input = 'a:files, b:files, c'
	p10.input = Channel.create([['infile1'], ['infile2']])
	p10._buildInput()
	assert 'No data found for input key "b"' in caplog.text
	assert 'No data found for input key "c"' in caplog.text
	caplog.clear()
	assert len(p10.input) == 3
	assert p10.size == 2
	assert p10.input['a'] == ('files', [['infile1'], ['infile2']])
	assert p10.input['b'] == ('files', [[], []])
	assert p10.input['c'] == ('var', ['', ''])

	p10.props.template = TemplateLiquid
	p10.props.workdir = tmpdir / 'test_buildinput_p10'
	p10.resume = 'resume'
	fs.remove(Path(p10.workdir) / 'proc.settings.yaml')
	with pytest.raises(ProcInputError):
		p10._buildInput()
	fs.mkdir(p10.workdir)

	p10.props.input = OBox()
	p10.input['a'] = ('files', [['infile1'], ['infile2']])
	p10.input['b'] = ('files', [[], []])
	p10.input['c'] = ('var', ['', ''])
	p10._saveSettings()
	p10.props.input = None
	p10._buildInput()
	assert len(p10.input) == 3
	assert p10.size == 2
	assert p10.input['a'] == ('files', [['infile1'], ['infile2']])
	assert p10.input['b'] == ('files', [[], []])
	assert p10.input['c'] == ('var', ['', ''])

def test_buildinput_empty(tmpdir):
	sys.argv = ['pytest']
	p102 = Proc()
	p102._buildInput()
	assert p102.size == 0
	assert p102.jobs == []

def test_buildprocvars(tmpdir, caplog):
	p11 = Proc()
	p11.args = {'a': 1}
	p11._buildProcVars()
	assert 'p11: a      => 1' in caplog.text
	assert 'p11: runner => local' in caplog.text
	assert 'p11: size   => 0' in caplog.text
	assert 'exdir' not in caplog.text
	assert p11.procvars['args'] is p11.args

	p11.config.args = {'a': 1}
	p11.exdir = 'abc'
	caplog.clear()
	p11._buildProcVars()
	assert 'p11: exdir  => abc' in caplog.text
	assert p11.procvars['args'] == p11.args
	assert p11.procvars['args'] is not p11.args

def test_buildoutput(tmpdir):
	p12 = Proc()
	p12.output = 'a'
	with pytest.raises(ProcOutputError):
		p12._buildOutput()
	p12.output = 'a:b:c:d'
	with pytest.raises(ProcOutputError):
		p12._buildOutput()
	p12.output = {'a': '1', 'b': 2}
	with pytest.raises(ProcOutputError):
		p12._buildOutput()
	p12.output = 'a:b:c'
	with pytest.raises(ProcOutputError):
		p12._buildOutput()
	p12.output = '1not.identifier:file'
	with pytest.raises(ProcOutputError):
		p12._buildOutput()
	p12.output = 'a:1, b:file:infile'
	p12.props.template = TemplateLiquid
	p12._buildOutput()
	assert len(p12.output) == 2
	assert p12.output['a'][0] == 'var'
	assert p12.output['a'][1].render() == '1'
	assert p12.output['b'][0] == 'file'
	assert p12.output['b'][1].render() == 'infile'

def test_buildscript(tmpdir, caplog):
	p13 = Proc()
	p13.props.template = TemplateLiquid
	p13._buildScript()
	assert 'No script specified' in caplog.text

	scriptfile = tmpdir / 'test_buildscript.txt'
	scriptfile.write_text('# script')
	p13.script = 'file:%s' % scriptfile
	fs.remove(scriptfile)
	with pytest.raises(ProcScriptError):
		p13._buildScript()

	scriptfile.write_text('''# script
	# PYPPL INDENT REMOVE
	abs
	bin
	# PYPPL INDENT KEEP
	callable
	def''')
	caplog.clear()
	p13.lang = 'python'
	p13._buildScript()
	assert 'Using template file: ' in caplog.text
	assert p13.script.render() == '''#!/usr/bin/env python
# script
abs
bin
	callable
	def
'''

def test_savesettings(tmpdir, caplog):
	import yaml
	p14 = Proc()
	p14.props.template = TemplateLiquid
	p14.props.workdir = tmpdir / 'test_savesettings_p14'
	p14.props.workdir.mkdir()
	p14._saveSettings()
	assert 'Settings saved to: ' in caplog.text

	with (p14.props.workdir / 'proc.settings.yaml').open() as f:
		saved = yaml.load(f, Loader = yaml.Loader)
	assert saved['workdir'] == p14.props.workdir

def test_buildjobs(tmpdir, caplog):
	p15 = Proc()
	p15.props.jobs = [None, None]
	p15._buildJobs()
	assert 'No data found for jobs, process will be skipped.' in caplog.text

	p15.props.input['a'] = ('var', [1,2,3])
	p15.props.jobs = [1,2,3]
	p15.props.runner = 'nosuchrunner'
	with pytest.raises(ProcAttributeError):
		p15._buildJobs()

	p15.props.runner = 'local'
	p15._buildJobs()
	assert len(p15.props.jobs) == 3
	assert p15.props.jobs[0].__class__.__name__ == 'RunnerLocal'

def test_readconfig(tmpdir):
	p16 = Proc()
	assert p16.id == 'p16'
	# nothing updated
	p16._readConfig(None, Config())
	assert p16.id == 'p16'

	config = Config()
	config._load({'f20': {'forks': 20}})
	p16.forks = 10
	p16._readConfig({'forks': 30}, config)
	assert p16.id == 'p16'
	assert p16.forks == 10
	assert p16.runner == 'local'
	assert p16.config.runner == '__tmp__'

	p17 = Proc()
	p17.forks = 10
	config = Config()
	config._load({'f30': {'forks': 20}})
	# no such profile in config
	p17._readConfig('dry', config)
	assert p17.forks == 10
	assert p17.runner == 'dry'
	assert p17.config.runner == 'dry'

def test_readconfig_preload(tmpdir):
	config._load({'xyz': {'runner': 'sge', 'forks': 50}})
	p18 = Proc()
	p18._readConfig('xyz', Config())
	assert p18.runner == 'sge'
	assert p18.forks == 50
	assert p18.config.runner == 'xyz'

def test_readconfig_preset(tmpdir):
	p181 = Proc()
	p181.runner = 'xyz'
	config = Config()
	cfile = tmpdir / 'test_readconfig_preset.ini'
	cfile.write_text("""
[xyz]
runner: sge
forks: 50
""")
	config._load(cfile)
	p181._readConfig('', config)
	assert p181.runner == 'sge'
	assert p181.forks == 50
	assert p181.config.runner == 'xyz'

def test_runcmd(tmpdir, caplog):
	p19 = Proc()
	p19.props.template = TemplateLiquid
	p19._runCmd('pre')
	assert 'Running ' not in caplog.text

	p19.preCmd = 'echo "Hello world!"'
	p19._runCmd('before')
	assert 'Running <beforeCmd> ...' in caplog.text
	assert 'Hello world!' in caplog.text

	p19.postCmd = 'nosuchcommand'
	with pytest.raises(ProcRunCmdError):
		p19._runCmd('post')

def test_preruntidy(tmpdir, caplog):
	p20 = Proc()
	p20.input = 'a, b'
	p20.input = [(1,2), (3,4), (5,6)]
	p20.callfront = lambda p: setattr(p, 'forks', 20)
	p20._preRunTidy()
	assert 'Calling callfront ...' in caplog.text
	assert p20.forks == 20
	assert p20.size == 3

def test_runjobs(tmpdir):
	p21 = Proc()
	p21.forks = 3
	p21.input = 'a, b'
	p21.input = [(1,2), (3,4), (5,6)]
	p21.output = 'a:{{i.a}}, b:{{i.b}}'
	p21.script = 'echo Hello world!'
	p21._preRunTidy()
	p21._runJobs()
	assert p21.channel == [('1','2'), ('3','4'), ('5','6')]
	assert p21.channel.a.flatten() == ['1','3','5']
	assert p21.channel.b.flatten() == ['2','4','6']

def test_postruntidy(tmpdir, caplog):
	p22 = Proc()
	p22.resume = 'skip+'
	p22.callback = lambda p: p.props.update({'channel': p.channel.cbind(1, 2)})
	p22._postRunTidy()
	assert p22.channel == [(1, 2)]

	p23 = Proc()
	p23.forks = 5
	p23.input = 'a, b'
	p23.input = [(1,2), (3,4), (5,6), (7,8), (9,10)]
	p23.output = 'a:{{i.a}}, b:{{i.b}}'
	p23.script = 'echo Hello world!'
	p23.errhow = 'ignore'
	p23.callback = lambda p: setattr(p, 'forks', 10)
	p23._preRunTidy()
	p23._runJobs()
	p23.jobs[0].state = STATES.BUILTFAILED
	p23.jobs[1].state = STATES.SUBMITFAILED
	p23.jobs[2].state = STATES.DONE
	p23.jobs[3].state = STATES.DONECACHED
	p23.jobs[4].state = STATES.ENDFAILED
	p23._postRunTidy()
	assert ' Jobs (Cached: 1, Succ: 1, B.Fail: 1, S.Fail: 1, R.Fail: 1)' in caplog.text
	assert 'Failed but ignored (totally 3).' in caplog.text
	assert p23.forks == 10

	p23.errhow = 'terminate'
	caplog.clear()
	with pytest.raises(SystemExit):
		p23._postRunTidy()
	assert 'Cached: 4' in caplog.text
	assert 'Succeeded: 3' in caplog.text
	assert 'Building failed: 1' in caplog.text
	assert 'Submission failed: 2' in caplog.text
	assert 'Running failed: 5' in caplog.text

def test_run(tmpdir, caplog):
	sys.argv = ['pytest']
	p24 = Proc()
	p24.resume = 'resume'
	p24.props.workdir = tmpdir / 'test_run_p24'
	fs.mkdir(p24.workdir)
	(p24.workdir / 'proc.settings.yaml').write_text('input: ')
	p24.run('dry', Config())
	assert 'Previous processes skipped.' in caplog.text
	assert p24.runner == 'dry'

	p25 = Proc()
	p25.resume = 'skip'
	caplog.clear()
	p25.run(None, Config())
	assert 'Pipeline will resume from future processes.' in caplog.text

	p25.resume = 'skip+'
	caplog.clear()
	p25.props.workdir = tmpdir / 'test_run_p25'
	fs.mkdir(p25.workdir)
	(p25.workdir / 'proc.settings.yaml').write_text('input: ')
	p25.run(None, Config())
	assert 'Data loaded, pipeline will resume from future processes.' in caplog.text
