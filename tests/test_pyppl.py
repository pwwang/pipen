import sys
import os
os.environ['PYPPL_default_tag'] = 'pyppl'
os.environ['PYPPL_default__log'] = 'py:{"levels": "all"}'
from pathlib import Path
import pytest
from pyppl import PyPPL, Proc, Box, ProcSet
from pyppl.utils import config, fs

def test_preload_config():
	assert config.desc == 'No description'
	assert config.tag == 'pyppl'
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
	fs.remove(ppl.config._log.file)

	caplog.clear()
	ppl = PyPPL(cfgfile = tmp_path / 'nosuchfile.ini')
	assert 'Configuration file does not exist: ' in caplog.text

	tomlfile = tmp_path / 'test_init.toml'
	tomlfile.write_text('[default]\nforks = 2')
	ppl = PyPPL(cfgfile = tomlfile)
	assert ppl.config.forks == 2
	ppl = PyPPL({'forks': 3}, cfgfile = tomlfile)
	assert ppl.config.forks == 3

DEFPROCS = Box(
	pAny2Procs1 = Proc(),
	pAny2Procs2 = Proc(),
	pAny2Procs3 = Proc(),
	pAny2Procs4 = Proc(),
	pAny2Procs51 = Proc(tag = '51', id = 'pAny2Procs5'),
	pAny2Procs52 = Proc(tag = '52', id = 'pAny2Procs5'),
	pAny2Procs6 = Proc(),
	pAny2Procs7 = Proc(),)
DEFPROCS.aAggr = ProcSet(DEFPROCS.pAny2Procs6, DEFPROCS.pAny2Procs7)
DEFPROCS.aAggr.starts = [DEFPROCS.aAggr.pAny2Procs6, DEFPROCS.aAggr.pAny2Procs7]

@pytest.mark.parametrize('args,procnames', [
	(DEFPROCS.pAny2Procs1, ['pAny2Procs1']),
	([DEFPROCS.pAny2Procs1], ['pAny2Procs1']),
	(['abc'], []),
	([DEFPROCS.aAggr], ['pAny2Procs6@aAggr', 'pAny2Procs7@aAggr']),
	(['pAny2Procs5*'], ['pAny2Procs5.51', 'pAny2Procs5.52']),
	(['pAny2Procs5.51'], ['pAny2Procs5.51']),
	(['pAny2Procs1.notag'], ['pAny2Procs1']),
	(['pAny2Procs5', DEFPROCS.aAggr, [DEFPROCS.pAny2Procs2, 'pAny2Procs1.notag']], ['pAny2Procs5.51', 'pAny2Procs5.52', 'pAny2Procs6@aAggr', 'pAny2Procs7@aAggr', 'pAny2Procs2', 'pAny2Procs1'])
])
def test_procsselector(args, procnames):
	procs = PyPPL._procsSelector(args)
	assert [proc.name(True) for proc in procs] == procnames