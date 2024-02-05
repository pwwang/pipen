import os
import pytest

import pandas
from pipen import Proc
from pipen.exceptions import (
    ProcInputKeyError,
    ProcInputTypeError,
    ProcScriptFileNotFound,
    PipenOrProcNameError,
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
    pipen,  # noqa: F401
)


def test_proc_repr():
    assert repr(SimpleProc) == "<Proc:SimpleProc>"


def test_from_proc_no_name():
    procs = [None]
    with pytest.raises(PipenOrProcNameError):
        procs[0] = Proc.from_proc(SimpleProc)


def test_from_proc():
    proc = Proc.from_proc(
        SimpleProc,
        name="new_proc",
        desc="new desc",
        envs={"a": 1},
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
    assert proc.envs == {"a": 1}
    assert proc.cache
    assert proc.forks == 2
    assert proc.plugin_opts == {"p": 1}
    assert proc.scheduler == "sge"
    assert proc.scheduler_opts == {"s": 1}
    assert proc.error_strategy == "retry"
    assert proc.num_retries == 10
    assert proc.submission_batch == 3


def test_cached_run(caplog, pipen):
    NormalProc.nexts = []
    # force uncache NormalProc
    # shutil.rmtree(pipen.config.workdir)
    ret = pipen.set_start(NormalProc).run()
    assert ret

    # trigger caching
    ret = pipen.set_start(NormalProc).run()
    assert ret

    assert caplog.text.count("Cached jobs:") == 1


def test_more_nexts(pipen):
    proc1 = Proc.from_proc(NormalProc)
    Proc.from_proc(NormalProc, "proc2", requires=proc1)
    Proc.from_proc(NormalProc, "proc3", requires=proc1)
    ret = pipen.set_starts(proc1).run()
    assert ret


def test_proc_no_input(pipen):
    with pytest.raises(ProcInputKeyError):
        pipen.set_starts(NoInputProc).run()


def test_unsupported_input_type(pipen):
    with pytest.raises(ProcInputTypeError):
        pipen.set_starts(InputTypeUnsupportedProc).run()


def test_proc_with_input_data(pipen):
    proc = Proc.from_proc(NormalProc, input_data=[1])
    pipen.set_starts(proc).run()
    assert proc.output_data.equals(pandas.DataFrame({"output": ["1"]}))


def test_proc_with_input_callable(pipen):
    proc = Proc.from_proc(NormalProc, input_data=[1])
    proc2 = Proc.from_proc(
        NormalProc, requires=proc, input_data=lambda ch: ch >> mutate(output=2)
    )
    pipen.set_starts(proc).run()
    assert proc2.output_data.equals(pandas.DataFrame({"output": ["2"]}))


def test_proc_is_singleton(pipen):
    pipen.workdir = ".pipen/"
    os.makedirs(pipen.workdir, exist_ok=True)
    p1 = SimpleProc(pipen)
    p2 = SimpleProc(pipen)
    assert p1 is p2


def test_ignore_input_data_of_start_proc(caplog, pipen):
    proc = Proc.from_proc(NormalProc, input_data=[1])
    proc2 = Proc.from_proc(NormalProc, requires=proc, input_data=[2])
    pipen.set_starts(proc).run()
    assert "Ignoring input data" in caplog.text
    assert proc2.output_data.equals(pandas.DataFrame({"output": ["1"]}))


def test_proc_wasted_input_columns(caplog, pipen):
    proc1 = Proc.from_proc(NormalProc, input_data=[1])
    proc2 = Proc.from_proc(NormalProc, input_data=[1])
    proc3 = Proc.from_proc(NormalProc, requires=[proc1, proc2])
    pipen.set_starts(proc1, proc2).run()
    assert "Wasted 1 column" in caplog.text


def test_proc_not_enough_input_columns(caplog, pipen):
    proc1 = Proc.from_proc(NormalProc, input_data=[1])
    proc2 = Proc.from_proc(In2Out1Proc, requires=proc1)
    pipen.set_starts(proc1).run()
    assert "No data column for input: ['in2'], using None" in caplog.text
    assert proc2.output_data.equals(pandas.DataFrame({"out": ["1_None"]}))


def test_proc_relative_path_script(pipen):
    pipen.set_starts(RelPathScriptProc).run()
    script = RelPathScriptProc().script.render()
    assert "AbCdEf" in script


def test_script_file_exists(pipen):
    with pytest.raises(ProcScriptFileNotFound):
        pipen.set_starts(ScriptNotExistsProc).run()


def test_invalid_name():
    with pytest.raises(PipenOrProcNameError):
        Proc.from_proc(SimpleProc, name="a b")


def test_inherit_proc_envs():
    class Proc1_1(Proc):
        envs_depth = 1
        envs = {"a": {"b": 1, "c": 2}}

    class Proc2(Proc1_1):
        envs = {"a": {"b": 2}}

    class Proc1_2(Proc):
        envs_depth = 2
        envs = {"a": {"b": 1, "c": 2}}

    class Proc3(Proc1_2):
        envs_depth = 2
        envs = {"a": {"b": 3}}

    class Proc1_3(Proc):
        envs_depth = 3
        envs = {"a": {"b": 1, "c": 2}}

    class Proc4(Proc1_3):
        envs = {"a": {"b": 4}}

    Proc5 = Proc.from_proc(Proc1_3, envs={"a": {"b": 5}})

    assert Proc5.envs == {"a": {"b": 5, "c": 2}}
    assert Proc4.envs == {"a": {"b": 4, "c": 2}}
    assert Proc3.envs == {"a": {"b": 3, "c": 2}}
    assert Proc2.envs == {"a": {"b": 2}}
    assert Proc1_1.envs == {"a": {"b": 1, "c": 2}}
    assert Proc1_2.envs == {"a": {"b": 1, "c": 2}}
    assert Proc1_3.envs == {"a": {"b": 1, "c": 2}}
