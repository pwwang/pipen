"""Provides the process class: Proc"""
from __future__ import annotations

import asyncio
import inspect
import logging
from abc import ABC, ABCMeta
from functools import cached_property
from os import PathLike
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Mapping,
    Sequence,
    Type,
    TYPE_CHECKING,
)

from diot import Diot
from rich import box
from rich.panel import Panel
from varname import VarnameException, varname
from xqute import JobStatus, Xqute

from .defaults import ProcInputType
from .exceptions import (
    ProcInputKeyError,
    ProcInputTypeError,
    ProcScriptFileNotFound,
    PipenOrProcNameError,
)
from .pluginmgr import plugin
from .scheduler import get_scheduler
from .template import Template, get_template_engine
from .utils import (
    brief_list,
    copy_dict,
    desc_from_docstring,
    get_logpanel_width,
    ignore_firstline_dedent,
    is_subclass,
    is_valid_name,
    log_rich_renderable,
    logger,
    make_df_colnames_unique_inplace,
    strsplit,
    update_dict,
    get_shebang,
    get_base,
)

if TYPE_CHECKING:  # pragma: no cover
    from .pipen import Pipen


class ProcMeta(ABCMeta):
    """Meta class for Proc"""

    _INSTANCES: Dict[Type, Proc] = {}

    def __repr__(cls) -> str:
        """Representation for the Proc subclasses"""
        return f"<Proc:{cls.name}>"

    def __setattr__(cls, name: str, value: Any) -> None:
        if name == "requires":
            value = cls._compute_requires(value)
        return super().__setattr__(name, value)

    def __call__(cls, *args: Any, **kwds: Any) -> Proc:
        """Make sure Proc subclasses are singletons

        Args:
            *args: and
            **kwds: Arguments for the constructor

        Returns:
            The Proc instance
        """
        if cls not in cls._INSTANCES:
            cls._INSTANCES[cls] = super().__call__(*args, **kwds)

        return cls._INSTANCES[cls]


class Proc(ABC, metaclass=ProcMeta):

    """The abstract class for processes.

    It's an abstract class. You can't instantise a process using it directly.
    You have to subclass it. The subclass itself can be used as a process
    directly.

    Each subclass is a singleton, so to intantise a new process, each subclass
    an existing `Proc` subclass, or use `Proc.from_proc()`.

    Never use the constructor directly. The Proc is designed
    as a singleton class, and is instansiated internally.

    Attributes:
        name: The name of the process. Will use the class name by default.
        desc: The description of the process. Will use the summary from
            the docstring by default.
        envs: The arguments that are job-independent, useful for common options
            across jobs.
        cache: Should we detect whether the jobs are cached?
        dirsig: When checking the signature for caching, whether should we walk
            through the content of the directory? This is sometimes
            time-consuming if the directory is big.
        export: When True, the results will be exported to `<pipeline.outdir>`
            Defaults to None, meaning only end processes will export.
            You can set it to True/False to enable or disable exporting
            for processes
        error_strategy: How to deal with the errors
            - retry, ignore, halt
            - halt to halt the whole pipeline, no submitting new jobs
            - terminate to just terminate the job itself
        num_retries: How many times to retry to jobs once error occurs
        template: Define the template engine to use.
            This could be either a template engine or a dict with key `engine`
            indicating the template engine and the rest the arguments passed
            to the constructor of the `pipen.template.Template` object.
            The template engine could be either the name of the engine,
            currently jinja2 and liquidpy are supported, or a subclass of
            `pipen.template.Template`.
            You can subclass `pipen.template.Template` to use your own template
            engine.
        forks: How many jobs to run simultaneously?
        input: The keys for the input channel
        input_data: The input data (will be computed for dependent processes)
        lang: The language for the script to run. Should be the path to the
            interpreter if `lang` is not in `$PATH`.
        order: The execution order for this process. The bigger the number
            is, the later the process will be executed. Default: 0.
            Note that the dependent processes will always be executed first.
            This doesn't work for start processes either, whose orders are
            determined by `Pipen.set_starts()`
        output: The output keys for the output channel
            (the data will be computed)
        plugin_opts: Options for process-level plugins
        requires: The dependency processes
        scheduler: The scheduler to run the jobs
        scheduler_opts: The options for the scheduler
        script: The script template for the process
        submission_batch: How many jobs to be submited simultaneously

        nexts: Computed from `requires` to build the process relationships
        output_data: The output data (to pass to the next processes)
    """

    name: str = None
    desc: str = None
    envs: Mapping[str, Any] = None
    cache: bool = None
    dirsig: bool = None
    export: bool = None
    error_strategy: str = None
    num_retries: int = None
    template: str | Type[Template] = None
    template_opts: Mapping[str, Any] = None
    forks: int = None
    input: str | Sequence[str] = None
    input_data: Any = None
    lang: str = None
    order: int = None
    output: str | Sequence[str] = None
    plugin_opts: Mapping[str, Any] = None
    requires: Type[Proc] | Sequence[Type[Proc]] = None
    scheduler: str = None
    scheduler_opts: Mapping[str, Any] = None
    script: str = None
    submission_batch: int = None

    nexts: Sequence[Type[Proc]] = None
    output_data: Any = None
    workdir: PathLike = None
    # metadata that marks the process
    # Can also be used for plugins
    # It's not inheirted
    __meta__: Mapping[str, Any] = None

    @classmethod
    def from_proc(
        cls,
        proc: Type[Proc],
        name: str = None,
        desc: str = None,
        envs: Mapping[str, Any] = None,
        cache: bool = None,
        export: bool = None,
        error_strategy: str = None,
        num_retries: int = None,
        forks: int = None,
        input_data: Any = None,
        order: int = None,
        plugin_opts: Mapping[str, Any] = None,
        requires: Sequence[Type[Proc]] = None,
        scheduler: str = None,
        scheduler_opts: Mapping[str, Any] = None,
        submission_batch: int = None,
    ) -> Type[Proc]:
        """Create a subclass of Proc using another Proc subclass or Proc itself

        Args:
            proc: The Proc subclass
            name: The new name of the process
            desc: The new description of the process
            envs: The arguments of the process, will overwrite parent one
                The items that are specified will be inherited
            cache: Whether we should check the cache for the jobs
            export: When True, the results will be exported to
                `<pipeline.outdir>`
                Defaults to None, meaning only end processes will export.
                You can set it to True/False to enable or disable exporting
                for processes
            error_strategy: How to deal with the errors
                - retry, ignore, halt
                - halt to halt the whole pipeline, no submitting new jobs
                - terminate to just terminate the job itself
            num_retries: How many times to retry to jobs once error occurs
            forks: New forks for the new process
            input_data: The input data for the process. Only when this process
                is a start process
            order: The order to execute the new process
            plugin_opts: The new plugin options, unspecified items will be
                inherited.
            requires: The required processes for the new process
            scheduler: The new shedular to run the new process
            scheduler_opts: The new scheduler options, unspecified items will
                be inherited.
            submission_batch: How many jobs to be submited simultaneously

        Returns:
            The new process class
        """
        if not name:
            try:
                name = varname()
            except VarnameException as vexc:
                raise ValueError(
                    "Process name cannot be detected from assignment, "
                    "pass one explicitly to `Proc.from_proc(..., name=...)`"
                ) from vexc

        kwargs: Dict[str, Any] = {
            "name": name,
            "export": export,
            "input_data": input_data,
            "requires": requires,
            "nexts": None,
            "output_data": None,
        }

        locs = locals()
        for key in (
            "desc",
            "envs",
            "cache",
            "forks",
            "order",
            "plugin_opts",
            "scheduler",
            "scheduler_opts",
            "error_strategy",
            "num_retries",
            "submission_batch",
        ):
            if locs[key] is not None:
                kwargs[key] = locs[key]

        kwargs["__doc__"] = proc.__doc__
        out = type(name, (proc,), kwargs)
        return out

    def __init_subclass__(cls) -> None:
        """Do the requirements inferring since we need them to build up the
        process relationship
        """
        base = [
            mro
            for mro in cls.__mro__
            if issubclass(mro, Proc) and mro is not Proc and mro is not cls
        ]
        parent = base[0] if base else None
        # cls.requires = cls._compute_requires()
        # triggers cls.__setattr__() to compute requires
        cls.nexts = []
        cls.requires = cls.requires

        if cls.name is None or (parent and cls.name == parent.name):
            cls.name = cls.__name__

        if not is_valid_name(cls.name):
            raise PipenOrProcNameError(
                f"{cls.name} is not a valid process name, expecting "
                r"'^[\w.-]+$'"
            )

        envs = update_dict(parent.envs if parent else None, cls.envs)
        cls.envs = envs if isinstance(envs, Diot) else Diot(envs or {})
        cls.plugin_opts = update_dict(
            parent.plugin_opts if parent else None,
            cls.plugin_opts,
        )
        cls.scheduler_opts = update_dict(
            parent.scheduler_opts if parent else {},
            cls.scheduler_opts,
        )
        cls.__meta__ = {"procgroup": None}

    def __init__(self, pipeline: Pipen = None) -> None:
        """Constructor

        This is called only at runtime.

        Args:
            pipeline: The Pipen object
        """
        # instance properties
        self.pipeline = pipeline

        self.pbar = None
        self.jobs: List[Any] = []
        self.xqute = None
        self.__class__.workdir = Path(self.pipeline.workdir) / self.name
        # plugins can modify some default attributes
        plugin.hooks.on_proc_create(self)

        # Compute the properties
        # otherwise, the property can be accessed directly from class vars
        if self.desc is None:
            self.desc: str = desc_from_docstring(self.__class__, Proc)

        if self.export is None:
            self.export = bool(not self.nexts)

        # log the basic information
        self._log_info()

        # template
        self.template = get_template_engine(
            self.template or self.pipeline.config.template
        )
        template_opts = copy_dict(self.pipeline.config.template_opts)
        template_opts.update(self.template_opts or {})
        self.template_opts = template_opts

        plugin_opts = copy_dict(self.pipeline.config.plugin_opts)
        plugin_opts.update(self.plugin_opts or {})
        self.plugin_opts = plugin_opts

        # input
        self.input = self._compute_input()  # type: ignore
        plugin.hooks.on_proc_input_computed(self)
        # output
        self.output = self._compute_output()
        # scheduler
        self.scheduler = get_scheduler(  # type: ignore
            self.scheduler or self.pipeline.config.scheduler
        )
        # script
        self.script = self._compute_script()  # type: ignore
        self.workdir.mkdir(exist_ok=True)

        if self.submission_batch is None:
            self.submission_batch = self.pipeline.config.submission_batch

    async def init(self) -> None:
        """Init all other properties and jobs"""
        import pandas

        scheduler_opts = (
            copy_dict(self.pipeline.config.scheduler_opts, 2) or {}
        )
        scheduler_opts.update(self.scheduler_opts or {})
        self.xqute = Xqute(
            self.scheduler,
            job_metadir=self.workdir,
            job_submission_batch=self.submission_batch,
            job_error_strategy=self.error_strategy
            or self.pipeline.config.error_strategy,
            job_num_retries=self.pipeline.config.num_retries
            if self.num_retries is None
            else self.num_retries,
            scheduler_forks=self.forks or self.pipeline.config.forks,
            scheduler_jobprefix=self.name,
            **scheduler_opts,
        )
        # for the plugin hooks to access
        self.xqute.proc = self

        await plugin.hooks.on_proc_init(self)
        await self._init_jobs()
        self.__class__.output_data = pandas.DataFrame(
            (job.output for job in self.jobs)
        )

    def gc(self):
        """GC process for the process to save memory after it's done"""
        del self.xqute
        self.xqute = None

        del self.jobs[:]
        self.jobs = []

        del self.pbar
        self.pbar = None

    def log(
        self,
        level: int | str,
        msg: str,
        *args,
        logger: logging.LoggerAdapter = logger,
    ) -> None:
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
        logger.log(
            level,  # type: ignore
            "[cyan]%s:[/cyan] %s",
            self.name,
            msg,
        )

    async def run(self) -> None:
        """Run the process"""
        # init pbar
        self.pbar = self.pipeline.pbar.proc_bar(self.size, self.name)

        await plugin.hooks.on_proc_start(self)

        cached_jobs = []
        for job in self.jobs:
            if await job.cached:
                cached_jobs.append(job.index)
                await plugin.hooks.on_job_cached(self, job)
            else:
                await self.xqute.put(job)
        if cached_jobs:
            self.log("info", "Cached jobs: [%s]", brief_list(cached_jobs))
        await self.xqute.run_until_complete()
        self.pbar.done()
        await plugin.hooks.on_proc_done(
            self,
            False
            if not self.succeeded
            else "cached"
            if len(cached_jobs) == self.size
            else True,
        )

    # properties
    @cached_property
    def size(self) -> int:
        """The size of the process (# of jobs)"""
        return len(self.jobs)

    @cached_property
    def succeeded(self) -> bool:
        """Check if the process is succeeded (all jobs succeeded)"""
        return all(job.status == JobStatus.FINISHED for job in self.jobs)

    # Private methods
    @classmethod
    def _compute_requires(
        cls,
        requires: Type[Proc] | Sequence[Type[Proc]] = None,
    ) -> Sequence[Type[Proc]]:
        """Compute the required processes and fill the nexts

        Args:
            requires: The required processes. If None, will use `cls.requires`

        Returns:
            None or sequence of Proc subclasses
        """
        if requires is None:
            requires = cls.requires

        if requires is None:
            return requires

        if is_subclass(requires, Proc):
            requires = [requires]  # type: ignore

        # if req is in cls.__bases__, then cls.nexts will be affected by
        # req.nexts
        my_nexts = None if cls.nexts is None else cls.nexts[:]
        for req in requires:  # type: ignore
            if not req.nexts:
                req.nexts = [cls]
            else:
                req.nexts.append(cls)  # type: ignore
        cls.nexts = my_nexts

        return requires  # type: ignore

    async def _init_job(self, worker_id: int) -> None:
        """A worker to initialize jobs

        Args:
            worker_id: The worker id
        """
        for job in self.jobs:
            if job.index % self.submission_batch != worker_id:
                continue
            await job.prepare(self)

    async def _init_jobs(self) -> None:
        """Initialize all jobs

        Args:
            config: The pipeline configuration
        """

        for i in range(self.input.data.shape[0]):
            job = self.scheduler.job_class(i, "", self.workdir)
            self.jobs.append(job)

        await asyncio.gather(
            *(self._init_job(i) for i in range(self.submission_batch))
        )

    def _compute_input(self) -> Mapping[str, Mapping[str, Any]]:
        """Calculate the input based on input and input data

        Returns:
            A dict with type and data
        """
        import pandas
        from .channel import Channel

        # split input keys into keys and types
        input_keys = self.input
        if input_keys and isinstance(input_keys, str):
            input_keys = strsplit(input_keys, ",")

        if not input_keys:
            raise ProcInputKeyError(f"[{self.name}] No input provided")

        out = Diot(type={}, data=None)
        for input_key_type in input_keys:
            if ":" not in input_key_type:
                out.type[input_key_type] = ProcInputType.VAR
                continue

            input_key, input_type = strsplit(input_key_type, ":", 1)
            if input_type not in ProcInputType.__dict__.values():
                raise ProcInputTypeError(
                    f"[{self.name}] Unsupported input type: {input_type}"
                )
            out.type[input_key] = input_type

        # get the data
        if not self.requires and self.input_data is None:
            out.data = pandas.DataFrame([[None] * len(out.type)])
        elif not self.requires:
            out.data = Channel.create(self.input_data)
        elif callable(self.input_data):
            out.data = Channel.create(
                self.__class__.input_data(
                    *(req.output_data for req in self.requires)  # type: ignore
                )
            )
        else:
            if self.input_data:
                self.log(
                    "warning",
                    "Ignoring input data, this is not a start process.",
                )

            out.data = pandas.concat(
                (req.output_data for req in self.requires),  # type: ignore
                axis=1,
            ).fillna(method="ffill")

        make_df_colnames_unique_inplace(out.data)

        # try match the column names
        # if none matched, use the first columns
        rest_cols = out.data.columns.difference(out.type, False)
        len_rest_cols = len(rest_cols)
        matched_cols = out.data.columns.intersection(out.type)
        needed_cols = [col for col in out.type if col not in matched_cols]
        len_needed_cols = len(needed_cols)

        if len_rest_cols > len_needed_cols:
            self.log(
                "warning",
                "Wasted %s column(s) of input data.",
                len_rest_cols - len_needed_cols,
            )
        elif len_rest_cols < len_needed_cols:
            self.log(
                "warning",
                "No data column for input: %s, using None.",
                needed_cols[len_rest_cols:],
            )
            # Add None
            # Use loop to keep order
            for needed_col in needed_cols[len_rest_cols:]:
                out.data.insert(out.data.shape[1], needed_col, None)
            len_needed_cols = len_rest_cols

        out.data = out.data.rename(
            columns=dict(zip(rest_cols[:len_needed_cols], needed_cols))
        ).loc[:, list(out.type)]

        return out

    def _compute_output(self) -> str | List[str]:
        """Compute the output for jobs to render"""
        if not self.output:
            return None

        if isinstance(self.output, (list, tuple)):
            return [
                self.template(oput, **self.template_opts)  # type: ignore
                for oput in self.output
            ]

        return self.template(self.output, **self.template_opts)  # type: ignore

    def _compute_script(self) -> Template:
        """Compute the script for jobs to render"""
        if not self.script:
            self.log("warning", "No script specified.")
            return None

        script = self.script
        if script.startswith("file://"):
            script_file = Path(script[7:])
            if not script_file.is_absolute():
                base = get_base(
                    self.__class__,
                    Proc,
                    script,
                    lambda klass: getattr(klass, "script", None),
                )
                script_file = Path(inspect.getfile(base)).parent / script_file
            if not script_file.is_file():
                raise ProcScriptFileNotFound(
                    f"No such script file: {script_file}"
                )
            script = script_file.read_text()

        self.script = ignore_firstline_dedent(script)
        if not self.lang:
            self.lang = get_shebang(self.script)

        plugin.hooks.on_proc_script_computed(self)
        return self.template(self.script, **self.template_opts)  # type: ignore

    def _log_info(self):
        """Log some basic information of the process"""
        title = (
            f"{self.__meta__['procgroup'].name}/{self.name}"
            if self.__meta__["procgroup"]
            else self.name
        )
        panel = Panel(
            self.desc or "Undescribed",
            title=title,
            box=box.Box(
                "╭═┬╮\n"
                "║ ║║\n"
                "├═┼┤\n"
                "║ ║║\n"
                "├═┼┤\n"
                "├═┼┤\n"
                "║ ║║\n"
                "╰═┴╯\n"
            )
            if self.export
            else box.ROUNDED,
            width=get_logpanel_width(),
        )

        logger.info("")
        log_rich_renderable(panel, "cyan", logger.info)
        self.log("info", "Workdir: %r", str(self.workdir))
        self.log(
            "info",
            "[yellow]<<<[/yellow] %s",
            [proc.name for proc in self.requires]
            if self.requires
            else "[START]",
        )
        self.log(
            "info",
            "[yellow]>>>[/yellow] %s",
            [proc.name for proc in self.nexts] if self.nexts else "[END]",
        )
