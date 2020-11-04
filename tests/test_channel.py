from pathlib import Path
from math import ceil
import pytest
from pipen.channel import *
from pipen.channel import verbs
from pipen.channel import vector

from pandas import DataFrame

def test_create():
    assert isinstance(create(DataFrame([[1]])), DataFrame)

def test_from_glob():
    glob = Path(__file__).parent / 'test_*.py'
    glob_files = list(Path(__file__).parent.glob('test_*.py'))
    ch = from_glob(glob)
    assert ch.shape == (len(glob_files), 1)

def test_from_pairs():
    glob = Path(__file__).parent / 'test_*.py'
    glob_files = list(Path(__file__).parent.glob('test_*.py'))
    ch = from_pairs(glob)
    assert ch.shape == (ceil(len(glob_files) / 2.0), 2)

def test_expand_dir_collapse_files():
    ch0 = create([(Path(__file__).parent.as_posix(), 1)])
    ch1 = ch0 >> verbs.expand_dir(pattern='test_*.py')
    glob_files = list(Path(__file__).parent.glob('test_*.py'))
    assert ch1.shape == (len(glob_files), 2)

    ch2 = ch1 >> verbs.collapse_files()
    assert ch2.equals(ch0)
