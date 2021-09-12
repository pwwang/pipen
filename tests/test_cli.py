from subprocess import check_output, CalledProcessError
import pytest

def cmdoutput(cmd):
    try:
        return check_output(cmd, encoding="utf-8")
    except CalledProcessError as err:
        return err.stdout


def test_main():
    out = cmdoutput(["pipen"])
    assert "CLI Tool for pipen" in out


def test_profile_all():
    out = cmdoutput(["pipen", "profile"])
    assert "Note:" in out


def test_profile_default():
    out = cmdoutput(["pipen", "profile", "--name", "default"])
    assert "Profile: default" in out


def test_profile_nosuch():
    out = cmdoutput(["pipen", "profile", "-n", "nosuch"])
    assert "Profile: nosuch" not in out
