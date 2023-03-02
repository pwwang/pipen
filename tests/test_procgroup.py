import pytest  # noqa: F401

from pipen import Proc, Pipen
from pipen.procgroup import ProcGroup


def test_singleton():
    class PG(ProcGroup):
        def build(self):
            pass

    assert PG() is PG()


def test_option_overrides_defaults():
    class PG(ProcGroup):
        DEFAULTS = {"a": 1}

        def build(self):
            pass

    pg = PG(a=2)
    assert pg.opts.a == 2


def test_add_proc():

    class PG(ProcGroup):
        def build(self):
            pass

    pg = PG()

    @pg.add_proc
    class P1(Proc):
        pass

    assert pg.P1 is P1
    assert len(pg.procs) == 1
    assert pg.procs.P1 is P1


def test_define_proc():

    class P1(Proc): pass  # noqa: E701
    class P2(Proc): pass  # noqa: E701
    class P3(Proc): pass  # noqa: E701

    class PG(ProcGroup):
        def build(self):
            self.p2.requires = [self.p1]
            self.p3.depends = [self.p2]
            return [self.p1]

        @ProcGroup.define_proc
        def p1(self):
            return P1

        @ProcGroup.define_proc()
        def p2(self):
            return P2

        @ProcGroup.define_proc()
        def p3(self):
            return P3

    pg = PG()
    assert pg.build() == [P1]

    assert pg.p1 is P1
    assert pg.p2 is P2
    assert pg.p3 is P3


def test_as_pipen():
    class PG(ProcGroup):
        """A pipeline group"""
        def build(self):
            pass

    pg = PG()

    @pg.add_proc
    class P1(Proc):
        ...

    p = pg.as_pipen()
    assert isinstance(p, Pipen)
    assert p.desc == "A pipeline group"

    p = pg.as_pipen(desc="Test desc")
    assert p.desc == "Test desc"


def test_procgroup_cleared_when_subclassed():
    class PG(ProcGroup):
        def build(self):
            pass

    pg = PG()

    @pg.add_proc()
    class P1(Proc):
        ...

    assert P1.__procgroup__ is pg

    class P2(P1):
        ...

    assert P2.__procgroup__ is None


def test_name():
    class PG(ProcGroup):
        def build(self):
            pass

    pg = PG()
    assert pg.name == "PG"

    class PG2(ProcGroup):
        name = "PG10"

        def build(self):
            pass

    pg2 = PG2()
    assert pg2.name == "PG10"


def test_invliad_proc_name():
    class PG(ProcGroup):
        def build(self):
            pass

    pg = PG()

    with pytest.raises(ValueError, match="Process name `opts` is reserved"):
        @pg.add_proc()
        class opts(Proc):
            ...
