"""Provide the Job class"""

from __future__ import annotations

import logging
import shlex
from contextlib import suppress
from collections.abc import Iterable
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Mapping

from panpath import PanPath, CloudPath, LocalPath
from diot import OrderedDiot
from xqute import Job as XquteJob
from xqute.path import SpecPath, MountedPath

from ._job_caching import JobCaching
from .defaults import ProcInputType, ProcOutputType
from .exceptions import (
    ProcInputTypeError,
    ProcOutputNameError,
    ProcOutputTypeError,
    ProcOutputValueError,
    TemplateRenderingError,
)
from .template import Template
from .utils import logger, strsplit, path_is_symlink, path_symlink_to
from .pluginmgr import plugin

if TYPE_CHECKING:  # pragma: no cover
    from .proc import Proc


def _process_input_file_or_dir(
    inkey: str,
    intype: str,
    inval: Any,
    index: int | None = None,
    proc_name: str | None = None,
) -> CloudPath | MountedPath:
    """Process the input value for file or dir"""
    if inval is None or not isinstance(inval, (str, Path)):
        msg = (
            f"[{proc_name}] Got <{type(inval).__name__}> instead of "
            f"path-like object for input: {inkey + ':' + intype!r}"
        )
        if index is not None:
            msg = f"{msg} at index {index}"

        raise ProcInputTypeError(msg)

    if isinstance(inval, MountedPath):
        return inval

    if isinstance(inval, SpecPath):
        return inval.mounted

    if isinstance(inval, CloudPath):  # pragma: no cover
        return MountedPath(inval)

    if not isinstance(inval, str):  # other path-like types, should be all local
        return MountedPath(PanPath(inval).expanduser().absolute())

    # str
    # Let's see if it a path in str format, which is path1:path2
    # However, there is also a colon in cloud paths
    colon_count = inval.count(":")
    if colon_count == 0:  # a/b
        return MountedPath(PanPath(inval).expanduser().absolute())

    if colon_count > 3:  # a:b:c:d
        msg = (
            f"[{proc_name}] Invalid input value: {inkey + ':' + intype!r} "
            "(too many ':')"
        )
        if index is not None:
            msg = f"{msg} at index {index}"

        raise ProcInputTypeError(msg)

    if colon_count == 1:  # gs://a/b or a/b:c/d
        if isinstance(PanPath(inval), CloudPath):  # gs://a/b
            return MountedPath(inval)

        path1, path2 = inval.split(":")

    elif inval.count(":") == 3:  # gs://a/b:gs://c/d
        p1, p2, path2 = inval.split(":", 2)
        path1 = p1 + ":" + p2

    else:  # gs://a/b:c/d or a/b:gs://c/d
        p1, p2, p3 = inval.split(":", 2)
        path1, path2 = p1 + ":" + p2, p3
        if not isinstance(PanPath(path1), CloudPath):
            path1, path2 = p1, p2 + ":" + p3

    path1 = PanPath(path1)  # type: ignore
    path2 = PanPath(path2)  # type: ignore
    if isinstance(path1, LocalPath):
        path1 = path1.expanduser().absolute()
    if isinstance(path2, LocalPath):
        path2 = path2.expanduser().absolute()

    return MountedPath(path2, spec=path1)


class Job(XquteJob, JobCaching):
    """The job for pipen"""

    __slots__ = XquteJob.__slots__ + ("proc", "_output_types", "outdir", "output")

    def __init__(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.proc: Proc = None
        self._output_types: Dict[str, str] = {}
        # Where the real output directory is
        self.outdir: SpecPath = None
        self.output: Mapping[str, Any] = None

    async def prepare(self, proc: Proc) -> None:
        """Prepare the job by given process

        Primarily prepare the script, and provide cmd to the job for xqute
        to wrap and run

        Args:
            proc: the process object
        """
        # Attach the process
        self.proc = proc

        # Where the jobs of "export" process should put their outputs
        export_outdir = proc.pipeline.outdir / proc.name  # type: ignore
        # Where the jobs of "export" process should put their outputs
        # (in the mounted filesystem)
        sched_mounted_outdir = getattr(proc.xqute.scheduler, "MOUNTED_OUTDIR", None)
        if sched_mounted_outdir is not None:  # pragma: no cover
            if (
                isinstance(proc.pipeline.outdir, SpecPath)
                and proc.pipeline.outdir.mounted.is_mounted()
            ):
                raise ValueError(
                    "The pipeline outdir is a SpecPath, "
                    "but the MOUNTED_OUTDIR is provided by the scheduler "
                    f"<{proc.xqute.scheduler.__class__.__name__}>. "
                )

            mounted_outdir = PanPath(sched_mounted_outdir) / proc.name

        elif isinstance(proc.pipeline.outdir, SpecPath):  # pragma: no cover
            # In the case it is modified by a plugin
            # A dual path can not be specified as outdir of a pipeline
            mounted_outdir = proc.pipeline.outdir.mounted / proc.name  # type: ignore

        else:
            mounted_outdir = None

        if self.proc.export:
            # Don't put index if it is a single-job process
            self.outdir = SpecPath(
                export_outdir,
                mounted=mounted_outdir,
            )

            # Put job output in a subdirectory with index
            # if it is a multi-job process
            if self.proc.size > 1:
                self.outdir = self.outdir / str(self.index)  # type: ignore

            if sched_mounted_outdir is None:
                # Create the output directory if it is not mounted by the scheduler
                await self.outdir.mounted.a_mkdir(parents=True, exist_ok=True)

        else:
            # For non-export process, the output directory is the metadir
            self.outdir = self.metadir / "output"

        # compute the output
        await self.prepare_output()
        await self.prepare_outdir()

        if not proc.script:
            self.cmd = ("true",)
        else:
            try:
                script = proc.script.render(self.template_data)
            except Exception as exc:
                raise TemplateRenderingError(
                    f"[{self.proc.name}] Failed to render script."
                ) from exc

            if (
                await self.script_file.a_is_file()
                and await self.script_file.a_read_text() != script
            ):
                self.log("debug", "Job script updated.")
                await self.script_file.a_write_text(script)
            elif not await self.script_file.a_is_file():
                await self.script_file.a_write_text(script)

            lang = proc.lang or proc.pipeline.config.lang
            script_file = self.script_file.mounted
            script_file = await script_file.get_fspath()
            self.cmd = tuple((*shlex.split(lang), script_file))
            # self.cmd = tuple(shlex.split(lang) + [self.script_file.mounted.fspath])

        await plugin.hooks.on_job_init(self)

    @property
    def script_file(self) -> SpecPath:
        """Get the path to script file

        Returns:
            The path to the script file
        """
        return self.metadir / "job.script"

    async def prepare_outdir(self) -> SpecPath:
        """Get the path to the output directory.

        When proc.export is True, the output directory is based on the
        pipeline.outdir and the process name. Otherwise, it is based on
        the metadir.

        When the job is running in a detached system (a VM, typically),
        this will return the mounted path to the output directory.

        To access the real path, use self.outdir

        Returns:
            The path to the job output directory
        """
        # if ret is a dead link
        # when switching a proc from end/nonend to nonend/end
        # if path_is_symlink(self.outdir) and not self.outdir.exists():
        if await path_is_symlink(self.outdir) and (  # type: ignore
            # A local deak link
            not await self.outdir.a_exists()
            # A cloud fake link
            or isinstance(getattr(self.outdir, "path", self.outdir), CloudPath)
        ):
            await self.outdir.a_unlink()  # pragma: no cover

        await self.outdir.a_mkdir(parents=True, exist_ok=True)
        # If it is somewhere else, make a symbolic link to the metadir
        metaout = self.metadir / "output"
        if self.outdir != metaout:
            if await path_is_symlink(metaout) or await metaout.a_is_file():
                await metaout.a_unlink()
            elif await metaout.a_is_dir():
                # Remove the directory, it is inconsistent with current setting
                await metaout.a_rmtree()

            await path_symlink_to(metaout, self.outdir)  # type: ignore

        return self.outdir

    @cached_property
    def input(self) -> Mapping[str, Any]:
        """Get the input data for this job

        Returns:
            A key-value map, where keys are the input keys
        """
        import pandas

        ret = self.proc.input.data.iloc[self.index, :].to_dict()
        # check types
        for inkey, intype in self.proc.input.type.items():

            if intype == ProcInputType.VAR or ret[inkey] is None:
                continue  # pragma: no cover, covered actually

            if intype in (ProcInputType.FILE, ProcInputType.DIR):
                ret[inkey] = _process_input_file_or_dir(
                    inkey, intype, ret[inkey], None, self.proc.name
                )

            if intype in (ProcInputType.FILES, ProcInputType.DIRS):
                if isinstance(ret[inkey], pandas.DataFrame):  # pragma: no cover
                    # // todo: nested dataframe
                    ret[inkey] = ret[inkey].iloc[0, 0]

                if isinstance(ret[inkey], (str, Path)):
                    # if a single file, convert to list
                    ret[inkey] = [ret[inkey]]

                if not isinstance(ret[inkey], Iterable):
                    raise ProcInputTypeError(
                        f"[{self.proc.name}] Expected an iterable for input: "
                        f"{inkey + ':' + intype!r}, got {type(ret[inkey])}"
                    )

                for i, file in enumerate(ret[inkey]):
                    ret[inkey][i] = _process_input_file_or_dir(
                        inkey, intype, file, i, self.proc.name
                    )

        return ret

    async def prepare_output(self) -> None:
        """Get the output data of the job

        Returns:
            The key-value map where the keys are the output keys
        """
        output_template = self.proc.output
        if not output_template:
            self.output = {}
            return

        data = {
            "job": dict(
                index=self.index,
                metadir=self.metadir.mounted,
                outdir=self.outdir.mounted,
                stdout_file=self.stdout_file.mounted,
                stderr_file=self.stderr_file.mounted,
                jid_file=self.jid_file.mounted,
            ),
            "in": self.input,
            "in_": self.input,
            "proc": self.proc,
            "envs": self.proc.envs,
        }
        try:
            if isinstance(output_template, Template):
                # // TODO: check ',' in output value?
                outputs = strsplit(output_template.render(data), ",")
            else:
                outputs = [oput.render(data) for oput in output_template]
        except Exception as exc:
            raise TemplateRenderingError(
                f"[{self.proc.name}] Failed to render output."
            ) from exc

        self.output = ret = OrderedDiot()
        for oput in outputs:
            if ":" not in oput:
                raise ProcOutputNameError(
                    f"[{self.proc.name}] No name given in output."
                )

            if oput.count(":") == 1:
                output_name, output_value = oput.split(":")
                output_type = ProcOutputType.VAR
            else:
                output_name, output_type, output_value = oput.split(":", 2)
                if output_type not in ProcOutputType.__dict__.values():
                    raise ProcOutputTypeError(
                        f"[{self.proc.name}] " f"Unsupported output type: {output_type}"
                    )

            self._output_types[output_name] = output_type

            if output_type == ProcOutputType.VAR:
                ret[output_name] = output_value
            else:
                ov = PanPath(output_value)
                if isinstance(ov, CloudPath) or (
                    isinstance(ov, LocalPath) and ov.is_absolute()
                ):
                    raise ProcOutputValueError(
                        f"[{self.proc.name}] "
                        f"output path must be a segment: {output_value}"
                    )

                # self.outdir is already awaited
                out = self.outdir / output_value  # type: ignore
                if output_type == ProcOutputType.DIR:
                    with suppress(Exception):  # pragma: no cover
                        # Likely aiohttp.ClientResponseError
                        # In case we have many jobs and this is running in parallel
                        # Parallelly creating the same directory may cause
                        # a rate limit error in cloud storages
                        await out.a_mkdir(parents=True, exist_ok=True)

                ret[output_name] = out.mounted

    @cached_property
    def template_data(self) -> Mapping[str, Any]:
        """Get the data for template rendering

        Returns:
            The data for template rendering
        """
        return {
            "job": dict(
                index=self.index,
                metadir=self.metadir.mounted,
                outdir=self.outdir.mounted,
                script_file=self.script_file.mounted,
                stdout_file=self.stdout_file.mounted,
                stderr_file=self.stderr_file.mounted,
                jid_file=self.jid_file.mounted,
            ),
            "in": self.input,
            "in_": self.input,
            "out": self.output,
            "proc": self.proc,
            "envs": self.proc.envs,
        }

    def log(
        self,
        level: int | str,
        msg: str,
        *args,
        limit: int = 3,
        limit_indicator: bool = True,
        logger: logging.LoggerAdapter = logger,
    ) -> None:
        """Log message for the jobs

        Args:
            level: The log level of the record
            msg: The message to log
            *args: The arguments to format the message
            limit: limitation of the log (don't log for all jobs)
            limit_indicator: Whether to show an indicator saying the log
                has been limited (the level of the indicator will be DEBUG)
            logger: The logger used to log
        """
        if self.index > limit:
            return

        if self.index == limit:
            if limit_indicator:
                msg = f"{msg} (not showing similar logs)"

        if self.proc.size == 1:
            job_index_indicator = ""
        else:
            job_index_indicator = "[%s/%s] " % (
                str(self.index).zfill(len(str(self.proc.size - 1))),
                self.proc.size - 1,
            )

        self.proc.log(level, job_index_indicator + msg, *args, logger=logger)
