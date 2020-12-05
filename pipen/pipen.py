"""Main entry module, provide the Pipen class"""
from os import PathLike
from typing import ClassVar, List, Optional, Union, Iterable
import asyncio

from rich import box
from rich.panel import Panel

from slugify import slugify

from .defaults import DEFAULT_CONFIG_FILES, DEFAULT_CONFIG, config
from .plugin import plugin, PipenMainPlugin
from .proc import Proc, ProcType
from .progressbar import PipelinePBar
from .exceptions import ProcDependencyError
from .utils import (
    get_console_width,
    get_plugin_context, log_rich_renderable,
    render_scope,
    logger,
    pipen_banner,
    DEFAULT_CONSOLE_WIDTH
)

class Pipen:
    """The Pipen class provides interface to assemble and run the pipeline"""

    PIPELINE_COUNT: ClassVar[int] = 0

    def __init__(self,
                 name: Optional[str] = None,
                 desc: str = 'Undescribed.',
                 outdir: Optional[PathLike] = None,
                 **kwargs) -> None:

        if Pipen.PIPELINE_COUNT == 0:
            from . import __version__
            PipenMainPlugin.__version__ = __version__
            # make sure setup is called at runtime
            plugin.hooks.on_setup(DEFAULT_CONFIG.plugin_opts)
            config._load({'default': DEFAULT_CONFIG},
                         *DEFAULT_CONFIG_FILES)
            logger.setLevel(config.loglevel.upper())
            log_rich_renderable(pipen_banner(), 'magenta', logger.info)

        self.procs = None
        self.pbar = None
        self.name = name or f'pipeline-{Pipen.PIPELINE_COUNT}'
        self.desc = desc
        self.outdir = outdir or f'./{slugify(self.name)}-output'
        self.profile = 'default'

        self._starts = []

        self._print_banner()

        self.config = config.copy()
        self.config._load({'default': kwargs})

        self.plugin_context = get_plugin_context(self.config.plugins)
        self.plugin_context.__enter__()

        # make sure main plugin is enabled
        plugin.get_plugin('main').enable()

        logger.info('Enabled plugins: %s', [
            '{name}{version}'.format(
                name=name,
                version=(f'-{plg.__version__}' if plg.version else '')
            )
            for name, plg in plugin.get_enabled_plugins().items()
        ])

        Pipen.PIPELINE_COUNT += 1
        plugin.hooks.on_init(self)

    def starts(self, *procs: Union[ProcType, Iterable[ProcType]]):
        """Set the starts"""
        for proc in procs:
            if isinstance(proc, (list, tuple)):
                self._starts.extend(proc)
            else:
                self._starts.append(proc)

        return self

    def _print_banner(self) -> None:
        """Print he banner for the pipeline"""
        console_width = get_console_width()
        panel = Panel(self.desc,
                      title=self.name,
                      box=box.HEAVY,
                      width=min(DEFAULT_CONSOLE_WIDTH, console_width))
        logger.info('')
        log_rich_renderable(panel, 'green', logger.info)

    def _print_config(self) -> None:
        """Print the default configuration"""
        if self.profile == 'default':
            context = self.config._with('default')
        else:
            context = self.config._with(self.profile, 'default')

        logger.info('')
        with context as conf:
            log_rich_renderable(
                render_scope(conf, 'default configurations'),
                None,
                logger.info
            )

    async def _init(self) -> None:
        """Initialize the pipeline"""
        if not self._starts:
            raise ProcDependencyError('No start processes specified.')

        max_proc_name_len = self._init_procs(self._starts)
        desc_len = max(len(self.name), max_proc_name_len)
        self.pbar = PipelinePBar(len(self.procs), self.name, desc_len)

        # logger.debug('Calling hook: on_init ...')
        # prepare procs first then they'll be accessed in on_init
        for proc in self.procs:
            await proc.prepare(self, self.profile)

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

    async def async_run(self) -> None:
        """Run the processes one by one"""
        try:
            await self._init()
            await plugin.hooks.on_start(self)
            logger.info('Running pipeline using profile: %r', self.profile)
            logger.info('Output will be saved to: %r', str(self.outdir))
            self._print_config()

            succeeded = True
            for proc in self.procs:
                self.pbar.update_proc_running()
                await proc.run()
                if proc.succeeded:
                    self.pbar.update_proc_done()
                else:
                    self.pbar.update_proc_error()
                    succeeded = False
                    break
                proc.gc()
            await plugin.hooks.on_complete(self, succeeded)
        # except Exception as exc:
            # logger.exception(exc)
            # sys.exit(1)
            # rich has a shift on line numbers
        finally:
            if self.pbar:
                self.pbar.done()
            self.plugin_context.__exit__()

    def run(self, profile: str = 'default') -> None:
        """Run the pipeline with the given profile

        Args:
            profile: The default profile to use for the run
                Unless the profile is defined in the processes, otherwise
                this profile will be used
        """
        self.profile = profile
        asyncio.run(self.async_run())
