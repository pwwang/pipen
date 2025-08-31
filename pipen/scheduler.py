"""Provide builting schedulers"""

from __future__ import annotations

from typing import TYPE_CHECKING, Type

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
from xqute.schedulers.gbatch_scheduler import (
    GbatchScheduler as XquteGbatchScheduler,
    DEFAULT_MOUNTED_ROOT,
)
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
        mount: GCS path to mount (e.g. gs://my-bucket:/mnt/my-bucket)
            You can pass a list of mounts.
        service_account: GCP service account email (e.g. test-account@example.com)
        network: GCP network (e.g. default-network)
        subnetwork: GCP subnetwork (e.g. regions/us-central1/subnetworks/default)
        no_external_ip_address: Whether to disable external IP address
        machine_type: GCP machine type (e.g. e2-standard-4)
        provisioning_model: GCP provisioning model (e.g. SPOT)
        image_uri: Container image URI (e.g. ubuntu-2004-lts)
        entrypoint: Container entrypoint (e.g. /bin/bash)
        commands: The command list to run in the container.
            There are three ways to specify the commands:
            1. If no entrypoint is specified, the final command will be
            [commands, wrapped_script], where the entrypoint is the wrapper script
            interpreter that is determined by `JOBCMD_WRAPPER_LANG` (e.g. /bin/bash),
            commands is the list you provided, and wrapped_script is the path to the
            wrapped job script.
            2. You can specify something like "-c", then the final command
            will be ["-c", "wrapper_script_interpreter, wrapper_script"]
            3. You can use the placeholders `{lang}` and `{script}` in the commands
            list, where `{lang}` will be replaced with the interpreter (e.g. /bin/bash)
            and `{script}` will be replaced with the path to the wrapped job script.
            For example, you can specify ["{lang} {script}"] and the final command
            will be ["wrapper_interpreter, wrapper_script"]
        runnables: Additional runnables to run before or after the main job.
            Each runnable should be a dictionary that follows the
            [GCP Batch API specification](https://cloud.google.com/batch/docs/reference/rest/v1/projects.locations.jobs#runnable).
            You can also specify an "order" key in the dictionary to control the
            execution order of the runnables. Runnables with negative order
            will be executed before the main job, and those with non-negative
            order will be executed after the main job. The main job runnable
            will always be executed in the order it is defined in the list.
        **kwargs: Keyword arguments for the configuration of a job (e.g. taskGroups).
            See more details at <https://cloud.google.com/batch/docs/get-started>.
    """  # noqa: E501

    MOUNTED_METADIR: str = f"{DEFAULT_MOUNTED_ROOT}/pipen-pipeline/workdir"
    MOUNTED_OUTDIR: str = f"{DEFAULT_MOUNTED_ROOT}/pipen-pipeline/outdir"

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
        self.config["taskGroups"][0]["taskSpec"]["volumes"][0]["gcs"][
            "remotePath"
        ] = self.workdir.parent._no_prefix
        self.config["taskGroups"][0]["taskSpec"]["volumes"][0][
            "mountPath"
        ] = self.MOUNTED_METADIR

        # update the config to map the outdir to vm
        self.config["taskGroups"][0]["taskSpec"]["volumes"].append(
            Diot(
                {
                    "gcs": {"remotePath": proc.pipeline.outdir._no_prefix},
                    "mountPath": self.MOUNTED_OUTDIR,
                }
            )
        )

        # add labels
        self.config["labels"]["pipeline"] = proc.pipeline.name.lower()
        self.config["labels"]["proc"] = proc.name.lower()


class ContainerScheduler(  # type: ignore[misc]
    SchedulerPostInit,
    XquteContainerScheduler,
):
    """Scheduler to run jobs via containers (Docker/Podman/Apptainer)"""

    MOUNTED_METADIR: str = f"{DEFAULT_MOUNTED_ROOT}/pipen-pipeline/workdir"
    MOUNTED_OUTDIR: str = f"{DEFAULT_MOUNTED_ROOT}/pipen-pipeline/outdir"

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
