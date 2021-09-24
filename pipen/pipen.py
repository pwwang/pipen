"""Main entry module, provide the Pipen class"""
import asyncio
from itertools import chain
from os import PathLike
from pathlib import Path
from typing import ClassVar, List, Sequence, Type, Union

from diot import Diot
from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.console import Group
from simpleconf import Config
from slugify import slugify  # type: ignore

from .defaults import CONFIG, CONFIG_FILES, CONSOLE_WIDTH
from .exceptions import ProcDependencyError
from .pluginmgr import plugin
from .proc import Proc
from .progressbar import PipelinePBar
from .utils import (
    copy_dict,
    get_console_width,
    get_plugin_context,
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

    def __init__(
        self,
        name: str = None,
        desc: str = None,
        outdir: PathLike = None,
        **kwargs,
    ) -> None:
        """Constructor"""
        self.procs: List[Proc] = None
        self.pbar: PipelinePBar = None
        self.name = name or f"pipen-{self.__class__.PIPELINE_COUNT}"
        self.desc = desc
        self.outdir = Path(
            outdir or f"./{slugify(self.name)}_results"
        ).resolve()
        self.workdir: Path = None
        self.profile: str = "default"

        self.starts: List[Proc] = []
        self.config = Diot(copy_dict(CONFIG, 3))
        # We shouldn't update the config here, since we don't know
        # the profile yet
        self._kwargs = kwargs

        if not self.__class__.SETUP:  # pragma: no cover
            # Load plugins from entrypotins at runtime to avoid
            # cyclic imports
            plugin.load_entrypoints()

        plugins = self.config.plugins or self._kwargs.get("plugins", [])
        self.plugin_context = get_plugin_context(plugins)
        self.plugin_context.__enter__()

        # make sure main plugin is enabled
        plugin.get_plugin("main").enable()

        if not self.__class__.SETUP:  # pragma: no cover
            plugin.hooks.on_setup(self.config)
            self.__class__.SETUP = True

        self.__class__.PIPELINE_COUNT += 1

    async def async_run(self) -> bool:
        """Run the processes one by one

        Returns:
            True if the pipeline ends successfully else False
        """
        self.workdir = Path(self.config.workdir) / slugify(self.name)
        self.workdir.mkdir(parents=True, exist_ok=True)

        succeeded = True
        await self._init()
        logger.setLevel(self.config.loglevel.upper())
        log_rich_renderable(pipen_banner(), "magenta", logger.info)
        try:
            self._build_proc_relationships()
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
                await proc_obj._init()
                await proc_obj.run()
                if proc_obj.succeeded:
                    self.pbar.update_proc_done()
                else:
                    self.pbar.update_proc_error()
                    succeeded = False
                    break
                proc_obj.gc()

            logger.info("")
        finally:
            await plugin.hooks.on_complete(self, succeeded)
            self.plugin_context.__exit__()
            if self.pbar:
                self.pbar.done()

        return succeeded

    def run(
        self,
        *starts: Union[Type[Proc], Sequence[Type[Proc]]],
        profile: str = "default",
    ) -> int:
        """Run the pipeline with the given profile

        Args:
            profile: The default profile to use for the run

        Returns:
            True if the pipeline ends successfully else False
        """
        self.profile = profile
        self._set_starts(*starts)
        return asyncio.run(self.async_run())

    def _set_starts(self, *procs: Union[Type[Proc], Sequence[Type[Proc]]]):
        """Set the starts"""
        for proc in procs:
            if isinstance(proc, (list, tuple)):
                self._set_starts(*proc)
            elif proc not in self.starts:
                self.starts.append(proc)  # type: ignore

    def _log_pipeline_info(self) -> None:
        """Print the information of the pipeline"""
        items = (
            [
                Panel(
                    self.desc,
                    box=box.Box(
                        "    \n    \n    \n    \n    \n    \n    \n────\n",
                    ),
                    padding=(0, 0),
                )
            ]
            if self.desc
            else []
        )

        items_table = Table.grid(padding=(0, 1), pad_edge=True)
        items.append(items_table)  # type: ignore
        enabled_plugins = [
            "{name}{version}".format(
                name=name,
                version=(f"-{plg.__version__}" if plg.version else ""),
            )
            for name, plg in plugin.get_enabled_plugins().items()
        ]
        for key, value in chain(
            zip(
                ["# procs", "plugins", "profile", "outdir"],
                [
                    str(len(self.procs)),
                    enabled_plugins,
                    self.profile,
                    self.outdir,
                ],
            ),
            sorted(self.config.items()),
        ):
            items_table.add_row(
                Text.assemble((key, "scope.key")),
                Text.assemble(("=", "scope.equals")),
                str(value),
            )

        logger.info("")
        log_rich_renderable(
            Panel(
                Group(*items),
                title=self.name.upper(),
                width=min(CONSOLE_WIDTH, get_console_width()),
                box=box.Box(
                    "╭═┬╮\n"
                    "║ ║║\n"
                    "├═┼┤\n"
                    "║ ║║\n"
                    "├═┼┤\n"
                    "├═┼┤\n"
                    "║ ║║\n"
                    "╰═┴╯\n"
                ),
                padding=(0, 1),
            ),
            None,
            logger.info,
        )

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
        config = Config()
        config._load(*CONFIG_FILES)
        config._use(self.profile)
        self.config.update(config)

        # configs from files and CONFIG are loaded
        # allow plugins to change the default configs
        await plugin.hooks.on_init(self)
        # Then load the extra configurations passed from __init__(**kwargs)
        # Make sure dict options get inherited
        self.config.template_opts.update(self._kwargs.pop("template_opts", {}))
        self.config.scheduler_opts.update(
            self._kwargs.pop("scheduler_opts", {})
        )
        self.config.plugin_opts.update(self._kwargs.pop("plugin_opts", {}))
        self.config.update(self._kwargs)

    def _build_proc_relationships(self) -> None:
        """Build the proc relationships for the pipeline"""
        if not self.starts:
            raise ProcDependencyError("No start processes specified.")

        # build proc relationships
        self.procs = self.starts[:]
        nexts = set(sum((proc.nexts or [] for proc in self.procs), []))
        logger.debug("")
        logger.debug("Building process relationships:")
        logger.debug("- Start processes: %s", self.procs)
        while nexts:
            logger.debug("- Next processes: %s", nexts)
            # pick up one that can be added to procs
            for proc in sorted(nexts, key=lambda prc: prc.name):
                if proc in self.procs:
                    raise ProcDependencyError(
                        f"Cyclic dependency: {proc.name}"
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
