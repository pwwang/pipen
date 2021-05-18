"""Provide the Proc class"""

import asyncio
import logging
from pathlib import Path
from typing import Any, ClassVar, Dict, Iterable, List, Optional, Type, Union

from rich import box
from rich.panel import Panel

from slugify import slugify

from pandas import DataFrame
from simpleconf import Config
from xqute import Xqute, JobStatus
from xqute import Scheduler
from varname import varname

from .utils import (
    brief_list,
    log_rich_renderable,
    logger,
    get_console_width,
    cached_property,
    DEFAULT_CONSOLE_WIDTH
)
from .template import Template
from .plugin import plugin
from ._proc_properties import ProcProperties, ProcMeta, ProcType
from .exceptions import ProcWorkdirConflictException

class Proc(ProcProperties, metaclass=ProcMeta):
    """The Proc class provides process assembly functionality"""

    name: ClassVar[str] = None
    desc: ClassVar[str] = None
    singleton: ClassVar[bool] = None

    SELF: ClassVar["Proc"] = False

    def __new__(cls, *args, **kwargs):
        """Make sure cls() always get to the same instance"""
        if (not args and not kwargs) or kwargs.get('singleton', cls.singleton):
            if not cls.SELF or cls.SELF.__class__ is not cls:
                cls.SELF = super().__new__(cls)
            if args or kwargs:
                cls.SELF._inited = False
                cls.__init__(cls.SELF, *args, **kwargs)
            return cls.SELF
        return super().__new__(cls)

    # pylint: disable=redefined-builtin,redefined-outer-name
    def __init__(self,
                 name: Optional[str] = None,
                 desc: Optional[str] = None,
                 *,
                 end: Optional[bool] = None,
                 input_keys: Union[List[str], str] = None,
                 input: Optional[Union[str, Iterable[str]]] = None,
                 output: Optional[Union[str, Iterable[str]]] = None,
                 requires: Optional[Union[ProcType, Iterable[ProcType]]] = None,
                 lang: Optional[str] = None,
                 script: Optional[str] = None,
                 forks: Optional[int] = None,
                 cache: Optional[bool] = None,
                 args: Optional[Dict[str, Any]] = None,
                 envs: Optional[Dict[str, Any]] = None,
                 dirsig: Optional[bool] = None,
                 profile: Optional[str] = None,
                 template: Optional[Union[str, Type[Template]]] = None,
                 scheduler: Optional[Union[str, Scheduler]] = None,
                 scheduler_opts: Optional[Dict[str, Any]] = None,
                 plugin_opts: Optional[Dict[str, Any]] = None,
                 singleton: Optional[bool] = None) -> None:
        if getattr(self, '_inited', False):
            return

        if singleton is None:
            singleton = self.__class__.singleton

        super().__init__(
            end,
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
            scheduler_opts,
            plugin_opts
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

    async def prepare(self, pipeline: "Pipen") -> None:
        """Prepare the process

        Args:
            pipeline: The Pipen object
        """
        if self.end is None and not self.nexts:
            self.end = True
        self.pipeline = pipeline
        profile = self.profile or pipeline.profile

        if profile == 'default':
            # no profile specified or profile is default,
            # we should use __init__ the highest priority
            config = pipeline.config._use('default', copy=True)
        else:
            config = pipeline.config._use(profile, 'default', copy=True)

        self.properties_from_config(config)

        self.workdir = Path(config.workdir) / slugify(self.name)
        self._print_banner()
        self.log('info', 'Workdir: %r', str(self.workdir))
        self.compute_properties()
        self._print_dependencies()

        await plugin.hooks.on_proc_property_computed(self)

        # check if it's the same proc using the workdir
        proc_name_file = self.workdir / 'proc.name'
        if proc_name_file.is_file() and proc_name_file.read_text() != self.name:
            raise ProcWorkdirConflictException(
                'Workdir name is conflicting with process '
                f'{proc_name_file.read_text()!r}, use a differnt pipeline '
                'or a different process name.'
            )
        self.workdir.mkdir(parents=True, exist_ok=True)
        proc_name_file.write_text(self.name)

        self.xqute = Xqute(
            self.scheduler,
            job_metadir=self.workdir,
            job_submission_batch=config.submission_batch,
            job_error_strategy=config.error_strategy,
            job_num_retries=config.num_retries,
            scheduler_forks=self.forks,
            scheduler_jobprefix=self.name,
            **self.scheduler_opts)
        # for the plugin hooks to access
        self.xqute.proc = self

        # init all other properties and jobs
        await self._init_jobs(config)
        self.out_channel = DataFrame((job.output for job in self.jobs))

        await plugin.hooks.on_proc_init(self)

    def __repr__(self):
        return f'<Proc-{hex(id(self))}({self.name}: {self.size})>'

    @cached_property
    def size(self) -> int:
        """The size of the process (# of jobs)"""
        return len(self.jobs)

    @cached_property
    def succeeded(self) -> bool:
        """Check if the process is succeeded (all jobs succeeded)"""
        return all(job.status == JobStatus.FINISHED for job in self.jobs)

    async def run(self) -> None:
        """Run the process"""
        # init pbar
        self.pbar = self.pipeline.pbar.proc_bar(self.size, self.name)

        await plugin.hooks.on_proc_start(self)

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
        self.pbar.done()
        await plugin.hooks.on_proc_done(
            self,
            False if not self.succeeded
            # pylint: disable=comparison-with-callable
            else 'cached' if len(cached_jobs) == self.size
            else True
        )

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
        panel = Panel(
            self.desc,
            title=self.name,
            box=box.Box(
                "╭═┬╮\n"
                "║ ║║\n"
                "├═┼┤\n"
                "║ ║║\n"
                "├═┼┤\n"
                "├═┼┤\n"
                "║ ║║\n"
                "╰═┴╯\n"
            ) if self.end else box.ROUNDED,
            width=min(DEFAULT_CONSOLE_WIDTH, console_width)
        )

        logger.info('')
        log_rich_renderable(panel, 'cyan', logger.info)

    def _print_dependencies(self):
        """Print the dependencies"""
        self.log('info',
                 '[yellow]<<<[/yellow] %s',
                 [proc.name for proc in self.requires]
                 if self.requires else '[START]')
        self.log('info',
                 '[yellow]>>>[/yellow] %s',
                 [proc.name for proc in self.nexts]
                 if self.nexts else '[END]')
