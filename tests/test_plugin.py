import pytest

import time
import signal
from multiprocessing import Process
from pipen import plugin, Proc

from .helpers import pipen, OutputNotGeneratedProc

def test_job_succeeded(pipen, caplog):

    out = pipen.run(OutputNotGeneratedProc)
    assert not out
