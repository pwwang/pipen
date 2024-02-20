"""Test parameters for xqute"""
from pipen.proc import Proc
import pytest

import time
from .helpers import RetryProc, pipen  # noqa: F401


@pytest.mark.forked
def test_retry(caplog, pipen):  # noqa: F811
    proc = Proc.from_proc(RetryProc)
    rc = pipen.set_starts(proc).set_data([time.time()]).run()
    assert "Retrying" in caplog.text
    assert rc
