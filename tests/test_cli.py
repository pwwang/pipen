import sys
import pytest  # noqa: F401

from subprocess import check_output, CalledProcessError, STDOUT


def cmdoutput(cmd):
    try:
        return check_output(
            [sys.executable, "-m"] + cmd,
            stderr=STDOUT,
            encoding="utf-8",
        )
    except CalledProcessError as err:
        return err.output


@pytest.mark.forked
def test_main():
    out = cmdoutput(["pipen", "--help"])
    assert "CLI Tool for pipen" in out


@pytest.mark.forked
def test_nosuch_command():
    out = cmdoutput(["pipen", "x"])
    assert "invalid choice" in out


@pytest.mark.forked
def test_help():
    out = cmdoutput(["pipen", "help", "x"])
    assert "invalid choice" in out
    out = cmdoutput(["pipen", "help", "profile"])
    assert "The name of the profile to show" in out
    out = cmdoutput(["pipen", "help"])
    assert "CLI Tool for pipen" in out


@pytest.mark.forked
def test_profile_all():
    out = cmdoutput(["pipen", "profile"])
    assert "Note:" in out
    out = cmdoutput(["pipen", "profile", "--list"])
    assert "default" in out


@pytest.mark.forked
def test_profile_default():
    out = cmdoutput(["pipen", "profile", "--name", "default"])
    assert "Profile: default" in out


@pytest.mark.forked
def test_profile_nosuch():
    out = cmdoutput(["pipen", "profile", "-n", "nosuch"])
    assert "Profile: nosuch" not in out


@pytest.mark.forked
def test_version():
    out = cmdoutput(["pipen", "version"])
    assert "pipen" in out
    assert "python" in out
    assert "liquidpy" in out


@pytest.mark.forked
def test_unparsed_args():
    out = cmdoutput(["pipen", "version", "--x"])
    assert "unrecognized arguments: --x" in out
