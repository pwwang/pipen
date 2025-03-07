"""Provide builting schedulers"""

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence, Type

from diot import Diot

# Use cloudpathlib.GSPath instead of yunpath.GSPath,
# the latter is a subclass of the former.
# (_GSPath is cloudpathlib.GSPath)
from yunpath.patch import _GSPath
from xqute import Scheduler
from xqute.schedulers.local_scheduler import LocalScheduler as XquteLocalScheduler
from xqute.schedulers.sge_scheduler import SgeScheduler as XquteSgeScheduler
from xqute.schedulers.slurm_scheduler import SlurmScheduler as XquteSlurmScheduler
from xqute.schedulers.ssh_scheduler import SshScheduler as XquteSshScheduler
from xqute.schedulers.gbatch_scheduler import GbatchScheduler as XquteGbatchScheduler
from xqute.path import SpecPath

from .defaults import SCHEDULER_ENTRY_GROUP
from .exceptions import NoSuchSchedulerError, WrongSchedulerTypeError
from .job import Job
from .utils import is_subclass, load_entrypoints

if TYPE_CHECKING:
    from .proc import Proc


class SchedulerPostInit:
    """Provides post init function for all schedulers"""

    job_class = Job

    MOUNTED_METADIR: str
    MOUNTED_OUTDIR: str

    def post_init(self, proc: Proc) -> None: ...  # noqa: E704


class LocalScheduler(SchedulerPostInit, XquteLocalScheduler):
    """Local scheduler"""


class SgeScheduler(SchedulerPostInit, XquteSgeScheduler):
    """SGE scheduler"""


class SlurmScheduler(SchedulerPostInit, XquteSlurmScheduler):
    """Slurm scheduler"""


class SshScheduler(SchedulerPostInit, XquteSshScheduler):
    """SSH scheduler"""


class GbatchScheduler(SchedulerPostInit, XquteGbatchScheduler):
    """Google Cloud Batch scheduler"""

    MOUNTED_METADIR: str = "/mnt/pipen-pipeline/workdir"
    MOUNTED_OUTDIR: str = "/mnt/pipen-pipeline/outdir"

    # fast mount is used to add a volume taskGroups[0].taskSpec.volumes
    # to mount additional cloud directory to the VM
    # For example: fast_mount="gs://bucket/path:/mnt/path"
    # will add a volume: {
    #   "gcs": {"remotePath": "bucket/path"},
    #   "mountPath": "/mnt/path"
    # }
    def __init__(
        self,
        *args,
        project,
        location,
        fast_mount: str | Sequence[str] = None,
        **kwargs,
    ):
        super().__init__(*args, project=project, location=location, **kwargs)
        if not fast_mount:
            return

        if isinstance(fast_mount, str):
            fast_mount = [fast_mount]

        for fm in fast_mount:
            if fm.count(":") != 2:
                raise ValueError(
                    "'fast_mount' for gbatch scheduler should be in the format of "
                    "'gs://bucket/path:/mnt/path'"
                )

            if not fm.startswith("gs://"):
                raise ValueError(
                    "'fast_mount' for gbatch scheduler should be "
                    "a Google Cloud Storage path (begins with 'gs://')"
                )

            remote_path, mount_path = fm[5:].split(":", 1)
            self.config.taskGroups[0].taskSpec.volumes.append(
                Diot(
                    {
                        "gcs": {"remotePath": remote_path},
                        "mountPath": mount_path,
                    }
                )
            )

    def post_init(self, proc: Proc):
        super().post_init(proc)

        # Check if pipeline outdir is a GSPath
        if not isinstance(proc.pipeline.outdir, _GSPath):
            raise ValueError(
                "'gbatch' scheduler requires google cloud storage 'outdir'."
            )

        mounted_workdir = f"{self.MOUNTED_METADIR}/{proc.name}"
        self.workdir: SpecPath = SpecPath(self.workdir, mounted=mounted_workdir)

        # update the mounted metadir
        self.config.taskGroups[0].taskSpec.volumes[0].mountPath = mounted_workdir

        # update the config to map the outdir to vm
        self.config.taskGroups[0].taskSpec.volumes.append(
            Diot(
                {
                    "gcs": {"remotePath": proc.pipeline.outdir._no_prefix},
                    "mountPath": self.MOUNTED_OUTDIR,
                }
            )
        )


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

    if scheduler == "gbatch":
        return GbatchScheduler

    for n, obj in load_entrypoints(SCHEDULER_ENTRY_GROUP):  # pragma: no cover
        if n == scheduler:
            if not is_subclass(obj, Scheduler):
                raise WrongSchedulerTypeError(
                    "Scheduler should be a subclass of " "pipen.scheduler.Scheduler."
                )
            return obj

    raise NoSuchSchedulerError(str(scheduler))
