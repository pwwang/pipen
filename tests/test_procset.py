import pytest
from diot import Diot
from pyppl.procset import Proxy, Values, PSProxy, ProcSet

pytest_plugins = ["tests.fixt_procset"]


def test_proxy():
    p = Proxy([1, 2, 3, 4, 1])
    assert p.count(1) == 2
    assert p.denominator == [1] * 5

    p1 = Proxy([Diot(), Diot(), Diot()])
    p1.x = Values(1, 2)
    assert p1[0].x == 1
    assert p1[1].x == 2
    assert 'x' not in p1[2]

    p1.y = 3
    assert p1[0].y == 3
    assert p1[1].y == 3
    assert p1[2].y == 3

    p2 = p1[:2]
    assert len(p2) == 2
    assert p2[0] is p1[0]
    assert p2[1] is p1[1]

    assert p1['y'] == [3, 3, 3]

    p2[0] = Diot(a=1)
    assert p2[0].a == 1

    p2['y'] = 1
    assert p2['y'] == [1, 1]


def test_proxy_add():
    p = Proxy([1, 2, 3, 4])
    p2 = Proxy([1, 2, 5])
    p.add([])
    assert p == [1, 2, 3, 4]

    p.add(p2)
    assert p == [1, 2, 3, 4, 5]


def test_values():
    v = Values(1, 2, 3)
    assert v == [1, 2, 3]


def test_procset_init(ps3):
    assert ps3.id == 'ps3'
    assert ps3.tag is None
    assert ps3.starts == []
    assert ps3.ends == []
    assert ps3.delegates['input'] == ['starts']
    assert ps3.delegates['depends'] == ['starts']
    assert ps3.delegated('input') == []
    assert ps3.delegated('depends') == []
    assert repr(ps3) == f'ProcSet(name="ps3")'


def test_procset_init_empty(empty_ps):
    # nothing
    assert empty_ps.id == 'empty_ps'
    assert empty_ps.tag is None
    assert empty_ps.starts == []
    assert empty_ps.ends == []
    assert empty_ps.delegates['input'] == ['starts']
    assert empty_ps.delegates['depends'] == ['starts']
    assert empty_ps.delegated('input') == []
    assert empty_ps.delegated('depends') == []


def test_procset_init_depends(ps3_depends, pProc1, pProc2, pProc3):
    assert ps3_depends.pProc1 is pProc1
    assert ps3_depends.pProc2 is pProc2
    assert ps3_depends.pProc3 is pProc3

    assert ps3_depends.id == 'ps3_depends'
    assert ps3_depends.tag is None
    assert ps3_depends.starts == [pProc1]
    assert ps3_depends.ends == [pProc3]

    assert ps3_depends.delegates['input'] == ['starts']
    assert ps3_depends.delegates['depends'] == ['starts']

    assert ps3_depends.delegated('input') == [pProc1]
    assert ps3_depends.delegated('depends') == [pProc1]


def test_procset_init_copy(ps3_copy, pProc1, pProc2, pProc3):
    assert ps3_copy.pProc1 is not pProc1
    assert ps3_copy.pProc2 is not pProc2
    assert ps3_copy.pProc3 is not pProc3

    assert ps3_copy.id == 'ps3_copy'
    assert ps3_copy.tag is None
    assert ps3_copy.starts == []
    assert ps3_copy.ends == []

    assert ps3_copy.delegates['input'] == ['starts']
    assert ps3_copy.delegates['depends'] == ['starts']

    assert ps3_copy.delegated('input') == []
    assert ps3_copy.delegated('depends') == []


def test_procset_init_copy_depends(ps3_copy_depends, pProc1, pProc2, pProc3):
    assert ps3_copy_depends.pProc1 is not pProc1
    assert ps3_copy_depends.pProc2 is not pProc2
    assert ps3_copy_depends.pProc3 is not pProc3

    assert ps3_copy_depends.id == 'ps3_copy_depends'
    assert ps3_copy_depends.tag is None
    assert ps3_copy_depends.starts == [ps3_copy_depends.pProc1]
    assert ps3_copy_depends.ends == [ps3_copy_depends.pProc3]

    assert ps3_copy_depends.delegates['input'] == ['starts']
    assert ps3_copy_depends.delegates['depends'] == ['starts']

    assert ps3_copy_depends.delegated('input') == [ps3_copy_depends.pProc1]
    assert ps3_copy_depends.delegated('depends') == [ps3_copy_depends.pProc1]


def test_procset_delegate(ps3_copy_depends):
    ps3_copy_depends.delegate('args.*', 'pProc?')
    assert ps3_copy_depends.delegates['args.*'] == ['pProc?']
    assert ps3_copy_depends.delegated('args.*') == [
        ps3_copy_depends.pProc1, ps3_copy_depends.pProc2,
        ps3_copy_depends.pProc3
    ]

    assert ps3_copy_depends.delegated('x') is None


def test_procset_setattr(ps3_copy):
    ps3_copy.starts = 'pProc1'
    assert ps3_copy.starts == [ps3_copy.pProc1]
    ps3_copy.ends = ps3_copy.pProc3
    assert ps3_copy.ends == [ps3_copy.pProc3]
    ps3_copy.id = 'p3'
    assert ps3_copy.id == 'p3'
    ps3_copy.tag = 'sometag'
    assert ps3_copy.tag == 'sometag'

    ps3_copy.args = Diot(x=1)
    assert ps3_copy.pProc1.args.x == 1
    assert ps3_copy.pProc2.args.x == 1
    assert ps3_copy.pProc3.args.x == 1


def test_procset_getattr(ps3_copy_depends):
    assert ps3_copy_depends.id == 'ps3_copy_depends'
    assert ps3_copy_depends.pProc1 is ps3_copy_depends.procs['pProc1']

    assert isinstance(ps3_copy_depends.args, PSProxy)
    assert ps3_copy_depends.args.procset is ps3_copy_depends
    assert ps3_copy_depends.args.path == ['args']


def test_procset_getitem(ps3_depends, pProc1, pProc2, pProc3):
    assert ps3_depends[0] == [pProc1]
    assert ps3_depends[:2] == [pProc1, pProc2]
    assert ps3_depends[:] == [pProc1, pProc2, pProc3]
    assert ps3_depends['pProc1, pProc2'] == [pProc1, pProc2]
    assert ps3_depends['pProc1, pProc?'] == [pProc1, pProc2, pProc3]


def test_psproxy(psp3):
    procset = psp3.procset
    assert len(procset.procs) == 3
    assert psp3.path == []

    procset.delegate('x', 'starts')
    assert psp3._delegated_attrs('x') == [procset.pProc1]

    psp3.__dict__['path'] = ['args']
    procset.delegate('args.*', 'pProc?')
    assert psp3._delegated_attrs('x') == [
        procset.pProc1.args, procset.pProc2.args, procset.pProc3.args
    ]

    assert psp3.args is psp3
    procset.args.x = Values(1, 2, 3)
    assert procset.pProc1.args.x == 1
    assert procset.pProc2.args.x == 2
    assert procset.pProc3.args.x == 3


def test_procset_copy(ps3_copy_depends):
    copied = ps3_copy_depends.copy(depends=False)
    assert copied.starts == []
    assert copied.ends == []
    assert list(copied.procs.keys()) == [
        proc.id for proc in ps3_copy_depends.procs.values()
    ]
    assert copied.pProc1 is not ps3_copy_depends.pProc1
    assert copied.pProc2 is not ps3_copy_depends.pProc2
    assert copied.pProc3 is not ps3_copy_depends.pProc3

    copied_depends = ps3_copy_depends.copy(depends=True)
    assert copied_depends.starts == [copied_depends.pProc1]
    assert copied_depends.ends == [copied_depends.pProc3]

    assert copied_depends.pProc2.depends == [copied_depends.pProc1]
    assert copied_depends.pProc3.depends == [copied_depends.pProc2]


def test_procset_module(ps3_copy_depends):
    @ps3_copy_depends.module
    def ps3_copy_depends_mod():
        pass

    with pytest.raises(TypeError):
        ps3_copy_depends.modules.mod()

    @ps3_copy_depends.module('reset')
    def reset(ps):
        ps.starts.clear()
        ps.ends.clear()

    ps3_copy_depends.modules.reset()
    assert ps3_copy_depends.starts == []
    assert ps3_copy_depends.ends == []

    @ps3_copy_depends.module('mod2')
    def mod2(ps):
        ps.starts.add(ps.pProc2)

    ps3_copy_depends.modules.mod2()
    assert ps3_copy_depends.starts == [
        ps3_copy_depends.pProc1, ps3_copy_depends.pProc2
    ]

    @ps3_copy_depends.module
    def mod3(ps, restore=False):
        ps.starts.add(ps.pProc3)

    ps3_copy_depends.modules.mod3()
    assert ps3_copy_depends.starts == [
        ps3_copy_depends.pProc1, ps3_copy_depends.pProc2,
        ps3_copy_depends.pProc3
    ]
