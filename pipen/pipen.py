"""Main entry module, provide the Pipen class"""
from typing import Any, ClassVar, List, Optional, Union
import asyncio
from io import StringIO

from rich import box
from rich.console import Console
from rich.panel import Panel

from .defaults import DEFAULT_CONFIG_FILES, DEFAULT_CONFIG, config
from .plugin import plugin, PipenMainPlugin
from .proc import Proc, ProcType
from .progressbar import PipelinePBar
from .exceptions import ProcDependencyError
from .utils import (
    get_console_width,
    get_plugin_context,
    logger,
    pipen_banner,
    DEFAULT_CONSOLE_WIDTH
)

class Pipen:
    """The Pipen class provides interface to assemble and run the pipeline"""

    PIPELINE_COUNT: ClassVar[int] = 0

    def __init__(self,
                 starts: Union[ProcType, List[ProcType]],
                 name: Optional[str] = None,
                 desc: str = 'Undescribed.',
                 plugins: Optional[List[Any]] = None,
                 **kwargs) -> None:

        if Pipen.PIPELINE_COUNT == 0:
            from . import __version__
            PipenMainPlugin.__version__ = __version__
            # make sure setup is called at runtime
            plugin.hooks.on_setup(DEFAULT_CONFIG.plugins)
            config._load({'default': DEFAULT_CONFIG},
                         *DEFAULT_CONFIG_FILES)
            logger.setLevel(config.loglevel.upper())
            for line in pipen_banner():
                logger.info(line)
            # logger.debug('Plugin setup complete.')

        self.procs = None
        self.pbar = None
        self.name = name or f'pipeline-{Pipen.PIPELINE_COUNT}'
        self.desc = desc
        self.starts = [starts] if not isinstance(starts, list) else starts

        self._print_banner()

        self.config = config.copy()
        self.config._load({'__init__': kwargs})

        self.plugin_context = get_plugin_context(plugins)
        if self.plugin_context:
            self.plugin_context.__enter__()
        logger.info('Enabled plugins: %s', [
            '{name}{version}'.format(
                name=name,
                version=(f'-v{plg.__version__}' if plg.version else '')
            )
            for name, plg in plugin.get_enabled_plugins().items()
        ])


        Pipen.PIPELINE_COUNT += 1

    def _print_banner(self) -> None:
        """Print he banner for the pipeline"""
        console_width = get_console_width()
        stream = StringIO()
        console = Console(file=stream)
        panel = Panel(self.desc,
                      title=self.name,
                      box=box.HEAVY,
                      width=min(DEFAULT_CONSOLE_WIDTH, console_width))
        console.print(panel)
        logger.info('')
        for line in console.file.getvalue().splitlines():
            logger.info(f'[green]{line}[/green]')

    def _init(self) -> None:
        """Initialize the pipeline"""
        max_proc_name_len = self._init_procs(self.starts)
        desc_len = max(len(self.name), max_proc_name_len)
        self.pbar = PipelinePBar(len(self.procs), self.name, desc_len)

        # logger.debug('Calling hook: on_init ...')
        plugin.hooks.on_init(self)

    def _init_procs(self, starts: List[ProcType]) -> int:
        """Instantiate all processes

        Args:
            starts: The start processes

        Returns:
            The max length of all processes names (used to align the desc of
                the progressbar
        """
        # logger.debug('Initializing all involved processes ...')
        self.procs = [start if isinstance(start, Proc) else start()
                      for start in starts]
        max_proc_name_len = max(len(proc.name) for proc in self.procs)
        nexts = set(sum((proc.nexts for proc in self.procs), []))
        while nexts:
            # pick up one that can be added to procs
            for proc in nexts:
                if proc in self.procs:
                    raise ProcDependencyError(
                        f'Cyclic dependency: {proc.name}'
                    )
                if not set(proc.requires) - set(self.procs):
                    max_proc_name_len = max(max_proc_name_len, len(proc.name))
                    self.procs.append(proc)
                    nexts.remove(proc)
                    nexts |= set(proc.nexts)
                    break
            else:
                if nexts:
                    raise ProcDependencyError(
                        'No available next process. '
                        'Did you forget to start with some processes?'
                    )

        logger.info('Loaded processes: %s', len(self.procs))
        return max_proc_name_len

    async def async_run(self, profile: str) -> None:
        """Run the processes one by one

        Args:
            profile: The default profile to use for the run
                Unless the profile is defined in the processes, otherwise
                this profile will be used
        """
        try:
            self._init()
            for proc in self.procs:
                self.pbar.update_proc_running()
                await proc.prepare(self, profile)
                await proc.run()
                if proc.succeeded:
                    self.pbar.update_proc_done()
                else:
                    self.pbar.update_proc_error()
                    break
        # except Exception as exc:
            # logger.exception(exc)
            # sys.exit(1)
            # rich has a shift on line numbers
        finally:
            self.pbar.done()
            if self.plugin_context:
                self.plugin_context.__exit__()

    def run(self, profile: str = 'default') -> None:
        """Run the pipeline with the given profile

        Args:
            profile: The default profile to use for the run
                Unless the profile is defined in the processes, otherwise
                this profile will be used
        """
        asyncio.run(self.async_run(profile))
        plugin.hooks.on_complete(self)
