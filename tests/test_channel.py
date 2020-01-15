import pytest
from diot import Diot
from pyppl.channel import Channel

pytest_plugins = ["tests.fixt_channel"]

@pytest.mark.parametrize('obj, expt', [
    ('', ('', )),
    ([], ([], )),
    (1, (1, )),
    ((1,2,3), (1,2,3)),
])
def test_cleanup(obj, expt):
    assert Channel._tuplize(obj) == expt

@pytest.mark.parametrize('obj, expt', [
    (1,     [(1, )]),
    ("a,b", [("a,b", )]),
    (["a", "b"], [("a", ), ("b", )]),
    (("a", "b"), [("a", "b")]),
    ([], []),
    ([[]], [([], )]),
    # issue #29
    ('', [('', )])
])
def test_create(obj, expt):
    assert Channel.create(obj) == expt

def test_create_exc():
    with pytest.raises(ValueError):
        Channel.create([("a", ), ("c", "d")])

@pytest.mark.parametrize('length,width', [
    (0, 0),
    (1, 1),
    (0, 1),
    (1, 0),
    (2, 2),
    (10, 3),
])
def test_nones(length, width):
    assert Channel.nones(length, width) == [(None, ) * width] * length

@pytest.mark.parametrize('channels, expt', [
    ([Channel.create([(1, 2), (3, 4)]), Channel.create('a'), Channel.create([5, 6])],
     [(1, 2, 'a', 5), (3, 4, 'a', 6)]),
    ([Channel.create([]), Channel.create([])], []),
    ([Channel.create([]), Channel.create(1), Channel.create([1, 2])], [(1,1), (1,2)]),
])
def test_fromchannels(channels, expt):
    assert Channel.fromChannels(*channels) == expt

# 'testFromPattern0_FDir.ext2', # 1 file
# 'testFromPattern1_File.ext1', # 2 link 1
# 'testFromPattern2_Link.ext1', # 3 file
# 'testFromPattern3_File.ext1', # 4 link 3
# 'testFromPattern4_Link.ext1', # 5 dir
# 'testFromPattern5_FDir.ext1', # 6 dir
# 'testFromPattern6_FDir.ext2', # 7 link 5
# 'testFromPattern7_Link.ext2', # 8 link 6
# 'testFromPattern8_Link.ext2', # 9 file
# 'testFromPattern9_File.ext2'
@pytest.mark.parametrize('pattern,kwargs,expt', [
    ('*', Diot(), range(10)),
    ('*.ext2', Diot(), [0, 6, 7, 8, 9]),
    ('*', Diot(ftype = 'file'), [1, 3, 9]),
    ('*', Diot(ftype = 'dir'), [0, 5, 6]),
    ('*', Diot(ftype = 'link'), [2, 4, 7, 8]),
    ('testFromPattern?_F*.*', Diot(ftype = 'any', sortby = 'mtime'), [9,3,1,0,5,6]),
    ('testFromPattern?_F*.*', Diot(ftype = 'file', sortby = 'size', reverse = True), [3, 1, 9]),
])
def test_frompattern(tmp_test_dir, pattern, expt, kwargs, pattern_files):
    assert Channel.fromPattern(
        (tmp_test_dir / 'test_frompattern' / pattern).as_posix(), **kwargs) == [
        ((tmp_test_dir / 'test_frompattern' / pattern_files[e]).as_posix(), ) for e in expt]

# 'testFromPairs10.txt',
# 'testFromPairs11.txt',
# 'testFromPairs12.txt',
# 'testFromPairs13.txt',
# 'testFromPairs20.txt',
# 'testFromPairs21.txt',
# 'testFromPairs22.txt',
# 'testFromPairs23.txt',
@pytest.mark.parametrize('pattern,expt', [
    ('testFromPairs1?.txt', [(0,1),(2,3)]),
    ('testFromPairs2?.txt', [(4,5),(6,7)]),
])
def test_frompairs(tmp_test_dir, pattern, expt, paired_files):
    assert Channel.fromPairs(
        (tmp_test_dir / 'test_frompairs' / pattern).as_posix()) == [
        ((tmp_test_dir / 'test_frompairs' / paired_files[e[0]]).as_posix(),
         (tmp_test_dir / 'test_frompairs' / paired_files[e[1]]).as_posix()
        ) for e in expt]

@pytest.mark.parametrize('fileidx, kwargs, expt, headers', [
    (0, Diot(header = False, skip = 0, delimit = "\t"),
     [("a1", "b1", "c1"), ("a2", "b2", "c2")],
     []),
    (1, Diot(header = True, skip = 0, delimit = ","),
     [("a1", "b1", "c1"), ("a2", "b2", "c2")],
     ["a", "b", "c"]),
    (2, Diot(header = True, skip = 2, delimit = ","),
     [("a1", "b1", "c1"), ("a2", "b2", "c2")],
     ["RowNames", "b", "c"]),
])
def test_fromfile(tmp_test_dir, fileidx, kwargs, expt, headers, file_files):
    ch = Channel.fromFile(
        (tmp_test_dir / 'test_fromfile' / file_files[fileidx]).as_posix(),
        **kwargs)
    assert ch == expt
    assert all(head in dir(ch) for head in headers)

def test_fromfile_exc(tmp_test_dir, file_files):
    thefile = tmp_test_dir / 'test_fromfile' / file_files[3]
    with pytest.raises(ValueError):
        Channel.fromFile(thefile.as_posix(), header = True, skip = 1, delimit=",")

@pytest.mark.parametrize('args,expt', [
    (["prog", "a", "b", "c"], [("a",), ("b",), ("c",)]),
    (["prog", "a1,a2", "b1,b2", "c1,c2"], [("a1","a2"), ("b1","b2"), ("c1","c2")]),
    (["prog"], []),
])
def test_fromargs(args, expt):
    import sys
    sys.argv = args
    assert Channel.fromArgv() == expt

def test_fromargs_exc():
    import sys
    sys.argv = ["prog", "a1,a2", "b1", "c1,c2"]
    with pytest.raises(ValueError):
        Channel.fromArgv()

def test_fromparams():
    from pyparam import params
    params._test1 = [1,2,3]
    params._test2 = [4,4,4]
    assert Channel.fromParams('_test1', '_test2') == [(1,4), (2,4), (3,4)]
    params._test3 = 5
    params._test4 = 6
    assert Channel.fromParams('_test3', '_test4') == [(5,6)]
    with pytest.raises(ValueError):
        Channel.fromParams('_test3', '_test1')

def test_expand(expand_dirs):
    dir1, dir2 = expand_dirs
    file1 = str(dir1 / 'testExpand1.txt')
    file2 = str(dir1 / 'testExpand2.txt')
    file3 = str(dir2 / 'testExpand3.txt')
    file4 = str(dir2 / 'testExpand4.txt')
    assert Channel.create().expand(col = 0) == []
    assert Channel.create(dir1).expand(col = 0) == [(file1,), (file2,)]
    assert Channel.create(('a', 1, dir2)).expand(col = 2) == [
        ('a', 1, file3), ('a', 1, file4)]
    assert Channel.create(('a', 1, dir2)).expand(col = 2, pattern = 'a.*') == []
    assert Channel.create([
        ('a', 1, dir1),	('b', 2, dir2)
    ]).expand(col = 2) == Channel.create([
        ('a', 1, file1),
        ('a', 1, file2),
        ('b', 2, file3),
        ('b', 2, file4),
    ])

def test_collapse(expand_dirs):
    dir1, dir2 = expand_dirs
    file1 = str(dir1 / 'testExpand1.txt')
    file2 = str(dir1 / 'testExpand2.txt')
    file3 = str(dir2 / 'testExpand3.txt')
    file4 = str(dir2 / 'testExpand4.txt')
    with pytest.raises(ValueError):
        Channel.create().collapse(col = 0)
    assert Channel.create([file1, file2]).collapse() == [(str(dir1), )]
    assert Channel.create([
        ('a1', file1, 'a2'), ('b1', file2, 'b2')]).collapse(1) == [('a1', str(dir1), 'a2')]
    assert Channel.create([
        ('a1', file1, 'a2'), ('b1', file2, 'b2')]).collapse(0) == [('', file1, 'a2')]

@pytest.mark.parametrize('ch1, row', [
    ([], (1,)),
    ([(1,2)], (3,4))
])
def test_copy(ch1, row):
    ch1 = Channel.create(ch1)
    ch2 = ch1.copy()
    ch1.append(row)
    assert ch1 != ch2

@pytest.mark.parametrize('ch, width', [
    ([], 0),
    ((1,2), 2),
    ([1,2], 1),
])
def test_width(ch, width):
    assert Channel.create(ch).width() == width

@pytest.mark.parametrize('ch, length', [
    ([], 0),
    ((1,2), 1),
    ([1,2], 2),
])
def test_length(ch, length):
    assert Channel.create(ch).length() == length
    assert len(Channel.create(ch)) == length

@pytest.mark.parametrize('ch, func, outs', [
    ([], lambda x: x*2, []),
    ([1,2,3,4,5], lambda x: x*2, [(1,1),(2,2),(3,3),(4,4),(5,5)]),
    ([(1,1),(2,2),(3,3),(4,4),(5,5)], lambda x: (x[0], x[1]*2,), [(1,2),(2,4),(3,6),(4,8),(5,10)]),
])
def test_map(ch, func, outs):
    ch   = Channel.create(ch)
    ch2  = ch.map(func)
    outs = Channel.create(outs)
    assert ch2 == outs

@pytest.mark.parametrize('ch, func, col, outs', [
    ([], lambda x: x*2, 0, []),
    ([1,2,3,4,5], lambda x: x*2, 0, [2,4,6,8,10]),
    ([(1,1),(2,2),(3,3),(4,4),(5,5)], lambda x: x*2, 1, [(1,2),(2,4),(3,6),(4,8),(5,10)]),
])
def test_mapcol(ch, func, col, outs):
    ch   = Channel.create(ch)
    ch2  = ch.mapCol(func, col)
    outs = Channel.create(outs)
    assert ch2 == outs

@pytest.mark.parametrize('ch, func, outs', [
    ([], None, []),
    ([
        (1, 0, 0, 1),
        ('a', '', 'b', '0'),
        (True, False, 0, 1),
        ([], [1], [2], [0]),
    ], None, [
        (1, 0, 0, 1),
        ('a', '', 'b', '0'),
        (True, False, 0, 1),
        ([], [1], [2], [0]),
    ]),
    ([
        (1, 0, 0, 1),
        ('a', '', 'b', '0'),
        (True, False, 0, 1),
        ([], [1], [2], [0]),
    ], lambda x: all([isinstance(_, int) for _ in x]), [
        (1, 0, 0, 1),
        (True, False, 0, 1),
    ])
])
def test_filter(ch, func, outs):
    ch   = Channel.create(ch)
    ch2  = ch.filter(func)
    outs = Channel.create(outs)
    assert ch2 == outs

@pytest.mark.parametrize('ch, func, col, outs', [
    ([], None, 0, []),
    ([
        (1, 0, 0, 1),
        ('a', '', 'b', '0'),
        (True, False, 0, 1),
        ([], [1], [2], [0]),
    ], None, 1, [
        ([], [1], [2], [0]),
    ]),
    ([
        (1, 0, 0, 1),
        ('a', '', 'b', '0'),
        (True, False, 0, 1),
        ([], [1], [2], [0]),
    ], lambda x: bool(x), 2, [
        ('a', '', 'b', '0'),
        ([], [1], [2], [0]),
    ])
])
def test_filtercol(ch, func, col, outs):
    ch   = Channel.create(ch)
    ch2  = ch.filterCol(func, col)
    outs = Channel.create(outs)
    assert ch2 == outs

def test_reduce_exc():
    with pytest.raises(TypeError):
        Channel.create([]).reduce(None)

@pytest.mark.parametrize('ch, func, outs', [
    ([1], None, (1,)),
    ([1,2,3,4,5], lambda x,y: x+y, (1,2,3,4,5)),
    ([2], lambda x,y: (x[0] * y[0], ), (2,)),
])
def test_reduce(ch, func, outs):
    ch   = Channel.create(ch)
    ch2  = ch.reduce(func)
    assert ch2 == outs

def test_reducecol_exc():
    with pytest.raises(TypeError):
        Channel.create([]).reduceCol(None, 0)

@pytest.mark.parametrize('ch, func, col, outs', [
    ([
        (1, 0, 0, 1),
        ('a', '', 'b', '0'),
        (True, False, 0, 1),
        ([], [1], [2], [0]),
    ], lambda x,y: bool(x) and bool(y), 1, False),
    ([
        (1, 0, 0, 1),
        ('a', '', 'b', '0'),
        (True, False, 0, 1),
        ([], [1], [2], [0]),
    ], lambda x, y: int(x[0] if isinstance(x, list) else x) + int(y[0] if isinstance(y, list) else y), 3, 2)
])
def test_reducecol(ch, func, col, outs):
    ch2  = Channel.create(ch).reduceCol(func, col)
    assert ch2 == outs

def test_rbind_exc():
    with pytest.raises(ValueError):
        Channel.create((1,2,3)).rbind((4,5))

@pytest.mark.parametrize('ch, rows, outs', [
    ([], [], []),
    ([], [()], []),
    ([], [[()]], []),
    ([], [1], [1]),
    ([], [1, (1,2)], [(1,1), (1,2)]),
    ((1,2,3), [1], [(1,2,3), (1,1,1)]),
    ((1,2,3), [(4,5,6)], [(1,2,3),(4,5,6)]),
])
def test_rbind(ch, rows, outs):
    assert Channel.create(ch).rbind(*rows) == Channel.create(outs)

@pytest.mark.parametrize('pos, ch1, ch2, ch2islist', [
    (None, Channel.create(), [Channel.create([4,5]), Channel.create([1,2,3])], True),
    (None, Channel.create([(1,2), (3,4)]), [1,2,3], False)
])
def test_insert_exc(pos, ch1, ch2, ch2islist):
    with pytest.raises(ValueError):
        if ch2islist:
            ch1.insert(pos, *ch2)
        else:
            ch1.insert(pos, ch2)

@pytest.mark.parametrize('pos, ch1, ch2, outs, ch2islist', [
    (0, Channel.create([(1, 2), (3, 4)]), Channel.create([5, 6]), [(5, 1, 2), (6, 3, 4)], False),
    (1, Channel.create([(1, 2), (3, 4)]), Channel.create([5, 6]), [(1, 5, 2), (3, 6, 4)], False),
    (-1, Channel.create([(1, 2), (3, 4)]), Channel.create([5, 6]), [(1, 5, 2), (3, 6, 4)], False),
    (None, Channel.create([(1, 2), (3, 4)]), Channel.create([5, 6]), [(1, 2, 5), (3, 4, 6)], False),
    (0,    Channel.create([(1, 2), (3, 4)]), Channel.create(5), [(5, 1, 2), (5, 3, 4)], False),
    (1,    Channel.create([(1, 2), (3, 4)]), Channel.create(5), [(1, 5, 2), (3, 5, 4)], False),
    (-1,   Channel.create([(1, 2), (3, 4)]), Channel.create(5), [(1, 5, 2), (3, 5, 4)], False),
    (None, Channel.create([(1, 2), (3, 4)]), Channel.create(5), [(1, 2, 5), (3, 4, 5)], False),
    (0,    Channel.create([(1, 2), (3, 4)]), [5, 6], [(5, 1, 2), (6, 3, 4)], False),
    (1,    Channel.create([(1, 2), (3, 4)]), [5, 6], [(1, 5, 2), (3, 6, 4)], False),
    (-1,   Channel.create([(1, 2), (3, 4)]), [5, 6], [(1, 5, 2), (3, 6, 4)], False),
    (None, Channel.create([(1, 2), (3, 4)]), [5, 6], [(1, 2, 5), (3, 4, 6)], False),
    (0,    Channel.create([(1, 2), (3, 4)]), (5, 6), [(5, 6, 1, 2), (5, 6, 3, 4)], False),
    (1,    Channel.create([(1, 2), (3, 4)]), (5, 6), [(1, 5, 6, 2), (3, 5, 6, 4)], False),
    (-1,   Channel.create([(1, 2), (3, 4)]), (5, 6), [(1, 5, 6, 2), (3, 5, 6, 4)], False),
    (None, Channel.create([(1, 2), (3, 4)]), (5, 6), [(1, 2, 5, 6), (3, 4, 5, 6)], False),
    (0,    Channel.create([(1, 2), (3, 4)]), "a",    [('a', 1, 2), ('a', 3, 4)], False),
    (1,    Channel.create([(1, 2), (3, 4)]), "a",    [(1, 'a', 2), (3, 'a', 4)], False),
    (-1,   Channel.create([(1, 2), (3, 4)]), "a",    [(1, 'a', 2), (3, 'a', 4)], False),
    (None, Channel.create([(1, 2), (3, 4)]), "a",    [(1, 2, 'a'), (3, 4, 'a')], False),
    (0, Channel.create([(1, 2), (3, 4)]), [], Channel.create([(1, 2), (3, 4)]), False),
    (1, Channel.create([(1, 2), (3, 4)]), [], Channel.create([(1, 2), (3, 4)]), False),
    (-1, Channel.create([(1, 2), (3, 4)]), [], Channel.create([(1, 2), (3, 4)]), False),
    (None, Channel.create([(1, 2), (3, 4)]), [], Channel.create([(1, 2), (3, 4)]), False),
    (1, Channel.create(), Channel.create([21, 22]), Channel.create([21, 22]), False),
    (0, Channel.create(), [Channel.create([21, 22]), 3, [41, 42], (51, 52), 'a'], [(21, 3, 41, 51, 52, 'a'), (22, 3, 42, 51, 52, 'a')], True),
    (0, Channel.create(), [], Channel.create(), False),
    (1, Channel.create(), [], Channel.create(), False),
    (-1, Channel.create(), [], Channel.create(), False),
    (None, Channel.create(), [], Channel.create(), False),
    # 30-31
    (None, Channel.create(), [1, [1, 2]], [(1,1), (1,2)], True),
    (None, Channel.create(), [Channel.create(1), Channel.create([1,2])], [(1,1), (1,2)], True),
    # 32 Emptys
    (1, Channel.create(), [[], 1, [], [2, 3]], [(1,2), (1,3)], True)
])
def test_insert(pos, ch1, ch2, outs, ch2islist):
    if ch2islist:
        ch1.insert(pos, *ch2) == outs
    else:
        ch1.insert(pos, ch2) == outs

@pytest.mark.parametrize('ch, row, outs', [
    ([], 0, []),
    ([], 1, []),
    ([1,2,3], 1, 2),
    ([1,2,3], -1, 3),
    ([1,2,3], [1,-1], [2,3]),
    ([1,2,3], [-1,0], [3,1]),
    ([(1,4),(2,5),(3,6)], 1, (2,5)),
    ([(1,4),(2,5),(3,6)], -1, (3,6)),
    ([(1,4),(2,5),(3,6)], [1, -2], [(2,5),(2,5)]),
])
def test_rowat(ch, row, outs):
    ch   = Channel.create(ch)
    outs = Channel.create(outs)
    assert ch.rowAt(row) == outs

@pytest.mark.parametrize('ch, outs', [
    ([], []),
    ([1], [1]),
    ([1,2,3,4], [1,2,3,4]),
    ([1,2,2,4], [1,2,4]),
    ([1,2,3,1], [1,2,3]),
])
def test_unique(ch, outs):
    ch   = Channel.create(ch)
    outs = Channel.create(outs)
    assert ch.unique() == outs

@pytest.mark.parametrize('ch, start, length, outs', [
    ([], 0, None, []),
    ([], 1, None, []),
    ([], -1, None, []),
    ([1,2,3], 0, None, [1,2,3]),
    ((1,2,3), 1, None, (2,3)),
    ((1,2,3), -1, None, 3),
    ((1,2,3), -1, 1, 3),
    ([(1,2,3), (4,5,6)], -2, 1, [2,5]),
    ([(1,2,3), (4,5,6)], -2, 8, [(2,3), (5,6)]),
])
def test_slice(ch, start, length, outs):
    ch   = Channel.create(ch)
    outs = Channel.create(outs)
    assert ch.slice(start, length) == outs

@pytest.mark.parametrize('ch, n', [
    ([], 0),
    ([(1,2,3,4)], 3),
    ([(1,2,3,4), (5,6,7,8)], 8),
])

def test_fold_exc(ch, n):
    with pytest.raises(ValueError):
        Channel.create(ch).fold(n)

@pytest.mark.parametrize('ch, n, outs', [
    ([(1,2,3,4)], 2, [(1,2),(3,4)]),
    ([(1,2,3,4), (5,6,7,8)], 2, [(1,2),(3,4),(5,6),(7,8)]),
    ([(1,2,3,4), (5,6,7,8)], 1, [1,2,3,4,5,6,7,8]),
    ([(1,2,3,4), (5,6,7,8)], 4, [(1,2,3,4), (5,6,7,8)]),
])

def test_fold(ch, n, outs):
    outs = Channel.create(outs)
    assert Channel.create(ch).fold(n) == outs

@pytest.mark.parametrize('ch, n', [
    ([], 0),
    ([], -1),
    ([1,2,3,4], 3),
])

def test_unfold_exc(ch, n):
    with pytest.raises(ValueError):
        Channel.create(ch).unfold(n)

@pytest.mark.parametrize('ch, n, outs', [
    ([(1,2),(3,4),(5,6),(7,8)], 4, (1,2,3,4,5,6,7,8)),
    ([(1,2),(3,4),(5,6),(7,8)], 1, [(1,2),(3,4),(5,6),(7,8)]),
    ([1,2,3,4], 2, [(1,2), (3,4)]),
])

def test_unfold(ch, n, outs):
    outs = Channel.create(outs)
    assert Channel.create(ch).unfold(n) == outs

@pytest.mark.parametrize('ch, flatten, outs', [
    ([], True, []),
    ([], False, []),
    ([1,2,3], True, [[1, 2, 3]]),
    ([1,2,3], False, [Channel.create([1,2,3])]),
    ((1,2,3), True, [[1], [2], [3]]),
    ((1,2,3), False, [Channel.create(1), Channel.create(2), Channel.create(3)]),
    ([(1,4),(2,5),(3,6)], True, [[1, 2, 3], [4,5,6]]),
    ([(1,4),(2,5),(3,6)], False, [Channel.create([1,2,3]), Channel.create([4,5,6])]),
])
def test_split(ch, flatten, outs):
    ch = Channel.create(ch)
    ch.split(flatten) == outs

@pytest.mark.parametrize('ch, names, exception', [
    ([], ['a'], ValueError),
    ([(1,2)], ['a', 'b', 'c'], ValueError),
    ([(1,2)], ['attach', 'attach1'], AttributeError),
])
def test_attach_exc(ch, names, exception):
    with pytest.raises(exception):
        Channel.create(ch).attach(*names)

@pytest.mark.parametrize('ch, names, flatten, outs', [
    ([], [], False, {}),
    ((1,2,3), ['a', 'b'], False, {'a': [(1,)], 'b': [(2,)]}),
    ([1,2], ['a'], False, {'a': [(1,), (2,)]}),
    ([(1,2,3), (4,5,6)], ['a', 'b'], True, {'a': [1,4], 'b': [2,5]}),
])
def test_attach(ch, names, flatten, outs):
    ch = Channel.create(ch)
    ch.attach(*names, flatten = flatten)
    for name in names:
        assert getattr(ch, name) == outs[name]

@pytest.mark.parametrize('ch, idx', [
    ([], 0), ([1,2,3], 4)
])
def test_get_exc(ch, idx):
    with pytest.raises(IndexError):
        Channel.create(ch).get(idx)

@pytest.mark.parametrize('ch, idx, outs', [
    ([1,2,3], 1, 2),
    ([1,2,3], 0, 1),
    ((1,2,3), 0, 1),
    ((1,2,3), -1, 3),
])
def test_get(ch, idx, outs):
    assert Channel.create(ch).get(idx) == outs

@pytest.mark.parametrize('ch, n, outs', [
    ([], 1, []),
    ([], 2, []),
    ([], 0, []),
    ([1], 2, (1,1)),
    ([1, 2], 2, [(1,1), (2,2)]),
    ((1,2), 2, [(1,2, 1,2)]),
    ([(1,2), (3,4)], 2, [(1,2,1,2),(3,4,3,4)]),
])
def test_repcol(ch, n, outs):
    ch   = Channel.create(ch)
    outs = Channel.create(outs)
    assert ch.repCol(n) == outs

@pytest.mark.parametrize('ch, n, outs', [
    ([], 1, []),
    ([], 2, []),
    ([], 0, []),
    ([1], 2, [1,1]),
    ([1, 2], 2, [1,2,1,2]),
    ((1,2), 2, [(1,2), (1,2)]),
    ([(1,2), (3,4)], 2, [(1,2),(3,4),(1,2),(3,4)]),
])
def test_reprow(ch, n, outs):
    ch   = Channel.create(ch)
    outs = Channel.create(outs)
    assert ch.repRow(n) == outs

def test_flatten_exc():
    with pytest.raises(IndexError):
        Channel.create([1,2,3]).flatten(1)

@pytest.mark.parametrize('ch, col, outs', [
    ([], None, []),
    ([], 0, []),
    ([], 1, []),
    ([], -1, []),
    ([1,2,3], -1, [1,2,3]),
    ([1,2,3], None, [1,2,3]),
    ((1,2,3), None, [1,2,3]),
    ([1,2,3], 0, [1,2,3]),
    ((1,2,3), 0, [1]),
    ((1,2,3), 1, [2]),
    ((1,2,3), -1, [3]),
])
def test_flatten(ch, col, outs, exception = None):
    ch = Channel.create(ch)
    assert ch.flatten(col) == outs

@pytest.mark.parametrize('ch, outs', [
    ([(1,2,3), (4,5,6)], [(1,4), (2,5), (3,6)]),
])
def test_transpose(ch, outs):
    Channel.create(ch).t() == outs
