"""Provide builting schedulers"""

from __future__ import annotations

from typing import TYPE_CHECKING, Type

from diot import Diot

from panpath import GSPath, PanPath
from xqute import Scheduler
from xqute.path import SpecPath
from xqute.defaults import DEFAULT_WORKDIR_NAME
from xqute.schedulers.local_scheduler import LocalScheduler as XquteLocalScheduler
from xqute.schedulers.sge_scheduler import SgeScheduler as XquteSgeScheduler
from xqute.schedulers.slurm_scheduler import SlurmScheduler as XquteSlurmScheduler
from xqute.schedulers.ssh_scheduler import (
    SshScheduler as XquteSshScheduler,  # type: ignore[misc]
)
from xqute.schedulers.gbatch_scheduler import (
    GbatchScheduler as XquteGbatchScheduler,
)
from xqute.schedulers.container_scheduler import (
    ContainerScheduler as XquteContainerScheduler,
)

from .defaults import SCHEDULER_ENTRY_GROUP
from .exceptions import NoSuchSchedulerError, WrongSchedulerTypeError
from .job import Job
from .utils import is_subclass, load_entrypoints

if TYPE_CHECKING:
    from .proc import Proc


class SchedulerPostInit:
    """Provides post init function for all schedulers"""

    job_class = Job

    async def post_init(self, proc: Proc) -> None: ...  # noqa: E704


class LocalScheduler(SchedulerPostInit, XquteLocalScheduler):  # type: ignore[misc]
    """Local scheduler"""


class SgeScheduler(SchedulerPostInit, XquteSgeScheduler):  # type: ignore[misc]
    """SGE scheduler"""


class SlurmScheduler(SchedulerPostInit, XquteSlurmScheduler):  # type: ignore[misc]
    """Slurm scheduler"""


class SshScheduler(SchedulerPostInit, XquteSshScheduler):  # type: ignore[misc]
    """SSH scheduler"""


class GbatchScheduler(SchedulerPostInit, XquteGbatchScheduler):  # type: ignore[misc]
    __doc__ = XquteGbatchScheduler.__doc__

    def __init__(self, *args, **kwargs):
        workdir = PanPath(kwargs["workdir"])
        proc_name = workdir.name
        # instead of mounting the workdir of this specific proc,
        # we mount the parent dir (the pipeline workdir), because the procs
        # of the pipeline may share files (e.g. input files from output of other procs)
        kwargs["workdir"] = str(workdir.parent)
        super().__init__(*args, **kwargs)

        self._mount_as_cwd = kwargs.get("mount_as_cwd") or kwargs.get("volume_as_cwd")
        self.workdir = self.workdir / proc_name

    async def post_init(self, proc: Proc):
        await super().post_init(proc)
        proc.workdir = self.workdir

        volumes = self.config["taskGroups"][0]["taskSpec"]["volumes"]
        # Check mount_as_cwd was given and workdir_set
        # if mount_as_cwd is given, and the first volume must be the mount_as_cwd
        outdir = proc.pipeline.outdir
        outdir_mount_needed = False
        mounted_outdir = None
        if outdir.is_absolute():  # type: ignore
            outdir_mount_needed = True
            mounted_outdir = (
                f"{self.DEFAULT_MOUNTED_ROOT}/"
                f"{DEFAULT_WORKDIR_NAME}-{proc.pipeline.name}-output"
            )
        elif self._mount_as_cwd:
            outdir_mount_needed = False
            mounted_outdir = f"{self.cwd}/{outdir}"
            outdir = PanPath(self._mount_as_cwd) / str(outdir)

        # Check if pipeline outdir is a GSPath
        if not isinstance(outdir, GSPath):
            raise ValueError(
                "'gbatch' scheduler requires google cloud storage 'outdir'."
            )

        proc._export_dir = SpecPath(proc._export_dir, mounted=mounted_outdir)

        if outdir_mount_needed:
            # update the config to map the outdir to vm
            volumes.append(
                Diot(
                    {
                        "gcs": {
                            "remotePath": str(proc.pipeline.outdir).split("://", 1)[1]
                        },
                        "mountPath": mounted_outdir,
                    }
                )
            )

        # add labels
        self.config["labels"]["pipeline"] = proc.pipeline.name.lower()  # type: ignore
        self.config["labels"]["proc"] = proc.name.lower()


class ContainerScheduler(  # type: ignore[misc]
    SchedulerPostInit,
    XquteContainerScheduler,
):
    __doc__ = XquteContainerScheduler.__doc__

    def __init__(self, *args, **kwargs):
        workdir = PanPath(kwargs["workdir"])
        proc_name = workdir.name
        # instead of mounting the workdir of this specific proc,
        # we mount the parent dir (the pipeline workdir), because the procs
        # of the pipeline may share files (e.g. input files from output of other procs)
        kwargs["workdir"] = str(workdir.parent)
        super().__init__(*args, **kwargs)

        self._mount_as_cwd = kwargs.get("mount_as_cwd") or kwargs.get("volume_as_cwd")
        self.workdir = self.workdir / proc_name

    async def post_init(self, proc: Proc):
        await super().post_init(proc)
        proc.workdir = self.workdir

        outdir = proc.pipeline.outdir
        if self._mount_as_cwd and not outdir.is_absolute():  # type: ignore
            outdir_mount_needed = False
            mounted_outdir = f"{self._mount_as_cwd}/{outdir}"
            outdir = PanPath(self._mount_as_cwd) / str(outdir)
        else:
            outdir_mount_needed = True
            mounted_outdir = (
                f"{self.DEFAULT_MOUNTED_ROOT}/"
                f"{DEFAULT_WORKDIR_NAME}-{proc.pipeline.name}-output"
            )

        if outdir_mount_needed:
            self.volumes.append(f"{outdir}:{mounted_outdir}")  # type: ignore

        proc._export_dir = SpecPath(proc._export_dir, mounted=mounted_outdir)


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

    if scheduler == "container":
        return ContainerScheduler

    for n, obj in load_entrypoints(SCHEDULER_ENTRY_GROUP):  # pragma: no cover
        if n == scheduler:
            if not is_subclass(obj, Scheduler):
                raise WrongSchedulerTypeError(
                    "Scheduler should be a subclass of " "pipen.scheduler.Scheduler."
                )
            return obj

    raise NoSuchSchedulerError(str(scheduler))
