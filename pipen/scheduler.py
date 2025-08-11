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
from xqute.schedulers.container_scheduler import (
    ContainerScheduler as XquteContainerScheduler,
)
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


class LocalScheduler(SchedulerPostInit, XquteLocalScheduler):  # type: ignore[misc]
    """Local scheduler"""


class SgeScheduler(SchedulerPostInit, XquteSgeScheduler):  # type: ignore[misc]
    """SGE scheduler"""


class SlurmScheduler(SchedulerPostInit, XquteSlurmScheduler):  # type: ignore[misc]
    """Slurm scheduler"""


class SshScheduler(SchedulerPostInit, XquteSshScheduler):  # type: ignore[misc]
    """SSH scheduler"""


class GbatchScheduler(SchedulerPostInit, XquteGbatchScheduler):  # type: ignore[misc]
    """Google Cloud Batch scheduler

    Args:
        *args: Positional arguments for the base class
        project: Google Cloud project ID
        location: Google Cloud region or zone
        fast_mount: Optional; a string or a sequence of strings to mount additional
            Google Cloud Storage paths to the VM. The format should be
            "gs://bucket/path:/mnt/path". This will add a volume to the VM
            with the specified remote path mounted at the specified mount path.
            The configuration will be expanded to the `taskGroups[0].taskSpec.volumes`.
        fast_container: Optional; a dictionary to configure the container, a shortcut
            for `taskGroups[0].taskSpec.runnables[0].container`.
            When both provided, `fast_container` will override the configuration
            specified in `taskGroups[0].taskSpec.runnables[0].container` in `kwargs`.
        **kwargs: Keyword arguments for the configuration of a job (e.g. taskGroups).
            See more details at <https://cloud.google.com/batch/docs/get-started>.
    """

    MOUNTED_METADIR: str = "/mnt/disks/pipen-pipeline/workdir"
    MOUNTED_OUTDIR: str = "/mnt/disks/pipen-pipeline/outdir"

    def __init__(
        self,
        *args,
        project,
        location,
        fast_mount: str | Sequence[str] = None,
        fast_container: dict | None = None,
        **kwargs,
    ):
        fast_container = fast_container or {}
        # we need to let kwargs know that we have container
        # so the Scheduler can handle it properly (specify the script to
        # the container, instead of script.text)
        if fast_container:
            try:
                task_groups = kwargs.setdefault("taskGroups", [{}])
                task_spec = task_groups[0].setdefault("taskSpec", {})
                runnables = task_spec.setdefault("runnables", [{}])
                container = runnables[0].setdefault("container", {})
                container.update(fast_container)
            except (AttributeError, TypeError, IndexError, KeyError):
                # Let super().__init__ handle the error
                pass

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
        self.workdir = SpecPath(
            self.workdir,  # type: ignore
            mounted=mounted_workdir,
        )

        # update the mounted metadir
        # instead of mounting the workdir of this specific proc,
        # we mount the parent dir (the pipeline workdir), because the procs
        # of the pipeline may share files (e.g. input files from output of other procs)
        self.config.taskGroups[0].taskSpec.volumes[0].gcs[
            "remotePath"
        ] = self.workdir.parent._no_prefix
        self.config.taskGroups[0].taskSpec.volumes[0].mountPath = self.MOUNTED_METADIR

        # update the config to map the outdir to vm
        self.config.taskGroups[0].taskSpec.volumes.append(
            Diot(
                {
                    "gcs": {"remotePath": proc.pipeline.outdir._no_prefix},
                    "mountPath": self.MOUNTED_OUTDIR,
                }
            )
        )

        # add labels
        self.config.labels["pipeline"] = proc.pipeline.name.lower()
        self.config.labels["proc"] = proc.name.lower()


class ContainerScheduler(  # type: ignore[misc]
    SchedulerPostInit,
    XquteContainerScheduler,
):
    """Scheduler to run jobs via containers (Docker/Podman/Apptainer)"""

    MOUNTED_METADIR: str = "/mnt/disks/pipen-pipeline/workdir"
    MOUNTED_OUTDIR: str = "/mnt/disks/pipen-pipeline/outdir"

    def post_init(self, proc: Proc):
        super().post_init(proc)

        mounted_workdir = f"{self.MOUNTED_METADIR}/{proc.name}"
        self.workdir = SpecPath(
            str(self.workdir),  # ignore the mounted_workdir by xqute
            mounted=mounted_workdir,
        )
        self.volumes[-1] = f"{self.workdir}:{self.workdir.mounted}"  # type: ignore
        proc.pipeline.outdir.mkdir(parents=True, exist_ok=True)  # type: ignore
        self.volumes.append(f"{proc.pipeline.outdir}:{self.MOUNTED_OUTDIR}")


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
