"""Define hooks specifications and provide plugin manager"""
import signal
from pathlib import Path
from typing import Any, Dict, Optional, Union, TYPE_CHECKING

from simplug import Simplug, SimplugResult
from xqute import JobStatus, Scheduler
from xqute.utils import a_read_text, a_write_text

from .defaults import ProcOutputType


if TYPE_CHECKING:  # pragma: no cover
    from xqute import Xqute
    from .job import Job
    from .proc import Proc
    from .pipen import Pipen

plugin = Simplug("pipen")


@plugin.spec
def on_setup(config: Dict[str, Any]) -> None:
    """Setup for plugins, primarily used for the plugins to
    setup some default configurations.

    This is only called once for all pipelines.

    Args:
        config: The configuration dictionary
            plugin options should be defined under "plugin_opts"
            One should define a configuration item either with a prefix as
            the identity for the plugin or a namespace inside the plugin config
    """


@plugin.spec
async def on_init(pipen: "Pipen") -> None:
    """When the pipeline is initialized, and default configs are loaded

    Args:
        pipen: The Pipen object
    """


@plugin.spec
async def on_start(pipen: "Pipen") -> None:
    """Right before the pipeline starts running.

    Process relationships are inferred.

    Args:
        pipen: The Pipen object
    """


@plugin.spec
async def on_complete(pipen: "Pipen", succeeded: bool):
    """The the pipeline is completed.

    Args:
        pipen: The Pipen object
        succeeded: Whether the pipeline has successfully completed.
    """


@plugin.spec
def on_proc_init(proc: "Proc"):
    """Called before proc get instantiated.

    Enables plugins to modify the default attributes of processes

    Args:
        proc: The Proc object
    """


@plugin.spec
def on_proc_input_computed(proc: "Proc"):
    """Called after process input data is computed.

    Args:
        proc: The Proc object
    """


@plugin.spec
async def on_proc_start(proc: "Proc"):
    """When a process is starting

    Args:
        proc: The process
    """


@plugin.spec(result=SimplugResult.FIRST)
def on_proc_shutdown(proc: "Proc", sig: Optional[signal.Signals]) -> None:
    """When pipeline is shutting down, by Ctrl-c for example.

    Return False to stop shutting down, but you have to shut it down
    by yourself, for example, `proc.xqute.task.cancel()`

    Only the first return value will be used.

    Args:
        pipen: The xqute object
        sig: The signal. `None` means a natural shutdown
    """


@plugin.spec
async def on_proc_done(proc: "Proc", succeeded: Union[bool, str]) -> None:
    """When a process is done

    Args:
        proc: The process
        succeeded: Whether the process succeeded or not. 'cached' if all jobs
            are cached.
    """


@plugin.spec
async def on_job_init(proc: "Proc", job: "Job"):
    """When a job is initialized

    Args:
        proc: The process
        job: The job
    """


@plugin.spec
async def on_job_queued(proc: "Proc", job: "Job"):
    """When a job is queued in xqute. Note it might not be queued yet in
    the scheduler system.

    Args:
        proc: The process
        job: The job
    """


@plugin.spec(result=SimplugResult.FIRST)
async def on_job_submitting(proc: "Proc", job: "Job") -> Optional[bool]:
    """When a job is submitting.

    The first plugin (based on priority) have this hook return False will
    cancel the submission

    Args:
        proc: The process
        job: The job

    Returns:
        False to cancel submission
    """


@plugin.spec
async def on_job_submitted(proc: "Proc", job: "Job"):
    """When a job is submitted in the scheduler system.

    Args:
        proc: The process
        job: The job
    """


@plugin.spec
async def on_job_running(proc: "Proc", job: "Job"):
    """When a job starts to run in then scheduler system.

    Args:
        proc: The process
        job: The job
    """


@plugin.spec(result=SimplugResult.FIRST)
async def on_job_killing(proc: "Proc", job: "Job") -> Optional[bool]:
    """When a job is being killed.

    The first plugin (based on priority) have this hook return False will
    cancel the killing

    Args:
        proc: The process
        job: The job

    Returns:
        False to cancel killing
    """


@plugin.spec
async def on_job_killed(proc: "Proc", job: "Job"):
    """When a job is killed

    Args:
        proc: The process
        job: The job
    """


@plugin.spec
async def on_job_succeeded(proc: "Proc", job: "Job"):
    """When a job completes successfully.

    Args:
        proc: The process
        job: The job
    """


@plugin.spec
async def on_job_failed(proc: "Proc", job: "Job"):
    """When a job is done but failed.

    Args:
        proc: The process
        job: The job
    """


class PipenMainPlugin:
    """The builtin main plugin, used to update the progress bar and
    cache the job"""

    name = "main"

    @plugin.impl
    def on_proc_shutdown(self, proc: "Proc", sig: Optional[signal.Signals]):
        """When a process is shutting down"""
        if sig:  # pragma: no cover
            proc.log(
                "warning",
                "Got signal %r, trying a graceful shutdown ...",
                sig.name,
            )

    @plugin.impl
    async def on_job_submitted(self, proc: "Proc", job: "Job"):
        """Update the progress bar when a job is submitted"""
        proc.pbar.update_job_submitted()

    @plugin.impl
    async def on_job_running(self, proc: "Proc", job: "Job"):
        """Update the progress bar when a job starts to run"""
        proc.pbar.update_job_running()

    @plugin.impl
    async def on_job_succeeded(self, proc: "Proc", job: "Job"):
        """Cache the job and update the progress bar when a job is succeeded"""
        # now the returncode is 0, however, we need to check if output files
        # have been created or not, this makes sure job.cache not fail
        for outkey, outtype in job._output_types.items():
            if outtype == ProcOutputType.VAR:
                continue
            if not Path(job.output[outkey]).exists():
                job.status = JobStatus.FAILED
                proc.pbar.update_job_failed()
                stderr = await a_read_text(job.stderr_file)
                stderr = (
                    f"{stderr}\n\nOutput {outtype} {outkey!r} "
                    "is not generated."
                )
                await a_write_text(job.stderr_file, stderr)
                break
        else:
            await job.cache()
            proc.pbar.update_job_succeeded()

    @plugin.impl
    async def on_job_failed(self, proc: "Proc", job: "Job"):
        """Update the progress bar when a job is failed"""
        proc.pbar.update_job_failed()
        if job.status == JobStatus.RETRYING:
            job.log("debug", "Retrying #%s", job.trial_count + 1)
            proc.pbar.update_job_retrying()

    @plugin.impl
    async def on_job_killed(self, proc: "Proc", job: "Job"):
        """Update the status of a killed job"""
        # instead of FINISHED to force the whole pipeline to quit
        job.status = JobStatus.FAILED  # pragma: no cover


plugin.register(PipenMainPlugin)

xqute_plugin = Simplug("xqute")


class XqutePipenPlugin:
    """The plugin for xqute working as proxy for pipen plugin hooks"""

    name = "xqute.pipen"

    @xqute_plugin.impl
    def on_shutdown(self, xqute: "Xqute", sig: Optional[signal.Signals]):
        """When a process is shutting down"""
        return plugin.hooks.on_proc_shutdown(xqute.proc, sig)

    @xqute_plugin.impl
    async def on_job_init(self, scheduler: Scheduler, job: "Job"):
        """When a job is initialized"""
        await plugin.hooks.on_job_init(job.proc, job)

    @xqute_plugin.impl
    async def on_job_queued(self, scheduler: Scheduler, job: "Job"):
        """When a job is queued"""
        await plugin.hooks.on_job_queued(job.proc, job)

    @xqute_plugin.impl
    async def on_job_submitting(self, scheduler: Scheduler, job: "Job"):
        """When a job is being submitted"""
        return await plugin.hooks.on_job_submitting(job.proc, job)

    @xqute_plugin.impl
    async def on_job_submitted(self, scheduler: Scheduler, job: "Job"):
        """When a job is submitted"""
        await plugin.hooks.on_job_submitted(job.proc, job)

    @xqute_plugin.impl
    async def on_job_running(self, scheduler: Scheduler, job: "Job"):
        """When a job starts to run"""
        await plugin.hooks.on_job_running(job.proc, job)

    @xqute_plugin.impl
    async def on_job_killing(self, scheduler: Scheduler, job: "Job"):
        """When a job is being killed"""
        return await plugin.hooks.on_job_killing(  # pragma: no cover
            job.proc,
            job,
        )

    @xqute_plugin.impl
    async def on_job_killed(self, scheduler: Scheduler, job: "Job"):
        """When a job is killed"""
        await plugin.hooks.on_job_killed(  # pragma: no cover
            job.proc,
            job,
        )

    @xqute_plugin.impl
    async def on_job_succeeded(self, scheduler: Scheduler, job: "Job"):
        """When a job is succeeded"""
        await plugin.hooks.on_job_succeeded(job.proc, job)

    @xqute_plugin.impl
    async def on_job_failed(self, scheduler: Scheduler, job: "Job"):
        """When a job is failed"""
        await plugin.hooks.on_job_failed(job.proc, job)


xqute_plugin.register(XqutePipenPlugin)
