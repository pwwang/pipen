import sys
import pytest
import psutil
from faker import Faker
from diot import Diot, OrderedDiot
from pyppl.utils import funcsig, format_secs, always_list, \
 brief_list, chmod_x, filesig, ThreadEx, ThreadPool, \
 PQueue, _MultiDestTransition, StateMachine, try_deepcopy
# load fixtures
pytest_plugins = ["tests.fixt_utils"]


def test_funcsig(fixt_funcsig):
    assert funcsig(fixt_funcsig.func) == fixt_funcsig.expt


@pytest.mark.parametrize('secs, expect', [
    (1, "00:00:01.000"),
    (1.001, "00:00:01.001"),
    (100, "00:01:40.000"),
    (7211, "02:00:11.000"),
])
def test_formatsecs(secs, expect):
    assert format_secs(secs) == expect


@pytest.mark.parametrize(
    'data,trim,expect',
    [
        ("a, b,c", True, ['a', 'b', 'c']),
        ("a, b,c", True, ['a', 'b', 'c']),
        (["a, b,c", "d"], True, ['a, b,c', 'd']),
        ('a, b,c , d', False, ['a', ' b', 'c ', ' d']),
        ("a,b, c, 'd,e'", True, ['a', 'b', 'c', "'d", "e'"]),
        ([
            "o1:var:{{c1}}",
            "o2:var:{{c2 | __import__('math').pow(float(_), 2.0)}}",
            "o3:file:{{c3.fn}}2{{c3.ext}}"
        ], True, [
            "o1:var:{{c1}}",
            "o2:var:{{c2 | __import__('math').pow(float(_), 2.0)}}",
            "o3:file:{{c3.fn}}2{{c3.ext}}"
        ]),
    ])
def test_always_list(data, trim, expect):
    assert always_list(data, trim) == expect


@pytest.mark.parametrize('data', [1, {}])
def test_always_list_raises(data):
    with pytest.raises((AttributeError, TypeError)):
        always_list(data)


@pytest.mark.parametrize('inlist,expect', [
    ([], '[]'),
    (None, '[]'),
    ([1], '1'),
    ([0, 1, 2, 3, 4, 5, 6, 7], "0-7"),
    ([1, 3, 5, 7, 9], "1, 3, 5, 7, 9"),
    ([1, 3, 5, 7, 9, 4, 8, 12, 13], "1, 3-5, 7-9, 12, 13"),
    ([13, 9, 5, 7, 4, 3, 8, 1, 12], "1, 3-5, 7-9, 12, 13"),
])
def test_brief_list(inlist, expect):
    assert brief_list(inlist) == expect


def test_chmod_x(fixt_chmodx):
    if isinstance(fixt_chmodx.expt, type):
        with pytest.raises(fixt_chmodx.expt):
            chmod_x(fixt_chmodx.file)
    else:
        assert chmod_x(fixt_chmodx.file) == fixt_chmodx.expt


def test_filesig(fixt_filesig):
    fixt_filesig.dirsig = fixt_filesig.get('dirsig', True)
    assert filesig(fixt_filesig.file, fixt_filesig.dirsig) == fixt_filesig.expt


def test_threadex(fixt_threadex):
    thread = ThreadEx(target=fixt_threadex.worker)
    assert thread.daemon
    assert thread.ex is None
    thread.start()
    thread.join()
    if fixt_threadex.expt_ex:
        assert isinstance(thread.ex, fixt_threadex.expt_ex)


def test_threadpool(fixt_threadpool):
    nthread = fixt_threadpool.nthread
    initializer = fixt_threadpool.initializer
    initargs = fixt_threadpool.get('initargs')
    cleanup = fixt_threadpool.get('cleanup')
    exc = fixt_threadpool.expt_exc
    pool = ThreadPool(nthread, initializer, initargs)
    assert len(pool.threads) == nthread
    assert isinstance(pool.threads[0], ThreadEx)
    if exc:
        with pytest.raises(exc):
            pool.join(cleanup=cleanup, interval=.1)
    else:
        # make sure thread alive after one round join
        # so that is_alive will be executed
        pool.join(cleanup=cleanup, interval=.01)
    for thread in pool.threads:
        thread.join()
    assert all([not thread.is_alive() for thread in pool.threads])


@pytest.mark.parametrize('batch_len,puts,expect', [(10, [
    ('put', 5, 0),
    ('put', 0, 0),
    ('put', 7, 0),
    ('put_next', 4, 2),
    ('put_next', 6, 3),
    ('put_next', 3, 3),
    ('put', 3, 3),
    ('put', 6, 3),
], [(0, 0), (3, 3), (6, 3), (4, 4), (3, 5), (5, 5), (6, 5), (7, 7)])])
def test_pqueue(batch_len, puts, expect):
    pqueue = PQueue(batch_len=batch_len)
    for method, item, batch in puts:
        getattr(pqueue, method)(item, batch)
    ret = []
    while not pqueue.empty():
        ret.append(pqueue.get())
    assert ret == expect


def test_pqueue_batchlen():
    with pytest.raises(ValueError):
        PQueue()


def test_statemachine():
    with pytest.raises(AttributeError):
        _MultiDestTransition('solid', {})
    _MultiDestTransition('solid', 'liquid', depends_on='depends_on')

    class Model(object):
        def depends_on(self):
            return 'turntoliquid'

    model = Model()
    machine = StateMachine(model=model,
                           states=['solid', 'liquid', 'gas'],
                           initial='solid')
    machine.add_transition('heat',
                           'solid', {
                               'turntoliquid': 'liquid',
                               'turntogas': 'gas'
                           },
                           depends_on='depends_on')
    model.heat()
    assert model.state == 'liquid'


@pytest.mark.parametrize(
    'val,expt,asserts',
    [(None, None, ['is']), (1, 1, ['is']), (sys, sys, ['is']),
     (Diot(a=Diot(b=Diot(c=1))), Diot(a=Diot(b=Diot(c=1))), ['=']),
     ([1, sys, [1]], [1, sys, [1]], [(0, 'is'), (1, 'is'), (2, '=')]),
     ({
         'a': sys,
         'b': [1]
     }, {
         'a': sys,
         'b': [1]
     }, [('a', 'is'), ('b', '=')])])
def test_trydeepcopy(val, expt, asserts):
    copied = try_deepcopy(val)

    for ast in asserts:
        if ast == '=':
            assert copied == val
            assert copied is not val
        elif ast == 'is':
            assert copied is val
        else:
            key, eq = ast
            if eq == '=':
                assert copied[key] == val[key]
                assert copied[key] is not val[key]
            else:
                assert copied[key] is val[key]
