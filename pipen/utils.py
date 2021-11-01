"""Provide some utilities"""
import logging
import textwrap
from io import StringIO
from os import PathLike
from collections import defaultdict
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    DefaultDict,
    Iterable,
    List,
    Mapping,
    Tuple,
    Type,
    Union,
)

if TYPE_CHECKING:  # pragma: no cover
    import pandas

try:  # pragma: no cover
    from functools import cached_property
except ImportError:  # pragma: no cover
    # python 3.7
    from cached_property import cached_property

try:  # pragma: no cover
    from importlib import metadata as importlib_metadata
except ImportError:  # pragma: no cover
    # python 3.7
    import importlib_metadata

from more_itertools import consecutive_groups
from rich.console import Console, RenderableType
from rich.logging import RichHandler as _RichHandler
from rich.table import Table
from rich.text import Text
from simplug import SimplugContext

from .defaults import CONSOLE_WIDTH, CONSOLE_WIDTH_SHIFT, LOGGER_NAME
from .exceptions import ConfigurationError
from .pluginmgr import plugin
from .version import __version__


class RichHandler(_RichHandler):
    """Subclass of rich.logging.RichHandler, showing log levels as a single
    character"""

    def get_level_text(self, record: logging.LogRecord) -> Text:
        """Get the level name from the record.

        Args:
            record (LogRecord): LogRecord instance.

        Returns:
            Text: A tuple of the style and level name.
        """
        level_name = record.levelname
        level_text = Text.styled(
            level_name[0].upper(), f"logging.level.{level_name.lower()}"
        )
        return level_text


_logger_handler = RichHandler(
    show_path=False,
    show_level=True,
    console=Console(),
    rich_tracebacks=True,
    omit_repeated_times=False,  # rich 10+
    markup=True,
)
_logger_handler.setFormatter(
    logging.Formatter("[purple]%(plugin_name)-7s[/purple] %(message)s")
)


def get_logger(
    name: str = LOGGER_NAME,
    level: Union[str, int] = None,
) -> logging.LoggerAdapter:
    """Get the logger by given plugin name

    Args:
        level: The initial level of the logger

    Returns:
        The logger
    """
    log = logging.getLogger(f"pipen.{name}")
    log.addHandler(_logger_handler)

    if level is not None:
        log.setLevel(level.upper() if isinstance(level, str) else level)

    return logging.LoggerAdapter(log, {"plugin_name": name})


logger = get_logger()


def desc_from_docstring(obj: Any) -> str:
    """Get the description from docstring

    Only extract the summary.

    Args:
        obj: The object with docstring

    Returns:
        The summary as desc
    """
    if not obj.__doc__:  # pragma: no cover
        return None

    started: bool = False
    out: List[str] = []
    for line in obj.__doc__.splitlines():
        line = line.strip()
        if not started and not line:
            continue
        if not started:
            out.append(line)
            started = True
        elif line:
            out.append(line)
        else:
            break

    return " ".join(out)


def update_dict(
    parent: Mapping[str, Any],
    new: Mapping[str, Any],
) -> Mapping[str, Any]:
    """Update the new dict to the parent, but make sure parent does not change

    Args:
        parent: The parent dictionary
        new: The new dictionary

    Returns:
        The updated dictionary or None if both parent and new are None.
    """
    if parent is None and new is None:
        return None

    out = (parent or {}).copy()
    out.update(new or {})
    return out


def strsplit(
    string: str,
    sep: str,
    maxsplit: int = -1,
    trim: str = "both",
) -> List[str]:
    """Split the string, with the ability to trim each part."""
    parts = string.split(sep, maxsplit=maxsplit)
    if trim is None:
        return parts
    if trim == "left":
        return [part.lstrip() for part in parts]
    if trim == "right":
        return [part.rstrip() for part in parts]

    return [part.strip() for part in parts]


def get_shebang(script: str) -> str:
    """Get the shebang of the script

    Args:
        script: The script string

    Returns:
        None if the script does not contain a shebang, otherwise the shebang
        without `#!` prefix
    """
    script = script.lstrip()
    if not script.startswith("#!"):
        return None

    if "\n" not in script:
        return script[2:].strip()

    shebang_line, _ = strsplit(script, "\n", 1)
    return shebang_line[2:].strip()


def ignore_firstline_dedent(text: str) -> str:
    """Like textwrap.dedent(), but ignore first empty lines

    Args:
        text: The text the be dedented

    Returns:
        The dedented text
    """
    out = []
    started = False
    for line in text.splitlines():
        if not started and not line.strip():
            continue
        if not started:
            started = True
        out.append(line)

    return textwrap.dedent("\n".join(out))


def copy_dict(dic: Mapping[str, Any], depth: int = 1) -> Mapping[str, Any]:
    """Deep copy a dict

    Args:
        dic: The dict to be copied
        depth: The depth to be deep copied

    Returns:
        The deep-copied dict
    """
    if depth <= 1:
        return dic.copy()

    return {
        key: copy_dict(val, depth - 1) if isinstance(val, dict) else val
        for key, val in dic.items()
    }


def get_console_width(
    default: int = CONSOLE_WIDTH,
    shift: int = CONSOLE_WIDTH_SHIFT,
) -> int:
    """Get the console width

    Args:
        default: The default console width if failed to get
        shift: The shift to subtract from the width
            as we have time, level, plugin name in log

    Returns:
        The width of the console
    """
    try:
        return logger.logger.handlers[0].console.width - shift
    except (AttributeError, IndexError):  # pragma: no cover
        return default - shift


def get_plugin_context(plugins: List[Any]) -> SimplugContext:
    """Get the plugin context to enable and disable plugins per pipeline

    Args:
        plugins: A list of plugins to enable or a list of names with 'no:'
            as prefix to disable

    Returns:
        The plugin context manager
    """
    if plugins is None:  # pragma: no cover
        return plugin.plugins_only_context(None)

    no_plugins = [
        isinstance(plug, str) and plug.startswith("no:") for plug in plugins
    ]
    if any(no_plugins) and not all(no_plugins):
        raise ConfigurationError(
            'Either all plugin names start with "no:" or ' "none of them does."
        )
    if all(no_plugins):
        return plugin.plugins_but_context(plug[3:] for plug in plugins)

    return plugin.plugins_only_context(plugins)


def log_rich_renderable(
    renderable: RenderableType,
    color: str,
    logfunc: Callable,
    *args: Any,
    **kwargs: Any,
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
        logfunc(
            f"[{color}]{line}[/{color}]" if color else line,
            *args,
            **kwargs,
        )


def brief_list(blist: List[int]) -> str:
    """Briefly show an integer list, combine the continuous numbers.

    Args:
        blist: The list

    Returns:
        The string to show for the briefed list.
    """
    ret = []
    for group in consecutive_groups(blist):
        list_group = list(group)
        if len(list_group) > 1:
            ret.append(f"{list_group[0]}-{list_group[-1]}")
        else:
            ret.append(str(list_group[0]))
    return ", ".join(ret)


def pipen_banner() -> RenderableType:
    """The banner for pipen

    Returns:
        The banner renderable
    """
    table = Table(
        width=min(CONSOLE_WIDTH, get_console_width()),
        show_header=False,
        show_edge=False,
        show_footer=False,
        show_lines=False,
        caption=f"version: {__version__}",
    )
    table.add_column(justify="center")
    table.add_row(r"  _____________________________________   __")
    table.add_row(r"  ___  __ \___  _/__  __ \__  ____/__  | / /")
    table.add_row(r" __  /_/ /__  / __  /_/ /_  __/  __   |/ / ")
    table.add_row(r"_  ____/__/ /  _  ____/_  /___  _  /|  /  ")
    table.add_row(r"/_/     /___/  /_/     /_____/  /_/ |_/   ")
    table.add_row("")

    return table


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

    mtime = 0.0
    for file in path.glob("*"):
        mtime = max(mtime, get_mtime(file, dir_depth - 1))
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
    for dist in importlib_metadata.distributions():  # pragma: no cover
        for epoint in dist.entry_points:
            if epoint.group != group:
                continue
            obj = epoint.load()
            yield (epoint.name, obj)


def truncate_text(text: str, width: int, end: str = "…") -> str:
    """Truncate a text not based on words/whitespaces
    Otherwise, we could use textwrap.shorten.

    Args:
        text: The text to be truncated
        width: The max width of the the truncated text
        end: The end string of the truncated text
    Returns:
        The truncated text with end appended.
    """
    if len(text) <= width:
        return text

    return text[: (width - len(end))] + end


def make_df_colnames_unique_inplace(thedf: "pandas.DataFrame") -> None:
    """Make the columns of a data frame unique

    Args:
        thedf: The data frame
    """
    col_counts: DefaultDict = defaultdict(lambda: 0)
    new_cols = []
    for col in thedf.columns:
        if col_counts[col] == 0:
            new_cols.append(col)
        else:
            new_cols.append(f"{col}_{col_counts[col]}")
        col_counts[col] += 1
    thedf.columns = new_cols


def get_base(
    klass: Type,
    abc_base: Type,
    value: Any,
    value_getter: Callable,
) -> Type:
    """Get the base class where the value was first defined

    Args:
        klass: The class
        abc_base: The very base class to check in __bases__
        value: The value to check
        value_getter: How to get the value from the class

    Returns:
        The base class
    """
    bases = [
        base for base in klass.__bases__
        if issubclass(base, abc_base) and value_getter(base) == value
    ]
    if not bases:
        return klass

    return get_base(bases[0], abc_base, value, value_getter)
