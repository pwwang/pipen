"""Test parameters for xqute"""
from pipen.proc import Proc
import pytest

import time
from .helpers import RetryProc, get_simple_pipen

def test_retry(caplog):
    pipen = get_simple_pipen()
    proc = Proc.from_proc(RetryProc, input_data=[time.time()])
    rc = pipen.run(proc)
    assert "Retrying" in caplog.text
    assert rc
