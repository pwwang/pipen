#coding: utf-8
import os
import pytest
import tempfile
import shutil
from pathlib import Path
# make L14 covered
if os.path.exists(os.path.join(tempfile.gettempdir(), 'fsutil.locks')):
	shutil.rmtree(os.path.join(tempfile.gettempdir(), 'fsutil.locks'))
from hashlib import md5
from filelock import FileLock
from pyppl.utils import Fs as fsutil, TargetExistsError

@pytest.mark.parametrize('path, lockfile', [
	('a', os.path.join(fsutil.TMPDIR, md5('a'.encode()).hexdigest() + '.lock'))
])
def test_getLockFile(path, lockfile):
	assert fsutil._getLockFile(path) == lockfile

def test_lock(tmpdir):
	testfile1 = tmpdir / 'test1'
	testfile2 = tmpdir / 'test2'

	with fsutil.lock(testfile1) as lock0:
		assert os.path.exists(fsutil._getLockFile(testfile1))
		assert lock0.is_locked
	assert not lock0.is_locked

	with fsutil.lock(testfile1, testfile2) as locks:
		assert os.path.exists(fsutil._getLockFile(testfile1))
		assert os.path.exists(fsutil._getLockFile(testfile2))
		assert locks[0].is_locked
		assert locks[1].is_locked
	assert not locks[0].is_locked
	assert not locks[1].is_locked

def test_autolock(tmpdir):
	testfile1 = tmpdir / 'test1'

	def exists(arg):
		assert exists.lock.is_locked
		return os.path.exists(arg)

	locked_exists = fsutil.autolock(exists)

	assert not locked_exists(testfile1)

def test_alias(tmpdir):
	assert fsutil.exists(tmpdir)
	assert fsutil.isdir(tmpdir)
	test1 = tmpdir / 'test1'
	test1.write_text('', encoding = 'utf-8')
	assert fsutil.isfile(test1)
	test2 = tmpdir / 'test2'
	if fsutil.exists(test2):
		test2.unlink()
	Path(test2).symlink_to(test1)
	assert fsutil.islink(test2)

def test_remove(tmpdir):
	test1 = Path(tmpdir / 'link')
	test2 = tmpdir / 'file'
	test2.write_text('', encoding = 'utf-8')
	test1.symlink_to(test2)
	test3 = tmpdir / 'dir'
	test3.mkdir()
	assert fsutil.exists(test3)
	fsutil.remove(test3)
	assert not fsutil.exists(test3)
	assert fsutil.exists(test1)
	assert fsutil.islink(test1)
	fsutil.remove(test1)
	assert not fsutil.exists(test1)
	assert not fsutil.islink(test1)
	assert fsutil.exists(test2)
	fsutil.remove(test2)
	assert not fsutil.exists(test2)
	with pytest.raises(OSError):
		fsutil.remove(tmpdir / 'notexists', False)

def test_move(tmpdir):
	tmpdir = Path(tmpdir)
	test1 = tmpdir / 'test1'
	test2 = tmpdir / 'test2'
	test1.write_text('1')
	test2.write_text('2')
	with pytest.raises(OSError):
		fsutil.move(test1, test2, False)
	assert test2.read_text() == '2'
	assert fsutil.exists(test1)
	test1.write_text('1')
	fsutil.move(test1, test2, True)
	assert test2.read_text() == '1'
	assert not fsutil.exists(test1)

def test_copy(tmpdir):
	tmpdir = Path(tmpdir)
	test1 = tmpdir / 'test1'
	test2 = tmpdir / 'test2'
	test1.write_text('1')
	test2.write_text('2')
	with pytest.raises(OSError):
		fsutil.copy(test1, test2, False)
	assert test1.read_text() == '1'
	assert test2.read_text() == '2'
	fsutil.copy(test1, test2, True)
	assert test1.read_text() == '1'
	assert test2.read_text() == '1'
	dir1 = tmpdir / 'dir1'
	dir2 = tmpdir / 'dir2'
	dir1.mkdir()
	dir2.mkdir()
	fsutil.copy(test1, dir1 / 'test1')
	with pytest.raises(OSError):
		fsutil.copy(dir1, dir2, False)
	fsutil.copy(dir1, dir2)
	fsutil.exists(dir1 / 'test1')
	fsutil.exists(dir2 / 'test2')

def test_link(tmpdir):
	tmpdir = Path(tmpdir)
	test1 = tmpdir / 'testlink1'
	test2 = tmpdir / 'testlink2'
	test1.write_text('')
	test2.write_text('')
	with pytest.raises(OSError):
		fsutil.link(test1, test2, False)
	fsutil.link(test1, test2)
	assert fsutil.islink(test2)

def test_samefile(tmpdir):
	tmpdir = Path(tmpdir)
	test1 = tmpdir / 'testlink1'
	test2 = tmpdir / 'testlink1'
	test3 = tmpdir / 'testlink3'
	assert fsutil.samefile(test1, test2)
	test1.write_text('')
	assert not fsutil.samefile(test1, test3)
	fsutil.link(test1, test3)
	assert fsutil.samefile(test1, test3)

def test_mkdir(tmpdir):
	tmpdir = Path(tmpdir)
	dir1 = tmpdir / 'testdir1'
	dir1.mkdir()
	with pytest.raises(OSError):
		fsutil.mkdir(dir1, False)
	fsutil.mkdir(dir1)
	assert fsutil.isdir(dir1)

def test_gzip(tmpdir):
	tmpdir = Path(tmpdir)
	test1 = tmpdir / 'test1.gz'
	test2 = tmpdir / 'test2'
	test3 = tmpdir / 'test3'
	test2.write_text('1')
	with pytest.raises(OSError):
		fsutil.gzip(test1, test2, False)
	fsutil.gzip(test2, test1)
	assert fsutil.exists(test1)
	fsutil.gunzip(test1, test3)
	assert fsutil.exists(test3)
	assert test3.read_text() == '1'

	dir1 = tmpdir / 'dir1'
	dir2 = tmpdir / 'dir2'
	tgz = tmpdir / 'dir1.tgz'
	fsutil.mkdir(dir1)
	test3 = dir1 / 'test'
	test3.write_text('2')
	fsutil.gzip(dir1, tgz)
	assert fsutil.exists(tgz)
	fsutil.gunzip(tgz, dir2)
	assert fsutil.isdir(dir2)
	assert fsutil.exists(dir2 / 'test')
	with pytest.raises(OSError):
		fsutil.gunzip(tgz, dir2, False)
