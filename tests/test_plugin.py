import pytest

from pipen import plugin, Pipen, Proc
from pipen.exceptions import ProcInputValueError, ProcOutputValueError

from .helpers import pipen, ioproc, OutputNotGeneratedProc, SimpleProc


class Plugin:
    def __init__(self, name):
        self.name = name

    @plugin.impl
    async def on_complete(self, pipen, succeeded):
        print(f"<<<{self.name}>>>")


@pytest.mark.forked
def test_job_succeeded(pipen, caplog):
    out = pipen.set_starts(OutputNotGeneratedProc).run()
    assert not out


@pytest.mark.forked
def test_plugin_context_only(tmp_path, capsys):
    plugin1 = Plugin("plugin1")
    plugin2 = Plugin("plugin2")
    plugin3 = Plugin("plugin3")
    plugin4 = Plugin("plugin4")

    plugin.register(plugin1, plugin2, plugin3, plugin4)
    plugin.get_plugin("plugin4").disable()

    pipeline = Pipen(
        name="pipeline_plugin_context_only",
        desc="No description",
        loglevel="debug",
        cache=True,
        workdir=tmp_path / ".pipen",
        outdir=tmp_path / "pipeline_plugin_context_only",
        plugins=["plugin1", "plugin2"],
    )
    pipeline.set_starts(SimpleProc).run()
    out = capsys.readouterr().out
    assert "<<<plugin1>>>" in out
    assert "<<<plugin2>>>" in out
    assert "<<<plugin3>>>" not in out
    assert "<<<plugin4>>>" not in out


@pytest.mark.forked
def test_plugin_context_mixed(tmp_path, capsys):
    plugin1 = Plugin("plugin1")
    plugin2 = Plugin("plugin2")
    plugin3 = Plugin("plugin3")
    plugin4 = Plugin("plugin4")

    plugin.register(plugin1, plugin2, plugin3, plugin4)
    plugin.get_plugin("plugin3").disable()
    plugin.get_plugin("plugin4").disable()

    pipeline = Pipen(
        name="pipeline_plugin_context_mixed",
        desc="No description",
        loglevel="debug",
        cache=True,
        workdir=tmp_path / ".pipen",
        outdir=tmp_path / "pipeline_plugin_context_mixed",
        plugins=["+plugin3", plugin.get_plugin("plugin4"), "-plugin2"],
    )
    pipeline.set_starts(SimpleProc).run()
    out = capsys.readouterr().out
    assert "<<<plugin1>>>" in out
    assert "<<<plugin2>>>" not in out
    assert "<<<plugin3>>>" in out
    assert "<<<plugin4>>>" in out


@pytest.mark.forked
def test_io_hooks_unsupported_in_protocol(pipen, ioproc):

    pipen.set_starts(ioproc)
    with pytest.raises(
        ProcInputValueError,
        match="Unsupported protocol for input path: myio://",
    ):
        pipen.run()


@pytest.mark.forked
def test_io_hooks_unsupported_out_protocol(pipen, ioproc, tmp_path):

    class MyIOPlugin:
        @plugin.impl
        def norm_inpath(self, job, inpath, is_dir):
            if not inpath.startswith("myio://"):
                return None
            return tmp_path / inpath[7:]

        # no outpath handled, should raise error

    plugin.register(MyIOPlugin)

    pipen.set_starts(ioproc)
    with pytest.raises(
        ProcOutputValueError,
        match="Unsupported protocol for output path: myio://",
    ):
        pipen.run()


@pytest.mark.forked
def test_io_hooks_localized(tmp_path, pipen, ioproc):
    test_file = tmp_path / "test.txt"
    test_outdir = tmp_path / "output"
    test_file.write_text("abcd")
    test_outdir.mkdir()

    class MyIOPlugin:
        @plugin.impl
        def norm_inpath(self, job, inpath, is_dir):
            if not inpath.startswith("myio://"):
                return None
            return tmp_path / inpath.split("/")[-1]

        @plugin.impl
        def norm_outpath(self, job, outpath, is_dir):
            if not outpath.startswith("myio://"):
                return None
            return test_outdir / outpath.split("/")[-1]

    plugin.register(MyIOPlugin)

    pipen.set_starts(ioproc)
    assert pipen.run()
    # run again to trigger cache
    # won't raise error even when get_mtime, clear_path and output_exists
    # are not implemented, because the inpath and outpath are localized
    assert pipen.run()
    assert test_outdir.joinpath("out.txt").exists()
    assert test_outdir.joinpath("out.txt").read_text() == "abcd"


@pytest.mark.forked
def test_io_hooks_nonlocalized(tmp_path, pipen, ioproc):
    test_file = tmp_path / "test.txt"
    test_outdir = tmp_path / "output"
    test_file.write_text("abcd")
    test_outdir.mkdir()

    class IOProc(ioproc):
        script = (
            f"cp {tmp_path}/{{{{in.infile.split('/')[-1]}}}} "
            f"{test_outdir}/{{{{out.outfile.split('/')[-1]}}}}"
        )

    @plugin.register
    class MyIOPlugin:
        @plugin.impl
        def norm_inpath(self, job, inpath, is_dir):
            if not inpath.startswith("myio://"):
                return None
            return inpath

        @plugin.impl
        def norm_outpath(self, job, outpath, is_dir):
            if not outpath.startswith("myio://"):
                return None
            return outpath

    pipen.set_starts(IOProc)
    with pytest.raises(
        NotImplementedError,
        match="Unsupported protocol in path to clear: myio://",
    ):
        pipen.run()

    @plugin.register
    class MyIOPlugin2(MyIOPlugin):
        @plugin.impl
        async def clear_path(self, job, path, is_dir):
            return False

    class IOProc2(IOProc):
        ...

    pipen.set_starts(IOProc2)
    with pytest.raises(
        NotImplementedError,
        match="Unsupported protocol in path to test existence: myio://",
    ):
        pipen.run()

    @plugin.register
    class MyIOPlugin3(MyIOPlugin2):

        @plugin.impl
        async def output_exists(self, job, path, is_dir):
            # check if the remote file exists
            return test_outdir.joinpath(path.split("/")[-1]).exists()

    class IOProc3(IOProc2):
        ...

    pipen.set_starts(IOProc3)
    with pytest.raises(
        NotImplementedError,
        match="Unsupported protocol in path to get mtime: myio://",
    ):
        pipen.run()

    @plugin.register
    class MyIOPlugin4(MyIOPlugin3):
        @plugin.impl
        def get_mtime(self, job, path, dirsig):
            return 0

    class IOProc4(IOProc3):
        ...

    pipen.set_starts(IOProc4)
    assert pipen.run()
    # # assert pipen.run()
    assert test_outdir.joinpath("out.txt").exists()
    assert test_outdir.joinpath("out.txt").read_text() == "abcd"


@pytest.mark.forked
def test_jobcmd_hooks(pipen):

    @plugin.register
    class MyJobCmdPlugin:
        @plugin.impl
        def on_jobcmd_init(job):
            return "# on_jobcmd_init from myjobcmdplugin"

        @plugin.impl
        def on_jobcmd_prep(job):
            return "# on_jobcmd_prep from myjobcmdplugin"

        @plugin.impl
        def on_jobcmd_end(job):
            return "# on_jobcmd_end from myjobcmdplugin"

    class MyProc(Proc):
        input = "in:var"
        input_data = [1]
        output = "out:var:{{in.in}}"
        script = "echo {{proc.name}}"

    pipen.set_starts(MyProc).run()
    assert pipen.run()

    wrapper_script = pipen.workdir / "MyProc" / "0" / "job.wrapped.local"
    assert wrapper_script.exists()
    content = wrapper_script.read_text()
    assert "# on_jobcmd_init from myjobcmdplugin" in content
    assert "# on_jobcmd_prep from myjobcmdplugin" in content
    assert "# on_jobcmd_end from myjobcmdplugin" in content
