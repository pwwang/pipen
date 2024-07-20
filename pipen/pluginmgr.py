"""Define hooks specifications and provide plugin manager"""
from __future__ import annotations

import shutil
from os import PathLike
from pathlib import Path
from functools import partial
from typing import Any, Dict, Callable, TYPE_CHECKING

from simplug import Simplug, SimplugResult, makecall
from xqute import JobStatus, Scheduler
from xqute.utils import a_read_text, a_write_text, asyncify

from .defaults import ProcOutputType
from .exceptions import ProcInputValueError, ProcOutputValueError
from .utils import get_mtime as _get_mtime


if TYPE_CHECKING:  # pragma: no cover
    import signal
    from simplug import SimplugImplCall
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
async def on_init(pipen: Pipen) -> None:
    """When the pipeline is initialized, and default configs are loaded

    Args:
        pipen: The Pipen object
    """


@plugin.spec
async def on_start(pipen: Pipen) -> None:
    """Right before the pipeline starts running.

    Process relationships are inferred.

    Args:
        pipen: The Pipen object
    """


@plugin.spec
async def on_complete(pipen: Pipen, succeeded: bool):
    """The the pipeline is completed.

    Args:
        pipen: The Pipen object
        succeeded: Whether the pipeline has successfully completed.
    """


@plugin.spec
def on_proc_create(proc: Proc):
    """Called Proc constructor when a process is created.

    Enables plugins to modify the default attributes of processes

    Args:
        proc: The Proc object
    """


@plugin.spec
async def on_proc_init(proc: Proc):
    """Called when a process is initialized.

    Allows plugins to modify the process attributes after initialization, but
    before the jobs are initialized.

    Args:
        proc: The Proc object
    """


@plugin.spec
def on_proc_input_computed(proc: Proc):
    """Called after process input data is computed.

    Args:
        proc: The Proc object
    """


@plugin.spec
def on_proc_script_computed(proc: Proc):
    """Called after process script is computed.

    The script is computed as a string that is about to compiled into a
    template.

    Args:
        proc: The Proc object
    """


@plugin.spec
async def on_proc_start(proc: Proc):
    """When a process is starting

    Args:
        proc: The process
    """


@plugin.spec(result=SimplugResult.TRY_ALL_FIRST_AVAIL)
def on_proc_shutdown(proc: Proc, sig: signal.Signals) -> None:
    """When pipeline is shutting down, by Ctrl-c for example.

    Return False to stop shutting down, but you have to shut it down
    by yourself, for example, `proc.xqute.task.cancel()`

    Only the first return value will be used.

    Args:
        pipen: The xqute object
        sig: The signal. `None` means a natural shutdown
    """


@plugin.spec
async def on_proc_done(proc: Proc, succeeded: bool | str) -> None:
    """When a process is done

    Args:
        proc: The process
        succeeded: Whether the process succeeded or not. 'cached' if all jobs
            are cached.
    """


@plugin.spec
async def on_job_init(proc: Proc, job: Job):
    """When a job is initialized

    Args:
        proc: The process
        job: The job
    """


@plugin.spec
async def on_job_queued(proc: Proc, job: Job):
    """When a job is queued in xqute. Note it might not be queued yet in
    the scheduler system.

    Args:
        proc: The process
        job: The job
    """


@plugin.spec(result=SimplugResult.TRY_ALL_FIRST_AVAIL)
async def on_job_submitting(proc: Proc, job: Job) -> bool:
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
async def on_job_submitted(proc: Proc, job: Job):
    """When a job is submitted in the scheduler system.

    Args:
        proc: The process
        job: The job
    """


@plugin.spec
async def on_job_started(proc: Proc, job: Job):
    """When a job starts to run in then scheduler system.

    Note that the job might not be running yet in the scheduler system.

    Args:
        proc: The process
        job: The job
    """


@plugin.spec
async def on_job_polling(proc: Proc, job: Job):
    """When status of a job is being polled.

    Args:
        proc: The process
        job: The job
    """


@plugin.spec(result=SimplugResult.TRY_ALL_FIRST_AVAIL)
async def on_job_killing(proc: Proc, job: Job) -> bool:
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
async def on_job_killed(proc: Proc, job: Job):
    """When a job is killed

    Args:
        proc: The process
        job: The job
    """


@plugin.spec
async def on_job_succeeded(proc: Proc, job: Job):
    """When a job completes successfully.

    Args:
        proc: The process
        job: The job
    """


@plugin.spec
async def on_job_cached(proc: Proc, job: Job):
    """When a job is cached.

    Args:
        proc: The process
        job: The job
    """


@plugin.spec
async def on_job_failed(proc: Proc, job: Job):
    """When a job is done but failed.

    Args:
        proc: The process
        job: The job
    """


class PipenMainPlugin:
    """The builtin core plugin, used to update the progress bar and
    cache the job"""

    name = "core"
    # The priority is set to -1000 to make sure it is the first plugin
    # to be called
    priority = -1000

    @plugin.impl
    def on_proc_shutdown(self, proc: Proc, sig: signal.Signals):
        """When a process is shutting down"""
        if sig:  # pragma: no cover
            proc.log(
                "warning",
                "Got signal %r, trying a graceful shutdown ...",
                sig.name,
            )

    @plugin.impl
    async def on_job_submitted(self, proc: Proc, job: Job):
        """Update the progress bar when a job is submitted"""
        proc.pbar.update_job_submitted()

    @plugin.impl
    async def on_job_started(self, proc: Proc, job: Job):
        """Update the progress bar when a job starts to run"""
        proc.pbar.update_job_running()

    @plugin.impl
    async def on_job_cached(self, proc: Proc, job: Job):
        """Update the progress bar when a job is cached"""
        proc.pbar.update_job_submitted()
        proc.pbar.update_job_running()
        proc.pbar.update_job_succeeded()
        job.status = JobStatus.FINISHED

    @plugin.impl
    async def on_job_succeeded(self, proc: Proc, job: Job):
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
    async def on_job_failed(self, proc: Proc, job: Job):
        """Update the progress bar when a job is failed"""
        proc.pbar.update_job_failed()
        if job.status == JobStatus.RETRYING:
            job.log("debug", "Retrying #%s", job.trial_count + 1)
            proc.pbar.update_job_retrying()

    @plugin.impl
    async def on_job_killed(self, proc: Proc, job: Job):
        """Update the status of a killed job"""
        # instead of FINISHED to force the whole pipeline to quit
        job.status = JobStatus.FAILED  # pragma: no cover


plugin.register(PipenMainPlugin)

ioplugin = Simplug("pipen.io")


def _collect_io_results(
    calls: list[SimplugImplCall],
    exc: Callable[[list[SimplugImplCall]], Exception],
    convert: Callable = None,
) -> Any:
    for call in calls:
        out = makecall(call)
        if out is not None:
            return convert(out) if convert else out

    raise exc  # pragma: no cover


async def _acollect_io_results(
    calls: list[SimplugImplCall],
    exc: Callable[[list[SimplugImplCall]], Exception],
    convert: Callable = None,
) -> Any:
    for call in calls:
        out = await makecall(call, True)
        if out is not None:
            return convert(out) if convert else out

    raise exc  # pragma: no cover


@ioplugin.spec(
    result=partial(
        _collect_io_results,
        exc=lambda calls: ProcInputValueError(
            f"Unsupported protocol for input path: {calls[0].args[0]}"
        ),
        convert=str,
    )
)
def norm_inpath(inpath: str | PathLike, is_dir: bool) -> str:
    """Normalize the input path

    Args:
        inpath: The input path
        is_dir: Whether the path is a directory

    Returns:
        The normalized path
    """


@ioplugin.spec(
    result=partial(
        _collect_io_results,
        exc=lambda calls: ProcOutputValueError(
            f"Unsupported protocol for output path: {calls[0].args[1]}"
        ),
        convert=str,
    )
)
def norm_outpath(outdir: Path, outpath: str, is_dir: bool) -> str:
    """Normalize the output path

    Args:
        outdir: The job output directory
        outpath: The output path
        is_dir: Whether the path is a directory

    Returns:
        The normalized path
    """


@ioplugin.spec(
    result=partial(
        _collect_io_results,
        exc=lambda calls: NotImplementedError(
            f"Unsupported protocol in path to get mtime: {calls[0].args[0]}"
        ),
    )
)
def get_mtime(path: str | PathLike, dirsig: int) -> float:
    """Get the mtime of a path, either a file or a directory

    Args:
        path: The path to get mtime
        dirsig: The depth of the directory to check the last modification time

    Returns:
        The last modification time
    """


@ioplugin.spec(
    result=partial(
        _acollect_io_results,
        exc=lambda calls: NotImplementedError(
            f"Unsupported protocol in path to clear: {calls[0].args[0]}"
        ),
    )
)
async def clear_path(path: str | PathLike, is_dir: bool) -> bool:
    """Clear the path, either a file or a directory

    Args:
        path: The path to clear
        is_dir: Whether the path is a directory

    Returns:
        Whether the path is cleared successfully
    """


@ioplugin.spec(
    result=partial(
        _acollect_io_results,
        exc=lambda calls: NotImplementedError(
            f"Unsupported protocol in path to test existence: {calls[0].args[0]}"
        ),
    )
)
async def output_exists(path: str, is_dir: bool) -> bool:
    """Check if the output exists

    Args:
        path: The path to check
        is_dir: Whether the path is a directory

    Returns:
        Whether the output exists
    """


class PipenMainIOPlugin:
    """The builtin core plugin for IO"""

    name = "core"
    # The priority is set to 9999 to make sure it is the last plugin
    # to be called
    priority = 9999

    @ioplugin.impl
    def norm_inpath(
        self,
        inpath: str | PathLike,
        is_dir: bool,
    ):
        """Normalize the input path"""
        return str(Path(inpath).expanduser().resolve())

    @ioplugin.impl
    def norm_outpath(
        self,
        outdir: Path,
        outpath: str,
        is_dir: bool,
    ):
        """Normalize the output path"""
        if Path(outpath).is_absolute():
            raise ProcOutputValueError("Process output should be a relative path")

        out = outdir.resolve() / outpath
        if is_dir:
            out.mkdir(parents=True, exist_ok=True)

        return str(out)

    @ioplugin.impl
    def get_mtime(
        self,
        path: str | PathLike,
        dirsig: int,
    ):
        """Get the mtime of a path"""
        return _get_mtime(path, dirsig)

    @ioplugin.impl
    async def clear_path(self, path: str | PathLike, is_dir: bool):
        """Clear the path"""
        # dead link

        path = Path(path)
        try:
            if not path.exists():
                if path.is_symlink():
                    await asyncify(Path.unlink)(path)

            elif not is_dir:
                await asyncify(Path.unlink)(path)

            else:
                await asyncify(shutil.rmtree)(path)
                path.mkdir()
        except Exception:  # pragma: no cover
            return False
        return True

    @ioplugin.impl
    async def output_exists(self, path: str, is_dir: bool):
        """Check if the output exists"""
        path: Path = Path(path)
        if not path.exists():
            return False
        if is_dir:
            return len(list(path.iterdir())) > 0  # pragma: no cover
        return True


ioplugin.register(PipenMainIOPlugin)

xqute_plugin = Simplug("xqute")


class XqutePipenPlugin:
    """The plugin for xqute working as proxy for pipen plugin hooks"""

    name = "xqute.pipen"

    @xqute_plugin.impl
    def on_shutdown(self, xqute: Xqute, sig: signal.Signals):
        """When a process is shutting down"""
        return plugin.hooks.on_proc_shutdown(xqute.proc, sig)

    @xqute_plugin.impl
    async def on_job_init(self, scheduler: Scheduler, job: Job):
        """When a job is initialized"""
        await plugin.hooks.on_job_init(job.proc, job)

    @xqute_plugin.impl
    async def on_job_queued(self, scheduler: Scheduler, job: Job):
        """When a job is queued"""
        await plugin.hooks.on_job_queued(job.proc, job)

    @xqute_plugin.impl
    async def on_job_submitting(self, scheduler: Scheduler, job: Job):
        """When a job is being submitted"""
        return await plugin.hooks.on_job_submitting(job.proc, job)

    @xqute_plugin.impl
    async def on_job_submitted(self, scheduler: Scheduler, job: Job):
        """When a job is submitted"""
        await plugin.hooks.on_job_submitted(job.proc, job)

    @xqute_plugin.impl
    async def on_job_started(self, scheduler: Scheduler, job: Job):
        """When a job starts to run"""
        await plugin.hooks.on_job_started(job.proc, job)

    @xqute_plugin.impl
    async def on_job_polling(self, scheduler: Scheduler, job: Job):
        """When a job starts to run"""
        await plugin.hooks.on_job_polling(job.proc, job)

    @xqute_plugin.impl
    async def on_job_killing(self, scheduler: Scheduler, job: Job):
        """When a job is being killed"""
        return await plugin.hooks.on_job_killing(  # pragma: no cover
            job.proc,
            job,
        )

    @xqute_plugin.impl
    async def on_job_killed(self, scheduler: Scheduler, job: Job):
        """When a job is killed"""
        await plugin.hooks.on_job_killed(  # pragma: no cover
            job.proc,
            job,
        )

    @xqute_plugin.impl
    async def on_job_succeeded(self, scheduler: Scheduler, job: Job):
        """When a job is succeeded"""
        await plugin.hooks.on_job_succeeded(job.proc, job)

    @xqute_plugin.impl
    async def on_job_failed(self, scheduler: Scheduler, job: Job):
        """When a job is failed"""
        await plugin.hooks.on_job_failed(job.proc, job)


xqute_plugin.register(XqutePipenPlugin)
