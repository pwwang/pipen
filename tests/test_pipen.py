import pytest
from pipen import Proc, Pipen
from pipen.exceptions import (
    PipenException,
    ProcDependencyError,
    PipenSetDataError,
)

from .helpers import (
    ErrorProc,
    NormalProc,
    SimpleProc,
    RelPathScriptProc,
    pipen,
    SimplePlugin,
    pipen_with_plugin,
)


def test_init(pipen):
    assert isinstance(pipen, Pipen)


def test_name():
    p = Pipen()
    assert p.name == "p"
    [p] = [Pipen()]
    assert p.name.startswith("pipen-")


def test_run(pipen):
    ret = pipen.set_starts(SimpleProc).run()
    assert ret

    ret = pipen.set_starts([ErrorProc]).run()
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

    with pytest.raises(ProcDependencyError, match="Cyclic dependency"):
        pipen.set_starts(proc1, proc3).run()


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
        pipen.set_starts(proc1).run()


def test_plugins_are_pipeline_dependent(pipen, pipen_with_plugin, caplog):
    simproc = Proc.from_proc(SimpleProc)
    pipen_with_plugin.set_starts(simproc).run()
    assert "simpleplugin" in caplog.text

    caplog.clear()
    pipen.set_starts(simproc).run()  # No simple plugin enabled
    assert "simpleplugin" not in caplog.text


def test_set_starts_error(pipen):
    with pytest.raises(ProcDependencyError):
        pipen.set_starts(SimpleProc, SimpleProc)


def test_set_data(pipen):
    simproc = Proc.from_proc(SimpleProc, input_data=[1])
    pipen.set_starts(simproc).set_data(None)
    assert simproc.input_data == [1]

    with pytest.raises(PipenSetDataError):
        pipen.set_data([2])


def test_proc_order(pipen):
    proc1 = Proc.from_proc(NormalProc, input_data=[1])
    proc2 = Proc.from_proc(NormalProc, requires=proc1)
    proc3 = Proc.from_proc(NormalProc, requires=proc1, order=-1)

    pipen.set_starts(proc1).run()
    assert pipen.procs == [proc1, proc3, proc2]


def test_proc_inherited(pipen):
    proc1 = Proc.from_proc(RelPathScriptProc)
    proc2 = Proc.from_proc(proc1)
    pipen.set_starts(proc2).set_data([1]).run()
    assert proc2.__doc__ == RelPathScriptProc.__doc__
