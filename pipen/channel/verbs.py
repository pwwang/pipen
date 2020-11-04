"""Verbs for pipen channels"""
from os import path
from typing import Union
import pandas
from pandas import DataFrame
import siuba
from siuba.dply.verbs import singledispatch2
# pylint: disable=redefined-builtin,wildcard-import,unused-wildcard-import
from siuba.dply.verbs import *
from . import from_glob

__all__ = tuple(siuba.dply.verbs.__all__) + ('expand_dir', 'collapse_files')

# some useful pipe verbs
@singledispatch2(DataFrame)
def expand_dir(data: DataFrame,
               col: Union[str, int] = 0,
               pattern: str = '*',
               ftype: str = 'any',
               sortby: str = 'name',
               reverse: bool = False) -> DataFrame:
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
    expanded = from_glob(full_pattern, ftype, sortby, reverse)
    ret = pandas.concat([data] * expanded.size, axis=0)
    ret[data.columns[col_loc]] = expanded.values
    ret.reset_index(drop=True)
    return ret

@singledispatch2(DataFrame)
def collapse_files(data: DataFrame,
                   col: Union[str, int] = 0) -> DataFrame:
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
