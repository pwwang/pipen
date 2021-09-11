import pytest
from pipen import Proc, Pipen
from pipen.exceptions import PipenException, ProcDependencyError

from .helpers import ErrorProc, NormalProc, SimpleProc, get_simple_pipen


def test_init():
    assert isinstance(get_simple_pipen(), Pipen)


def test_run():
    pipen_simple = get_simple_pipen()
    ret = pipen_simple.run(SimpleProc)
    assert ret
    pipen_simple = get_simple_pipen()
    ret = pipen_simple.run([ErrorProc])
    assert not ret


def test_no_start_procs():
    pipen_simple = get_simple_pipen()
    with pytest.raises(ProcDependencyError):
        pipen_simple.run()


def test_cannot_run_twice():
    pipen = get_simple_pipen()
    pipen.run(SimpleProc)
    with pytest.raises(PipenException):
        pipen.run()

def test_cyclic_dependency():
    """
    proc1(start) --> proc2 --> proc3(start)
                           <--
    """
    pipen_simple = get_simple_pipen()
    proc1 = Proc.from_proc(NormalProc, input_data=[1])
    proc2 = Proc.from_proc(NormalProc)
    proc3 = Proc.from_proc(NormalProc, requires=proc2)
    proc2.requires = [proc1, proc3]
    # trigger requires/nexts computation
    proc2.__init_subclass__()

    with pytest.raises(ProcDependencyError, match="Cyclic dependency"):
        pipen_simple.run(proc1, proc3)


def test_no_next_procs():
    """
    proc1 --> proc2 --> proc3
                    <--
    """
    pipen_simple = get_simple_pipen()
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
        pipen_simple.run(proc1)
