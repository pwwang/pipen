"""Provide some utilities"""

from __future__ import annotations

import re
import sys
import importlib
import importlib.util
import logging
import shutil
import textwrap
import typing
from itertools import groupby
from operator import itemgetter
from io import StringIO
from os import PathLike, get_terminal_size, environ
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
    Sequence,
    Tuple,
    Type,
)

import diot
import simplug
from yunpath import AnyPath, CloudPath
from rich.console import Console
from rich.logging import RichHandler as _RichHandler
from rich.table import Table
from rich.text import Text
from simplug import SimplugContext

from .defaults import (
    CONSOLE_DEFAULT_WIDTH,
    CONSOLE_WIDTH_WITH_PANEL,
    CONSOLE_WIDTH_SHIFT,
    LOGGER_NAME,
)
from .version import __version__

from importlib import metadata as importlib_metadata

if TYPE_CHECKING:  # pragma: no cover
    import pandas
    from rich.segment import Segment
    from rich.console import RenderableType
    from xqute.path import SpecPath

    from .pipen import Pipen
    from .proc import Proc
    from .procgroup import ProcGroup

LOADING_ARGV0 = "@pipen"


class RichHandler(_RichHandler):
    """Subclass of rich.logging.RichHandler, showing log levels as a single
    character"""

    def get_level_text(self, record: logging.LogRecord) -> Text:
        """Get the level name from the record.

        Args:
            record: LogRecord instance.

        Returns:
            Text: A tuple of the style and level name.
        """
        level_name = record.levelname
        level_text = Text.styled(
            level_name[0].upper(), f"logging.level.{level_name.lower()}"
        )
        return level_text


class RichConsole(Console):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        try:
            self._width = get_terminal_size().columns
        except (AttributeError, ValueError, OSError):  # maybe not a terminal
            if environ.get("JUPYTER_COLUMNS") is not None:  # pragma: no cover
                self._width = int(environ.get("JUPYTER_COLUMNS"))
            elif environ.get("COLUMNS") is not None:  # pragma: no cover
                self._width = int(environ.get("COLUMNS"))
            else:
                self._width = CONSOLE_DEFAULT_WIDTH

    def _render_buffer(self, buffer: Iterable[Segment]) -> str:
        out = super()._render_buffer(buffer)
        return out.rstrip() + "\n"


logging.lastResort = logging.NullHandler()  # type: ignore
logger_console = RichConsole()
_logger_handler = RichHandler(
    show_path=False,
    show_level=True,
    console=logger_console,
    rich_tracebacks=True,
    omit_repeated_times=False,  # rich 10+
    markup=True,
    log_time_format="%m-%d %H:%M:%S",
    tracebacks_extra_lines=0,
    tracebacks_suppress=[simplug, diot, typing],
)
_logger_handler.setFormatter(
    logging.Formatter("[purple]%(plugin_name)-7s[/purple] %(message)s")
)


def _excepthook(
    type_: Type[BaseException],
    value: BaseException,
    traceback: Any,
) -> None:
    """The excepthook for pipen, to show rich traceback"""
    if issubclass(type_, KeyboardInterrupt):  # pragma: no cover
        logger.error("")
        logger.error("Interrupted by user")
        return

    print("", file=sys.stderr)
    _excepthook.oldhook(type_, value, traceback)


_excepthook.oldhook = sys.excepthook
sys.excepthook = _excepthook


def get_logger(
    name: str = LOGGER_NAME,
    level: str | int = None,
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


def desc_from_docstring(
    obj: Type[Pipen | Proc],
    base: Type[Pipen | Proc],
) -> str:
    """Get the description from docstring

    Only extract the summary.

    Args:
        obj: The object with docstring

    Returns:
        The summary as desc
    """
    if not obj.__doc__:
        # If the docstring is empty, use the base's docstring
        # Get the base from mro
        bases = [
            cls
            for cls in obj.__mro__
            if is_subclass(cls, base) and cls != base and cls != obj
        ]
        if not bases:
            return None

        return desc_from_docstring(bases[0], base)

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
    depth: int = 0,
) -> Mapping[str, Any]:
    """Update the new dict to the parent, but make sure parent does not change

    Args:
        parent: The parent dictionary
        new: The new dictionary
        depth: The depth to be copied. 0 for updating to the deepest level.

    Examples:
        >>> parent = {"a": {"b": 1}}
        >>> new = {"a": {"c": 2}}
        >>> update_dict(parent, new)
        >>> # {"a": {"b": 1, "c": 2}}

    Returns:
        The updated dictionary or None if both parent and new are None.
    """
    if parent is None and new is None:
        return None

    out = (parent or {}).copy()
    for key, val in (new or {}).items():
        if (
            key not in out
            or not isinstance(val, dict)
            or not isinstance(out[key], dict)
            or depth == 1
        ):
            out[key] = val
        else:
            out[key] = update_dict(out[key], val, depth - 1)

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


def get_logpanel_width() -> int:
    """Get the width of the log content

    Args:
        max_width: The maximum width to return
            Note that it's not the console width. With console width, you
            have to subtract the width of the log meta info
            (CONSOLE_WIDTH_SHIFT).

    Returns:
        The width of the log content
    """
    return (
        min(
            logger_console.width,
            CONSOLE_WIDTH_WITH_PANEL,
        )
        - CONSOLE_WIDTH_SHIFT
    )


def log_rich_renderable(
    renderable: RenderableType,
    color: str | None,
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
    console = Console(
        file=StringIO(),
        width=logger_console.width - CONSOLE_WIDTH_SHIFT,
    )
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
    for _, g in groupby(enumerate(blist), lambda x: x[0] - x[1]):
        list_group = list(map(itemgetter(1), g))
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
        width=get_logpanel_width(),
        show_header=False,
        show_edge=False,
        show_footer=False,
        show_lines=False,
        caption=f"version: {__version__}",
    )
    table.add_column(justify="center")
    table.add_row(r"   _____________________________________   __")
    table.add_row(r"   ___  __ \___  _/__  __ \__  ____/__  | / /")
    table.add_row(r"  __  /_/ /__  / __  /_/ /_  __/  __   |/ / ")
    table.add_row(r" _  ____/__/ /  _  ____/_  /___  _  /|  /  ")
    table.add_row(r"/_/     /___/  /_/     /_____/  /_/ |_/   ")
    table.add_row("")

    return table


def get_mtime(
    path: str | PathLike | CloudPath | SpecPath,
    dir_depth: int = 1,
) -> float:
    """Get the modification time of a path.
    If path is a directory, try to get the last modification time of the
    contents in the directory at given dir_depth
    Args:
        dir_depth: The depth of the directory to check the
            last modification time
    Returns:
        The last modification time of path
    """
    path = getattr(path, "path", path)

    mtime = 0.0
    path = AnyPath(path)
    if not path.exists():
        return mtime

    if not path_is_symlink(path):
        if dir_depth == 0 or not path.is_dir():
            return path.stat().st_mtime

        for file in path.iterdir():
            mtime = max(mtime, get_mtime(file, dir_depth - 1))

        return mtime

    # Is it a real symlink or fake
    if isinstance(path, Path) and path.is_symlink():
        if dir_depth == 0 or not path.is_dir():
            return path.lstat().st_mtime

        for file in path.iterdir():
            mtime = max(mtime, get_mtime(file, dir_depth - 1))

        return mtime

    # Fake symlink
    dest = path.read_text().removeprefix("symlink:")
    dpath = AnyPath(dest)
    if dir_depth == 0 or not dpath.is_dir():
        try:
            return dpath.stat().st_mtime
        except Exception:
            return path.stat().st_mtime

    for file in dpath.iterdir():
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


def load_entrypoints(group: str) -> Iterable[Tuple[str, Any]]:  # pragma: no cover
    """Load objects from setuptools entrypoints by given group name

    Args:
        group: The group name of the entrypoints

    Returns:
        An iterable of tuples with name and the loaded object
    """
    try:
        eps = importlib_metadata.entry_points(group=group)
    except TypeError:
        eps = importlib_metadata.entry_points().get(group, [])  # type: ignore

    yield from ((ep.name, ep.load()) for ep in eps)


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


def make_df_colnames_unique_inplace(thedf: pandas.DataFrame) -> None:
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
        base
        for base in klass.__bases__
        if issubclass(base, abc_base) and value_getter(base) == value
    ]
    if not bases:
        return klass

    return get_base(bases[0], abc_base, value, value_getter)


def mark(**kwargs) -> Callable[[type], type]:
    """Mark a class (e.g. Proc) with given kwargs as metadata

    These marks will not be inherited by the subclasses if the class is
    a subclass of `Proc` or `ProcGroup`.

    Args:
        **kwargs: The kwargs to mark the proc

    Returns:
        The decorator
    """

    def decorator(cls: type) -> type:
        if not getattr(cls, "__meta__", None):
            cls.__meta__ = {}

        cls.__meta__.update(kwargs)
        return cls

    return decorator


def get_marked(cls: type, mark_name: str, default: Any = None) -> Any:
    """Get the marked value from a proc

    Args:
        cls: The proc
        mark_name: The mark name
        default: The default value if the mark is not found

    Returns:
        The marked value
    """
    if not getattr(cls, "__meta__", None):
        return default

    return cls.__meta__.get(mark_name, default)


def is_valid_name(name: str) -> bool:
    """Check if a name is valid for a proc or pipen

    Args:
        name: The name to check

    Returns:
        True if valid, otherwise False
    """
    return re.match(r"^[\w.-]+$", name) is not None


def _get_obj_from_spec(spec: str) -> Any:
    """Get the object from a spec like `<module[.submodule]>:name` or
    `/path/to/script.py:name`

    Args:
        spec: The spec

    Returns:
        The object

    Raises:
        AttributeError: If name cannot be found in the module
    """
    modpath, sep, name = spec.rpartition(":")
    if sep != ":":
        raise ValueError(
            f"Invalid specification: {spec}.\n"
            "It must be in the format '<module[.submodule]>:name' or \n"
            "'/path/to/spec.py:name'"
        )

    path = Path(modpath)
    if path.is_file():
        mspec = importlib.util.spec_from_file_location(path.stem, modpath)
        module = importlib.util.module_from_spec(mspec)
        mspec.loader.exec_module(module)
    else:
        module = importlib.import_module(modpath)

    return getattr(module, name)


async def load_pipeline(
    obj: str | Type[Proc] | Type[ProcGroup] | Type[Pipen] | Pipen,
    argv0: str | None = None,
    argv1p: Sequence[str] | None = None,
    **kwargs: Any,
) -> Pipen:
    """Load a pipeline from a Pipen, Proc or ProcGroup object

    It does not only load the Pipen object or convert the Proc/ProcGroup
    object to Pipen, but also build the process relationships. So that we
    can access `pipeline.procs` and `requires/nexts` of each proc.

    To avoid running the pipeline and notify the plugins that this is just
    for loading the pipeline, `sys.argv[0]` is set to `@pipen`.

    Args:
        obj: The Pipen, Proc or ProcGroup object. It can also be a string in
            the format of `part1:part2` to load the pipeline, where part1 is
            a path to a python file or package directory, and part2 is the name
            of the proc, procgroup or pipeline to load.
            It should be able to be loaded by `getattr(module, part2)`, where
            module is loaded from `part1`.
        argv0: The value to replace sys.argv[0]. "@pipen" will be used
            by default.
        argv1p: The values to replace sys.argv[1:]. Do not replace by default.
        kwargs: The kwargs to pass to the Pipen constructor

    Returns:
        The loaded Pipen object

    Raises:
        TypeError: If obj or loaded obj is not a Pipen, Proc or ProcGroup
        object
    """
    from .pipen import Pipen
    from .proc import Proc
    from .procgroup import ProcGroup

    old_argv = sys.argv
    if argv0 is None:
        # Set it at runtime to allow LOADING_ARGV0 to be monkey-patched
        argv0 = LOADING_ARGV0
    if argv1p is None:
        # Set it at runtime to adopt sys.argv changes
        argv1p = sys.argv[1:]
    sys.argv = [argv0] + list(argv1p)

    try:
        if isinstance(obj, str):
            obj = _get_obj_from_spec(obj)
        if isinstance(obj, Pipen) or (
            isinstance(obj, type) and issubclass(obj, (Pipen, Proc, ProcGroup))
        ):
            pass
        else:
            raise TypeError(
                "Expected a Pipen, Proc, ProcGroup class, or a Pipen object, "
                f"got {type(obj)}"
            )

        pipeline = obj
        if isinstance(obj, type) and issubclass(obj, Proc):
            kwargs.setdefault("name", f"{obj.name}Pipeline")
            pipeline = Pipen(**kwargs).set_starts(obj)

        elif isinstance(obj, type) and issubclass(obj, ProcGroup):
            pipeline = obj().as_pipen(**kwargs)  # type: ignore

        elif isinstance(obj, type) and issubclass(obj, Pipen):
            # Avoid "pipeline" to be used as pipeline name by varname
            (pipeline,) = (obj(**kwargs),)  # type: ignore

        elif isinstance(obj, Pipen):
            pipeline._kwargs.update(kwargs)  # type: ignore

        # Initialize the pipeline so that the arguments definied by
        # other plugins (i.e. pipen-args) to take in place.
        pipeline.workdir = Path(pipeline.config.workdir).joinpath(  # type: ignore
            kwargs.get("name", pipeline.name)
        )
        await pipeline._init()  # type: ignore
        pipeline.workdir.mkdir(parents=True, exist_ok=True)  # type: ignore
        pipeline.build_proc_relationships()  # type: ignore
    finally:
        sys.argv = old_argv

    return pipeline  # type: ignore


def is_loading_pipeline(*flags: str, argv: Sequence[str] | None = None) -> bool:
    """Check if we are loading the pipeline. Works only when
    `argv0` is "@pipen" while loading the pipeline.

    Note if you are using this function at compile time, make
    sure you load your pipeline using the string form (`part1:part2`)
    See more with `load_pipline()`.

    Args:
        *flags: Additional flags to check in sys.argv (e.g. "-h", "--help")
            to determine if we are loading the pipeline
        argv: The arguments to check. sys.argv is used by default.
            Note that the first argument should be included in the check.
            You could typically pass `[sys.argv[0], *your_args]` to this if you want
            to check if `sys.argv[0]` is "@pipen" or `your_args` contains some flags.

    Returns:
        True if we are loading the pipeline (argv[0] == "@pipen"),
        otherwise False
    """
    if argv is None:
        argv = sys.argv

    if len(argv) > 0 and argv[0] == LOADING_ARGV0:
        return True

    if flags:
        return any(flag in argv for flag in flags)

    return False  # pragma: no cover


def path_is_symlink(path: Path | CloudPath | SpecPath) -> bool:
    """Check if a path is a symlink.

    CloudPath.is_symlink() is not implemented yet, so we need to check
    it manually.

    Args:
        path: The path to check

    Returns:
        True if the path is a symlink, otherwise False
    """
    path = getattr(path, "path", path)
    if isinstance(path, Path):
        if path.is_symlink():
            return True

    if not path.exists():
        return False

    # Check if the path is a fake symlink file
    try:
        return path.read_text().startswith("symlink:")
    except Exception:
        return False


def path_symlink_to(
    src: Path | CloudPath | SpecPath,
    dst: Path | CloudPath | SpecPath,
    target_is_directory: bool = False,
) -> None:
    """Create a symbolic link pointing to src named dst.

    Args:
        src: The source path
        dst: The destination path
        target_is_directory: If True, the symbolic link will be to a directory.
    """
    src = getattr(src, "path", src)
    dst = getattr(dst, "path", dst)
    if isinstance(dst, CloudPath) or isinstance(src, CloudPath):
        # Create a fake symlink file for cloud paths
        src.write_text(f"symlink:{dst}")
    else:
        src.symlink_to(dst, target_is_directory=target_is_directory)
