"""Provide the Job class"""

from __future__ import annotations

import logging
import shlex
from functools import cached_property
from os import PathLike
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Mapping

from yunpath import AnyPath, CloudPath
from diot import OrderedDiot
from xqute import Job as XquteJob
from xqute.path import DualPath, MountedPath

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

if TYPE_CHECKING:  # pragma: no cover
    from .proc import Proc


class Job(XquteJob, JobCaching):
    """The job for pipen"""

    __slots__ = XquteJob.__slots__ + ("proc", "_output_types", "_outdir")

    def __init__(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.proc: Proc = None
        self._output_types: Dict[str, str] = {}
        # Where the real output directory is
        self._outdir: DualPath = None

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
        mounted_outdir = getattr(proc.xqute.scheduler, "MOUNTED_OUTDIR", None)
        if mounted_outdir is not None:  # pragma: no cover
            mounted_outdir = Path(mounted_outdir) / proc.name

        if self.proc.export:
            # Don't put index if it is a single-job process
            self._outdir = DualPath(export_outdir, mounted=mounted_outdir)

            # Put job output in a subdirectory with index
            # if it is a multi-job process
            if len(self.proc.jobs) > 1:
                self._outdir = self._outdir / str(self.index)

        else:
            # For non-export process, the output directory is the metadir
            self._outdir = self.metadir / "output"

        if not proc.script:
            self.cmd = []
            return

        try:
            script = proc.script.render(self.template_data)
        except Exception as exc:
            raise TemplateRenderingError(
                f"[{self.proc.name}] Failed to render script."
            ) from exc

        if self.script_file.is_file() and self.script_file.read_text() != script:
            self.log("debug", "Job script updated.")
            self.script_file.write_text(script)
        elif not self.script_file.is_file():
            self.script_file.write_text(script)

        lang = proc.lang or proc.pipeline.config.lang
        self.cmd = shlex.split(lang) + [self.script_file.mounted.fspath]

    @property
    def script_file(self) -> DualPath:
        """Get the path to script file

        Returns:
            The path to the script file
        """
        return self.metadir / "job.script"

    @cached_property
    def outdir(self) -> DualPath:
        """Get the path to the output directory.

        When proc.export is True, the output directory is based on the
        pipeline.outdir and the process name. Otherwise, it is based on
        the metadir.

        When the job is running in a detached system (a VM, typically),
        this will return the mounted path to the output directory.

        To access the real path, use self._outdir

        Returns:
            The path to the job output directory
        """
        # if ret is a dead link
        # when switching a proc from end/nonend to nonend/end
        # if path_is_symlink(self._outdir) and not self._outdir.exists():
        if path_is_symlink(self._outdir) and (
            # A local deak link
            not self._outdir.exists()
            # A cloud fake link
            or isinstance(getattr(self._outdir, "path", self._outdir), CloudPath)
        ):
            self._outdir.unlink()  # pragma: no cover

        self._outdir.mkdir(parents=True, exist_ok=True)
        # If it is somewhere else, make a symbolic link to the metadir
        metaout = self.metadir / "output"
        if self._outdir != metaout:
            if path_is_symlink(metaout) or metaout.is_file():
                metaout.unlink()
            elif metaout.is_dir():
                metaout.rmtree()

            path_symlink_to(metaout, self._outdir)

        return self._outdir

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
                if not isinstance(ret[inkey], (str, PathLike, CloudPath, DualPath)):
                    raise ProcInputTypeError(
                        f"[{self.proc.name}] Got {type(ret[inkey])} instead of "
                        f"PathLike object for input: {inkey + ':' + intype!r}"
                    )

                if isinstance(ret[inkey], DualPath):
                    # if it is a dualpath, it means it is a mounted path
                    # we should use the mounted path to access the file
                    ret[inkey] = ret[inkey].mounted

                elif not isinstance(ret[inkey], MountedPath):
                    # str, Path, CloudPath
                    path = AnyPath(ret[inkey])
                    if isinstance(path, Path):
                        # Same as:
                        # p = MountedPath(path.expanduser().absolute())
                        # p.spec = path.expanduser().absolute()
                        ret[inkey] = DualPath(path.expanduser().absolute()).mounted
                    else:
                        ret[inkey] = DualPath(path).mounted

                # already a MountedPath

            if intype in (ProcInputType.FILES, ProcInputType.DIRS):
                if isinstance(ret[inkey], pandas.DataFrame):
                    # // todo: nested dataframe
                    ret[inkey] = ret[inkey].iloc[0, 0]  # pragma: no cover

                if not isinstance(ret[inkey], (list, tuple)):
                    raise ProcInputTypeError(
                        f"[{self.proc.name}] Expected a sequence for input: "
                        f"{inkey + ':' + intype!r}, got {type(ret[inkey])}"
                    )

                for i, file in enumerate(ret[inkey]):
                    if not isinstance(file, (str, PathLike, CloudPath, DualPath)):
                        raise ProcInputTypeError(
                            f"[{self.proc.name}] Got {type(file)} instead of "
                            f"PathLike object for input: {inkey + ':' + intype!r} "
                            f"at index {i}"
                        )

                    if isinstance(file, DualPath):
                        # if it is a dualpath, it means it is a mounted path
                        # we should use the mounted path to access the file
                        ret[inkey][i] = file.mounted

                    elif not isinstance(file, MountedPath):
                        # str, Path, CloudPath
                        path = AnyPath(file)
                        if isinstance(path, Path):
                            ret[inkey][i] = DualPath(
                                path.expanduser().absolute()
                            ).mounted
                        else:
                            ret[inkey][i] = DualPath(path).mounted

        return ret

    @cached_property
    def output(self) -> Mapping[str, Any]:
        """Get the output data of the job

        Returns:
            The key-value map where the keys are the output keys
        """
        output_template = self.proc.output
        if not output_template:
            return {}

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

        ret = OrderedDiot()
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
                ov = AnyPath(output_value)
                if isinstance(ov, CloudPath) or (
                    isinstance(ov, Path) and ov.is_absolute()
                ):
                    raise ProcOutputValueError(
                        f"[{self.proc.name}] "
                        f"output path must be a segment: {output_value}"
                    )

                out = self.outdir / output_value
                if output_type == ProcOutputType.DIR:
                    out.mkdir(parents=True, exist_ok=True)

                ret[output_name] = out.mounted

        return ret

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

        job_index_indicator = "[%s/%s] " % (
            str(self.index).zfill(len(str(self.proc.size - 1))),
            self.proc.size - 1,
        )

        self.proc.log(level, job_index_indicator + msg, *args, logger=logger)
