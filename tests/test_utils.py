from pathlib import Path

import pytest
import pipen
from yunpath import CloudPath
from pipen.utils import (
    brief_list,
    desc_from_docstring,
    get_logger,
    get_mtime,
    get_shebang,
    ignore_firstline_dedent,
    strsplit,
    truncate_text,
    update_dict,
    copy_dict,
    mark,
    get_marked,
    _get_obj_from_spec,
    load_pipeline,
    path_is_symlink,
    path_symlink_to,
)
from pipen.proc import Proc
from pipen.procgroup import ProcGroup
from pipen.exceptions import ConfigurationError

from .helpers import BUCKET

HERE = Path(__file__).parent.resolve()


@pytest.mark.forked
def test_get_logger(caplog):
    logger = get_logger("test", "info")
    logger.debug("debug message")
    assert "debug message" not in caplog.text


@pytest.mark.forked
def test_brief_list():
    assert brief_list([1]) == "1"
    assert brief_list([1, 2, 3]) == "1-3"


@pytest.mark.forked
async def test_get_mtime_dir():
    package_dir = Path(pipen.__file__).parent
    mtime = await get_mtime(package_dir, 2)
    assert mtime > 0


@pytest.mark.forked
async def test_get_mtime_symlink_dir(tmp_path):
    tmp_path = PanPath(tmp_path)
    dir = tmp_path / "dir"
    dir.mkdir()
    file = dir / "file"
    file.touch()
    link = tmp_path / "link"
    link.symlink_to(dir)
    mtime = await get_mtime(link, 2)
    assert mtime > 0


@pytest.mark.forked
async def test_get_mtime_cloud_file():
    file = PanPath(f"{BUCKET}/pipen-test/channel/test1.txt")
    mtime = await get_mtime(file)
    assert mtime > 0


@pytest.mark.forked
async def test_get_mtime_symlink_to_cloud_dir(tmp_path):
    tmp_path = PanPath(tmp_path)
    link = tmp_path / "link"
    await path_symlink_to(link, PanPath(f"{BUCKET}/pipen-test/channel"))
    # get the mtime of the link itself
    lmtime = await get_mtime(link, 0)
    # get the mtime of the target dir, this should be older than the link mtime
    mtime = await get_mtime(link)
    assert mtime < lmtime


# @pytest.mark.forked
async def test_get_mtime_cloud_symlink_to_cloud_dir():
    link = PanPath(f"{BUCKET}/pipen-test/link_to_channel")
    await path_symlink_to(link, PanPath(f"{BUCKET}/pipen-test/channel"))
    # get the mtime of the link itself
    lmtime = await get_mtime(link, 0)
    # get the mtime of the target dir, this should be older than the link mtime
    mtime = await get_mtime(link)
    assert mtime < lmtime


@pytest.mark.forked
def test_desc_from_docstring():
    class Base:
        ...

    class Obj1(Base):
        """

        abc
        def

        """

    desc = desc_from_docstring(Obj1, Base)
    assert desc == "abc def"


@pytest.mark.forked
def test_update_dict():
    assert update_dict(None, None) is None
    assert update_dict({}, None) == {}
    assert update_dict(None, {}) == {}
    assert update_dict({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}
    assert update_dict({"a": 1}, {"a": 2}) == {"a": 2}
    assert update_dict({"a": {"b": 1}}, {"a": {"c": 2}}) == {
        "a": {"b": 1, "c": 2}
    }
    assert update_dict({"a": {"b": 1}}, {"a": {"c": 2}}, depth=1) == {
        "a": {"c": 2}
    }
    assert update_dict(
        {"a": {"b1": {"c": 1, "d": 2}, "b2": {"c": 1, "d": 2}}},
        {"a": {"b1": {"c": 2}}},
    ) == {"a": {"b1": {"c": 2, "d": 2}, "b2": {"c": 1, "d": 2}}}

    assert update_dict(
        {"a": {"b1": {"c": 1, "d": 2}, "b2": {"c": 1, "d": 2}}},
        {"a": {"b1": {"c": 2}}},
        depth=2,
    ) == {"a": {"b1": {"c": 2}, "b2": {"c": 1, "d": 2}}}

    assert update_dict(
        {"a": {"b1": {"c": 1, "d": 2}, "b2": {"c": 1, "d": 2}}},
        {"a": {"b1": {"c": 2}}},
        depth=1,
    ) == {"a": {"b1": {"c": 2}}}

    assert update_dict(
        {"a": [{"b": 1}]},
        {"a": [{"c": 2}]},
        try_list=True,
    ) == {"a": [{"b": 1, "c": 2}]}

    assert update_dict(
        {"a": [{"b": 1}, {"b": 2}]},
        {"a": [{"c": 2}]},
        try_list=True,
    ) == {"a": [{"b": 1, "c": 2}, {"b": 2}]}

    assert update_dict(
        {"a": [{"b": 1}]},
        {"a": 2},
        try_list=True,
    ) == {"a": 2}

    assert update_dict(
        {"a": {"b": 1}},
        {"a": [2]},
        try_list=True,
    ) == {"a": [2]}

    assert update_dict(
        {"a": [1, 2]},
        {"a": [2]},
        try_list=True,
    ) == {"a": [2, 2]}

    assert update_dict(
        {"a": [1, 2]},
        {"a": [2, 3, 4]},
        try_list=True,
    ) == {"a": [2, 3, 4]}


@pytest.mark.forked
def test_copy_dict():
    dic = {"a": {"b": 1, "c": 2}, "d": [3, 4]}
    copied = copy_dict(dic, depth=1)
    assert copied == {"a": {"b": 1, "c": 2}, "d": [3, 4]}
    assert copied is not dic
    assert copied["a"] is dic["a"]
    assert copied["d"] is dic["d"]

    copied = copy_dict(dic, depth=2)
    assert copied == {"a": {"b": 1, "c": 2}, "d": [3, 4]}
    assert copied is not dic
    assert copied["a"] is not dic["a"]
    assert copied["d"] is dic["d"]


@pytest.mark.forked
def test_strsplit():
    assert strsplit("a ,b ", ",", trim=None) == ["a ", "b "]
    assert strsplit("a , b", ",", trim="left") == ["a ", "b"]
    assert strsplit("a , b", ",", trim="right") == ["a", " b"]


@pytest.mark.forked
def test_get_shebang():
    assert get_shebang("") is None
    assert get_shebang("#!bash") == "bash"
    assert get_shebang("#!bash \n") == "bash"


@pytest.mark.forked
def test_ignore_firstline_dedent():
    text = """

    a
    """
    assert ignore_firstline_dedent(text) == "a\n"


@pytest.mark.forked
def test_truncate_text():
    assert truncate_text("abcd", 2) == "a…"


@pytest.mark.forked
def test_mark():
    @mark(a=1)
    class P1(pipen.Proc):
        ...

    assert get_marked(P1, "a") == 1

    class P2(P1):
        ...

    assert get_marked(P2, "a", None) is None

    P3 = pipen.Proc.from_proc(P1)
    assert get_marked(P3, "a") is None

    class X:
        ...

    assert get_marked(X, "a", None) is None

    @mark(a=1)
    class Y:
        ...

    assert get_marked(Y, "a") == 1

    class Z(Y):
        ...

    # Marks inherited, as Y/Z are not Proc nor ProcGroup
    assert get_marked(Z, "a", None) == 1


@pytest.mark.forked
def test_get_obj_from_spec():
    with pytest.raises(ValueError):
        _get_obj_from_spec("a.b.c")

    obj = _get_obj_from_spec(f"{HERE}/helpers.py:SimpleProc")
    assert obj.name == "SimpleProc"

    obj = _get_obj_from_spec("pipen:Pipen")
    assert obj is pipen.Pipen


@pytest.mark.forked
@pytest.mark.asyncio
async def test_load_pipeline(tmp_path):
    with pytest.raises(TypeError):
        await load_pipeline(f"{HERE}/helpers.py:create_dead_link")
    with pytest.raises(TypeError):
        await load_pipeline(ConfigurationError)

    # Proc
    pipeline = await load_pipeline(f"{HERE}/helpers.py:SimpleProc")
    assert pipeline.name == "SimpleProcPipeline"

    # ProcGroup
    class PG(ProcGroup):
        ...

    pg = PG()

    @pg.add_proc()
    class P1(Proc):
        pass

    pipeline = await load_pipeline(PG)
    assert pipeline.name == "PG"

    pipeline = await load_pipeline(f"{HERE}/helpers.py:PipenIsLoading")
    assert pipeline.name == "PipenIsLoading"
    assert pipeline.starts[0].name == "SimpleProc"
    assert len(pipeline.procs) == 1


@pytest.mark.forked
@pytest.mark.asyncio
async def test_load_pipeline_pipen_object(tmp_path):
    p = await load_pipeline(f"{HERE}/helpers.py:pipeline", a=1)
    assert p._kwargs["a"] == 1


@pytest.mark.forked
# To avoid: Another plugin named simpleplugin has already been registered.
@pytest.mark.asyncio
async def test_is_load_pipeline_with_help(tmp_path):
    pipeline = await load_pipeline(
        f"{HERE}/helpers.py:PipenIsLoading",
        "_",  # not @pipen
        ["--help"],
    )
    assert pipeline.name == "PipenIsLoading"
    assert pipeline.starts[0].name == "SimpleProc"
    assert len(pipeline.procs) == 1


def test_path_is_symlink(tmp_path):
    link = tmp_path / "link"
    path_symlink_to(link, tmp_path / "target")
    assert path_is_symlink(link)

    fake_symlink = tmp_path / "fake_symlink"
    path_symlink_to(fake_symlink, CloudPath(f"{BUCKET}/target"))
    assert path_is_symlink(fake_symlink)

    nonexist_file = tmp_path / "nonexist"
    assert not path_is_symlink(nonexist_file)

    dir = tmp_path / "dir"
    dir.mkdir()
    assert not path_is_symlink(dir)
