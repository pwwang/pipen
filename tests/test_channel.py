import os
from io import StringIO
from pathlib import Path
from math import ceil

import pytest  # noqa
from pipen.channel import Channel, expand_dir, collapse_files
from datar.tibble import tibble

from pandas import DataFrame

from .helpers import BUCKET


def test_create():
    assert isinstance(Channel.create(DataFrame([[1]])), DataFrame)


def test_from_glob():
    glob = Path(__file__).parent / "test_*.py"
    glob_files = list(Path(__file__).parent.glob("test_*.py"))
    ch = Channel.from_glob(glob)
    assert ch.shape == (len(glob_files), 1)


def test_from_glob_sortby_mtime(tmp_path):
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"
    file3 = tmp_path / "file3.txt"
    file1.touch()
    file2.touch()
    file3.touch()
    os.utime(file1, (1000, 1000))
    os.utime(file2, (3000, 3000))
    os.utime(file3, (2000, 2000))
    ch = Channel.from_glob(tmp_path / "*.txt", sortby="mtime")
    assert ch.iloc[0, 0] == str(file1)
    assert ch.iloc[1, 0] == str(file3)
    assert ch.iloc[2, 0] == str(file2)


def test_from_glob_sortby_size(tmp_path):
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"
    file3 = tmp_path / "file3.txt"
    file1.write_text("1")
    file2.write_text("222")
    file3.write_text("33")
    ch = Channel.from_glob(tmp_path / "*.txt", sortby="size")
    assert ch.iloc[0, 0] == str(file1)
    assert ch.iloc[1, 0] == str(file3)
    assert ch.iloc[2, 0] == str(file2)


def test_from_glob_filter_link(tmp_path):
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"
    file3 = tmp_path / "file3.txt"
    file1.touch()
    file2.symlink_to(file1)
    file3.symlink_to(file1)
    ch = Channel.from_glob(tmp_path / "*.txt", ftype="link")
    assert ch.shape == (2, 1)
    assert ch.iloc[0, 0] == str(file2)
    assert ch.iloc[1, 0] == str(file3)


def test_from_glob_filter_dir_file(tmp_path):
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"
    file3 = tmp_path / "file3.txt"
    file1.mkdir()
    file2.touch()
    file3.mkdir()

    ch = Channel.from_glob(tmp_path / "*.txt", ftype="dir")
    assert ch.shape == (2, 1)
    assert ch.iloc[0, 0] == str(file1)
    assert ch.iloc[1, 0] == str(file3)

    ch = Channel.from_glob(tmp_path / "*.txt", ftype="file")
    assert ch.shape == (1, 1)
    assert ch.iloc[0, 0] == str(file2)


def test_from_glob_cloudpath():
    ch = Channel.from_glob(f"{BUCKET}/pipen-test/channel/test*.txt")
    assert ch.shape == (3, 1)
    assert ch.iloc[0, 0] == f"{BUCKET}/pipen-test/channel/test1.txt"
    assert ch.iloc[1, 0] == f"{BUCKET}/pipen-test/channel/test2.txt"
    assert ch.iloc[2, 0] == f"{BUCKET}/pipen-test/channel/test3.txt"


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
