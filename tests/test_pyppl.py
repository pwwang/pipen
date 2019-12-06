import sys
import os
os.environ['PYPPL_default__log'] = 'py:{"levels": "all"}'
from pathlib import Path
import pytest
from pyppl import PyPPL, Proc, Diot, ProcSet, runner
from pyppl.utils import config, fs
from pyppl.proctree import ProcTree
from pyppl.exception import PyPPLProcRelationError, ProcTreeProcExists, RunnerClassNameError

def setup_module(module):
	PyPPL.COUNTER = 0

def teardown_module(module):
	for path in Path().glob('*.log'):
		fs.remove(path)
	for path in Path().glob('*.svg'):
		fs.remove(path)
	for path in Path().glob('*.dot'):
		fs.remove(path)

@pytest.fixture(scope = 'function')
def pset():
	ProcTree.NODES.clear()
	p14 = Proc()
	p15 = Proc()
	p16 = Proc()
	p17 = Proc()
	p18 = Proc()
	p19 = Proc()
	p20 = Proc()
	# p15 -> p16  ->  p17 -> 19
	# p14 _/  \_ p18_/  \_ p20
	#           hide
	#p18.hide = True
	p20.depends = p17
	p19.depends = p17
	p17.depends = p16, p18
	p18.depends = p16
	p16.depends = p14, p15
	return Diot(p15 = p15, p16 = p16, p17 = p17, p18 = p18, p19 = p19, p20 = p20, p14 = p14)

def test_preload_config():
	assert config.desc == 'No description'
	assert PyPPL.COUNTER == 0

def test_init(tmp_path, caplog):
	config._log.file = False
	ppl = PyPPL()
	assert PyPPL.COUNTER == 1
	assert ppl.config == config
	assert ppl.config._log.file == False

	os.environ['PYPPL2_default__log'] = 'py:{"file": True}'
	ppl = PyPPL(cfgfile = 'PYPPL2.osenv')
	assert ppl.counter == 1
	assert ppl.config._log.file == Path('./%s.1.pyppl.log' % (Path(sys.argv[0]).stem))

	caplog.clear()
	ppl = PyPPL(cfgfile = tmp_path / 'nosuchfile.ini')
	assert 'Configuration file does not exist: ' in caplog.text

	tomlfile = tmp_path / 'test_init.toml'
	tomlfile.write_text('[default]\nforks = 2')
	ppl = PyPPL(cfgfile = tomlfile)
	assert ppl.config.forks == 2
	ppl = PyPPL({'default': {'forks': 3}}, cfgfile = tomlfile)
	assert ppl.config.forks == 3

	yamlfile = tmp_path / 'test_init.yaml'
	yamlfile.write_text('default:\n  forks: 4')
	ppl = PyPPL(cfgfile = yamlfile)
	assert ppl.config.forks == 4

@pytest.fixture
def defprocs():
	ProcTree.NODES.clear()
	ret = Diot(
		pAny2Procs1 = Proc(),
		pAny2Procs2 = Proc(),
		pAny2Procs3 = Proc(),
		pAny2Procs4 = Proc(),
		pAny2Procs51 = Proc(tag = '51', id = 'pAny2Procs5'),
		pAny2Procs52 = Proc(tag = '52', id = 'pAny2Procs5'),
		pAny2Procs6 = Proc(),
		pAny2Procs7 = Proc(),)
	ret.aAggr = ProcSet(ret.pAny2Procs6, ret.pAny2Procs7)
	ret.aAggr.starts = [ret.aAggr.pAny2Procs6, ret.aAggr.pAny2Procs7]
	ProcTree.register(ret.pAny2Procs1)
	ProcTree.register(ret.pAny2Procs2)
	ProcTree.register(ret.pAny2Procs3)
	ProcTree.register(ret.pAny2Procs4)
	ProcTree.register(ret.pAny2Procs51)
	ProcTree.register(ret.pAny2Procs52)
	return ret

@pytest.mark.parametrize('args,procnames', [
	('DEFPROCS.pAny2Procs1', ['pAny2Procs1']),
	(['DEFPROCS.pAny2Procs1'], ['pAny2Procs1']),
	(['abc'], []),
	(['DEFPROCS.aAggr'], ['pAny2Procs6@aAggr', 'pAny2Procs7@aAggr']),
	(['pAny2Procs5*'], ['pAny2Procs5.51', 'pAny2Procs5.52']),
	(['pAny2Procs5.51'], ['pAny2Procs5.51']),
	(['pAny2Procs1.notag'], ['pAny2Procs1']),
	(['pAny2Procs5', 'DEFPROCS.aAggr', ['DEFPROCS.pAny2Procs2', 'pAny2Procs1.notag']], ['pAny2Procs5.51', 'pAny2Procs5.52', 'pAny2Procs6@aAggr', 'pAny2Procs7@aAggr', 'pAny2Procs2', 'pAny2Procs1'])
])
def test_procsselector(args, procnames, defprocs):
	def args2selectors(args):
		if isinstance(args, str) and args.startswith('DEFPROCS.'):
			return defprocs[args[9:]]
		if isinstance(args, str):
			return args
		for i, arg in enumerate(args):
			args[i] = args2selectors(arg)
		return args
	args = args2selectors(args)
	procs = PyPPL._procsSelector(args)
	assert [proc.name(True) for proc in procs] == procnames

def test_start(pset, caplog):
	PyPPL().start(pset.p14, pset.p15)
	assert 'Start process' not in caplog.text
	PyPPL().start(pset.p16, pset.p15)
	assert 'Start process' in caplog.text

def test_resume_exc(pset):
	# p15 -> p16  ->  p17 -> 19
	# p14 _/  \_ p18_/  \_ p20
	#           hide
	ppl = PyPPL().start(pset.p14, pset.p15)
	with pytest.raises(PyPPLProcRelationError):
		ppl._resume(pset.p18)
	ppl._resume(pset.p19, pset.p20)

def test__resume(pset):
	ppl = PyPPL().start(pset.p14, pset.p15)
	ppl._resume(pset.p16, plus = True)
	assert pset.p16.resume == 'resume+'
	assert pset.p14.resume == 'skip+'
	assert pset.p15.resume == 'skip+'

def test_resume(pset):
	ppl = PyPPL().start(pset.p14, pset.p15)
	ppl.resume('')
	ppl.resume(pset.p16)
	assert pset.p16.resume == 'resume'
	assert pset.p14.resume == 'skip'
	assert pset.p15.resume == 'skip'

def test_resume2(pset):
	ppl = PyPPL().start(pset.p14, pset.p15)
	ppl.resume2('')
	ppl.resume2(pset.p16)
	assert pset.p16.resume == 'resume+'
	assert pset.p14.resume == 'skip+'
	assert pset.p15.resume == 'skip+'

# moved to flowchart plugin
# def test_showallroutes(pset, caplog):
# 	# p15 -> p16  ->  ps -> p19
# 	# p14 _/  \_ p18_/  \_ p20
# 	#           hide
# 	pset.p17.depends = []
# 	ps = ProcSet(Proc(id = 'p1'), Proc(id = 'p2'))
# 	ps.depends = pset.p16, pset.p18
# 	pset.p19.depends = ps
# 	pset.p20.depends = ps
# 	ppl = PyPPL().start(pset.p14, pset.p15)
# 	ppl.showAllRoutes()
# 	assert 'ALL ROUTES:' in caplog.text
# 	assert '* p14 -> p16 -> p18 -> [ps] -> p19' in caplog.text
# 	assert '* p14 -> p16 -> p18 -> [ps] -> p20' in caplog.text
# 	assert '* p14 -> p16 -> [ps] -> p19' in caplog.text
# 	assert '* p14 -> p16 -> [ps] -> p20' in caplog.text
# 	assert '* p15 -> p16 -> p18 -> [ps] -> p19' in caplog.text
# 	assert '* p15 -> p16 -> p18 -> [ps] -> p20' in caplog.text
# 	assert '* p15 -> p16 -> [ps] -> p19' in caplog.text
# 	assert '* p15 -> p16 -> [ps] -> p20' in caplog.text

def test_run(pset, caplog, tmp_path):
	p1 = Proc()
	p2 = Proc()
	p2.depends = p1
	pset.p14.props.origin = 'pOrig'
	for p in pset.values():
		p.input = {'a': [1]}
		p.output = 'a:var:{{i.a}}'
	ppl = PyPPL({'default': {'ppldir': tmp_path / 'test_run_ppldir'}}).start(pset.p14, pset.p15)
	ppl.run({'ppldir': tmp_path / 'test_run_ppldir2'})
	# see if we have the right depends
	assert 'p14: START => p14 => [p16]' in caplog.text
	assert 'p15: START => p15 => [p16]' in caplog.text
	assert 'p16: [p14, p15] => p16 => [p17, p18]' in caplog.text
	assert 'p18: [p16] => p18 => [p17]' in caplog.text
	assert 'p17: [p16, p18] => p17 => [p20, p19]' in caplog.text
	assert 'p19: [p17] => p19 => END' in caplog.text
	assert 'p20: [p17] => p20 => END' in caplog.text
	#assert "p2 won't run as path can't be reached: p2 <- p1" in caplog.text
	assert pset.p14.ppldir == tmp_path / 'test_run_ppldir2'

def test_run_noprofile(pset, tmp_path):
	pset.p14.props.origin = 'pOrig'
	for p in pset.values():
		p.input = {'a': [1]}
		p.output = 'a:var:{{i.a}}'
	ppl = PyPPL({'default': {'ppldir': tmp_path / 'test_run_noprofile'}}).start(pset.p14, pset.p15)
	ppl.run()
	assert pset.p14.ppldir == tmp_path / 'test_run_noprofile'

def test_run_extrafile(tmp_path):
	cfile = tmp_path / 'test_run_extrafile.ini'
	cfile.write_text('''
[default]
forks = 2
[f10]
forks = 10
''')
	pCfile = Proc()
	pCfile.input = {'a': [0]}
	PyPPL(cfgfile = cfile).start(pCfile).run('f10')
	assert pCfile.forks == 10

def test_run_defaultcfg(tmp_path):
	os.environ['PYPPL2_f100_forks'] = '100'
	config._load('PYPPL2.osenv')
	pF100 = Proc()
	pF100.input = {'a': [0]}
	PyPPL().start(pF100).run('f100')
	assert pF100.forks == 100

# moved to plugin
# def test_flowchart(pset, caplog, tmp_path):
# 	for p in pset.values():
# 		p.input = {'a': [1]}
# 		p.output = 'a:var:{{i.a}}'
# 	ppl = PyPPL({'ppldir': tmp_path / 'test_flowchart_ppldir'}).start(pset.p14, pset.p15)
# 	ppl.counter = 0
# 	ppl.flowchart()
# 	assert 'Flowchart file saved to:' in caplog.text
# 	assert 'DOT file saved to:' in caplog.text
# 	assert fs.exists('./%s.pyppl.svg' % Path(sys.argv[0]).stem)
# 	assert fs.exists('./%s.pyppl.dot' % Path(sys.argv[0]).stem)

# 	dot = Path('./%s.pyppl.dot' % Path(sys.argv[0]).stem).read_text()
# 	assert 'p17 -> p19' in dot
# 	assert 'p17 -> p20' in dot
# 	assert 'p16 -> p17' in dot
# 	#assert 'p16 -> p18' in dot # hidden
# 	assert 'p14 -> p16' in dot
# 	assert 'p15 -> p16' in dot

def test_registerProc():
	px = Proc()
	PyPPL._registerProc(px)
	assert px in ProcTree.NODES

def test_checkProc():
	py = Proc()
	pz = Proc(id = 'py')
	PyPPL._registerProc(py)
	PyPPL._registerProc(pz)
	with pytest.raises(ProcTreeProcExists):
		PyPPL._checkProc(pz)

def test_registerRunner():
	with pytest.raises(RunnerClassNameError):
		PyPPL.registerRunner(object)

	class RunnerX:
		pass
	PyPPL.registerRunner(RunnerX)
	assert PyPPL.RUNNERS['x'] is RunnerX

	assert PyPPL.RUNNERS['local'] is runner.RunnerLocal
	assert PyPPL.RUNNERS['dry'] is runner.RunnerDry
	assert PyPPL.RUNNERS['ssh'] is runner.RunnerSsh
	assert PyPPL.RUNNERS['sge'] is runner.RunnerSge
	assert PyPPL.RUNNERS['slurm'] is runner.RunnerSlurm
