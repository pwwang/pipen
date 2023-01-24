from subprocess import check_output, CalledProcessError
import pytest  # noqa: F401


def cmdoutput(cmd):
    try:
        return check_output(cmd, encoding="utf-8")
    except CalledProcessError as err:
        return err.stdout


def test_main():
    out = cmdoutput(["pipen"])
    assert "CLI Tool for pipen" in out

    out = cmdoutput(["pipen", "--help"])
    assert "CLI Tool for pipen" in out


def test_nosuch_command():
    out = cmdoutput(["pipen", "x"])
    assert "No such command" in out


def test_help():
    out = cmdoutput(["pipen", "help", "x"])
    assert "No such command" in out
    out = cmdoutput(["pipen", "help", "profile"])
    assert "List available profiles" in out


def test_profile_all():
    out = cmdoutput(["pipen", "profile"])
    assert "Note:" in out


def test_profile_default():
    out = cmdoutput(["pipen", "profile", "--name", "default"])
    assert "Profile: default" in out


def test_profile_nosuch():
    out = cmdoutput(["pipen", "profile", "-n", "nosuch"])
    assert "Profile: nosuch" not in out


def test_version():
    out = cmdoutput(["pipen", "version"])
    assert "pipen" in out
    assert "python" in out
    assert "liquidpy" in out
