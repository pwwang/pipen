import pytest

from pipen.scheduler import *


def test_get_scheduler():
    sge = get_scheduler("sge")
    assert sge is SgeScheduler

    sge = get_scheduler(sge)
    assert sge is SgeScheduler

    with pytest.raises(NoSuchSchedulerError):
        get_scheduler("nosuchscheduler")
