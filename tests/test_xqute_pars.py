"""Test parameters for xqute"""
from pipen.proc import Proc  # noqa: F401
import pytest  # noqa: F401

import time  # noqa: F401
from .helpers import RetryProc, pipen  # noqa: F401


# pytest causing previous item was not torn down properly error
# @pytest.mark.forked
# def test_retry(caplog, pipen):  # noqa: F811
#     proc = Proc.from_proc(RetryProc)
#     rc = pipen.set_starts(proc).set_data([time.time()]).run()
#     assert "Retrying" in caplog.text
#     assert rc
