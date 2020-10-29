"""Provide the Job class"""
import logging
from pathlib import Path
from typing import Any, Dict, Union

from diot import OrderedDiot
from xqute import Job as XquteJob
from xqute.utils import a_read_text

from .defaults import ProcOutputType
from .utils import logger
from .exceptions import ProcOutputNameError, ProcOutputTypeError
from .template import Template
from ._job_caching import JobCaching

class Job(XquteJob, JobCaching):
    """The job for pipen"""

    # pylint: disable=redefined-outer-name

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.proc = None
        self._output_types = {}

    @property
    def script_file(self) -> Path:
        """Get the path to script file"""
        return self.metadir / 'job.script'

    @property
    def outdir(self) -> Path:
        """Get the path to the output directory"""
        return self.metadir / 'output'

    @property
    def input(self) -> Dict[str, Any]:
        """Get the input data"""
        return (self.proc.input.data.
                iloc[[self.index], :].
                to_dict('records')[0])

    @property
    def output(self) -> Dict[str, Any]:
        """Get the output data"""
        output_template = self.proc.output
        if not output_template:
            return {}

        data = {
            'job': dict(
                index=self.index,
                metadir=self.metadir,
                outdir=self.outdir,
                stdout_file=self.stdout_file,
                stderr_file=self.stderr_file,
                lock_file=self.lock_file,
            ),
            'in': self.input,
            'proc': self.proc,
            'args': self.proc.args
        }

        if isinstance(output_template, Template):
            # // TODO: check ',' in output value?
            outputs = [oput.strip()
                       for oput in output_template.render(data).split(',')]
        else:
            outputs = [oput.render(data) for oput in output_template]

        ret = OrderedDiot()
        for oput in outputs:
            if ':' not in oput:
                raise ProcOutputNameError('No name given in output.')
            if oput.count(':') == 1:
                output_name, output_value = oput.split(':')
                output_type = ProcOutputType.VAR
            else:
                output_name, output_type, output_value = oput.split(':', 2)
                if output_type in ProcOutputType.__dict__.values():
                    raise ProcOutputTypeError('Unsupported output type.')
            self._output_types[output_name] = output_type
            ret[output_name] = output_value
        return ret


    @property
    def rendering_data(self) -> Dict[str, Any]:
        """Get the data for template rendering"""
        return {
            'job': dict(
                index=self.index,
                metadir=self.metadir,
                outdir=self.outdir,
                stdout_file=self.stdout_file,
                stderr_file=self.stderr_file,
                lock_file=self.lock_file,
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
            limit_indicator: bool = False,
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

        prefix = '[cyan]%s[/cyan]: [%s/%s]' % (
            self.proc.name,
            str(self.index).zfill(len(str(self.proc.size-1))),
            self.proc.size
        )
        if self.index == limit:
            if limit_indicator:
                logger.debug('%s Not showing similar logs for further jobs.',
                             prefix)
            return

        if not isinstance(level, int):
            level = logging.getLevelName(level.upper())

        msg = msg % args
        logger.log(level, '%s %s', prefix, msg)

    async def prepare(self, proc: "Proc") -> None:
        """Prepare the job by given process

        Primarily prepare the script, and provide cmd to the job for xqute
        to wrap and run

        Args:
            proc: the process object
        """
        self.proc = proc

        if not proc.script:
            self.cmd = []
            return

        script = proc.script.render(self.rendering_data)
        if self.script_file.is_file() and await a_read_text(
                self.script_file
        ) != script:
            self.log('debug', 'Job script updated.')
            self.script_file.write_text(script)
        elif not self.script_file.is_file():
            self.script_file.write_text(script)
        self.cmd = [proc.lang, self.script_file]


