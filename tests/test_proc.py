import pytest

import shutil

import pandas
from pipen import Proc
from pipen.exceptions import (
    ProcInputKeyError,
    ProcInputTypeError,
    ProcScriptFileNotFound,
    ProcWorkdirConflictException,
)
from datar.dplyr import mutate

from .helpers import (
    In2Out1Proc,
    NoInputProc,
    NormalProc,
    RelPathScriptProc,
    ScriptNotExistsProc,
    SimpleProc,
    InputTypeUnsupportedProc,
    get_simple_pipen,
)


def test_proc_repr():
    assert repr(SimpleProc) == "<Proc:SimpleProc>"


def test_from_proc_no_name():
    procs = [None]
    with pytest.raises(ValueError, match="Process name cannot"):
        procs[0] = Proc.from_proc(SimpleProc)


def test_from_proc():
    proc = Proc.from_proc(
        SimpleProc,
        name="new_proc",
        desc="new desc",
        args={"a": 1},
        cache=True,
        forks=2,
        plugin_opts={"p": 1},
        scheduler="sge",
        scheduler_opts={"s": 1},
        error_strategy="retry",
        num_retries=10,
        submission_batch=3,
    )
    assert proc.name == "new_proc"
    assert proc.desc == "new desc"
    assert proc.args == {"a": 1}
    assert proc.cache
    assert proc.forks == 2
    assert proc.plugin_opts == {"p": 1}
    assert proc.scheduler == "sge"
    assert proc.scheduler_opts == {"s": 1}
    assert proc.error_strategy == "retry"
    assert proc.num_retries == 10
    assert proc.submission_batch == 3


# def test_from_proc_name_from_assignment():
#     proc = Proc.from_proc(SimpleProc)
#     assert proc.name == "proc"


def test_proc_workdir_conflicts():
    pipen_simple = get_simple_pipen()
    proc1 = Proc.from_proc(NormalProc, name="proc.1")
    Proc.from_proc(NormalProc, name="proc-1", requires=proc1)
    with pytest.raises(ProcWorkdirConflictException):
        pipen_simple.run(proc1)


def test_cached_run(caplog):
    NormalProc.nexts = []
    pipen_simple = get_simple_pipen(927)
    # force uncache NormalProc
    shutil.rmtree(pipen_simple.config.workdir)
    ret = pipen_simple.run(NormalProc)
    assert ret

    pipen_simple = get_simple_pipen(927)
    # trigger caching
    ret = pipen_simple.run(NormalProc)
    assert ret

    assert caplog.text.count("Cached jobs:") == 1


def test_more_nexts():
    proc1 = Proc.from_proc(NormalProc)
    Proc.from_proc(NormalProc, "proc2", requires=proc1)
    Proc.from_proc(NormalProc, "proc3", requires=proc1)
    ret = get_simple_pipen().run(proc1)
    assert ret


def test_proc_no_input():
    pipen = get_simple_pipen()
    with pytest.raises(ProcInputKeyError):
        NoInputProc(pipen)


def test_unsupported_input_type():
    pipen = get_simple_pipen()
    with pytest.raises(ProcInputTypeError):
        InputTypeUnsupportedProc(pipen)


def test_proc_with_input_data():
    pipen = get_simple_pipen()
    proc = Proc.from_proc(NormalProc, input_data=[1])
    pipen.run(proc)
    assert proc.output_data.equals(pandas.DataFrame({"output": ["1"]}))


def test_proc_with_input_callable():
    pipen = get_simple_pipen()
    proc = Proc.from_proc(NormalProc, input_data=[1])
    proc2 = Proc.from_proc(
        NormalProc,
        requires=proc,
        input_data=lambda ch: ch >> mutate(output=2)
    )
    pipen.run(proc)
    assert proc2.output_data.equals(pandas.DataFrame({"output": ["2"]}))

def test_proc_is_singleton():
    pipen = get_simple_pipen()
    p1 = SimpleProc(pipen)
    p2 = SimpleProc(pipen)
    assert p1 is p2

def test_ignore_input_data_of_start_proc(caplog):
    pipen = get_simple_pipen()
    proc = Proc.from_proc(NormalProc, input_data=[1])
    proc2 = Proc.from_proc(NormalProc, requires=proc, input_data=[2])
    pipen.run(proc)
    assert "Ignoring input data" in caplog.text
    assert proc2.output_data.equals(pandas.DataFrame({"output": ["1"]}))

def test_proc_wasted_input_columns(caplog):
    pipen = get_simple_pipen()
    proc1 = Proc.from_proc(NormalProc, input_data=[1])
    proc2 = Proc.from_proc(NormalProc, input_data=[1])
    proc3 = Proc.from_proc(NormalProc, requires=[proc1, proc2])
    pipen.run(proc1, proc2)
    assert "Wasted 1 column" in caplog.text

def test_proc_not_enough_input_columns(caplog):
    pipen = get_simple_pipen()
    proc1 = Proc.from_proc(NormalProc, input_data=[1])
    proc2 = Proc.from_proc(In2Out1Proc, requires=proc1)
    pipen.run(proc1)
    assert "No data column for input: ['in2'], using None" in caplog.text
    assert proc2.output_data.equals(pandas.DataFrame({"out": ["1_None"]}))

def test_proc_relative_path_script():
    pipen = get_simple_pipen()
    proc = RelPathScriptProc(pipen)
    script = proc.script.render()
    assert "AbCdEf" in script

def test_script_file_exists():
    pipen = get_simple_pipen()
    with pytest.raises(ProcScriptFileNotFound):
        ScriptNotExistsProc(pipen)
