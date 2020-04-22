from pathlib import Path
import traceback
import os
import sys
import pytest
from diot import Diot
from pyppl.pyppl import PROCESSES, _get_next_procs, _anything2procs, PyPPL, PIPELINES
from pyppl.exception import ProcessAlreadyRegistered, PyPPLInvalidConfigurationKey, PyPPLNameError, PyPPLWrongPositionMethod, PyPPLMethodExists
from pyppl.proc import Proc
from pyppl.config import config
from pyppl.logger import logger
from pyppl.plugin import hookimpl, pluginmgr

# avoid other tests registering processes
PROCESSES.clear()

def setup_function():
    for plugin in pluginmgr.get_plugins():
        pluginmgr.unregister(plugin)

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
    assert _get_next_procs([pNPProcs11,
                            pNPProcs12]) == [pNPProcs13, pNPProcs14]
    assert _get_next_procs([pNPProcs11, pNPProcs12, pNPProcs13,
                            pNPProcs14]) == [pNPProcs15]

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
    assert _anything2procs(pAny2Procs1,
                           pAny2Procs2) == [pAny2Procs1, pAny2Procs2]
    assert set(_anything2procs('pAny2Procs?')) == {pAny2Procs1, pAny2Procs2}

    from pyppl.procset import ProcSet
    psAny2Procs = ProcSet(pAny2Procs1, pAny2Procs2)
    assert _anything2procs(psAny2Procs) == [psAny2Procs.pAny2Procs1]
    assert _anything2procs(psAny2Procs,
                           procset='ends') == [psAny2Procs.pAny2Procs2]


def test_init(caplog):
    PIPELINES.clear()
    ppl = PyPPL(name='ppl', forks=10)

    assert ppl.name == 'ppl'
    assert 'Read from PYPPL.osenv' in caplog.text
    assert ('PIPELINE: %s' % ppl.name) in caplog.text
    assert ppl.runtime_config.forks == 10
    with pytest.raises(PyPPLNameError):
        PyPPL(name=ppl.name)
    with pytest.raises(PyPPLInvalidConfigurationKey):
        PyPPL(a=1)

    ppl = PyPPL(logger={'file': True})
    logfile = Path('.') / ('%s.pyppl.log' % ppl.name)
    assert logfile.is_file()
    logfile.unlink()

    caplog.clear()

    class pyppl_plugin:
        __version__ = '0.1.0'

    ppl = PyPPL(plugins=[pyppl_plugin()])
    assert 'Loaded plugins:' in caplog.text


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
    assert "Start process 'pStart2.notag' ignored, as it's depending on:" in caplog.text
    assert "[Proc(name='pStart1.notag')]" in caplog.text


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
    pStart20 = Proc()
    pStart21 = Proc()
    pStart21.depends = pStart20, pStart21
    caplog.clear()
    ppl = PyPPL().start(pStart20)
    assert "[Proc(name='pStart21.notag')] will not run, as they depend on non-start processes or themselves." in caplog.text


def test_start_cyclic_dependencies(caplog):
    # cyclic dependencies 2
    pStart31 = Proc()
    pStart32 = Proc()
    pStart32.depends = pStart31
    pStart31.depends = pStart32
    caplog.clear()
    ppl = PyPPL().start(pStart31)
    assert "Start process 'pStart31.notag' ignored, as it's depending on:" in caplog.text
    assert "[Proc(name='pStart32.notag')]" in caplog.text

    caplog.clear()
    ppl = PyPPL().start(pStart31, pStart32)
    assert "Start process 'pStart31.notag' ignored, as it's depending on:" in caplog.text
    assert "[Proc(name='pStart32.notag')]" in caplog.text


def test_run(caplog, tmp_path):
    class pyppl_stoprun:
        @hookimpl
        def proc_prerun(self, proc):
            return False

    from pyppl.job import Job
    from pyppl.jobmgr import STATES
    Job.state = STATES.DONE
    pRun1 = Proc(ppldir=tmp_path)
    pRun1.input = {'a:var': [1]}
    pRun1.output = 'a:var:1'
    PyPPL(plugins=[pyppl_stoprun()]).start(pRun1).run('local')
    assert 'pRun1.notag: No description.' in caplog.text

    caplog.clear()
    pRun2 = pRun1.copy(ppldir=tmp_path, desc = 's'*200)
    # plugins regiested
    PyPPL(logger_level='TITLE',
          config_files=dict(default={}),
          runner='local',
          runner_sge_q='1-day',
          envs_k='k').start(pRun2).run()
    assert 'pRun2.notag (pRun1): ' in caplog.text
    assert '  sssssssssssss' in caplog.text
    assert pRun2.envs.k == 'k'
    assert pRun2.runner.runner == 'local'
    assert pRun2.runner.sge_q == '1-day'

def test_run_settings(caplog, tmp_path):
    # let's see if PyPPL().run(profile) is inheriting the default config's
    # runner settings
    # using PyPPL.osenv
    os.environ['PYPPLTEST_default_runner'] = 'py:{"sge_prescript": "someprescripts"}'
    os.environ['PYPPLTEST_sgexd_runner'] = 'py:{"sge_m": "b"}'
    # we need to insert this to the config to mimic module is loaded before
    # the envs are set
    config._load('PYPPLTEST.osenv')
    assert config.runner.sge_prescript == 'someprescripts'

    pRun3 = Proc(ppldir=tmp_path)
    pRun3.input = {'a:var': [1]}
    pRun3.output = 'a:var:1'
    PyPPL(runner_sge_q='x-day').start(pRun3).run('sgexd')
    assert pRun3.runner.sge_m == 'b'
    assert pRun3.runner.sge_prescript == 'someprescripts'

    pRun4 = Proc(ppldir=tmp_path)
    pRun4.input = {'a:var': [1]}
    pRun4.output = 'a:var:1'
    pRun4.runner = 'sgexd'
    PyPPL(runner_sge_q='x-day').start(pRun4).run()
    assert pRun4.runner.sge_m == 'b'
    assert pRun4.runner.sge_prescript == 'someprescripts'



def test_config_in_construct(tmp_path):
    class pyppl_pconfig:
        @hookimpl
        def proc_init(self, proc):
            proc.add_config('x')

    from pyppl.plugin import config_plugins
    config_plugins(pyppl_pconfig())
    from pyppl.job import Job
    from pyppl.jobmgr import STATES
    Job.state = STATES.DONE
    pPCIC = Proc(ppldir=tmp_path)
    pPCIC.input = {'a:var': [1]}
    pPCIC.output = 'a:var:1'
    PyPPL(config_x=10).start(pPCIC).run()
    assert pPCIC.config.x == 10


def test_add_method(capsys):
    ppl = PyPPL()

    def themethod(self, a, b=1):
        print('a = {}, b = {}'.format(a, b))

    ppl.add_method(themethod)
    with pytest.raises(PyPPLMethodExists):
        ppl.add_method(themethod)
    with pytest.raises(PyPPLWrongPositionMethod):
        ppl.themethod(a=3)
    ppl.starts = True
    ppl.themethod(a=3)
    assert 'a = 3, b = 1' in capsys.readouterr().out

    ppl2 = PyPPL()

    def themethod2(self, a, b=4):
        print('a = {}, b = {}'.format(a, b))

    ppl2.add_method(themethod2, require='run')
    with pytest.raises(PyPPLWrongPositionMethod):
        ppl2.themethod2(a=3)

    ppl2.procs = [Diot(channel=True)]
    ppl2.themethod2(a=3)
    assert 'a = 3, b = 4' in capsys.readouterr().out

def test_depends_printing(tmp_path, caplog):

    pDepPrinting1 = Proc(ppldir=tmp_path)
    pDepPrinting2 = Proc(ppldir=tmp_path)
    pDepPrinting3 = Proc(ppldir=tmp_path)
    pDepPrinting4 = Proc(ppldir=tmp_path)
    pDepPrinting5 = Proc(ppldir=tmp_path)
    pDepPrinting6 = Proc(ppldir=tmp_path)

    pDepPrinting4.depends = pDepPrinting1, pDepPrinting2, pDepPrinting3,
    pDepPrinting5.depends = pDepPrinting4
    pDepPrinting6.depends = pDepPrinting4

    pDepPrinting1.input = pDepPrinting2.input = pDepPrinting3.input = \
        pDepPrinting4.input = pDepPrinting5.input = pDepPrinting6.input = {'a:var': [1]}
    pDepPrinting1.output = pDepPrinting2.output = pDepPrinting3.output = \
        pDepPrinting4.output = pDepPrinting5.output = pDepPrinting6.output = 'a:var:1'

    PyPPL().start(pDepPrinting1, pDepPrinting2, pDepPrinting3).run()
    assert '| pDepPrinting1.notag |                           | pDepPrinting5.notag |' in caplog.text
    assert '| pDepPrinting2.notag | => pDepPrinting4.notag => | pDepPrinting6.notag |' in caplog.text
    assert '| pDepPrinting3.notag |                           |                     |' in caplog.text

    caplog.clear()

    pDepPrinting11 = Proc(ppldir=tmp_path)
    pDepPrinting12 = Proc(ppldir=tmp_path)
    pDepPrinting13 = Proc(ppldir=tmp_path)
    pDepPrinting14 = Proc(ppldir=tmp_path)
    pDepPrinting15 = Proc(ppldir=tmp_path)
    pDepPrinting16 = Proc(ppldir=tmp_path)
    pDepPrinting17 = Proc(ppldir=tmp_path)

    pDepPrinting11.input = pDepPrinting12.input = pDepPrinting13.input = \
        pDepPrinting14.input = pDepPrinting15.input = pDepPrinting16.input = \
        pDepPrinting17.input = {'a:var': [1]}
    pDepPrinting11.output = pDepPrinting12.output = pDepPrinting13.output = \
        pDepPrinting14.output = pDepPrinting15.output = pDepPrinting16.output = \
        pDepPrinting17.output = 'a:var:1'

    pDepPrinting13.depends = pDepPrinting11, pDepPrinting12
    pDepPrinting14.depends = pDepPrinting13
    pDepPrinting15.depends = pDepPrinting13
    pDepPrinting16.depends = pDepPrinting13
    pDepPrinting17.depends = pDepPrinting13

    PyPPL().start(pDepPrinting11, pDepPrinting12).run()
    assert '|                      |                            | pDepPrinting14.notag |' in caplog.text
    assert '| pDepPrinting11.notag | => pDepPrinting13.notag => | pDepPrinting15.notag |' in caplog.text
    assert '| pDepPrinting12.notag |                            | pDepPrinting16.notag |' in caplog.text
    assert '|                      |                            | pDepPrinting17.notag |' in caplog.text


