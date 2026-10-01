import sys
from contextlib import contextmanager

import pytest
import simplug
from pipen.cli import main
from pipen_cli_run import PipenCliRunPlugin
from . import (
    example_procs,
    example_pipeline,
    example_pipeline_process,
    example_extra_args,
)
from .utils import plugin_to_entrypoint

pipen_cli_run_plugin_init = PipenCliRunPlugin.__init__


def init(self, parser, subparser):
    pipen_cli_run_plugin_init(self, parser, subparser)
    self.entry_points["exm_procs"] = plugin_to_entrypoint(example_procs)
    self.entry_points["exm_pipes"] = plugin_to_entrypoint(example_pipeline)
    self.entry_points["exm_extra"] = plugin_to_entrypoint(example_extra_args)
    self.entry_points["exm_pipes_proc"] = plugin_to_entrypoint(
        example_pipeline_process
    )


@pytest.fixture
def patch_init():
    PipenCliRunPlugin.__init__ = init
    yield
    PipenCliRunPlugin.__init__ = pipen_cli_run_plugin_init


@contextmanager
def with_argv(argv):
    old = sys.argv[:]
    sys.argv = argv
    print("argv:", sys.argv)
    yield
    sys.argv = old


@pytest.mark.forked
def test_plugin_added(capsys):
    with with_argv(["pipen"]), pytest.raises(SystemExit):
        main()

    assert "run" in capsys.readouterr().err


@pytest.mark.forked
def test_wrong_choice(capsys):
    with with_argv(["pipen", "run", "xxx"]), pytest.raises(SystemExit):
        main()

    assert "invalid choice: 'xxx'" in capsys.readouterr().err


@pytest.mark.forked
def test_list(capsys, patch_init):
    with with_argv(["pipen", "run"]), pytest.raises(SystemExit):
        main()
    assert "exm_procs" in capsys.readouterr().err


@pytest.mark.forked
def test_list_help(capsys, patch_init):
    with with_argv(["pipen", "run", "--help"]), pytest.raises(SystemExit):
        main()
    assert "exm_procs" in capsys.readouterr().out


@pytest.mark.forked
def test_list_ns(capsys, patch_init):
    with with_argv(["pipen", "run", "exm_procs"]), pytest.raises(SystemExit):
        main()
    out = capsys.readouterr().err
    assert "UndescribedProc" in out
    assert "P1" in out


@pytest.mark.forked
def test_list_ns_help(capsys, patch_init):
    with with_argv(["pipen", "run", "exm_procs", "--help"]), pytest.raises(
        SystemExit
    ):
        main()
    out = capsys.readouterr().out
    assert "UndescribedProc" in out
    assert "P1" in out


@pytest.mark.forked
def test_list_ns_proc(capsys, patch_init):
    with with_argv(["pipen", "run", "exm_pipes"]), pytest.raises(SystemExit):
        main()
    assert "ExampleProcGroup" in capsys.readouterr().err


@pytest.mark.forked
def test_list_ns_proc_help(capsys, patch_init):
    with with_argv(["pipen", "run", "exm_pipes", "--help"]), pytest.raises(
        SystemExit
    ):
        main()
    assert "ExampleProcGroup" in capsys.readouterr().out


@pytest.mark.forked
def test_nosuch_ns(capsys, patch_init):
    with with_argv(["pipen", "run", "xyz"]), pytest.raises(SystemExit):
        main()
    assert "invalid choice: 'xyz'" in capsys.readouterr().err


@pytest.mark.forked
def test_pipeline(capsys, patch_init):
    with with_argv(
        ["pipen", "run", "exm_pipes", "ExampleProcGroup", "--help"]
    ), pytest.raises(SystemExit):
        main()
    assert "--ExampleProcGroup.input" in capsys.readouterr().out


@pytest.mark.forked
def test_pipeline_no_starts(patch_init):
    with with_argv(
        ["pipen", "run", "exm_pipes", "ExampleProcGroup2", "--help"]
    ), pytest.raises(simplug.ResultError):
        # caused by ProcDependencyError
        main()


@pytest.mark.forked
def test_pipeline_run(patch_init, tmp_path):
    with with_argv(
        [
            "pipen",
            "run",
            "exm_pipes",
            "ExampleProcGroup",
            "--ExampleProcGroup.input",
            "1",
            "--outdir",
            str(tmp_path),
            "--name",
            "pipeline_run",
        ]
    ):
        main()

    outfile = tmp_path / "P2" / "out.txt"
    assert outfile.read_text().strip() == "1\n123"


@pytest.mark.forked
def test_pipeline_run_process_decor(patch_init, tmp_path):
    with with_argv(
        [
            "pipen",
            "run",
            "exm_pipes_proc",
            "ExampleProcGroup",
            "--ExampleProcGroup.input",
            "1",
            "--outdir",
            str(tmp_path / 'outdir'),
            "--workdir",
            str(tmp_path / 'workdir'),
        ]
    ):
        main()

    outfile = tmp_path / "outdir" / "P2" / "out.txt"
    assert outfile.read_text().strip() == "1\n123"


@pytest.mark.forked
def test_pipeline_api(tmp_path):
    pipe = example_pipeline.ExampleProcGroup(input=["1"]).as_pipen(
        outdir=str(tmp_path / "outdir"),
        workdir=str(tmp_path / "workdir"),
        name="pipeline_api",
        plugins=["-args"],
    )
    pipe.run()
    outfile = tmp_path / "outdir" / "P2" / "out.txt"
    assert outfile.read_text().strip() == "1\n123"


@pytest.mark.forked
def test_procs_help(capsys, patch_init):
    with with_argv(
        [
            "pipen",
            "run",
            "exm_procs",
            "P1",
            "--help",
        ]
    ), pytest.raises(SystemExit):
        main()

    assert "The first process" in capsys.readouterr().out


@pytest.mark.forked
def test_extra_args(capsys, patch_init):
    with with_argv(
        [
            "pipen",
            "run",
            "exm_extra",
            "example_pipeline",
            "--extra",
            "A nice process",
        ]
    ):
        main()

    assert "A nice process" in capsys.readouterr().out


@pytest.mark.forked
def test_extra_args2(patch_init):
    with with_argv(
        [
            "pipen",
            "run",
            "exm_procs",
            "P1",
            "+extra=2",
        ]
    ), pytest.raises(SystemExit):
        assert "+extra=2" in sys.argv
        main()

    assert "+extra=2" not in sys.argv


@pytest.mark.forked
def test_procs_run(tmp_path, patch_init):
    infile = tmp_path / "infile.txt"
    infile.write_text("1234")
    with with_argv(
        [
            "pipen",
            "run",
            "exm_procs",
            "P1",
            "--in.infile",
            str(infile),
            "--outdir",
            str(tmp_path),
            "--plugin_opts",
            '{"a": 8}',
            "--scheduler_opts",
            '{"a": 18}',
        ]
    ):
        main()

    outfile = tmp_path / "P1" / "out.txt"
    assert outfile.read_text().strip() == "1234"


@pytest.mark.forked
def test_full_opts(patch_init, capsys):
    with with_argv(
        [
            "pipen",
            "run",
            "exm_procs",
            "P1",
            "--help+",
        ]
    ), pytest.raises(SystemExit):
        main()

    assert "error_strategy" in capsys.readouterr().out
