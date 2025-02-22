from pipen.exceptions import (
    ProcInputTypeError,
    ProcOutputNameError,
    ProcOutputTypeError,
    ProcOutputValueError,
    TemplateRenderingError,
)
import pytest
import os
import time
from pathlib import Path

from pipen import Proc

from .helpers import (  # noqa: F401
    ErrorProc,
    FileInputProc,
    FileInputsProc,
    MixedInputProc,
    DirOutputProc,
    NormalProc,
    OutputAbsPathProc,
    OutputNoNameErrorProc,
    OutputRenderErrorProc,
    OutputWrongTypeProc,
    ScriptRenderErrorProc,
    SimpleProc,
    pipen,
    infile,
    infile1,
    infile2,
    create_dead_link,
)


# @pytest.mark.forked
def test_caching(caplog, pipen, infile):
    proc = Proc.from_proc(FileInputProc, input_data=[infile])
    pipen.set_starts(proc).run()

    pipen.set_starts(proc).run()

    assert caplog.text.count("Cached jobs:") == 1


@pytest.mark.forked
def test_input_files_caching(caplog, pipen, infile):
    proc = Proc.from_proc(FileInputsProc, input_data=[[infile, infile]])
    pipen.set_starts(proc).run()

    pipen.set_starts(proc).run()
    assert caplog.text.count("Cached jobs:") == 1


@pytest.mark.forked
def test_mixed_input_caching(caplog, pipen, infile):
    proc = Proc.from_proc(MixedInputProc, input_data=[("in", infile)])
    pipen.set_starts(proc).run()

    pipen.set_starts(proc).run()
    assert caplog.text.count("Cached jobs:") == 1


@pytest.mark.forked
def test_clear_output_dead_link(pipen, infile):
    outfile = Path(pipen.outdir) / "proc" / "infile"
    outfile.parent.mkdir(parents=True, exist_ok=True)
    create_dead_link(outfile)
    assert not outfile.is_file() and outfile.is_symlink()

    proc = Proc.from_proc(FileInputProc, input_data=[infile])
    # dead link can be cleared!
    pipen.set_starts(proc).run()
    assert outfile.is_file() and outfile.exists()


@pytest.mark.forked
def test_clear_outfile(pipen, infile):
    outfile = Path(pipen.outdir) / "proc" / "infile"
    outfile.parent.mkdir(parents=True, exist_ok=True)
    outfile.write_text("")

    proc = Proc.from_proc(FileInputProc, input_data=[infile])

    pipen.set_starts(proc).run()
    assert outfile.read_text() == "in"


@pytest.mark.forked
def test_dir_output_auto_created(pipen):
    proc = Proc.from_proc(DirOutputProc, input_data=[1])
    pipen.set_starts(proc).run()
    outdir = pipen.outdir / "proc" / "outdir"
    assert outdir.is_dir()


@pytest.mark.forked
def test_clear_outdir(pipen):

    outdir = Path(pipen.outdir) / "proc_job_clear_outdir" / "outdir"
    outdir.mkdir(parents=True, exist_ok=True)
    outfile = outdir / "outfile"
    outfile.write_text("def")

    proc_job_clear_outdir = Proc.from_proc(
        DirOutputProc,
        input_data=["abc"],
        cache=False,
    )
    # outdir cleared
    pipen.set_starts(proc_job_clear_outdir).run()

    assert outdir.joinpath("outfile").read_text().strip() == "abc"


@pytest.mark.forked
def test_check_cached_input_or_output_different(
    caplog, pipen, infile1, infile2
):

    proc_io_diff1 = Proc.from_proc(FileInputProc, input_data=[infile1])
    proc_io_diff2 = Proc.from_proc(
        FileInputProc, name="proc_io_diff1", input_data=[infile2]
    )
    pipen.set_starts(proc_io_diff1).run()

    caplog.clear()
    pipen.set_starts(proc_io_diff2).run()
    pipen.build_proc_relationships()  # not redoing it.
    assert "Not cached (input or output is different)" in caplog.text


@pytest.mark.forked
def test_check_cached_script_file_newer(caplog, pipen, infile):

    proc_script_newer = Proc.from_proc(NormalProc, input_data=[(1, infile)])
    pipen.set_starts(proc_script_newer).run()

    script_file = proc_script_newer.workdir / "0" / "job.script"
    os.utime(script_file, (script_file.stat().st_mtime + 10,) * 2)
    pipen.set_starts(proc_script_newer).run()
    assert "Not cached (script file is newer" in caplog.text


@pytest.mark.forked
def test_check_cached_cache_false(caplog, pipen):
    proc = Proc.from_proc(SimpleProc, cache=False)
    pipen.set_starts(proc).run()
    assert "Not cached (proc.cache is False)" in caplog.text


@pytest.mark.forked
def test_check_cached_rc_ne_0(caplog, pipen):
    proc = Proc.from_proc(ErrorProc)
    pipen.set_starts(proc).run()

    pipen.set_starts(proc).run()
    assert "Not cached (job.rc != 0)" in caplog.text


@pytest.mark.forked
def test_check_cached_sigfile_notfound(caplog, pipen):
    proc = Proc.from_proc(SimpleProc, input_data=[1])
    # run to generate signature file
    pipen.set_starts(proc).run()

    sigfile = proc.workdir / "0" / "job.signature.toml"
    sigfile.unlink()
    pipen.set_starts(proc).run()
    assert "Not cached (signature file not found)" in caplog.text


@pytest.mark.forked
def test_check_cached_force_cache(caplog, pipen, infile):
    proc_script_newer2 = Proc.from_proc(NormalProc, input_data=[(1, infile)])
    proc_script_newer3 = Proc.from_proc(
        NormalProc,
        name="proc_script_newer2",
        input_data=[(1, infile)],
        cache="force",
    )
    pipen.set_starts(proc_script_newer2).run()
    caplog.clear()

    script_file = proc_script_newer2.workdir / "0" / "job.script"
    os.utime(script_file, (script_file.stat().st_mtime + 10,) * 2)
    pipen.set_starts(proc_script_newer3).run()
    assert "Cached jobs:" in caplog.text


@pytest.mark.forked
def test_check_cached_infile_newer(caplog, pipen, infile):
    proc_infile_newer = Proc.from_proc(
        MixedInputProc, input_data=[(1, infile)]
    )
    pipen.set_starts(proc_infile_newer).run()

    caplog.clear()
    os.utime(infile, (infile.stat().st_mtime + 10,) * 2)
    pipen.set_starts(proc_infile_newer).run()
    assert "Not cached (Input file is newer:" in caplog.text


@pytest.mark.forked
def test_check_cached_infiles_newer(caplog, pipen, infile):
    proc_infile_newer = Proc.from_proc(
        FileInputsProc, input_data=[[infile, infile]]
    )
    pipen.set_starts(proc_infile_newer).run()

    caplog.clear()
    os.utime(infile, (infile.stat().st_mtime + 10,) * 2)
    # wait for 1 second to make sure the new mtime is different
    time.sleep(1)
    pipen.set_starts(proc_infile_newer).run()
    assert "Not cached (One of the input files is newer:" in caplog.text


@pytest.mark.forked
def test_check_cached_outfile_removed(caplog, pipen, infile):
    proc_outfile_removed = Proc.from_proc(FileInputProc, input_data=[infile])
    pipen.set_starts(proc_outfile_removed).run()
    caplog.clear()

    out_file = proc_outfile_removed.workdir / "0" / "output" / "infile"
    out_file.unlink()
    pipen.set_starts(proc_outfile_removed).run()
    assert "Not cached (Output file removed:" in caplog.text


@pytest.mark.forked
def test_metaout_was_dir(pipen):
    proc1 = Proc.from_proc(NormalProc)
    proc2 = Proc.from_proc(NormalProc, requires=proc1)  # noqa: F841
    # proc1's metadir/output will be directory
    pipen.set_starts(proc1).run()
    metaout = proc1.workdir / "0" / "output"
    assert not metaout.is_symlink()

    proc3 = Proc.from_proc(NormalProc, name="proc1")
    # clear previous output
    pipen.set_starts(proc3).run()
    assert metaout.is_symlink()
    metaout.unlink()


@pytest.mark.forked
def test_script_failed_to_render(pipen):
    proc = Proc.from_proc(ScriptRenderErrorProc, input_data=[1])
    with pytest.raises(TemplateRenderingError, match="script"):
        pipen.set_starts(proc).run()


@pytest.mark.forked
def test_output_failed_to_render(pipen):
    proc = Proc.from_proc(OutputRenderErrorProc, input_data=[1])
    with pytest.raises(TemplateRenderingError, match="output"):
        pipen.set_starts(proc).run()


@pytest.mark.forked
def test_output_no_name_type(pipen):
    proc = Proc.from_proc(OutputNoNameErrorProc, input_data=[1])
    with pytest.raises(ProcOutputNameError, match="output"):
        pipen.set_starts(proc).run()


@pytest.mark.forked
def test_output_wrong_type(pipen):
    proc = Proc.from_proc(OutputWrongTypeProc, input_data=[1])
    with pytest.raises(ProcOutputTypeError, match="output"):
        pipen.set_starts(proc).run()


@pytest.mark.forked
def test_output_abspath(pipen):
    proc = Proc.from_proc(OutputAbsPathProc, input_data=[1])
    with pytest.raises(ProcOutputValueError, match="output"):
        pipen.set_starts(proc).run()


@pytest.mark.forked
def test_job_log_limit(caplog, pipen):
    proc = Proc.from_proc(SimpleProc, input_data=[1] * 5)
    pipen.set_starts(proc).run()

    class proc2(proc):
        name = "proc"
        script = "echo 123"  # job script updated
        cache = False

    caplog.clear()
    pipen.set_starts(proc2).run()
    assert "showing similar logs" in caplog.text


@pytest.mark.forked
def test_wrong_input_type(pipen):
    proc = Proc.from_proc(MixedInputProc, input_data=[(1, 1)])
    with pytest.raises(ProcInputTypeError):
        pipen.set_starts(proc).run()


@pytest.mark.forked
def test_wrong_input_type_for_files(pipen):
    proc = Proc.from_proc(FileInputsProc, input_data=[1])
    with pytest.raises(ProcInputTypeError):
        pipen.set_starts(proc).run()
