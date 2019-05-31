import pytest
from pyppl import Box
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
	('*', Box(), range(10)),
	('*.ext2', Box(), [0, 6, 7, 8, 9]),
	('*', Box(ftype = 'file'), [1, 3, 9]),
	('*', Box(ftype = 'dir'), [0, 5, 6]),
	('*', Box(ftype = 'link'), [2, 4, 7, 8]),
	('testFromPattern?_F*.*', Box(ftype = 'any', sortby = 'mtime'), [9,3,1,0,5,6]),
	('testFromPattern?_F*.*', Box(ftype = 'file', sortby = 'size', reverse = True), [3, 1, 9]),
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
	(0, Box(header = False, skip = 0, delimit = "\t"),
	 [("a1", "b1", "c1"), ("a2", "b2", "c2")],
	 []),
	(1, Box(header = True, skip = 0, delimit = ","),
	 [("a1", "b1", "c1"), ("a2", "b2", "c2")],
	 ["a", "b", "c"]),
	(2, Box(header = True, skip = 2, delimit = ","),
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
