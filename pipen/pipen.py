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
from .exceptions import ProcDependencyError, PipenException
from .plugin import plugin
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

    Args:
        name: The name of the pipeline
        desc: The description of the pipeline
        outdir: The output directory of the results
        **kwargs: Other configurations
    """

    PIPELINE_COUNT: ClassVar[int] = 0

    def __init__(
        self,
        name: str = None,
        desc: str = None,
        outdir: PathLike = None,
        **kwargs,
    ) -> None:
        """constructor"""
        self.procs: List[Proc] = None
        self.pbar: PipelinePBar = None
        self.name = name or f"pipen-{Pipen.PIPELINE_COUNT}"
        self.desc = desc
        self.outdir = Path(outdir or f"./{slugify(self.name)}_results")
        self._done = False

        self.starts: List[Proc] = []
        self.config = Diot(copy_dict(CONFIG, 3)) | kwargs
        # make sure main plugin is enabled
        plugin.get_plugin("main").enable()

        plugin.hooks.on_init(self)

    async def async_run(self, profile: str = "default") -> bool:
        """Run the processes one by one

        Args:
            profile: The profile to use

        Returns:
            True if the pipeline ends successfully else False
        """
        if self._done:
            raise PipenException(
                "Cannot run a pipeline twice. "
                "If it is intentional, make a new Pipen instance."
            )

        config = Config()
        config._load(*CONFIG_FILES)
        config._use(profile)
        self.config.update(config)
        self.config.workdir = Path(self.config.workdir) / slugify(self.name)
        logger.setLevel(self.config.loglevel.upper())

        log_rich_renderable(pipen_banner(), "magenta", logger.info)
        if self.__class__.PIPELINE_COUNT == 0:
            plugin.hooks.on_setup(self.config.plugin_opts)
        self.__class__.PIPELINE_COUNT += 1

        succeeded = True
        with get_plugin_context(self.config.plugins):
            try:
                await self._init()
                self._log_pipeline_info(profile)
                await plugin.hooks.on_start(self)

                for proc in self.procs:
                    self.pbar.update_proc_running()
                    proc_obj = proc(self)  # type: ignore
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
                await plugin.hooks.on_complete(self, succeeded)
            finally:
                if self.pbar:
                    self.pbar.done()

        self._done = True
        return succeeded

    def run(
        self,
        *starts: Union[Type[Proc], Sequence[Type[Proc]]],
        profile: str = "default",
    ) -> int:
        """Run the pipeline with the given profile

        Args:
            profile: The default profile to use for the run
                Unless the profile is defined in the processes, otherwise
                this profile will be used

        Returns:
            True if the pipeline ends successfully else False
        """
        self._set_starts(*starts)
        return asyncio.run(self.async_run(profile))

    def _set_starts(self, *procs: Union[Type[Proc], Sequence[Type[Proc]]]):
        """Set the starts"""
        for proc in procs:
            if isinstance(proc, (list, tuple)):
                self._set_starts(*proc)
            elif proc not in self.starts:
                self.starts.append(proc)  # type: ignore

    def _log_pipeline_info(self, profile: str) -> None:
        """Print the information of the pipeline

        Args:
            profile: The profile to print
        """
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
                [str(len(self.procs)), enabled_plugins, profile, self.outdir],
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
        """Initialize the pipeline"""
        if not self.starts:
            raise ProcDependencyError("No start processes specified.")

        # build proc relationships
        self.procs = self.starts[:]
        max_proc_name_len = max(len(proc.name) for proc in self.procs)
        nexts = set(sum((proc.nexts or [] for proc in self.procs), []))
        logger.debug("")
        logger.debug("Building process relationships:")
        logger.debug("- Start processes: %s", self.procs)
        while nexts:
            logger.debug("- Next processes: %s", nexts)
            # pick up one that can be added to procs
            for proc in sorted(nexts, key=lambda prc: prc.name):
                if proc in self.procs:
                    raise ProcDependencyError(f"Cyclic dependency: {proc.name}")

                # Add proc to self.procs if all their requires
                # are added to self.procs
                # Then remove proc from nexts
                # If there are still procs in nexts
                # meaning some requires of those procs cannot run before
                # those procs.
                if not set(proc.requires) - set(self.procs):  # type: ignore
                    max_proc_name_len = max(max_proc_name_len, len(proc.name))
                    self.procs.append(proc)  # type: ignore
                    nexts.remove(proc)
                    nexts |= set(proc.nexts or ())
                    break
            else:
                if nexts:
                    raise ProcDependencyError(
                        f"No available next processes for {nexts}. "
                        "Did you forget to start with their required processes?"
                    )

        desc_len = max(len(self.name), max_proc_name_len)
        self.pbar = PipelinePBar(len(self.procs), self.name.upper(), desc_len)
