import sys
# import signal
from tempfile import gettempdir
from pathlib import Path
# from shutil import rmtree
# from multiprocessing import Process

import pytest
from pipen import Proc, Pipen, plugin
from pipen.utils import is_loading_pipeline


class SimpleProc(Proc):
    """A very simple process for testing"""

    input = ["input"]
    script = "sleep 1.5"  # let on_job_polling run


class NormalProc(Proc):
    """A normal proc"""

    input = "input:var"
    output = ["output:{{in.input}}"]
    script = "echo {{in.input}}"


class In2Out1Proc(Proc):
    """Process with 2 input vars and 1 output var"""

    input = "in1:var, in2:var"
    output = "out:var:{{in.in1}}_{{in.in2}}"
    script = "echo {{in.in1}} {{in.in2}}"


class RelPathScriptProc(Proc):
    """Process uses relative path script"""

    input = "in"
    output = "out:var:{{in.in}}"
    # use this file itself
    script = "file://__init__.py"


class ScriptNotExistsProc(Proc):
    """Process uses relative path script"""

    input = "in"
    output = "out:var:{{in.in}}"
    # use this file itself
    script = "file:///no/such/file"


class ErrorProc(Proc):
    """Errant process"""

    input = ["input"]
    script = "exit 1"


class ScriptRenderErrorProc(Proc):
    """When script is failed to render"""

    input = "a"
    output = "b:var:1"
    script = "{{c(d)}}"


class SleepingProc(Proc):
    """Process to sleep for a certain time"""

    input = "time"
    script = "sleep {{in.time}}"


class RetryProc(ErrorProc):
    input = "starttime"
    error_strategy = "retry"
    num_retries = 10
    lang = sys.executable  # python
    script = """
        import sys, time
        sys.exit(1 if time.time() < {{in.starttime}} + 3 else 0)
    """


class OutputRenderErrorProc(Proc):
    """When output is failed to render"""

    input = "a"
    output = "b:var:{{c(d)}}"


class OutputNoNameErrorProc(Proc):
    """When no name/type given in output"""

    input = "a"
    output = "b"


class OutputWrongTypeProc(Proc):
    """When no name/type given in output"""

    input = "a"
    output = "b:c:d"


class OutputAbsPathProc(Proc):
    """When no name/type given in output"""

    input = "a"
    output = "b:file:/a/b"


class NoInputProc(Proc):
    """Process without input"""


class InputTypeUnsupportedProc(Proc):
    """Input type not supported"""

    input = "input:unsupported:1"


class FileInputProc(Proc):
    """Process with file input"""

    input = "in:file"
    output = "out:file:{{in.in.split('/')[-1]}}"
    script = "cat {{in.in}} > {{out.out}}"


class OutputNotGeneratedProc(Proc):
    """Process with output file not generated intentionally"""

    input = "in"
    output = "out:file:{{in.in}}"
    script = "echo {{in.in}}"


class FileInputsProc(Proc):
    """Process with files input"""

    input = "in:files"
    output = "out:file:{{in.in[0].split('/')[-1]}}"
    script = "echo {{in.in}} > {{out.out}}"


class MixedInputProc(Proc):
    """Process with mixed types of input"""

    input = "invar:var, infile:file"
    output = "outfile:file:{{in.invar}}"
    script = "echo {{in.invar}} > {{out.outfile}}"


class DirOutputProc(Proc):
    """Process with directory output"""

    input = "in"
    output = "outfile:dir:outdir"
    script = "echo {{in.in}} > {{out.outfile}}/outfile; "


class SimplePlugin:
    @plugin.impl
    async def on_init(pipen):
        if getattr(pipen.__class__, "loading", False):
            assert is_loading_pipeline("--help")
        print("SimplePlugin")

    @plugin.impl
    async def on_job_polling(proc, job):
        print("SimplePlugin on_job_polling")


@pytest.fixture
def pipen(tmp_path):
    """Get a simple Pipen object each time"""
    index = Pipen.PIPELINE_COUNT + 1
    pipen_simple = Pipen(
        name=f"simple_pipeline_{index}",
        desc="No description",
        loglevel="debug",
        cache=True,
        workdir=tmp_path / ".pipen",
        outdir=tmp_path / f"pipen_simple_{index}",
    )

    return pipen_simple


@pytest.fixture
def pipen_with_plugin(tmp_path):
    """Get a simple Pipen object each time"""
    index = Pipen.PIPELINE_COUNT + 1
    pipen_simple = Pipen(
        name=f"simple_pipeline_{index}",
        desc="No description",
        loglevel="debug",
        cache=True,
        plugins=[SimplePlugin()],
        workdir=tmp_path / ".pipen",
        outdir=tmp_path / f"pipen_simple_{index}",
    )

    return pipen_simple


class PipenIsLoading(Pipen):
    name = "PipenIsLoading"
    loading = True
    plugins = [SimplePlugin()]
    starts = SimpleProc


@pytest.fixture
def infile(tmp_path):
    out = tmp_path / "infile"
    out.write_text("in")
    return out


@pytest.fixture
def infile1(tmp_path):
    out = tmp_path / "infile1"
    out.write_text("in1")
    return out


@pytest.fixture
def infile2(tmp_path):
    out = tmp_path / "infile2"
    out.write_text("in2")
    return out


def create_dead_link(path):
    target = Path(gettempdir()) / "__NoSuchFile__"
    target.write_text("")
    link = Path(path)
    if link.exists() or link.is_symlink():
        link.unlink()
    link.symlink_to(target)
    target.unlink()
