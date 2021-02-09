"""Provide the Job class"""
import logging
import shlex
from os import PathLike
from pathlib import Path
from typing import Any, Dict, Union

import pandas
from diot import OrderedDiot
from xqute import Job as XquteJob
from xqute.utils import a_read_text

from .defaults import ProcInputType, ProcOutputType
from .utils import logger, cached_property # pylint: disable=unused-import
from .exceptions import (ProcInputTypeError,
                         ProcOutputNameError,
                         ProcOutputTypeError,
                         ProcOutputValueError,
                         TemplateRenderingError)
from .template import Template
from ._job_caching import JobCaching

class Job(XquteJob, JobCaching):
    """The job for pipen"""

    # pylint: disable=redefined-outer-name
    __slots__ = ('proc', '_output_types', '_outdir')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.proc = None
        self._output_types = {}
        self._outdir = self.metadir / 'output'

    @property
    def script_file(self) -> Path:
        """Get the path to script file"""
        return self.metadir / 'job.script'

    @cached_property
    def outdir(self) -> Path:
        """Get the path to the output directory"""
        ret = Path(self._outdir)
        ret.mkdir(parents=True, exist_ok=True)
        return ret

    @cached_property
    def input(self) -> Dict[str, Any]:
        """Get the input data"""
        ret = self.proc.input.data.iloc[[self.index], :].to_dict('records')[0]
        # check types
        for inkey, intype in self.proc.input.type.items():
            if intype == ProcInputType.VAR or ret[inkey] is None:
                continue
            if intype == ProcInputType.FILE:
                if not isinstance(ret[inkey], (str, PathLike)):
                    raise ProcInputTypeError(
                        f"Got {type(ret[inkey])} instead of PathLike object "
                        f"for input: {inkey + ':' + intype!r}"
                    )
                # if not Path(ret[inkey]).exists():
                #     raise FileNotFoundError(
                #         f"[{self.proc.name}] Input file not found: "
                #         f"{ret[inkey]}"
                #     )
                # we should use it as a string
                ret[inkey] = str(Path(ret[inkey]).resolve())
            if intype == ProcInputType.FILES:
                if isinstance(ret[inkey], pandas.DataFrame):
                    ret[inkey] = ret[inkey].iloc[0, 0]

                if not isinstance(ret[inkey], (list, tuple)):
                    raise ProcInputTypeError(
                        f"[{self.proc.name}] Expected a list/tuple for input: "
                        f"{inkey + ':' + intype!r}, got {type(ret[inkey])}"
                    )

                for i, file in enumerate(ret[inkey]):
                    # if not Path(file).exists():
                    #     raise FileNotFoundError(
                    #         f"[{self.proc.name}] Input file not found: {file}"
                    #     )
                    ret[inkey][i] = str(Path(file).resolve())
        return ret

    @cached_property
    def output(self) -> Dict[str, Any]:
        """Get the output data"""
        output_template = self.proc.output
        if not output_template:
            return {}

        data = {
            'job': dict(
                index=self.index,
                metadir=str(self.metadir),
                outdir=str(self.outdir),
                stdout_file=str(self.stdout_file),
                stderr_file=str(self.stderr_file),
                lock_file=str(self.lock_file),
            ),
            'in': self.input,
            'proc': self.proc,
            'args': self.proc.args
        }

        try:
            if isinstance(output_template, Template):
                # // TODO: check ',' in output value?
                outputs = [
                    oput.strip()
                    for oput in output_template.render(data).split(',')
                ]
            else:
                outputs = [oput.render(data) for oput in output_template]
        except Exception as exc:
            raise TemplateRenderingError(
                f'[{self.proc.name}] Failed to render output.'
            ) from exc

        ret = OrderedDiot()
        for oput in outputs:
            if ':' not in oput:
                raise ProcOutputNameError('No name given in output.')

            if oput.count(':') == 1:
                output_name, output_value = oput.split(':')
                output_type = ProcOutputType.VAR
            else:
                output_name, output_type, output_value = oput.split(':', 2)
                if output_type not in ProcOutputType.__dict__.values():
                    raise ProcOutputTypeError(
                        f'Unsupported output type: {output_type}'
                    )

            self._output_types[output_name] = output_type
            ret[output_name] = output_value

            if output_type == ProcOutputType.VAR:
                continue

            if Path(output_value).is_absolute() and self.proc.end:
                raise ProcOutputValueError(
                    'Only relative path allowed as output for ending process. '
                    'If you want to redirect the output path, set `end` to '
                    'False for the process.'
                )
            if Path(output_value).is_absolute():
                ret[output_name] = output_value
            else:
                ret[output_name] = str(self.outdir.resolve() / output_value)

        return ret


    @cached_property
    def rendering_data(self) -> Dict[str, Any]:
        """Get the data for template rendering"""
        return {
            'job': dict(
                index=self.index,
                metadir=str(self.metadir),
                outdir=str(self.outdir),
                stdout_file=str(self.stdout_file),
                stderr_file=str(self.stderr_file),
                lock_file=str(self.lock_file),
            ),
            'in': self.input,
            'out': self.output,
            'proc': self.proc,
            'args': self.proc.args
        }

    def log(self,
            level: Union[int, str],
            msg: str,
            *args,
            limit: int = 3,
            limit_indicator: bool = True,
            logger: logging.Logger = logger) -> None:
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
                self.proc.log('debug',
                              'Not showing similar logs for further jobs.')
            return

        job_index_indicator = '[%s/%s] ' % (
            str(self.index).zfill(len(str(self.proc.size-1))),
            self.proc.size - 1
        )

        self.proc.log(level, job_index_indicator + msg, *args, logger=logger)

    async def prepare(self, proc: "Proc") -> None:
        """Prepare the job by given process

        Primarily prepare the script, and provide cmd to the job for xqute
        to wrap and run

        Args:
            proc: the process object
        """
        self.proc = proc
        if self.proc.end and len(self.proc.jobs) == 1:
            self._outdir = Path(self.proc.pipeline.outdir) / self.proc.name
        elif self.proc.end:
            self._outdir = (Path(self.proc.pipeline.outdir) /
                            self.proc.name /
                            str(self.index))

        if not proc.script:
            self.cmd = [] # pylint: disable=attribute-defined-outside-init
            return

        rendering_data = self.rendering_data
        try:
            script = proc.script.render(rendering_data)
        except Exception as exc:
            raise TemplateRenderingError(
                f'[{self.proc.name}] Failed to render script.'
            ) from exc
        if self.script_file.is_file() and await a_read_text(
                self.script_file
        ) != script:
            self.log('debug', 'Job script updated.')
            self.script_file.write_text(script)
        elif not self.script_file.is_file():
            self.script_file.write_text(script)
        # pylint: disable=attribute-defined-outside-init
        self.cmd = shlex.split(proc.lang) + [self.script_file]
