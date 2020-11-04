"""Provide some utilities"""
import logging
from os import PathLike
from pathlib import Path
from io import StringIO
from typing import (
    Any, Callable, Iterable, List, Mapping, Optional, Tuple, Union
)
# pylint: disable=unused-import
try: # pragma: no cover
    from functools import cached_property
except ImportError: # pragma: no cover
    from cached_property import cached_property
# pylint: enable=unused-import

try: # pragma: no cover
    import importlib_metadata
except ImportError: # pragma: no cover
    # pylint: disable=ungrouped-imports
    from importlib import metadata as importlib_metadata

from rich.logging import RichHandler
from rich.console import Console, RenderableType
from rich.highlighter import ReprHighlighter
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich.pretty import Pretty


from more_itertools import consecutive_groups
from simplug import SimplugContext

from .defaults import (LOGGER_NAME,
                       DEFAULT_CONSOLE_WIDTH,
                       DEFAULT_CONSOLE_WIDTH_SHIFT)
from .exceptions import ConfigurationError
from .plugin import plugin

# pylint: disable=invalid-name

_logger_handler = RichHandler(show_path=False,
                              show_level=False,
                              rich_tracebacks=True,
                              markup=True)
_logger_format = logging.Formatter(
    '[logging.level.%(levelname)s]%(levelname).1s[/logging.level.%(levelname)s]'
    ' /%(plugin_name)-7s %(message)s',
    '%m-%d %H:%M:%S'
)
_logger_handler.setFormatter(_logger_format)

def get_logger(name: str,
               level: Optional[Union[str, int]] = None) -> logging.Logger:
    """Get the logger by given plugin name

    Args:
        level: The initial level of the logger

    Returns:
        The logger
    """
    log = logging.getLogger(f'pipen.{name}')
    log.addHandler(_logger_handler)

    if level is not None:
        log.setLevel(level.upper() if isinstance(level, str) else level)

    return logging.LoggerAdapter(log, {'plugin_name': name})

logger = get_logger(LOGGER_NAME)

def get_console_width(default: int = DEFAULT_CONSOLE_WIDTH,
                      shift: int = DEFAULT_CONSOLE_WIDTH_SHIFT) -> int:
    """Get the console width

    Args:
        default: The default console width if failed to get
        shift: The shift to subtract from the width
            as we have time, level, plugin name in log
    """
    try:
        return logger.logger.handlers[0].console.width - shift
    except (AttributeError, IndexError):  # pragma: no cover
        return default - shift

def get_plugin_context(plugins: Optional[List[Any]]) -> SimplugContext:
    """Get the plugin context to enable and disable plugins per pipeline

    Args:
        plugins: A list of plugins to enable or a list of names with 'no:'
            as prefix to disable

    Returns:
        The plugin context manager
    """
    if plugins is None:
        return plugin.plugins_only_context(None)

    no_plugins = [isinstance(plug, str) and plug.startswith('no:')
                  for plug in plugins]
    if any(no_plugins) and not all(no_plugins):
        raise ConfigurationError(
            'Either all plugin names start with "no:" or '
            'none of them does.'
        )
    if all(no_plugins):
        return plugin.plugins_but_context(
            plug[3:] for plug in plugins
        )
    return plugin.plugins_only_context(plugins)

def log_rich_renderable(
        renderable: RenderableType,
        color: str,
        logfunc: Callable,
        *args,
        **kwargs
) -> None:
    """Log a rich renderable to logger

    Args:
        renderable: The rich renderable
        splitline: Whether split the lines or log the entire message
        logfunc: The log function, if message is not the first argument,
            use functools.partial to wrap it
        *args: The arguments to the log function
        **kwargs: The keyword arguments to the log function
    """
    console = Console(file=StringIO())
    console.print(renderable)

    for line in console.file.getvalue().splitlines():
        logfunc(f'[{color}]{line}[/{color}]' if color else line,
                *args,
                **kwargs)

def render_scope(scope: Mapping, title: str) -> RenderableType:
    """Log a mapping to console

    Args:
        scope: The mapping object
        title: The title of the scope
    """
    highlighter = ReprHighlighter()
    items_table = Table.grid(padding=(0, 1), expand=False)
    items_table.add_column(justify="left")

    for key, value in sorted(scope.items()):
        items_table.add_row(
            Text.assemble((key, "scope.key")),
            Text.assemble(('=', 'scope.equals')),
            Pretty(value, highlighter=highlighter, overflow='fold')
        )

    return Panel(
        items_table,
        title=title,
        width=min(DEFAULT_CONSOLE_WIDTH, get_console_width()),
        border_style="scope.border",
        padding=(0, 1),
    )

def pipen_banner() -> RenderableType:
    """The banner for pipen"""
    from . import __version__
    table = Table(width=min(DEFAULT_CONSOLE_WIDTH, get_console_width()),
                  show_header=False,
                  show_edge=False,
                  show_footer=False,
                  show_lines=False,
                  caption=f"version: {__version__}")
    table.add_column(justify='center')
    table.add_row(r"  _____________________________________   __")
    table.add_row(r"  ___  __ \___  _/__  __ \__  ____/__  | / /")
    table.add_row(r" __  /_/ /__  / __  /_/ /_  __/  __   |/ / ")
    table.add_row(r"_  ____/__/ /  _  ____/_  /___  _  /|  /  ")
    table.add_row(r"/_/     /___/  /_/     /_____/  /_/ |_/   ")
    table.add_row("")

    return table

def brief_list(blist: List[int]) -> str:
    """Briefly show an integer list, combine the continuous numbers.

    Args:
        blist: The list

    Returns:
        The string to show for the briefed list.
    """
    ret = []
    for group in consecutive_groups(blist):
        group = list(group)
        if len(group) > 1:
            ret.append(f'{group[0]}-{group[1]}')
        else:
            ret.append(str(group[0]))
    return ', '.join(ret)

def get_mtime(path: PathLike, dir_depth: int = 1) -> float:
    """Get the modification time of a path.

    If path is a directory, try to get the last modification time of the
    contents in the directory at given dir_depth

    Args:
        dir_depth: The depth of the directory to check the
            last modification time

    Returns:
        The last modification time of path
    """
    path = Path(path)
    if not path.is_dir() or dir_depth == 0:
        return path.stat().st_mtime

    mtime = 0
    for file in path.glob('*'):
        mtime = max(mtime, get_mtime(file, dir_depth-1))
    return mtime

def is_subclass(obj: Any, cls: type) -> bool:
    """Tell if obj is a subclass of cls

    Differences with issubclass is that we don't raise Type error if obj
    is not a class

    Args:
        obj: The object to check
        cls: The class to check

    Returns:
        True if obj is a subclass of cls otherwise False
    """
    try:
        return issubclass(obj, cls)
    except TypeError:
        return False

def load_entrypoints(group: str) -> Iterable[Tuple[str, Any]]:
    """Load objects from setuptools entrypoints by given group name

    Args:
        group: The group name of the entrypoints

    Returns:
        An iterable of tuples with name and the loaded object
    """
    for dist in importlib_metadata.distributions(): # pragma: no cover
        for epoint in dist.entry_points:
            if epoint.group != group:
                continue
            obj = epoint.load()
            yield (epoint.name, obj)
