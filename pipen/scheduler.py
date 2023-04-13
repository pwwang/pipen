"""Provide builting schedulers"""
from __future__ import annotations

from typing import Type

from xqute import Scheduler
from xqute.schedulers.local_scheduler import (
    LocalJob as XquteLocalJob,
    LocalScheduler as XquteLocalScheduler,
)
from xqute.schedulers.sge_scheduler import (
    SgeJob as XquteSgeJob,
    SgeScheduler as XquteSgeScheduler
)
from xqute.schedulers.slurm_scheduler import (
    SlurmJob as XquteSlurmJob,
    SlurmScheduler as XquteSlurmScheduler,
)
from xqute.schedulers.ssh_scheduler import (
    SshJob as XquteSshJob,
    SshScheduler as XquteSshScheduler,
)

from .defaults import SCHEDULER_ENTRY_GROUP
from .exceptions import NoSuchSchedulerError, WrongSchedulerTypeError
from .job import Job
from .utils import is_subclass, load_entrypoints


class LocalJob(XquteLocalJob, Job):
    """Job class for local scheduler"""


class LocalScheduler(XquteLocalScheduler):
    """Local scheduler"""
    job_class = LocalJob


class SgeJob(XquteSgeJob, Job):
    """Job class for SGE scheduler"""


class SgeScheduler(XquteSgeScheduler):
    """SGE scheduler"""
    job_class = SgeJob


class SlurmJob(XquteSlurmJob, Job):
    """Job class for Slurm scheduler"""


class SlurmScheduler(XquteSlurmScheduler):
    """Slurm scheduler"""
    job_class = SlurmJob


class SshJob(XquteSshJob, Job):
    """Job class for SSH scheduler"""


class SshScheduler(XquteSshScheduler):
    """SSH scheduler"""
    job_class = SshJob


def get_scheduler(scheduler: str | Type[Scheduler]) -> Type[Scheduler]:
    """Get the scheduler by name of the scheduler class itself

    Args:
        scheduler: The scheduler class or name

    Returns:
        The scheduler class
    """
    if is_subclass(scheduler, Scheduler):
        return scheduler  # type: ignore

    if scheduler == "local":
        return LocalScheduler

    if scheduler == "sge":
        return SgeScheduler

    if scheduler == "slurm":
        return SlurmScheduler

    if scheduler == "ssh":
        return SshScheduler

    for n, obj in load_entrypoints(SCHEDULER_ENTRY_GROUP):  # pragma: no cover
        if n == scheduler:
            if not is_subclass(obj, Scheduler):
                raise WrongSchedulerTypeError(
                    "Scheduler should be a subclass of "
                    "pipen.scheduler.Scheduler."
                )
            return obj

    raise NoSuchSchedulerError(str(scheduler))
