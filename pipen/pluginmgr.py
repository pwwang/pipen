"""Define hooks specifications and provide plugin manager"""
from __future__ import annotations

import shutil
from os import PathLike
from pathlib import Path
from typing import Any, Dict, TYPE_CHECKING

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
async def on_job_init(job: Job):
    """When a job is initialized

    Args:
        job: The job
    """


@plugin.spec
async def on_job_queued(job: Job):
    """When a job is queued in xqute. Note it might not be queued yet in
    the scheduler system.

    Args:
        job: The job
    """


@plugin.spec(result=SimplugResult.TRY_ALL_FIRST_AVAIL)
async def on_job_submitting(job: Job) -> bool:
    """When a job is submitting.

    The first plugin (based on priority) have this hook return False will
    cancel the submission

    Args:
        job: The job

    Returns:
        False to cancel submission
    """


@plugin.spec
async def on_job_submitted(job: Job):
    """When a job is submitted in the scheduler system.

    Args:
        job: The job
    """


@plugin.spec
async def on_job_started(job: Job):
    """When a job starts to run in then scheduler system.

    Note that the job might not be running yet in the scheduler system.

    Args:
        job: The job
    """


@plugin.spec
async def on_job_polling(job: Job):
    """When status of a job is being polled.

    Args:
        job: The job
    """


@plugin.spec(result=SimplugResult.TRY_ALL_FIRST_AVAIL)
async def on_job_killing(job: Job) -> bool:
    """When a job is being killed.

    The first plugin (based on priority) have this hook return False will
    cancel the killing

    Args:
        job: The job

    Returns:
        False to cancel killing
    """


@plugin.spec
async def on_job_killed(job: Job):
    """When a job is killed

    Args:
        job: The job
    """


@plugin.spec
async def on_job_succeeded(job: Job):
    """When a job completes successfully.

    Args:
        job: The job
    """


@plugin.spec
async def on_job_cached(job: Job):
    """When a job is cached.

    Args:
        job: The job
    """


@plugin.spec
async def on_job_failed(job: Job):
    """When a job is done but failed.

    Args:
        job: The job
    """


def _collect_norm_inpath(calls: list[SimplugImplCall]) -> str:
    for call in calls:
        out = makecall(call)
        if out is not None:
            return str(out)

    from .job import Job
    # The first argument could be self in implementation
    idx = 0 if isinstance(calls[0].args[0], Job) else 1
    job = calls[0].kwargs.pop("job", calls[0].args[idx])
    inpath = calls[0].kwargs.pop("inpath", calls[0].args[idx + 1])
    raise ProcInputValueError(
        f"[{job.proc.name}] Unsupported protocol for input path: "
        f"{inpath.split('://')[0]}://"
    )


@plugin.spec(result=_collect_norm_inpath)
def norm_inpath(job: Job, inpath: str | PathLike, is_dir: bool) -> str:
    """Normalize the input path

    Args:
        job: The job
        inpath: The input path
        is_dir: Whether the path is a directory

    Returns:
        The normalized path
    """


def _collect_norm_outpath(calls: list[SimplugImplCall]) -> str:
    for call in calls:
        out = makecall(call)
        if out is not None:
            return str(out)

    from .job import Job
    # The first argument could be self in implementation
    idx = 0 if isinstance(calls[0].args[0], Job) else 1
    job = calls[0].kwargs.pop("job", calls[0].args[idx])
    outpath = calls[0].kwargs.pop("outpath", calls[0].args[idx + 1])
    raise ProcOutputValueError(
        f"[{job.proc.name}] Unsupported protocol for output path: "
        f"{outpath.split('://')[0]}://"
    )


@plugin.spec(result=_collect_norm_outpath)
def norm_outpath(job: Job, outpath: str, is_dir: bool) -> str:
    """Normalize the output path

    Args:
        job: The job
        outpath: The output path
        is_dir: Whether the path is a directory

    Returns:
        The normalized path
    """


def _collect_get_mtime(calls: list[SimplugImplCall]) -> float:
    for call in calls:
        out = makecall(call)
        if out is not None:
            return float(out)

    from .job import Job
    # The first argument could be self in implementation
    idx = 0 if isinstance(calls[0].args[0], Job) else 1
    job = calls[0].kwargs.pop("job", calls[0].args[idx])
    path = calls[0].kwargs.pop("path", calls[0].args[idx + 1])
    raise NotImplementedError(
        f"[{job.proc.name}] Unsupported protocol in path to get mtime: "
        f"{path.split('://')[0]}://"
    )


@plugin.spec(result=_collect_get_mtime)
def get_mtime(job: Job, path: str | PathLike, dirsig: int) -> float:
    """Get the mtime of a path, either a file or a directory

    Args:
        job: The job
        path: The path to get mtime
        dirsig: The depth of the directory to check the last modification time

    Returns:
        The last modification time
    """


async def _collect_clear_path(calls: list[SimplugImplCall]) -> bool:
    for call in calls:
        out = await makecall(call)
        if out is not None:
            return out

    from .job import Job
    # The first argument could be self in implementation
    idx = 0 if isinstance(calls[0].args[0], Job) else 1
    job = calls[0].kwargs.pop("job", calls[0].args[idx])
    path = calls[0].kwargs.pop("path", calls[0].args[idx + 1])
    raise NotImplementedError(
        f"[{job.proc.name}] Unsupported protocol in path to clear: "
        f"{path.split('://')[0]}://"
    )


@plugin.spec(result=_collect_clear_path)
async def clear_path(job: Job, path: str | PathLike, is_dir: bool) -> bool:
    """Clear the path, either a file or a directory

    Args:
        job: The job
        path: The path to clear
        is_dir: Whether the path is a directory

    Returns:
        Whether the path is cleared successfully
    """


async def _collect_output_exists(calls: list[SimplugImplCall]) -> bool:
    for call in calls:
        out = await makecall(call)
        if out is not None:
            return out

    from .job import Job
    # The first argument could be self in implementation
    idx = 0 if isinstance(calls[0].args[0], Job) else 1
    job = calls[0].kwargs.pop("job", calls[0].args[idx])
    path = calls[0].kwargs.pop("path", calls[0].args[idx + 1])
    raise NotImplementedError(
        f"[{job.proc.name}] Unsupported protocol in path to test existence: "
        f"{path.split('://')[0]}://"
    )


@plugin.spec(result=_collect_output_exists)
async def output_exists(job: Job, path: str, is_dir: bool) -> bool:
    """Check if the output exists

    Args:
        job: The job
        path: The path to check
        is_dir: Whether the path is a directory

    Returns:
        Whether the output exists
    """


@plugin.spec(result=SimplugResult.ALL_AVAILS)
def on_jobcmd_init(job: Job) -> str:
    """When the job command wrapper script is initialized before the prescript is run

    This should return a piece of bash code to be inserted in the wrapped job
    script (template), which is a python template string, with the following
    variables available: `status` and `job`. `status` is the class `JobStatus` from
    `xqute.defaults.py` and `job` is the `Job` instance.

    For multiple plugins, the code will be inserted in the order of the plugin priority.

    The code will replace the `#![jobcmd_init]` placeholder in the wrapped job script.
    See also <https://github.com/pwwang/xqute/blob/master/xqute/defaults.py#L95>

    Args:
        job: The job object

    Returns:
        The bash code to be inserted
    """


@plugin.spec(result=SimplugResult.ALL_AVAILS)
def on_jobcmd_prep(job: Job) -> str:
    """When the job command right about to be run

    This should return a piece of bash code to be inserted in the wrapped job
    script (template), which is a python template string, with the following
    variables available: `status` and `job`. `status` is the class `JobStatus` from
    `xqute.defaults.py` and `job` is the `Job` instance.

    The bash variable `$cmd` is accessible in the context. It is also possible to
    modify the `cmd` variable. Just remember to assign the modified value to `cmd`.

    For multiple plugins, the code will be inserted in the order of the plugin priority.
    Keep in mind that the `$cmd` may be modified by other plugins.

    The code will replace the `#![jobcmd_prep]` placeholder in the wrapped job script.
    See also <https://github.com/pwwang/xqute/blob/master/xqute/defaults.py#L95>

    Args:
        job: The job object

    Returns:
        The bash code to be inserted
    """


@plugin.spec(result=SimplugResult.ALL_AVAILS)
def on_jobcmd_end(job: Job) -> str:
    """When the job command finishes and after the postscript is run

    This should return a piece of bash code to be inserted in the wrapped job
    script (template), which is a python template string, with the following
    variables available: `status` and `job`. `status` is the class `JobStatus` from
    `xqute.defaults.py` and `job` is the `Job` instance.

    The bash variable `$rc` is accessible in the context, which is the return code
    of the job command.

    For multiple plugins, the code will be inserted in the order of the plugin priority.

    The code will replace the `#![jobcmd_end]` placeholder in the wrapped job script.
    See also <https://github.com/pwwang/xqute/blob/master/xqute/defaults.py#L95>

    Args:
        job: The job object

    Returns:
        The bash code to be inserted
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
    async def on_job_submitted(self, job: Job):
        """Update the progress bar when a job is submitted"""
        job.proc.pbar.update_job_submitted()

    @plugin.impl
    async def on_job_started(self, job: Job):
        """Update the progress bar when a job starts to run"""
        job.proc.pbar.update_job_running()

    @plugin.impl
    async def on_job_cached(self, job: Job):
        """Update the progress bar when a job is cached"""
        job.proc.pbar.update_job_submitted()
        job.proc.pbar.update_job_running()
        job.proc.pbar.update_job_succeeded()
        job.status = JobStatus.FINISHED

    @plugin.impl
    async def on_job_succeeded(self, job: Job):
        """Cache the job and update the progress bar when a job is succeeded"""
        # now the returncode is 0, however, we need to check if output files
        # have been created or not, this makes sure job.cache not fail
        for outkey, outtype in job._output_types.items():
            if outtype == ProcOutputType.VAR:
                continue

            output_exists = await plugin.hooks.output_exists(
                job,
                job.output[outkey],
                outtype == ProcOutputType.DIR,
            )
            if not output_exists:
                job.status = JobStatus.FAILED
                job.proc.pbar.update_job_failed()
                stderr = await a_read_text(job.stderr_file)
                stderr = (
                    f"{stderr}\n\nOutput {outtype} {outkey!r} "
                    "is not generated."
                )
                await a_write_text(job.stderr_file, stderr)
                break
        else:
            await job.cache()
            job.proc.pbar.update_job_succeeded()

    @plugin.impl
    async def on_job_failed(self, job: Job):
        """Update the progress bar when a job is failed"""
        job.proc.pbar.update_job_failed()
        if job.status == JobStatus.RETRYING:
            job.log("debug", "Retrying #%s", job.trial_count + 1)
            job.proc.pbar.update_job_retrying()

    @plugin.impl
    async def on_job_killed(self, job: Job):
        """Update the status of a killed job"""
        # instead of FINISHED to force the whole pipeline to quit
        job.status = JobStatus.FAILED  # pragma: no cover

    @plugin.impl
    def norm_inpath(
        self,
        job: Job,
        inpath: str | PathLike,
        is_dir: bool,
    ) -> str:
        """Normalize the input path"""
        if "://" in str(inpath):
            # Let the plugins handle the protocol
            return None

        return str(Path(inpath).expanduser().resolve())

    @plugin.impl
    def norm_outpath(
        self,
        job: Job,
        outpath: str,
        is_dir: bool,
    ) -> str:
        """Normalize the output path"""
        if "://" in outpath:
            # Let the plugins handle the protocol
            return None

        if Path(outpath).is_absolute():
            raise ProcOutputValueError(
                f"[{job.proc.name}] Process output should be a relative path: {outpath}"
            )

        out = job.outdir.resolve() / outpath
        if is_dir:
            out.mkdir(parents=True, exist_ok=True)

        return str(out)

    @plugin.impl
    def get_mtime(
        self,
        job: Job,
        path: str | PathLike,
        dirsig: int,
    ):
        """Get the mtime of a path"""
        if "://" in str(path):
            # Let the plugins handle the protocol
            return None

        return _get_mtime(path, dirsig)

    @plugin.impl
    async def clear_path(self, job: Job, path: str | PathLike, is_dir: bool):
        """Clear the path"""
        if "://" in str(path):
            # Let the plugins handle the protocol
            return None

        path = Path(path)
        try:
            # dead link
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

    @plugin.impl
    async def output_exists(self, job: Job, path: str, is_dir: bool):
        """Check if the output exists"""
        if "://" in path:
            # Let the plugins handle the protocol
            return None

        path = Path(path)
        if not path.exists():
            return False
        if is_dir:
            return len(list(path.iterdir())) > 0  # pragma: no cover
        return True


plugin.register(PipenMainPlugin)

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
        await plugin.hooks.on_job_init(job)

    @xqute_plugin.impl
    async def on_job_queued(self, scheduler: Scheduler, job: Job):
        """When a job is queued"""
        await plugin.hooks.on_job_queued(job)

    @xqute_plugin.impl
    async def on_job_submitting(self, scheduler: Scheduler, job: Job):
        """When a job is being submitted"""
        return await plugin.hooks.on_job_submitting(job)

    @xqute_plugin.impl
    async def on_job_submitted(self, scheduler: Scheduler, job: Job):
        """When a job is submitted"""
        await plugin.hooks.on_job_submitted(job)

    @xqute_plugin.impl
    async def on_job_started(self, scheduler: Scheduler, job: Job):
        """When a job starts to run"""
        await plugin.hooks.on_job_started(job)

    @xqute_plugin.impl
    async def on_job_polling(self, scheduler: Scheduler, job: Job):
        """When a job starts to run"""
        await plugin.hooks.on_job_polling(job)

    @xqute_plugin.impl
    async def on_job_killing(self, scheduler: Scheduler, job: Job):
        """When a job is being killed"""
        return await plugin.hooks.on_job_killing(job)  # pragma: no cover

    @xqute_plugin.impl
    async def on_job_killed(self, scheduler: Scheduler, job: Job):
        """When a job is killed"""
        await plugin.hooks.on_job_killed(job)  # pragma: no cover

    @xqute_plugin.impl
    async def on_job_succeeded(self, scheduler: Scheduler, job: Job):
        """When a job is succeeded"""
        await plugin.hooks.on_job_succeeded(job)

    @xqute_plugin.impl
    async def on_job_failed(self, scheduler: Scheduler, job: Job):
        """When a job is failed"""
        await plugin.hooks.on_job_failed(job)

    @xqute_plugin.impl
    def on_jobcmd_init(self, scheduler: Scheduler, job: Job):
        """When the job command wrapper script is initialized"""
        codes = plugin.hooks.on_jobcmd_init(job)
        if not codes:
            return None
        return "\n\n".join(codes)

    @xqute_plugin.impl
    def on_jobcmd_prep(self, scheduler: Scheduler, job: Job):
        """When the job command is about to be run"""
        codes = plugin.hooks.on_jobcmd_prep(job)
        if not codes:
            return None
        return "\n\n".join(codes)

    @xqute_plugin.impl
    def on_jobcmd_end(self, scheduler: Scheduler, job: Job):
        """When the job command finishes"""
        codes = plugin.hooks.on_jobcmd_end(job)
        if not codes:
            return None
        return "\n\n".join(codes)


xqute_plugin.register(XqutePipenPlugin)
