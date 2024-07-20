import pytest

from pipen import plugin, ioplugin, Pipen, Proc

from .helpers import pipen, OutputNotGeneratedProc, SimpleProc


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
def test_ioplugin(tmp_path):
    test_file = tmp_path / "test.txt"
    test_outdir = tmp_path / "output"
    test_file.write_text("abcd")
    test_outdir.mkdir()

    class MyIOPlugin:
        @ioplugin.impl
        def norm_inpath(self, inpath, is_dir):
            if not inpath.startswith("myio://"):
                return None
            return tmp_path / inpath[7:]

        @ioplugin.impl
        def norm_outpath(self, outdir, outpath, is_dir):
            if not outpath.startswith("myio://"):
                return None
            return test_outdir / outpath[7:]

    ioplugin.register(MyIOPlugin)

    class IOProc(Proc):
        input = "infile:file"
        input_data = ["myio://test.txt"]
        output = "outfile:file:myio://out.txt"
        script = "cp {{in.infile}} {{out.outfile}}"

    pipen = Pipen().set_starts(IOProc)
    assert pipen.run()
    assert test_outdir.joinpath("out.txt").exists()
    assert test_outdir.joinpath("out.txt").read_text() == "abcd"
