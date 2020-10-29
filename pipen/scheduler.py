"""Provide builting schedulers"""
from typing import Type, Union
from xqute import Scheduler
from xqute.schedulers.local_scheduler import (
    LocalJob as XquteLocalJob,
    LocalScheduler as XquteLocalScheduler
)
from xqute.schedulers.sge_scheduler import (
    SgeJob as XquteSgeJob,
    SgeScheduler as XquteSgeScheduler
)
from .job import Job

class LocalJob(Job):
    """Job class for local scheduler"""
    wrap_cmd = XquteLocalJob.wrap_cmd

class LocalScheduler(XquteLocalScheduler):
    """Local scheduler"""
    job_class = LocalJob

class SgeJob(Job):
    """Job class for sge scheduler"""
    wrap_cmd = XquteSgeJob.wrap_cmd

class SgeScheduler(XquteSgeScheduler):
    """Sge scheduler"""
    job_class = SgeJob

def get_scheduler(scheduler: Union[str, Type[Scheduler]]) -> Type[Scheduler]:
    """Get the scheduler by name of the scheduler class itself

    Args:
        scheduler: The scheduler class or name

    Returns:
        The scheduler class
    """
    if isinstance(scheduler, Scheduler):
        return scheduler

    if scheduler == 'local':
        return LocalScheduler
    if scheduler == 'sge':
        return SgeScheduler
    # TODO: get from entrypoint
    return None
