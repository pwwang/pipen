"""Provide some utilities"""
import logging
from os import PathLike
from pathlib import Path
from typing import Any, List, Optional, Union
# pylint: disable=unused-import
try:
    from functools import cached_property
except ImportError:
    from cached_property import cached_property
# pylint: enable=unused-import
from rich.logging import RichHandler
from more_itertools import consecutive_groups
from simplug import _SimplugContextOnly
from .defaults import LOGGER_NAME, DEFAULT_CONSOLE_WIDTH
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
    # TODO: check name
    log = logging.getLogger(f'pipen.{name}')
    log.addHandler(_logger_handler)

    if level is not None:
        log.setLevel(level.upper() if isinstance(level, str) else level)

    return logging.LoggerAdapter(log, {'plugin_name': name})

logger = get_logger(LOGGER_NAME)

def get_console_width(default: int = DEFAULT_CONSOLE_WIDTH) -> int:
    """Get the console width"""
    try:
        return logger.logger.handlers[0].console.width
    except (AttributeError, IndexError):  # pragma: no cover
        return default

def get_plugin_context(plugins: List[Any]) -> _SimplugContextOnly:
    """Get the plugin context to enable and disable plugins per pipeline

    Args:
        plugins: A list of plugins to enable or a list of names with 'no:'
            as prefix to disable

    Returns:
        The plugin context manager
    """
    if not plugins:
        return None
    no_plugins = [isinstance(plug, str) and plug.startswith('no:')
                  for plug in plugins]
    if any(no_plugins) and not all(no_plugins):
        raise ValueError('Either all plugin names start with "no:" or '
                         'none of them does.')
    if all(no_plugins):
        return plugin.plugins_but_context(
            *(plug[3:] for plug in plugins)
        )
    return plugin.plugins_only_context(*plugins)

def pipen_banner() -> List[str]:
    """The banner for pipen"""
    from . import __version__
    console_width = min(DEFAULT_CONSOLE_WIDTH, get_console_width())
    banner = (
        r"_____________________________________   __",
        r"___  __ \___  _/__  __ \__  ____/__  | / /",
        r"__  /_/ /__  / __  /_/ /_  __/  __   |/ / ",
        r"_  ____/__/ /  _  ____/_  /___  _  /|  /  ",
        r"/_/     /___/  /_/     /_____/  /_/ |_/   "
    )
    ret = []
    for ban in banner:
        ret.append(ban.center(console_width))

    ret.append(f"v{__version__}".center(console_width))
    ret.append("")
    return ret

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
