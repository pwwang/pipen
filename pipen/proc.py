"""Provide the Proc class"""

import asyncio
import logging
from pathlib import Path
from typing import Any, ClassVar, Dict, Iterable, List, Optional, Type, Union
from io import StringIO

from varname import varname
from simpleconf import Config
from rich.panel import Panel
from rich.console import Console
from xqute import Xqute, JobStatus
from xqute import Scheduler
from pandas import DataFrame

from .utils import brief_list, logger, get_console_width, DEFAULT_CONSOLE_WIDTH
from .template import Template
from .plugin import plugin
from ._proc_properties import ProcProperties, ProcMeta, ProcType

class Proc(ProcProperties, metaclass=ProcMeta):
    """The Proc class provides process assembly functionality"""

    name: ClassVar[str] = None
    desc: ClassVar[str] = None

    SELF: ClassVar["Proc"] = None

    def __new__(cls, *args, **kwargs):
        """Make sure cls() always get to the same instance"""
        if not args and not kwargs:
            if not cls.SELF:
                cls.SELF = super().__new__(cls)
            return cls.SELF
        return super().__new__(cls)

    # pylint: disable=redefined-builtin,redefined-outer-name
    def __init__(self,
                 name: Optional[str] = None,
                 desc: Optional[str] = None,
                 *,
                 input_keys: Union[List[str], str] = None,
                 input: Optional[Union[str, Iterable[str]]] = None,
                 output: Optional[Union[str, Iterable[str]]] = None,
                 lang: Optional[str] = None,
                 script: Optional[str] = None,
                 forks: Optional[int] = None,
                 requires: Optional[Union[ProcType, Iterable[ProcType]]] = None,
                 args: Optional[Dict[str, Any]] = None,
                 envs: Optional[Dict[str, Any]] = None,
                 cache: Optional[bool] = None,
                 dirsig: Optional[bool] = None,
                 profile: Optional[str] = None,
                 template: Optional[Union[str, Type[Template]]] = None,
                 scheduler: Optional[Union[str, Scheduler]] = None,
                 scheduler_opts: Optional[Dict[str, Any]] = None) -> None:
        if getattr(self, '_inited', False):
            return

        super().__init__(
            input_keys,
            input,
            output,
            lang,
            script,
            forks,
            requires,
            args,
            envs,
            cache,
            dirsig,
            profile,
            template,
            scheduler,
            scheduler_opts
        )

        self.nexts = []
        self.name = (
            name if name is not None
            else self.__class__.name if self.__class__.name is not None
            else self.__class__.__name__ if self is self.__class__.SELF
            else varname()
        )
        self.desc = (
            desc if desc is not None
            else self.__class__.desc
            if self.__class__.desc is not None
            else self.__doc__.lstrip().splitlines()[0]
            if self.__doc__
            else 'Undescribed.'
        )

        self.pipeline = None
        self.pbar = None
        self.jobs = []
        self.xqute = None
        self.workdir = None
        self.out_channel = None

        self._inited = True

    def log(self,
            level: Union[int, str],
            msg: str,
            *args,
            logger: logging.Logger = logger) -> None:
        """Log message for the process

        Args:
            level: The log level of the record
            msg: The message to log
            *args: The arguments to format the message
            logger: The logging logger
        """
        msg = msg % args
        if not isinstance(level, int):
            level = logging.getLevelName(level.upper())
        logger.log(level, '[cyan]%s:[/cyan] %s', self.name, msg)

    def gc(self):
        """GC process for the process to save memory after it's done"""
        del self.xqute
        self.xqute = None

        del self.jobs[:]
        self.jobs = []

        del self.pbar
        self.pbar = None

    async def prepare(self, pipeline: "Pipen", profile: str) -> None:
        """Prepare the process

        Args:
            pipeline: The Pipen object
            profile: The profile of the configuration
        """
        self._print_banner()
        self._print_dependencies()
        self.pipeline = pipeline
        profile = self.profile or profile

        if profile == 'default':
            config = pipeline.config._use('__init__', 'default', copy=True)
        else:
            config = pipeline.config._use('__init__', 'default', profile,
                                          copy=True)

        self.properties_from_config(config)
        self.compute_properties()

        self.workdir = Path(config.workdir) / self.name
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.log('info', 'Workdir: %r', str(self.workdir))

        self.xqute = Xqute(
            self.scheduler,
            job_metadir=self.workdir,
            job_submission_batch=config.submission_batch,
            job_error_strategy=config.error_strategy,
            job_num_retries=config.num_retries,
            scheduler_forks=self.forks,
            **self.scheduler_opts)

        # init all other properties and jobs
        await self._init_jobs(config)

        await plugin.hooks.on_proc_init(self)

        # init pbar
        self.pbar = pipeline.pbar.proc_bar(self.size, self.name)

    @property
    def size(self) -> int:
        """The size of the process (# of jobs)"""
        return len(self.jobs)

    @property
    def succeeded(self) -> bool:
        """Check if the process is succeeded (all jobs succeeded)"""
        return all(job.status == JobStatus.FINISHED for job in self.jobs)

    async def run(self) -> None:
        """Run the process"""
        cached_jobs = []
        for job in self.jobs:
            if await job.cached:
                cached_jobs.append(job.index)
                self.pbar.update_job_submitted()
                self.pbar.update_job_running()
                self.pbar.update_job_succeeded()
                job.status = JobStatus.FINISHED
            await self.xqute.put(job)
        if cached_jobs:
            self.log('info', 'Cached jobs: %s', brief_list(cached_jobs))
        await self.xqute.run_until_complete()
        self.out_channel = DataFrame((job.output for job in self.jobs))
        self.pbar.done()
        await plugin.hooks.on_proc_done(self)

    async def _init_job(self, worker_id: int, config: Config) -> None:
        """A worker to initialize jobs

        Args:
            worker_id: The worker id
            config: The pipeline configuration
        """
        for job in self.jobs:
            if job.index % config.submission_batch != worker_id:
                continue
            await job.prepare(self)

    async def _init_jobs(self, config: Config) -> None:
        """Initialize all jobs

        Args:
            config: The pipeline configuration
        """
        for i in range(self.input.data.shape[0]):
            job = self.scheduler.job_class(i, '', self.workdir)
            self.jobs.append(job)

        await asyncio.gather(
            *(self._init_job(i, config)
              for i in range(config.submission_batch))
        )


    def _print_banner(self) -> None:
        """Print the banner of the process"""
        console_width = get_console_width()
        stream = StringIO()
        console = Console(file=stream)
        panel = Panel(self.desc,
                      title=self.name,
                      width=min(DEFAULT_CONSOLE_WIDTH, console_width))
        console.print(panel)
        logger.info('')
        for line in console.file.getvalue().splitlines():
            logger.info(f'[cyan]{line}[/cyan]')

    def _print_dependencies(self):
        """Print the dependencies"""
        if self.requires:
            self.log('info',
                     '[yellow]<<<[/yellow] %s',
                     [proc.name for proc in self.requires])
        if self.nexts:
            self.log('info',
                     '[yellow]>>>[/yellow] %s',
                     [proc.name for proc in self.nexts])
