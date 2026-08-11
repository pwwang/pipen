"""Provide builting schedulers"""

from __future__ import annotations

from typing import TYPE_CHECKING, Type
from pathlib import Path

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
    fs_shared = True

    async def init_proc(self, proc: Proc) -> None:
        """Initialize the proc for the scheduler

        Args:
            proc: The proc to initialize
        """
        await self.post_init()  # type: ignore
        self._post_init_called = True

        proc.workdir = self.workdir = self.workdir / proc.name  # type: ignore


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
    fs_shared = False  # Gbatch scheduler does not share file system with the host

    async def init_proc(self, proc: Proc):
        await super().init_proc(proc)

        volumes = self.config["taskGroups"][0]["taskSpec"]["volumes"]
        # Check mount_as_cwd was given and workdir_set
        # if mount_as_cwd is given, and the first volume must be the mount_as_cwd
        outdir = proc.pipeline.outdir
        outdir_mount_needed = False
        mounted_outdir = (
            f"{self.DEFAULT_MOUNTED_ROOT}/"
            f"{DEFAULT_WORKDIR_NAME}-{proc.pipeline.name}-output"
        )
        if self._kwargs["mount_as_cwd"]:
            outdir_mount_needed = outdir.is_absolute()  # type: ignore
            if not outdir_mount_needed:
                mounted_outdir = f"{self.cwd}/{outdir}"
                outdir = PanPath(self._kwargs['mount_as_cwd']) / outdir  # type: ignore

        elif self.cwd:
            cwd = Path(self.cwd)
            outdir_mount_needed = outdir.is_absolute()  # type: ignore
            if not outdir_mount_needed:
                cloud_cwd = None
                for vol in volumes:
                    if cwd.is_relative_to(vol["mountPath"]):
                        cloud_cwd = (
                            PanPath(f"gs://{vol['gcs']['remotePath']}")
                            / cwd.relative_to(vol["mountPath"]),
                            Path(vol["mountPath"]) / cwd.relative_to(vol["mountPath"]),
                        )
                        break

                if cloud_cwd is None:
                    raise ValueError(
                        "Can't determine outdir with a relative path to "
                        "the mounted cwd. Use an absolute path for outdir or ensure "
                        "`cwd` is under one of the mounted paths."
                    )

                mounted_outdir = cloud_cwd[1] / outdir  # type: ignore
                outdir = cloud_cwd[0] / outdir  # type: ignore
        else:
            outdir_mount_needed = True

        # Check if pipeline outdir is a GSPath
        if not isinstance(outdir, GSPath):
            raise ValueError(
                "'gbatch' scheduler requires google cloud storage 'outdir'."
            )

        if outdir_mount_needed:
            # update the config to map the outdir to vm
            volumes.append(
                Diot(
                    {
                        "gcs": {
                            "remotePath": "/".join(outdir.parts[1:]),
                        },
                        "mountPath": mounted_outdir,
                    }
                )
            )

        # add labels
        self.config["labels"]["pipeline"] = proc.pipeline.name.lower()  # type: ignore
        self.config["labels"]["proc"] = proc.name.lower()  # type: ignore

        export_dir = SpecPath(outdir, mounted=mounted_outdir)  # type: ignore
        proc._export_dir = export_dir / proc.name  # type: ignore


class ContainerScheduler(  # type: ignore[misc]
    SchedulerPostInit,
    XquteContainerScheduler,
):
    __doc__ = XquteContainerScheduler.__doc__
    fs_shared = False  # Container scheduler does not share file system with the host

    async def init_proc(self, proc: Proc):
        await super().init_proc(proc)

        volues = self.volumes
        outdir = proc.pipeline.outdir
        outdir_mount_needed = False
        mounted_outdir = (
            f"{self.DEFAULT_MOUNTED_ROOT}/"
            f"{DEFAULT_WORKDIR_NAME}-{proc.pipeline.name}-output"
        )
        if self._kwargs["volume_as_cwd"]:
            outdir_mount_needed = outdir.is_absolute()  # type: ignore
            if not outdir_mount_needed:
                mounted_outdir = f"{self.cwd}/{outdir}"
                outdir = Path(f"{self._kwargs['volume_as_cwd']}/{outdir}")

        elif self.cwd:
            cwd = Path(self.cwd)
            outdir_mount_needed = outdir.is_absolute()  # type: ignore
            if not outdir_mount_needed:
                host_cwd = None
                for vol in volues:
                    host, mount = vol.rpartition(":")[::2]
                    if cwd.is_relative_to(mount):
                        host_cwd = (
                            Path(host) / cwd.relative_to(mount),
                            Path(mount) / cwd.relative_to(mount),
                        )
                        break

                if not host_cwd:
                    raise ValueError(
                        "Can't determine outdir with a relative path to "
                        "the mounted cwd. Use an absolute path for outdir or ensure "
                        "`cwd` is under one of the mounted paths."
                    )

                mounted_outdir = host_cwd[1] / outdir  # type: ignore
                outdir = host_cwd[0] / outdir  # type: ignore

        else:
            outdir = outdir.resolve()  # type: ignore
            outdir_mount_needed = True

        if outdir_mount_needed:
            self.volumes.append(f"{outdir}:{mounted_outdir}")  # type: ignore

        export_dir = SpecPath(outdir, mounted=mounted_outdir)  # type: ignore
        proc._export_dir = export_dir / proc.name  # type: ignore


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
