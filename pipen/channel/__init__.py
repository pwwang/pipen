"""Provide some function for creating and modifying channels(dataframes)"""
from typing import Any, List, Union
from os import path
from glob import glob

import pandas
from pandas import DataFrame
from siuba.siu import _

__all__ = ('_', 'create', 'from_glob', 'from_pairs',
           'from_csv', 'from_excel', 'from_table')

def create(value: Union[DataFrame, List[Any]]) -> DataFrame:
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
        return DataFrame(value)
    return DataFrame((val, ) for val in value)

def from_glob(pattern,
              ftype='any',
              sortby='name',
              reverse=False) -> DataFrame:
    """Create a channel with a glob pattern

    Args:
        ftype: The file type, one of any, link, dir and file
        sortby: How the files should be sorted. One of name, mtime and size
        reverse: Whether sort them in a reversed way.

    Returns:
        The channel
    """
    sort_key = (str if sortby == 'name'
                else path.getmtime if sortby == 'mtime'
                else path.getsize if sortby == 'size'
                else None)
    file_filter = (path.islink if ftype == 'link'
                    else path.isdir if ftype == 'dir'
                    else path.isfile if ftype == 'file'
                    else None)
    files = (file for file in glob(str(pattern))
                if not file_filter or file_filter(file))
    return create(sorted(files, key=sort_key, reverse=reverse))

def from_pairs(pattern,
               ftype='any',
               sortby='name',
               reverse=False) -> DataFrame:
    """Create a width=2 channel with a glob pattern

    Args:
        ftype: The file type, one of any, link, dir and file
        sortby: How the files should be sorted. One of name, mtime and size
        reverse: Whether sort them in a reversed way.

    Returns:
        The channel
    """
    mates = from_glob(pattern, ftype, sortby, reverse)
    return pandas.concat(
        (mates.iloc[::2].reset_index(drop=True),
         mates.iloc[1::2].reset_index(drop=True)),
        axis=1
    )

from_csv = pandas.read_csv
from_csv.__doc__ = ("Create a channel from a csv file.\n\n"
                    f"{pandas.read_csv.__doc__}")
from_excel = pandas.read_excel
from_excel.__doc__ = ("Create a channel from an excel file.\n\n"
                      f"{pandas.read_excel.__doc__}")
from_table = pandas.read_table
from_table.__doc__ = ("Create a channel from a table file.\n\n"
                      f"{pandas.read_table.__doc__}")
