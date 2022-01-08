"""Main entry module, provide the Pipen class"""
import asyncio
from itertools import chain
from os import PathLike
from pathlib import Path
import pprint
import textwrap
from typing import ClassVar, Iterable, List, Sequence, Type, Union

from diot import Diot
from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.console import Group
from simpleconf import Config
from slugify import slugify  # type: ignore
from varname import varname, VarnameException

from .defaults import CONFIG, CONFIG_FILES, CONSOLE_WIDTH
from .exceptions import ProcDependencyError, PipenSetDataError
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
        if name is not None:
            self.name = name
        else:
            try:
                self.name = varname()
            except VarnameException:
                self.name = f"pipen-{self.__class__.PIPELINE_COUNT}"

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

    async def async_run(self, profile: str = "default") -> bool:
        """Run the processes one by one

        Args:
            profile: The default profile to use for the run

        Returns:
            True if the pipeline ends successfully else False
        """
        self.profile = profile
        self.workdir = Path(self.config.workdir) / slugify(self.name)
        self.workdir.mkdir(parents=True, exist_ok=True)

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

    def set_data(self, *indata: Iterable) -> "Pipen":
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
        *procs: Union[Type[Proc], Sequence[Type[Proc]]],
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
            sorted(
                (key, val)
                for key, val in self.config.items()
                if not key.endswith("_opts")
            ),
            (
                (
                    "plugin_opts",
                    pprint.pformat(self.config.plugin_opts, indent=1),
                ),
                (
                    "scheduler_opts",
                    pprint.pformat(self.config.scheduler_opts, indent=1),
                ),
                (
                    "template_opts",
                    pprint.pformat(
                        {
                            key: (
                                {
                                    ckey: textwrap.shorten(
                                        str(cval),
                                        width=30 - len(key),
                                        placeholder=" …",
                                    )
                                    for ckey, cval in chain(
                                        list(val.items())[:3],
                                        []
                                        if len(val) <= 3
                                        else [("...", "...")],
                                    )
                                }
                                if isinstance(val, dict)
                                else val
                            )
                            for key, val in self.config.template_opts.items()
                        },
                        indent=1,
                        # sort_dicts=False,
                    ),
                ),
            ),
        ):
            items_table.add_row(
                Text.assemble((key, "scope.key")),
                Text.assemble(("=", "scope.equals")),
                Text(str(value), overflow="fold"),
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
        nexts = set(sum((proc.nexts or [] for proc in self.procs), []))
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
