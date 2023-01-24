from io import StringIO
from pathlib import Path
from math import ceil

import pytest  # noqa
from pipen.channel import Channel, expand_dir, collapse_files
from datar.tibble import tibble

from pandas import DataFrame


def test_create():
    assert isinstance(Channel.create(DataFrame([[1]])), DataFrame)


def test_from_glob():
    glob = Path(__file__).parent / "test_*.py"
    glob_files = list(Path(__file__).parent.glob("test_*.py"))
    ch = Channel.from_glob(glob)
    assert ch.shape == (len(glob_files), 1)


def test_from_pairs():
    glob = Path(__file__).parent / "test_*.py"
    glob_files = list(Path(__file__).parent.glob("test_*.py"))
    ch = Channel.from_pairs(glob)
    assert ch.shape == (ceil(len(glob_files) / 2.0), 2)


def test_expand_dir_collapse_files():
    ch0 = Channel.create([(Path(__file__).parent.as_posix(), 1)])
    ch1 = ch0 >> expand_dir(pattern="test_*.py")
    glob_files = list(Path(__file__).parent.glob("test_*.py"))
    assert ch1.shape == (len(glob_files), 2)

    ch2 = ch1 >> collapse_files()
    assert ch2.equals(ch0)


def test_from_csv(tmp_path):
    df = tibble(a=[1, 2], b=[3, 4])
    df.to_csv(tmp_path / "input.csv", index=False)
    ch = Channel.from_csv(tmp_path / "input.csv")
    assert ch.equals(df)


def test_from_excel(tmp_path):
    df = tibble(a=[1, 2], b=[3, 4])
    df.to_excel(tmp_path / "input.xls", index=False)
    ch = Channel.from_excel(tmp_path / "input.xls")
    assert ch.equals(df)


def test_from_table():
    df = StringIO("a b\n1 3\n2 4\n")
    ch = Channel.from_table(df, sep=" ")
    exp = tibble(a=[1, 2], b=[3, 4])
    assert ch.equals(exp)
