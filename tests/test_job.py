from pipen.exceptions import ProcInputTypeError, ProcOutputNameError, ProcOutputTypeError, ProcOutputValueError, TemplateRenderingError
import pytest
import os
from pathlib import Path

from pipen import Proc

from .helpers import (
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
    get_simple_pipen,
    create_dead_link,
)


def test_caching(tmp_path, caplog):
    pipen = get_simple_pipen(872)
    infile = tmp_path / "infile"
    infile.write_text("")
    proc = Proc.from_proc(FileInputProc, input_data=[infile])
    pipen.run(proc)

    pipen2 = get_simple_pipen(872)
    pipen2.run(proc)

    assert caplog.text.count("Cached jobs:") == 1


def test_input_files_caching(tmp_path, caplog):
    pipen = get_simple_pipen(873)
    infile = tmp_path / "infile"
    infile.write_text("")
    proc = Proc.from_proc(FileInputsProc, input_data=[[infile, infile]])
    pipen.run(proc)

    pipen2 = get_simple_pipen(873)
    pipen2.run(proc)

    assert caplog.text.count("Cached jobs:") == 1


def test_mixed_input_caching(tmp_path, caplog):
    pipen = get_simple_pipen(874)
    infile = tmp_path / "infile"
    infile.write_text("")
    proc = Proc.from_proc(MixedInputProc, input_data=[("in", infile)])
    pipen.run(proc)

    pipen2 = get_simple_pipen(874)
    pipen2.run(proc)

    assert caplog.text.count("Cached jobs:") == 1


def test_clear_output_dead_link(tmp_path):
    pipen = get_simple_pipen()
    infile = tmp_path / "infile"
    infile.write_text("")
    outfile = Path(pipen.outdir) / "proc" / "infile"
    outfile.parent.mkdir(parents=True, exist_ok=True)
    create_dead_link(outfile)
    assert not outfile.is_file() and outfile.is_symlink()

    proc = Proc.from_proc(FileInputProc, input_data=[infile])
    # dead link can be cleared!
    pipen.run(proc)
    assert outfile.is_file() and outfile.exists()


def test_clear_outfile(tmp_path):
    pipen = get_simple_pipen()
    infile = tmp_path / "infile"
    infile.write_text("abc")
    outfile = Path(pipen.outdir) / "proc" / "infile"
    outfile.parent.mkdir(parents=True, exist_ok=True)
    outfile.write_text("")

    proc = Proc.from_proc(FileInputProc, input_data=[infile])

    pipen.run(proc)
    assert outfile.read_text() == "abc"


def test_dir_output_auto_created():
    pipen = get_simple_pipen()
    proc = Proc.from_proc(DirOutputProc, input_data=[1])
    pipen.run(proc)
    outdir = pipen.outdir / "proc" / "outdir"
    assert outdir.is_dir()


def test_clear_outdir():
    pipen = get_simple_pipen()

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
    pipen.run(proc_job_clear_outdir)

    assert outdir.joinpath("outfile").read_text().strip() == "abc"


def test_check_cached_input_or_output_different(tmp_path, caplog):
    infile1 = tmp_path / "infile1"
    infile1.write_text("abc")
    infile2 = tmp_path / "infile2"
    infile2.write_text("abc")

    pipen = get_simple_pipen(900)
    proc_io_diff1 = Proc.from_proc(FileInputProc, input_data=[infile1])
    proc_io_diff2 = Proc.from_proc(FileInputProc, name="proc_io_diff1", input_data=[infile2])
    pipen.run(proc_io_diff1)

    caplog.clear()
    pipen = get_simple_pipen(900)
    pipen.run(proc_io_diff2)
    assert "Not cached (input or output is different)" in caplog.text


def test_check_cached_script_file_newer(tmp_path, caplog):
    infile = tmp_path / "infile"
    infile.write_text("abc")

    pipen = get_simple_pipen(880)
    proc_script_newer = Proc.from_proc(NormalProc, input_data=[(1, infile)])
    pipen.run(proc_script_newer)

    script_file = proc_script_newer.workdir / "0" / "job.script"
    os.utime(script_file, (script_file.stat().st_mtime + 10,) * 2)
    pipen = get_simple_pipen(880)
    pipen.run(proc_script_newer)
    assert "Not cached (script file is newer" in caplog.text


def test_check_cached_cache_false(caplog):
    pipen = get_simple_pipen()
    proc = Proc.from_proc(SimpleProc, cache=False)
    pipen.run(proc)
    assert "Not cached (proc.cache is False)" in caplog.text


def test_check_cached_rc_ne_0(caplog):
    pipen = get_simple_pipen(881)
    proc = Proc.from_proc(ErrorProc)
    pipen.run(proc)

    pipen = get_simple_pipen(881)
    pipen.run(proc)
    assert "Not cached (job.rc != 0)" in caplog.text


def test_check_cached_sigfile_notfound(caplog):

    pipen = get_simple_pipen(882)
    proc = Proc.from_proc(SimpleProc, input_data=[1])
    # run to generate signature file
    pipen.run(proc)

    sigfile = proc.workdir / "0" / "job.signature.toml"
    sigfile.unlink()
    pipen = get_simple_pipen(882)
    pipen.run(proc)
    assert "Not cached (signature file not found)" in caplog.text


def test_check_cached_force_cache(tmp_path, caplog):
    infile = tmp_path / "infile"
    infile.write_text("abc")

    pipen = get_simple_pipen(883)
    proc_script_newer2 = Proc.from_proc(NormalProc, input_data=[(1, infile)])
    proc_script_newer3 = Proc.from_proc(
        NormalProc,
        name="proc_script_newer2",
        input_data=[(1, infile)], cache="force"
    )
    pipen.run(proc_script_newer2)
    caplog.clear()

    script_file = proc_script_newer2.workdir / "0" / "job.script"
    os.utime(script_file, (script_file.stat().st_mtime + 10,) * 2)
    pipen = get_simple_pipen(883)
    pipen.run(proc_script_newer3)
    assert "Cached jobs:" in caplog.text


def test_check_cached_infile_newer(tmp_path, caplog):
    infile = tmp_path / "infile"
    infile.write_text("abc")
    pipen = get_simple_pipen(884)
    proc_infile_newer = Proc.from_proc(MixedInputProc, input_data=[(1, infile)])
    pipen.run(proc_infile_newer)

    caplog.clear()
    os.utime(infile, (infile.stat().st_mtime + 10,) * 2)
    pipen = get_simple_pipen(884)
    pipen.run(proc_infile_newer)
    assert "Not cached (Input file is newer:" in caplog.text


def test_check_cached_infiles_newer(tmp_path, caplog):
    infile = tmp_path / "infile"
    infile.write_text("abc")
    pipen = get_simple_pipen(885)
    proc_infile_newer = Proc.from_proc(
        FileInputsProc, input_data=[[infile, infile]]
    )
    pipen.run(proc_infile_newer)

    caplog.clear()
    os.utime(infile, (infile.stat().st_mtime + 10,) * 2)
    pipen = get_simple_pipen(885)
    pipen.run(proc_infile_newer)
    assert "Not cached (One of the input files is newer:" in caplog.text

def test_check_cached_outfile_removed(tmp_path, caplog):
    infile = tmp_path / "infile"
    infile.write_text("abc")

    pipen = get_simple_pipen(886)
    proc_outfile_removed = Proc.from_proc(FileInputProc, input_data=[infile])
    pipen.run(proc_outfile_removed)
    caplog.clear()

    out_file = proc_outfile_removed.workdir / "0" / "output" / "infile"
    out_file.unlink()
    pipen = get_simple_pipen(886)
    pipen.run(proc_outfile_removed)
    assert "Not cached (Output file removed:" in caplog.text

def test_metaout_was_dir():
    pipen = get_simple_pipen(887)
    proc1 = Proc.from_proc(NormalProc)
    proc2 = Proc.from_proc(NormalProc, requires=proc1)
    # proc1's metadir/output will be directory
    pipen.run(proc1)
    metaout = proc1.workdir / "0" / "output"
    assert not metaout.is_symlink()

    pipen = get_simple_pipen(887)
    proc3 = Proc.from_proc(NormalProc, name="proc1")
    # clear previous output
    pipen.run(proc3)
    assert metaout.is_symlink()
    metaout.unlink()

def test_script_failed_to_render():
    pipen = get_simple_pipen()
    proc = Proc.from_proc(ScriptRenderErrorProc, input_data=[1])
    with pytest.raises(TemplateRenderingError, match="script"):
        pipen.run(proc)

def test_output_failed_to_render():
    pipen = get_simple_pipen()
    proc = Proc.from_proc(OutputRenderErrorProc, input_data=[1])
    with pytest.raises(TemplateRenderingError, match="output"):
        pipen.run(proc)

def test_output_no_name_type():
    pipen = get_simple_pipen()
    proc = Proc.from_proc(OutputNoNameErrorProc, input_data=[1])
    with pytest.raises(ProcOutputNameError, match="output"):
        pipen.run(proc)

def test_output_wrong_type():
    pipen = get_simple_pipen()
    proc = Proc.from_proc(OutputWrongTypeProc, input_data=[1])
    with pytest.raises(ProcOutputTypeError, match="output"):
        pipen.run(proc)

def test_output_abspath():
    pipen = get_simple_pipen()
    proc = Proc.from_proc(OutputAbsPathProc, input_data=[1])
    with pytest.raises(ProcOutputValueError, match="output"):
        pipen.run(proc)

def test_job_log_limit(caplog):
    pipen = get_simple_pipen(888)
    proc = Proc.from_proc(SimpleProc, input_data=[1] * 5)
    pipen.run(proc)

    class proc2(proc):
        name = 'proc'
        script = "echo 123" # job script updated
        cache = False

    caplog.clear()
    pipen = get_simple_pipen(888)
    pipen.run(proc2)
    assert "Not showing similar logs" in caplog.text

def test_wrong_input_type():
    pipen = get_simple_pipen()
    proc = Proc.from_proc(MixedInputProc, input_data=[(1, 1)])
    with pytest.raises(ProcInputTypeError):
        pipen.run(proc)

def test_wrong_input_type_for_files():
    pipen = get_simple_pipen()
    proc = Proc.from_proc(FileInputsProc, input_data=[1])
    with pytest.raises(ProcInputTypeError):
        pipen.run(proc)
