"""Main entry module, provide the Pipen class"""
from __future__ import annotations

import asyncio
from os import PathLike
from pathlib import Path
from typing import Any, ClassVar, Iterable, List, Sequence, Type

from diot import Diot
from rich import box
from rich.panel import Panel
from rich.text import Text
from simpleconf import ProfileConfig
from varname import varname, VarnameException

from .defaults import CONFIG, CONFIG_FILES
from .exceptions import (
    PipenOrProcNameError,
    ProcDependencyError,
    PipenSetDataError,
)
from .pluginmgr import plugin
from .proc import Proc
from .progressbar import PipelinePBar
from .utils import (
    copy_dict,
    desc_from_docstring,
    get_logpanel_width,
    get_plugin_context,
    is_valid_name,
    log_rich_renderable,
    logger,
    pipen_banner,
)


class Pipen:
    """The Pipen class provides interface to assemble and run the pipeline

    Attributes:
        name: The name of the pipeline
        desc: The description of the pipeline
        outdir: The output directory of the results
        procs: The processes
        pbar: The progress bar
        starts: The start processes
        config: The configurations
        workdir: The workdir for the pipeline
        profile: The profile of the configurations to run the pipeline
        _kwargs: The extra configrations passed to overwrite the default ones

        PIPELINE_COUNT: How many pipelines are loaded
        SETUP: Whether the one-time setup hook is called

    Args:
        name: The name of the pipeline
        desc: The description of the pipeline
        outdir: The output directory of the results
        **kwargs: Other configurations
    """

    PIPELINE_COUNT: ClassVar[int] = 0
    SETUP: ClassVar[bool] = False

    name: str = None
    desc: str = None
    outdir: str | PathLike = None
    starts: List[Proc] = []
    data: Iterable = None
    # other configs

    def __init__(
        self,
        name: str = None,
        desc: str = None,
        outdir: str | PathLike = None,
        **kwargs,
    ) -> None:
        """Constructor"""
        self.procs: List[Proc] = None
        self.pbar: PipelinePBar = None
        if name is not None:
            self.name = name
        elif self.__class__.name is not None:
            self.name = self.__class__.name
        else:
            try:
                self.name = varname()
            except VarnameException:
                if self.__class__.PIPELINE_COUNT == 0:
                    self.name = self.__class__.__name__
                else:
                    self.name = (
                        f"{self.__class__.__name__}-"
                        f"{self.__class__.PIPELINE_COUNT}"
                    )

        if not is_valid_name(self.name):
            raise PipenOrProcNameError(
                fr"Invalid pipeline name: {self.name}, expecting '^[\w.-]$'"
            )

        self.desc = (
            desc
            or self.__class__.desc
            or desc_from_docstring(self.__class__, Pipen)
        )
        self.outdir = Path(
            outdir or self.__class__.outdir or f"./{self.name}-output"
        ).resolve()
        self.workdir: Path = None
        self.profile: str = "default"

        self.starts: List[Proc] = self.__class__.starts
        if self.starts and not isinstance(self.starts, (tuple, list)):
            self.starts = [self.starts]

        self.config = Diot(copy_dict(CONFIG, 3))
        # We shouldn't update the config here, since we don't know
        # the profile yet
        self._kwargs = {
            key: value
            for key, value in self.__class__.__dict__.items()
            if key in self.config
        }
        self._kwargs.setdefault("plugin_opts", {}).update(
            kwargs.pop("plugin_opts", {})
        )
        self._kwargs.setdefault("template_opts", {}).update(
            kwargs.pop("template_opts", {})
        )
        self._kwargs.setdefault("scheduler_opts", {}).update(
            kwargs.pop("scheduler_opts", {})
        )
        self._kwargs.update(kwargs)
        # Initialize the workdir, as workdir is created before _init()
        # But the config is updated in _init()
        # Here we hack it to have the workdir passed in.
        if "workdir" in kwargs:
            self.config.workdir = kwargs["workdir"]

        if not self.__class__.SETUP:  # pragma: no cover
            # Load plugins from entrypotins at runtime to avoid
            # cyclic imports
            plugin.load_entrypoints()

        plugins = self.config.plugins or self._kwargs.get("plugins", [])
        self.plugin_context = get_plugin_context(plugins)
        self.plugin_context.__enter__()

        # make sure core plugin is enabled
        plugin.get_plugin("core").enable()

        if not self.__class__.SETUP:  # pragma: no cover
            plugin.hooks.on_setup(self.config)
            self.__class__.SETUP = True

        self.__class__.PIPELINE_COUNT += 1

        if self.__class__.data is not None:
            self.set_data(*self.__class__.data)

    def __init_subclass__(cls) -> None:
        cls.PIPELINE_COUNT = 0

    async def async_run(self, profile: str = "default") -> bool:
        """Run the processes one by one

        Args:
            profile: The default profile to use for the run

        Returns:
            True if the pipeline ends successfully else False
        """
        self.profile = profile
        self.workdir = Path(self.config.workdir) / self.name
        # self.workdir.mkdir(parents=True, exist_ok=True)

        succeeded = True
        await self._init()
        logger.setLevel(self.config.loglevel.upper())
        log_rich_renderable(pipen_banner(), "magenta", logger.info)
        try:
            self.build_proc_relationships()
            self._log_pipeline_info()
            await plugin.hooks.on_start(self)
            for proc in self.procs:
                self.pbar.update_proc_running()
                proc_obj = proc(self)  # type: ignore
                if proc in self.starts and proc.input_data is None:
                    proc_obj.log(
                        "warning",
                        "This is a start process, "
                        "but no 'input_data' specified.",
                    )
                await proc_obj.init()
                await proc_obj.run()
                if proc_obj.succeeded:
                    self.pbar.update_proc_done()
                else:
                    self.pbar.update_proc_error()
                    succeeded = False
                    break
                proc_obj.gc()

            logger.info("")
        except Exception:
            raise
        else:
            await plugin.hooks.on_complete(self, succeeded)
        finally:
            self.plugin_context.__exit__()
            if self.pbar:
                self.pbar.done()

        return succeeded

    def run(
        self,
        profile: str = "default",
    ) -> int:
        """Run the pipeline with the given profile
        This is just a sync wrapper for the async `async_run` function using
        `asyncio.run()`

        Args:
            profile: The default profile to use for the run

        Returns:
            True if the pipeline ends successfully else False
        """
        return asyncio.run(self.async_run(profile))

    def set_data(self, *indata: Any) -> Pipen:
        """Set the input_data for start processes

        Args:
            *indata: The input data for the start processes
                The data will set for the processes in the order determined by
                `set_starts()`.
                If a process has input_data set, an error will be raised.
                To use that input_data, set None here in the corresponding
                position for the process

        Raises:
            ProcInputDataError: When trying to set input data to
                processes with input_data already set

        Returns:
            `self` to chain the operations
        """
        for start, data in zip(self.starts, indata):
            if data is None:
                continue
            if start.input_data is not None:
                raise PipenSetDataError(
                    f"`input_data` has already set for {start}. "
                    "If you want to use it, set `None` at the position of "
                    "this process for `Pipen.set_data()`."
                )
            start.input_data = data
        return self

    def set_starts(
        self,
        *procs: Type[Proc] | Sequence[Type[Proc]],
        clear: bool = True,
    ):
        """Set the starts

        Args:
            *procs: The processes to set as starts of the pipeline.
            clear: Wether to clear previous set starts

        Raises:
            ProcDependencyError: When processes set as starts repeatedly

        Returns:
            `self` to chain the operations
        """
        if clear:
            self.starts = []
            self.procs = None

        for proc in procs:
            if isinstance(proc, (list, tuple)):
                self.set_starts(*proc, clear=False)
            elif proc not in self.starts:
                self.starts.append(proc)  # type: ignore
            else:
                raise ProcDependencyError(
                    f"{proc} is already a start process."
                )
        return self

    # In case people forget the "s"
    set_start = set_starts

    def _log_pipeline_info(self) -> None:
        """Print the information of the pipeline"""
        logger.info("")
        # Pipeline line and description
        log_rich_renderable(
            Panel(
                self.desc or Text(self.name.upper(), justify="center"),
                width=get_logpanel_width(),
                # padding=(0, 1),
                box=box.DOUBLE_EDGE,
                title=self.name.upper() if self.desc else None,
            ),
            "magenta",
            logger.info,
        )
        fmt = "[bold][magenta]%-16s:[/magenta][/bold] %s"
        enabled_plugins = (
            "{name} [cyan]{version}[/cyan]".format(
                name=name,
                version=(f"v{plg.version}" if plg.version else ""),
            )
            for name, plg in plugin.get_enabled_plugins().items()
            if name != "core"
        )
        for i, plug in enumerate(enabled_plugins):
            logger.info(fmt, "plugins" if i == 0 else "", plug)
        logger.info(fmt, "# procs", len(self.procs))
        logger.info(fmt, "profile", self.profile)
        logger.info(fmt, "outdir", self.outdir)
        logger.info(fmt, "cache", self.config.cache)
        logger.info(fmt, "dirsig", self.config.dirsig)
        logger.info(fmt, "error_strategy", self.config.error_strategy)
        logger.info(fmt, "forks", self.config.forks)
        logger.info(fmt, "lang", self.config.lang)
        logger.info(fmt, "loglevel", self.config.loglevel)
        logger.info(fmt, "num_retries", self.config.num_retries)
        logger.info(fmt, "scheduler", self.config.scheduler)
        logger.info(fmt, "submission_batch", self.config.submission_batch)
        logger.info(fmt, "template", self.config.template)
        logger.info(fmt, "workdir", self.workdir)
        for i, (key, val) in enumerate(self.config.plugin_opts.items()):
            logger.info(fmt, "plugin_opts" if i == 0 else "", f"{key}={val}")
        for i, (key, val) in enumerate(self.config.scheduler_opts.items()):
            logger.info(
                fmt, "scheduler_opts" if i == 0 else "", f"{key}={val}"
            )
        for i, (key, val) in enumerate(self.config.template_opts.items()):
            logger.info(fmt, "template_opts" if i == 0 else "", f"{key}={val}")

    async def _init(self) -> None:
        """Compute the configurations for the pipeline based on the priorities

        Configurations (priority from low to high)
        1. The default config in .defaults
        2. The plugin_opts defined in plugins (via on_setup() hook)
           (see __init__())
        3. Configuration files
        4. **kwargs from Pipen(..., **kwargs)
        5. Those defined in each Proc class
        """
        # Then load the configurations from config files
        config = ProfileConfig.load(
            {"default": self.config},
            *CONFIG_FILES,
            ignore_nonexist=True,
        )
        self.config = ProfileConfig.use_profile(
            config, self.profile, copy=True
        )

        # configs from files and CONFIG are loaded
        # allow plugins to change the default configs
        await plugin.hooks.on_init(self)
        self.workdir.mkdir(parents=True, exist_ok=True)
        # Then load the extra configurations passed from __init__(**kwargs)
        # Make sure dict options get inherited
        self.config.template_opts.update(self._kwargs.pop("template_opts", {}))
        self.config.scheduler_opts.update(
            self._kwargs.pop("scheduler_opts", {})
        )
        self.config.plugin_opts.update(self._kwargs.pop("plugin_opts", {}))
        self.config.update(self._kwargs)

    def build_proc_relationships(self) -> None:
        """Build the proc relationships for the pipeline"""
        if self.procs:
            return

        if not self.starts:
            raise ProcDependencyError(
                "No start processes specified. "
                "Did you forget to call `Pipen.set_starts()`?"
            )

        # build proc relationships
        self.procs = self.starts[:]
        nexts = set(
            sum((proc.nexts or [] for proc in self.procs), [])  # type: ignore
        )
        logger.debug("")
        logger.debug("Building process relationships:")
        logger.debug("- Start processes: %s", self.procs)
        while nexts:
            logger.debug("- Next processes: %s", nexts)
            # pick up one that can be added to procs
            for proc in sorted(
                nexts, key=lambda prc: (prc.order or 0, prc.name)
            ):
                if proc in self.procs:
                    raise ProcDependencyError(
                        f"Cyclic dependency: {proc.name}"
                    )

                if proc.name in [p.name for p in self.procs]:
                    raise PipenOrProcNameError(
                        f"'{proc.name}' is already used by another process."
                    )

                # Add proc to self.procs if all their requires
                # are added to self.procs
                # Then remove proc from nexts
                # If there are still procs in nexts
                # meaning some requires of those procs cannot run before
                # those procs.
                if not set(proc.requires) - set(self.procs):  # type: ignore
                    self.procs.append(proc)  # type: ignore
                    nexts.remove(proc)
                    nexts |= set(proc.nexts or ())
                    break
            else:
                if nexts:
                    raise ProcDependencyError(
                        f"No available next processes for {nexts}. "
                        "Did you forget to start with their "
                        "required processes?"
                    )

        self.pbar = PipelinePBar(len(self.procs), self.name.upper())
