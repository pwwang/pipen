import sys
import pytest
import psutil
from faker import Faker
from pyppl.utils import Box, OrderedBox, split, funcsig, uid, formatSecs, alwaysList, \
	briefList, briefPath, killtree, chmodX, filesig, fileflush, ThreadEx, ThreadPool, \
	PQueue, Hashable
# load fixtures
pytest_plugins = ["tests.fixt_utils"]

@pytest.mark.box
@pytest.mark.parametrize('construct', [
	{}, {'a':1}
])
def test_box_init(construct):
	assert Box(construct).__dict__['_box_config']['box_intact_types'] == (list, )

@pytest.mark.box
@pytest.mark.parametrize('construct,expect', [
	({}, "Box([], box_intact_types = (list,))"),
	([('a', 1), ('b', 2)], "Box([('a', 1), ('b', 2)], box_intact_types = (list,))"),
])
def test_box_repr(construct,expect):
	assert repr(Box(construct)) == expect

@pytest.mark.box
@pytest.mark.parametrize('construct', [
	{},
	[('a', 1), ('b', 2)],
])
def test_box_copy(construct):
	box = Box(construct)
	box2 = box.copy()
	assert id(box) != id(box2)
	box3 = box.__copy__()
	assert id(box) != id(box3)

@pytest.mark.box
@pytest.mark.parametrize('construct', [
	{},
	[('a', 1), ('b', 2)],
])
def test_obox_init(construct):
	assert OrderedBox(construct).__dict__['_box_config']['box_intact_types'] == (list, )
	assert OrderedBox(construct).__dict__['_box_config']['ordered_box']

@pytest.mark.repr
@pytest.mark.parametrize('construct,expect', [
	({}, "Box([], box_intact_types = (list,), ordered_box = True)"),
	([('b', 1), ('a', 2)], "Box([('b', 1), ('a', 2)], box_intact_types = (list,), ordered_box = True)"),
])
def test_obox_repr(construct,expect):
	assert repr(OrderedBox(construct)) == expect

def test_varname(fixt_varname):
	assert fixt_varname.var == fixt_varname.expt

@pytest.mark.parametrize('string, delimit, trim, expect', [
	("a\"|\"b", "|", True, ["a\"|\"b"]),
	("a|b|c", "|", True, ["a", "b", "c"]),
	('a|b\\|c', "|", True, ["a", "b\\|c"]),
	('a|b\\|c|(|)', "|", True, ["a", "b\\|c", "(|)"]),
	('a|b\\|c|(\\)|)', "|", True, ["a", "b\\|c", "(\\)|)"]),
	('a|b\\|c|(\\)\\\'|)', "|", True, ["a", "b\\|c", "(\\)\\'|)"]),
	('a|b\\|c |(\\)\\\'|)', "|", False, ["a", "b\\|c ", "(\\)\\'|)"]),
	('outdir:dir:{{i.pattern | lambda x: __import__("glob").glob(x)[0] | fn }}_etc', ':', True, ["outdir", "dir", "{{i.pattern | lambda x: __import__(\"glob\").glob(x)[0] | fn }}_etc"]),
])
def test_split(string, delimit, trim, expect):
	assert split(string, delimit, trim) == expect

def test_funcsig(fixt_funcsig):
	assert funcsig(fixt_funcsig.func) == fixt_funcsig.expt

@pytest.mark.parametrize('string, length, alphabet, expect', [
	('a', 8, '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz', 'O4JnVAW7'),
	('', 8, '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz', '6SFsQFoW'),
])
def test_uid(string, length, alphabet, expect):
	assert uid(string, length, alphabet) == expect

@pytest.mark.parametrize('randstrs', [
	([Faker().text()] * 10000, )
])
def test_uid_uniq(randstrs):
	uids = [uid(rstr) for rstr in randstrs]
	assert len(set(uids)) == len(uids)

@pytest.mark.parametrize('secs, expect', [
	(1, "00:00:01.000"),
	(1.001, "00:00:01.001"),
	(100, "00:01:40.000"),
	(7211, "02:00:11.000"),
])
def test_formatsecs(secs, expect):
	assert formatSecs(secs) == expect

@pytest.mark.parametrize('data,trim,expect', [
	("a, b,c", True, ['a', 'b', 'c']),
	(["a, b,c"], True, ['a', 'b', 'c']),
	(["a, b,c", 'd'], True, ['a', 'b', 'c', 'd']),
	(["a, b,c ", 'd'], False, ['a', ' b', 'c ', 'd']),
	("a,b, c, 'd,e'", True, ['a', 'b', 'c', "'d,e'"]),
	(
		["o1:var:{{c1}}", "o2:var:{{c2 | __import__('math').pow(float(_), 2.0)}}", "o3:file:{{c3.fn}}2{{c3.ext}}"], True,
		["o1:var:{{c1}}", "o2:var:{{c2 | __import__('math').pow(float(_), 2.0)}}", "o3:file:{{c3.fn}}2{{c3.ext}}"]
	),
	(
		["o1:var:{{c1}}", "o2:var:c2 | __import__('math').pow float(_), 2.0)}}", "o3:file:{{c3.fn}}2{{c3.ext}}"],
		#                                                             ^ comma is not quoted
		True,
		["o1:var:{{c1}}", "o2:var:c2 | __import__('math').pow float(_)", "2.0)}}", "o3:file:{{c3.fn}}2{{c3.ext}}"]
	)
])
def test_alwaysList(data, trim, expect):
	assert alwaysList(data, trim) == expect

@pytest.mark.parametrize('data', [
	1, (1,), {}
])
def test_alwaysList_raises(data):
	with pytest.raises(ValueError):
		alwaysList(data)

@pytest.mark.parametrize('inlist,expect', [
	([], '[]'),
	(None, '[]'),
	([1], '1'),
	([0, 1, 2, 3, 4, 5, 6, 7], "0-7"),
	([1, 3, 5, 7, 9], "1, 3, 5, 7, 9"),
	([1, 3, 5, 7, 9, 4, 8, 12, 13], "1, 3-5, 7-9, 12, 13"),
	([13, 9, 5, 7, 4, 3, 8, 1, 12], "1, 3-5, 7-9, 12, 13"),
])
def test_briefList(inlist, expect):
	assert briefList(inlist) == expect

@pytest.mark.parametrize('inpath,cutoff,expect', [
	("", 10, ""),
	("veryveryverlongpath", 2, "veryveryverlongpath"),
	("/abcd/efghi", None, "/abcd/efghi"),
	("/abcdef/efghi", 0, "/abcdef/efghi"),
	("/abcd/efghi", 20, "/abcd/efghi"),
	("/aaaa/eeeee", 8, "/a/eeeee"),
	("/aaaa/eeeee", 1, "/a/eeeee"),
	("/aaaaaa/eeeee", 10, "/aaa/eeeee"),
	("/1234567890/1234567890/eeeee", 20, "/123456/123456/eeeee"),
	("/1234567890/1234567890/eeeee", 19, "/123456/12345/eeeee"),
	("/1234567890/1234567890/abcdefg/eeeee", 19, "/1234/123/abc/eeeee"),
])
def test_briefPath(inpath, cutoff, expect):
	assert briefPath(inpath, cutoff) == expect

def test_killtree(fixt_killtree):
	assert len(fixt_killtree.children) == 2
	for child in fixt_killtree.children + [fixt_killtree.pid]:
		assert psutil.pid_exists(child)
	killtree(fixt_killtree.pid, killme = fixt_killtree.killme)
	if fixt_killtree.killme:
		for child in fixt_killtree.children + [fixt_killtree.pid]:
			assert not psutil.pid_exists(child)
	else:
		for child in fixt_killtree.children:
			assert not psutil.pid_exists(child)
		assert psutil.pid_exists(fixt_killtree.pid)

def test_chmodX(fixt_chmodx):
	if isinstance(fixt_chmodx.expt, type):
		with pytest.raises(fixt_chmodx.expt):
			chmodX(fixt_chmodx.file)
	else:
		assert chmodX(fixt_chmodx.file) == fixt_chmodx.expt

def test_filesig(fixt_filesig):
	fixt_filesig.dirsig = fixt_filesig.get('dirsig', True)
	assert filesig(fixt_filesig.file, fixt_filesig.dirsig) == fixt_filesig.expt

def test_fileflush(fixt_fileflush):
	lines, residue = fileflush(
		fixt_fileflush.filed, fixt_fileflush.residue, fixt_fileflush.get('end', False))
	assert lines == fixt_fileflush.expt_lines
	assert residue == fixt_fileflush.expt_residue

def test_threadex(fixt_threadex):
	thread = ThreadEx(target = fixt_threadex.worker)
	assert thread.daemon
	assert thread.ex is None
	thread.start()
	thread.join()
	if fixt_threadex.expt_ex:
		assert isinstance(thread.ex, fixt_threadex.expt_ex)

def test_threadpool(fixt_threadpool):
	nthread     = fixt_threadpool.nthread
	initializer = fixt_threadpool.initializer
	initargs    = fixt_threadpool.get('initargs')
	cleanup     = fixt_threadpool.get('cleanup')
	exc         = fixt_threadpool.expt_exc
	pool        = ThreadPool(nthread, initializer, initargs)
	assert len(pool.threads) == nthread
	assert isinstance(pool.threads[0], ThreadEx)
	if exc:
		with pytest.raises(exc):
			pool.join(cleanup = cleanup, interval = .1)
	else:
		# make sure thread alive after one round join
		# so that is_alive will be executed
		pool.join(cleanup = cleanup, interval = .01) 
	for thread in pool.threads:
		thread.join()
	assert all([not thread.is_alive() for thread in pool.threads])

@pytest.mark.parametrize('batch_len,puts,expect', [
	(10, {
		5: 'putToBuild',
		4: 'putToFirstSubmit',
		0: 'putToFirstRun',
		6: 'putToBuild',
		7: 'putToFirstRun',
		3: 3,
		'3 ': 6
	}, [(0, 0), (7, 0), (4, 1), (5, 2), (6, 2), (3, 6), (3, 9)])
])
def test_pqueue(batch_len, puts, expect):
	pqueue = PQueue(batch_len = batch_len)
	for key, val in puts.items():
		if not isinstance(key, int):
			key = int(key.strip())
		if isinstance(val, int):
			pqueue.put(key, val)
		else:
			getattr(pqueue, val)(key)
	ret = []
	while not pqueue.empty():
		ret.append(pqueue.get())
	assert ret == expect

def test_pqueue_batchlen():
	with pytest.raises(ValueError):
		PQueue()

def test_hashable():
	h1 = Hashable()
	h2 = Hashable()
	assert h1 != h2
	assert not h1 == h2
	adict = {h1: 1, h2: 2}
	for key, val in adict.items():
		if val == 1:
			assert key == h1
			assert key is h1
		else:
			assert key == h2
			assert key is h2

