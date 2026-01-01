"""Provide some function for creating and modifying channels (dataframes)"""

from __future__ import annotations

from os import path
from typing import Any, Iterable, List

import pandas
from panpath import PanPath
from pandas import DataFrame
from pipda import register_verb

from .utils import path_is_symlink, path_is_symlink_sync


# ----------------------------------------------------------------
# Creators
class Channel(DataFrame):
    """A DataFrame wrapper with creators"""

    @classmethod
    def create(cls, value: DataFrame | List[Any]) -> DataFrame:
        """Create a channel from a list.

        The second dimension is identified by tuple. if all elements are tuple,
        then a channel is created directly. Otherwise, elements are converted
        to tuples first and channels are created then.

        Examples:
            >>> Channel.create([1, 2, 3]) # 3 rows, 1 column
            >>> Channel.create([(1,2,3)]) # 1 row, 3 columns

        Args:
            value: The value to create a channel

        Returns:
            A channel (dataframe)
        """
        if isinstance(value, DataFrame):
            return value
        if all(isinstance(elem, tuple) for elem in value):
            return cls(value)
        return cls((val,) for val in value)

    @classmethod
    def from_glob(
        cls,
        pattern: str,
        ftype: str = "any",
        sortby: str = "name",
        reverse: bool = False,
    ) -> DataFrame:
        """Create a channel with a glob pattern

        Args:
            ftype: The file type, one of any, link, dir and file
            sortby: How the files should be sorted. One of name, mtime and size
            reverse: Whether sort them in a reversed way.

        Returns:
            The channel
        """

        def sort_key(file: PanPath) -> Any:
            if sortby == "mtime":
                return file.stat().st_mtime
            if sortby == "size":
                return file.stat().st_size

            return str(file)  # sort by name

        def file_filter(file: PanPath) -> bool:
            if ftype == "link":
                return path_is_symlink_sync(file)
            if ftype == "dir":
                return file.is_dir()
            if ftype == "file":
                return file.is_file()
            return True

        pattern = str(pattern)
        parts = pattern.split("/")
        wildcard_index = -1
        for i, part in enumerate(parts):
            if "*" in part or "?" in part or "[" in part:
                wildcard_index = i
                break
        if wildcard_index == -1:
            files: Iterable[PanPath] = (
                [PanPath(pattern)] if file_filter(PanPath(pattern)) else []
            )
            return cls.create([str(file) for file in files])

        base_path = PanPath("/".join(parts[:wildcard_index]))
        sub_pattern = "/".join(parts[wildcard_index:])

        files = (
            PanPath(file)
            for file in base_path.glob(sub_pattern)
            if file_filter(PanPath(file))
        )

        return cls.create(
            [
                str(file)
                for file in sorted(
                    files,
                    key=sort_key if sortby in ("name", "mtime", "size") else None,
                    reverse=reverse,
                )  # type: ignore
            ]
        )

    @classmethod
    async def a_from_glob(
        cls,
        pattern: str,
        ftype: str = "any",
        sortby: str = "name",
        reverse: bool = False,
    ) -> DataFrame:
        """Create a channel with a glob pattern asynchronously

        Args:
            pattern: The glob pattern, supported: "dir1/dir2/*.txt"
            ftype: The file type, one of any, link, dir and file
            sortby: How the files should be sorted. One of name, mtime and size
            reverse: Whether sort them in a reversed way.

        Returns:
            The channel
        """

        async def get_sort_key(file: PanPath, sort_by: str) -> Any:
            if sortby == "mtime":  # pragma: no cover
                return (await file.a_stat()).st_mtime
            if sortby == "size":
                return (await file.a_stat()).st_size

            return str(file)  # sort by name

        async def file_filter(file: PanPath) -> bool:
            if ftype == "link":  # pragma: no cover
                return await path_is_symlink(file)
            if ftype == "dir":  # pragma: no cover
                return await file.a_is_dir()
            if ftype == "file":
                return await file.a_is_file()
            return True

        pattern = str(pattern)
        parts = pattern.split("/")
        wildcard_index = -1
        for i, part in enumerate(parts):
            if "*" in part or "?" in part or "[" in part:
                wildcard_index = i
                break
        if wildcard_index == -1:
            files = [PanPath(pattern)] if await file_filter(PanPath(pattern)) else []
            return cls.create([str(file) for file in files])

        base_path = PanPath("/".join(parts[:wildcard_index]))
        sub_pattern = "/".join(parts[wildcard_index:])

        files = [
            PanPath(file)
            async for file in base_path.a_glob(sub_pattern)
            if await file_filter(PanPath(file))
        ]

        sort_keys = dict(
            [
                (
                    file,
                    await get_sort_key(file, sortby),
                )
                for file in files
            ]
        )

        return cls.create(
            [
                str(file)
                for file in sorted(
                    files,
                    key=(
                        sort_keys.get  # type: ignore[arg-type]
                        if sortby in ("name", "mtime", "size")
                        else None
                    ),
                    reverse=reverse,
                )
            ]
        )

    @classmethod
    def from_pairs(
        cls,
        pattern: str,
        ftype: str = "any",
        sortby: str = "name",
        reverse: bool = False,
    ) -> DataFrame:
        """Create a width=2 channel with a glob pattern

        Args:
            ftype: The file type, one of any, link, dir and file
            sortby: How the files should be sorted. One of name, mtime and size
            reverse: Whether sort them in a reversed way.

        Returns:
            The channel
        """
        mates = cls.from_glob(pattern, ftype, sortby, reverse)
        return pandas.concat(
            (
                mates.iloc[::2].reset_index(drop=True),
                mates.iloc[1::2].reset_index(drop=True),
            ),
            axis=1,
        )

    @classmethod
    async def a_from_pairs(
        cls,
        pattern: str,
        ftype: str = "any",
        sortby: str = "name",
        reverse: bool = False,
    ) -> DataFrame:
        """Create a width=2 channel with a glob pattern

        Args:
            ftype: The file type, one of any, link, dir and file
            sortby: How the files should be sorted. One of name, mtime and size
            reverse: Whether sort them in a reversed way.

        Returns:
            The channel
        """
        mates = await cls.a_from_glob(pattern, ftype, sortby, reverse)
        return pandas.concat(
            (
                mates.iloc[::2].reset_index(drop=True),
                mates.iloc[1::2].reset_index(drop=True),
            ),
            axis=1,
        )

    @classmethod
    def from_csv(cls, *args, **kwargs):
        """Create a channel from a csv file

        Uses pandas.read_csv() to create a channel

        Args:
            *args: and
            **kwargs: Arguments passing to pandas.read_csv()
        """
        return pandas.read_csv(*args, **kwargs)

    @classmethod
    def from_excel(cls, *args, **kwargs):
        """Create a channel from an excel file.

        Uses pandas.read_excel() to create a channel

        Args:
            *args: and
            **kwargs: Arguments passing to pandas.read_excel()
        """
        return pandas.read_excel(*args, **kwargs)

    @classmethod
    def from_table(cls, *args, **kwargs):
        """Create a channel from a table file.

        Uses pandas.read_table() to create a channel

        Args:
            *args: and
            **kwargs: Arguments passing to pandas.read_table()
        """
        return pandas.read_table(*args, **kwargs)


# ----------------------------------------------------------------
# Verbs
@register_verb(DataFrame)
def expand_dir(
    data: DataFrame,
    col: str | int = 0,
    pattern: str = "*",
    ftype: str = "any",
    sortby: str = "name",
    reverse: bool = False,
) -> DataFrame:
    """Expand a Channel according to the files in <col>,
    other cols will keep the same.

    This is only applicable to a 1-row channel.

    Examples:
        >>> ch = channel.create([('./', 1)])
        >>> ch >> expand()
        >>> [['./a', 1], ['./b', 1], ['./c', 1]]

    Args:
        col: the index or name of the column used to expand
        pattern: use a pattern to filter the files/dirs, default: `*`
        ftype: the type of the files/dirs to include
            - 'dir', 'file', 'link' or 'any' (default)
        sortby:  how the list is sorted
            - 'name' (default), 'mtime', 'size'
        reverse: reverse sort.

    Returns:
        The expanded channel
    """
    assert data.shape[0] == 1, "Can only expand a single row DataFrame."
    col_loc = col if isinstance(col, int) else data.columns.get_loc(col)
    full_pattern = f"{data.iloc[0, col_loc]}/{pattern}"
    expanded = Channel.from_glob(
        full_pattern,
        ftype,
        sortby,
        reverse,
    ).iloc[:, 0]
    ret = pandas.concat([data] * expanded.size, axis=0, ignore_index=True)
    ret.iloc[:, col_loc] = expanded.values
    return ret.reset_index(drop=True)


@register_verb(DataFrame)
def collapse_files(data: DataFrame, col: str | int = 0) -> DataFrame:
    """Collapse a Channel according to the files in <col>,
    other cols will use the values in row 0.

    Note that other values in other rows will be discarded.

    Examples:
        >>> ch = channel.create([['./a', 1], ['./b', 1], ['./c', 1]])
        >>> ch >> collapse()
        >>> [['.', 1]]

    Args:
        data: The original channel
        col: the index or name of the column used to collapse on

    Returns:
        The collapsed channel
    """
    assert data.shape[0] > 0, "Cannot collapse on an empty DataFrame."
    col_loc = col if isinstance(col, int) else data.columns.get_loc(col)
    paths = list(data.iloc[:, col_loc])
    compx = path.dirname(path.commonprefix(paths))
    ret = data.iloc[[0], :].copy()
    ret.iloc[0, col_loc] = compx
    return ret
