from pathlib import Path
import traceback
import pytest
from diot import Diot
from pyppl.pyppl import PROCESSES, _get_next_procs, _anything2procs, PyPPL, PIPELINES
from pyppl.exception import ProcessAlreadyRegistered, PyPPLInvalidConfigurationKey, PyPPLNameError, PyPPLWrongPositionMethod, PyPPLMethodExists
from pyppl.proc import Proc
from pyppl.config import config
from pyppl.logger import logger
from pyppl.plugin import hookimpl

# avoid other tests registering processes
PROCESSES.clear()

def test_register_proc():
	p1 = Proc('p1')
	assert p1 in PROCESSES

	p2 = Proc('p2')
	assert p2 in PROCESSES

	with pytest.raises(ProcessAlreadyRegistered) as exc:
		p3 = Proc('p2')
	assert "p2 = Proc('p2')" in str(exc.value)
	assert "p3 = Proc('p2')" in str(exc.value)

def test_next_possible_procs():
	pNPProcs1 = Proc()
	pNPProcs2 = Proc()
	pNPProcs3 = Proc()
	pNPProcs4 = Proc()
	pNPProcs5 = Proc()

	pNPProcs2.depends = pNPProcs1
	pNPProcs3.depends = pNPProcs2
	pNPProcs4.depends = pNPProcs3
	pNPProcs5.depends = pNPProcs4

	assert _get_next_procs([pNPProcs1]) == [pNPProcs2]
	assert _get_next_procs([pNPProcs2]) == [pNPProcs3]
	assert _get_next_procs([pNPProcs3]) == [pNPProcs4]
	assert _get_next_procs([pNPProcs4]) == [pNPProcs5]
	assert _get_next_procs([pNPProcs5]) == []

	pNPProcs11 = Proc()
	pNPProcs12 = Proc()
	pNPProcs13 = Proc()
	pNPProcs14 = Proc()
	pNPProcs15 = Proc()

	pNPProcs13.depends = pNPProcs11, pNPProcs12
	pNPProcs14.depends = pNPProcs11, pNPProcs12
	pNPProcs15.depends = pNPProcs11, pNPProcs14

	assert _get_next_procs([pNPProcs11]) == []
	assert _get_next_procs([pNPProcs11, pNPProcs12]) == [pNPProcs13, pNPProcs14]
	assert _get_next_procs([pNPProcs11, pNPProcs12, pNPProcs13, pNPProcs14]) == [pNPProcs15]

	# cyclic dependencies
	pNPProcs21 = Proc()
	pNPProcs22 = Proc()
	pNPProcs23 = Proc()
	pNPProcs22.depends = pNPProcs21
	pNPProcs23.depends = pNPProcs22
	pNPProcs21.depends = pNPProcs23

	assert _get_next_procs([pNPProcs21]) == [pNPProcs22]
	assert _get_next_procs([pNPProcs21, pNPProcs22]) == [pNPProcs23]
	assert _get_next_procs([pNPProcs21, pNPProcs22, pNPProcs23]) == []

	# auto dependencies
	pNPProcs31 = Proc()
	pNPProcs31.depends = pNPProcs31
	assert _get_next_procs([pNPProcs31]) == []

def test_anything2procs():
	pAny2Procs1 = Proc()
	pAny2Procs2 = Proc()
	assert _anything2procs(pAny2Procs1) == [pAny2Procs1]
	assert _anything2procs('pAny2Procs1') == [pAny2Procs1]
	assert _anything2procs(pAny2Procs1, pAny2Procs2) == [pAny2Procs1, pAny2Procs2]
	assert set(_anything2procs('pAny2Procs?')) == {pAny2Procs1, pAny2Procs2}

	from pyppl.procset import ProcSet
	psAny2Procs = ProcSet(pAny2Procs1, pAny2Procs2)
	assert _anything2procs(psAny2Procs) == [psAny2Procs.pAny2Procs1]
	assert _anything2procs(psAny2Procs, procset = 'ends') == [psAny2Procs.pAny2Procs2]

def test_init(caplog):
	PIPELINES.clear()
	ppl = PyPPL(forks = 10)
	assert 'Read from PYPPL.osenv' in caplog.text
	assert 'PIPELINE: PyPPL_1' in caplog.text
	assert ppl.name == 'PyPPL_1'
	assert ppl.runtime_config.forks == 10

	with pytest.raises(PyPPLNameError):
		PyPPL(name = 'PyPPL_1')
	with pytest.raises(PyPPLInvalidConfigurationKey):
		PyPPL(a = 1)

	ppl = PyPPL(logger = {'file': True})
	logfile = Path('.') / 'PyPPL_2.pyppl.log'
	assert logfile.is_file()
	logfile.unlink()

	caplog.clear()
	class pyppl_plugin:
		__version__ = '0.1.0'

	ppl = PyPPL(plugins = [pyppl_plugin()])
	assert 'Loaded plugin: pyppl_plugin (v0.1.0)' in caplog.text

def test_start(caplog):

	pStart1 = Proc()
	pStart2 = Proc()
	pStart2.depends = pStart1

	ppl = PyPPL().start(pStart1)
	assert ppl.starts == [pStart1]
	assert ppl.ends == [pStart2]
	assert ppl.procs == [pStart1, pStart2]

	caplog.clear()
	# start process depending on others
	ppl = PyPPL().start(pStart2)
	assert "Start process Proc(name='pStart2.notag') is depending on others: [Proc(name='pStart1.notag')]" in caplog.text

def test_start_nonstart_dependencies(caplog):
	# non-start process dependencies
	pStart11 = Proc()
	pStart12 = Proc()
	pStart13 = Proc()
	pStart13.depends = pStart11, pStart12

	caplog.clear()
	ppl = PyPPL().start(pStart11)
	assert "[Proc(name='pStart13.notag')] will not run, as they depend on non-start processes or themselves." in caplog.text
	assert ppl.starts == ppl.ends == ppl.procs == [pStart11]

def test_start_auto_dependencies(caplog):
	# auto dependencies
	pStart21 = Proc()
	pStart21.depends = pStart21
	caplog.clear()
	ppl = PyPPL().start(pStart21)
	assert "[Proc(name='pStart21.notag')] will not run, as they depend on non-start processes or themselves." in caplog.text

def test_start_cyclic_dependencies(caplog):
	# cyclic dependencies 2
	pStart31 = Proc()
	pStart32 = Proc()
	pStart32.depends = pStart31
	pStart31.depends = pStart32
	caplog.clear()
	ppl = PyPPL().start(pStart31)
	assert "Start process Proc(name='pStart31.notag') is depending on others: [Proc(name='pStart32.notag')]" in caplog.text

	caplog.clear()
	ppl = PyPPL().start(pStart31, pStart32)
	assert "Start process Proc(name='pStart31.notag') is depending on others: [Proc(name='pStart32.notag')]" in caplog.text

def test_run(caplog):
	class pyppl_stoprun:
		@hookimpl
		def proc_prerun(self, proc):
			return False
	from pyppl.job import Job
	from pyppl.jobmgr import STATES
	Job.state = STATES.DONE
	pRun1 = Proc()
	pRun1.input = {'a:var': [1]}
	pRun1.output = 'a:var:1'
	PyPPL(plugins = [pyppl_stoprun()]).start(pRun1).run('local')
	assert 'pRun1: No description.' in caplog.text

	caplog.clear()
	pRun2 = pRun1.copy()
	# plugins regiested
	PyPPL(logger_level = 'TITLE', config_files = dict(default = {}),
		runner = 'local', runner_sge_q = '1-day', envs_k = 'k').start(pRun2).run()
	assert 'pRun2 (pRun1): No description.' in caplog.text
	assert pRun2.envs.k == 'k'
	assert pRun2.runner.runner == 'local'
	assert pRun2.runner.sge_q == '1-day'

def test_config_in_construct():
	class pyppl_pconfig:
		@hookimpl
		def proc_init(self, proc):
			proc.add_config('x')

	from pyppl.plugin import config_plugins
	config_plugins(pyppl_pconfig())
	from pyppl.job import Job
	from pyppl.jobmgr import STATES
	Job.state = STATES.DONE
	pPCIC = Proc()
	pPCIC.input = {'a:var': [1]}
	pPCIC.output = 'a:var:1'
	PyPPL(config_x = 10).start(pPCIC).run()
	assert pPCIC.config.x == 10

def test_add_method(capsys):
	ppl = PyPPL()

	def themethod(self, a, b = 1):
		print('a = {}, b = {}'.format(a, b))

	ppl.add_method(themethod)
	with pytest.raises(PyPPLMethodExists):
		ppl.add_method(themethod)
	with pytest.raises(PyPPLWrongPositionMethod):
		ppl.themethod(a = 3)
	ppl.starts = True
	ppl.themethod(a = 3)
	assert 'a = 3, b = 1' in capsys.readouterr().out

	ppl2 = PyPPL()
	def themethod2(self, a, b=4):
		print('a = {}, b = {}'.format(a,b))

	ppl2.add_method(themethod2, require = 'run')
	with pytest.raises(PyPPLWrongPositionMethod):
		ppl2.themethod2(a = 3)

	ppl2.procs = [Diot(channel = True)]
	ppl2.themethod2(a = 3)
	assert 'a = 3, b = 4' in capsys.readouterr().out

