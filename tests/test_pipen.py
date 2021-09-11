import pytest
from pipen import Proc, Pipen
from pipen.exceptions import PipenException, ProcDependencyError

from .helpers import (
    ErrorProc,
    NormalProc,
    SimpleProc,
    pipen,
    SimplePlugin,
    pipen_with_plugin,
)


def test_init(pipen):
    assert isinstance(pipen, Pipen)


def test_run(pipen):
    ret = pipen.run(SimpleProc)
    assert ret

    ret = pipen.run([ErrorProc])
    assert not ret


def test_no_start_procs(pipen):
    with pytest.raises(ProcDependencyError):
        pipen.run()


def test_cyclic_dependency(pipen):
    """
    proc1(start) --> proc2 --> proc3(start)
                           <--
    """
    proc1 = Proc.from_proc(NormalProc, input_data=[1])
    proc2 = Proc.from_proc(NormalProc)
    proc3 = Proc.from_proc(NormalProc, requires=proc2)
    proc2.requires = [proc1, proc3]
    # trigger requires/nexts computation
    proc2.__init_subclass__()

    with pytest.raises(ProcDependencyError, match="Cyclic dependency"):
        pipen.run(proc1, proc3)


def test_no_next_procs(pipen):
    """
    proc1 --> proc2 --> proc3
                    <--
    """
    proc1 = Proc.from_proc(NormalProc, input_data=[1])
    proc2 = Proc.from_proc(NormalProc)
    proc3 = Proc.from_proc(NormalProc, requires=proc2)
    proc2.requires = [proc1, proc3]
    # trigger requires/nexts computation
    proc2.__init_subclass__()

    with pytest.raises(
        ProcDependencyError,
        match="No available next processes",
    ):
        pipen.run(proc1)


def test_plugins_are_pipeline_dependent(pipen, pipen_with_plugin, caplog):
    simproc = Proc.from_proc(SimpleProc)
    pipen_with_plugin.run(simproc)
    assert "SimplePlugin" in caplog.text

    caplog.clear()
    pipen.run(simproc)  # No simple plugin enabled
    assert "SimplePlugin" not in caplog.text
