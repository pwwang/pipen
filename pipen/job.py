"""Provide the Job class"""
from __future__ import annotations

import logging
import shlex
import shutil
from functools import cached_property
from os import PathLike
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Mapping

from diot import OrderedDiot
from xqute import Job as XquteJob
from xqute.utils import a_read_text

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
from .utils import logger, strsplit

if TYPE_CHECKING:  # pragma: no cover
    from .proc import Proc


class Job(XquteJob, JobCaching):
    """The job for pipen"""

    __slots__ = ("proc", "_output_types", "_outdir")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.proc: Proc = None
        self._output_types: Dict[str, str] = {}
        self._outdir = self.metadir / "output"

    @property
    def script_file(self) -> Path:
        """Get the path to script file

        Returns:
            The path to the script file
        """
        return self.metadir / "job.script"

    @cached_property
    def outdir(self) -> Path:
        """Get the path to the output directory

        Returns:
            The path to the job output directory
        """
        ret = Path(self._outdir)
        # if ret is a dead link
        # when switching a proc from end/nonend to nonend/end
        if ret.is_symlink() and not ret.exists():
            ret.unlink()  # pragma: no cover
        ret.mkdir(parents=True, exist_ok=True)
        # If it is somewhere else, make a symbolic link to the metadir
        metaout = self.metadir / "output"
        if ret != metaout:
            if metaout.is_symlink() or metaout.is_file():
                metaout.unlink()
            elif metaout.is_dir():
                shutil.rmtree(metaout)
            metaout.symlink_to(ret)
        return ret

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
                if not isinstance(ret[inkey], (str, PathLike)):
                    raise ProcInputTypeError(
                        f"Got {type(ret[inkey])} instead of PathLike object "
                        f"for input: {inkey + ':' + intype!r}"
                    )

                # we should use it as a string
                ret[inkey] = str(Path(ret[inkey]).resolve())

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
                    ret[inkey][i] = str(Path(file).resolve())
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
                metadir=str(self.metadir),
                outdir=str(self.outdir),
                stdout_file=str(self.stdout_file),
                stderr_file=str(self.stderr_file),
                jid_file=str(self.jid_file),
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
                        f"[{self.proc.name}] "
                        f"Unsupported output type: {output_type}"
                    )

            self._output_types[output_name] = output_type
            ret[output_name] = output_value

            if output_type == ProcOutputType.VAR:
                continue

            if Path(output_value).is_absolute():
                raise ProcOutputValueError(
                    f"[{self.proc.name}] Path in output should be relative."
                )

            ret[output_name] = self.outdir.resolve() / output_value

            if output_type == ProcOutputType.DIR:
                ret[output_name].mkdir(parents=True, exist_ok=True)

            ret[output_name] = str(ret[output_name])

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
                metadir=str(self.metadir),
                outdir=str(self.outdir),
                stdout_file=str(self.stdout_file),
                stderr_file=str(self.stderr_file),
                jid_file=str(self.jid_file),
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

    async def prepare(self, proc: Proc) -> None:
        """Prepare the job by given process

        Primarily prepare the script, and provide cmd to the job for xqute
        to wrap and run

        Args:
            proc: the process object
        """
        # Attach the process
        self.proc = proc

        if self.proc.export and len(self.proc.jobs) == 1:
            # Don't put index if it is a single-job process
            self._outdir = Path(self.proc.pipeline.outdir) / self.proc.name

        elif self.proc.export:
            self._outdir = (
                Path(self.proc.pipeline.outdir)
                / self.proc.name
                / str(self.index)
            )

        if not proc.script:
            self.cmd = []
            return

        template_data = self.template_data
        try:
            script = proc.script.render(template_data)
        except Exception as exc:
            raise TemplateRenderingError(
                f"[{self.proc.name}] Failed to render script."
            ) from exc
        if (
            self.script_file.is_file()
            and await a_read_text(self.script_file) != script
        ):
            self.log("debug", "Job script updated.")
            self.script_file.write_text(script)
        elif not self.script_file.is_file():
            self.script_file.write_text(script)

        lang = proc.lang or proc.pipeline.config.lang
        self.cmd = shlex.split(lang) + [self.script_file]  # type: ignore
