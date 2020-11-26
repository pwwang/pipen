from pathlib import Path
import sys
import os
import signal
import pytest
from pipen import Pipen, Proc
from pipen.defaults import config
from pipen.exceptions import *
from pipen.plugin import plugin
from pipen.channel import *
from pipen.channel.verbs import *
from pipen.channel.vector import *

class Process(Proc):
    input_keys = ['a', 'b:file']
    input = [(1, __file__), (2, __file__)]
    args = {'a': 1}
    output = 'a:{{in.a}}'
    script = "echo {{in.a}} {{in.b}}"

class Process2(Proc):
    input_keys = 'a'
    requires = Process
    script = 'echo {{in.a}}'

def test_pipen(tmp_path):
    pipen = Pipen(loglevel='debug', workdir=tmp_path).starts(Process)
    assert Process().nexts == [Process2()]
    assert Process2().nexts == []
    pipen.run()
    # run again to trigger cache
    pipen.run()

def test_subclassing():
    class Process3(Process):
        ...

    proc = Process3()
    assert proc is not Process()
    assert proc.name == 'Process3'

def test_run_different_profile(tmp_path):
    config._load({'least_plugin': {'plugins': ['main']}})
    pipen = Pipen(loglevel='debug', workdir=tmp_path).starts(Process)
    assert Process().nexts == [Process2()]
    assert Process2().nexts == []
    pipen.run('least_plugin')

def test_cyclic_dependency(tmp_path):
    proc = Process(name='proc')
    proc2 = Process2(requires=proc)
    proc.requires = [proc2]
    proc2.nexts = [proc]

    assert proc.input == [(1, __file__), (2, __file__)]
    assert proc is not Process()

    pipen = Pipen(workdir=tmp_path).starts(proc)
    with pytest.raises(ProcDependencyError, match='Cyclic dependency'):
        pipen.run()

def test_forget_start(tmp_path):
    proc = Process(name='proc1')
    proc2 = Process2(requires=(Process, proc))
    pipen = Pipen(workdir=tmp_path).starts(proc)
    with pytest.raises(ProcDependencyError, match='No available next process'):
        pipen.run()

def test_proc_error(tmp_path):
    proc = Process(name='proc1')
    proc2 = Process2(
        requires=proc,
        script='echo1 {{in.a}}'
    )
    pipen = Pipen(workdir=tmp_path).starts(proc)
    pipen.run()
    assert 'proc1: 2' in repr(proc)
    assert not proc2.succeeded

def test_proc_input_type_error(tmp_path):
    proc = Process(name='proc1', input_keys='a:int, b:int')
    pipen = Pipen(workdir=tmp_path).starts(proc)
    with pytest.raises(ProcInputTypeError):
        pipen.run()

def test_proc_input_callbacks(tmp_path, caplog):
    script2 = tmp_path / 'proc2.script'
    script2.write_text('echo 1')
    proc = Process('proc1')
    proc2 = Process2(input=lambda ch: ch >> mutate(b=2), requires=proc,
                     output=['c:1', 'd:2'], script='file://%s' % script2)
    # invoke job script updated
    proc2_orig_script = tmp_path / proc2.name / '0' / 'job.script'
    proc2_orig_script.parent.mkdir(parents=True, exist_ok=True)
    proc2_orig_script.write_text('not echo 1')

    proc3 = Process2(input_keys='a,b', requires=proc,
                     lang=sys.executable,
                     script='file://conftest.py')
    class Process4(Process):
        script = None
    proc4 = Process4(input=[1], input_keys='a', requires=proc)
    pipen = Pipen(workdir=tmp_path, loglevel='debug').starts(proc)
    pipen.run()
    assert 'proc2:[/cyan] Wasted 1 column(s) of input data' in caplog.text
    assert 'proc2:[/cyan] [0/1] Job script updated' in caplog.text
    assert "proc3:[/cyan] No data columns for input: ['b']" in caplog.text
    assert "proc4:[/cyan] Ignoring input data" in caplog.text

def test_proc_script_notfound(tmp_path):
    proc = Process('proc1', script='file:///path/not/exists')
    pipen = Pipen(workdir=tmp_path).starts(proc)
    with pytest.raises(ProcScriptFileNotFound):
        pipen.run()

def test_proc_output_noname_given(tmp_path):
    proc = Process('proc1', output='a,b')
    pipen = Pipen(workdir=tmp_path).starts(proc)
    with pytest.raises(ProcOutputNameError):
        pipen.run()

def test_proc_output_type_not_supported(tmp_path):
    proc = Process('proc1', output='a:int:1,b:int:2')
    pipen = Pipen(workdir=tmp_path).starts(proc)
    with pytest.raises(ProcOutputTypeError):
        pipen.run()

def test_proc_output_path_redirected_error(tmp_path):
    proc = Process('proc1', output='a:file:a/b/c')
    pipen = Pipen(workdir=tmp_path).starts(proc)
    with pytest.raises(ProcOutputValueError):
        pipen.run()

def test_proc_output_path_redirected(tmp_path):
    class ProcessOutputFile(Proc):
        input_keys = 'a'
        forks = 5
        input = range(5)
        script = 'echo {{in.a}} > {{out.b}}'
        output = 'b:file:bfile'
    proc1 = ProcessOutputFile('proc1', output='b:file:%s/bfile' % tmp_path)
    proc2 = ProcessOutputFile('proc2', output='b:file:bfile_end',
                              input=lambda ch: ch >> filter(row_number(_) == 1),
                              requires=proc1)

    pipen = Pipen(workdir=tmp_path).starts(proc1)
    pipen.run()

    assert Path(proc1.out_channel.iloc[0, 0]).resolve() == (
        tmp_path / 'bfile'
    ).resolve()

    assert Path(proc2.out_channel.iloc[0, 0]).resolve() == (
        Path(pipen.outdir) / proc2.name / 'bfile_end'
    ).resolve()

def test_proc_output_not_generated(tmp_path, caplog):
    class ProcessOutputFileNotGenerated(Proc):
        input_keys = 'a'
        input = [1]
        script = 'echo {{in.a}}'
        output = 'b:file:bfile'

    pipen = Pipen(loglevel='debug',
                  workdir=tmp_path).starts(ProcessOutputFileNotGenerated)
    pipen.run()

    proc = ProcessOutputFileNotGenerated()
    assert 'is not generated' in (proc.workdir / '0' / 'job.stderr').read_text()

def test_proc_retry(tmp_path, caplog):
    class ProcessRetry(Proc):
        input_keys = 'a'
        input = [1]
        script = 'echo1 {{in.a}}'

    pipen = Pipen(loglevel='debug',
                  error_strategy='retry',
                  workdir=tmp_path).starts(ProcessRetry)
    pipen.run()

    assert 'Retrying' in caplog.text

def test_proc_killing(tmp_path, caplog):
    class ProcessKillPlugin:
        @plugin.impl
        async def on_job_running(self, proc, job):
            os.kill(os.getpid(), signal.SIGTERM)

    class ProcessLastLong(Proc):
        input_keys = 'a'
        input = [1]
        script = 'sleep 10'

    pipen = Pipen(loglevel='debug',
                  plugins=[ProcessKillPlugin],
                  workdir=tmp_path).starts(ProcessLastLong)
    pipen.run()

def test_proc_workdir_conflict(tmp_path):
    proc = Process('process 1')
    proc2 = Process2('process-1', requires=proc)
    pipen = Pipen(workdir=tmp_path).starts(proc)
    with pytest.raises(ProcWorkdirConflictException):
        pipen.run()
