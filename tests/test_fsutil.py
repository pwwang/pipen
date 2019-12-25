#coding: utf-8
import os
import pytest
import tempfile
import shutil
from pathlib import Path
from hashlib import md5
from filelock import FileLock
from pyppl.utils import fs

@pytest.mark.parametrize('path, lockfile', [
	('a', os.path.join(fs.TMPDIR, md5('a'.encode()).hexdigest() + '.lock'))
])
def test_get_lock_file(path, lockfile):
	assert fs._get_lock_file(path) == lockfile

def test_lock(tmpdir):
	testfile1 = tmpdir / 'test1'
	testfile2 = tmpdir / 'test2'

	with fs.lock(testfile1) as lock0:
		assert os.path.exists(fs._get_lock_file(testfile1))
		assert lock0.is_locked
	assert not lock0.is_locked

	with fs.lock(testfile1, testfile2) as locks:
		assert os.path.exists(fs._get_lock_file(testfile1))
		assert os.path.exists(fs._get_lock_file(testfile2))
		assert locks[0].is_locked
		assert locks[1].is_locked
	assert not locks[0].is_locked
	assert not locks[1].is_locked

def test_autolock(tmpdir):
	testfile1 = tmpdir / 'test1'

	def exists(arg):
		assert exists.lock.is_locked
		return os.path.exists(arg)

	locked_exists = fs.autolock(exists)

	assert not locked_exists(testfile1)

def test_alias(tmpdir):
	assert fs.exists(tmpdir)
	assert fs.isdir(tmpdir)
	test1 = tmpdir / 'test1'
	test1.write_text('', encoding = 'utf-8')
	assert fs.isfile(test1)
	test2 = tmpdir / 'test2'
	if fs.exists(test2):
		test2.unlink()
	Path(test2).symlink_to(test1)
	assert fs.islink(test2)

def test_remove(tmpdir):
	test1 = Path(tmpdir / 'link')
	test2 = tmpdir / 'file'
	test2.write_text('', encoding = 'utf-8')
	test1.symlink_to(test2)
	test3 = tmpdir / 'dir'
	test3.mkdir()
	assert fs.exists(test3)
	fs.remove(test3)
	assert not fs.exists(test3)
	assert fs.exists(test1)
	assert fs.islink(test1)
	fs.remove(test1)
	assert not fs.exists(test1)
	assert not fs.islink(test1)
	assert fs.exists(test2)
	fs.remove(test2)
	assert not fs.exists(test2)
	with pytest.raises(OSError):
		fs.remove(tmpdir / 'notexists', False)

def test_move(tmpdir):
	tmpdir = Path(tmpdir)
	test1 = tmpdir / 'test1'
	test2 = tmpdir / 'test2'
	test1.write_text('1')
	test2.write_text('2')
	with pytest.raises(OSError):
		fs.move(test1, test2, False)
	assert test2.read_text() == '2'
	assert fs.exists(test1)
	test1.write_text('1')
	fs.move(test1, test2, True)
	assert test2.read_text() == '1'
	assert not fs.exists(test1)

	# same file
	fs.link(test2, test1)
	fs.move(test1, test2)
	assert not fs.exists(test1)
	assert fs.isfile(test2)

def test_copy(tmpdir):
	tmpdir = Path(tmpdir)
	test1 = tmpdir / 'test1'
	test2 = tmpdir / 'test2'
	test1.write_text('1')
	test2.write_text('2')
	with pytest.raises(OSError):
		fs.copy(test1, test2, False)
	assert test1.read_text() == '1'
	assert test2.read_text() == '2'
	fs.copy(test1, test2, True)
	assert test1.read_text() == '1'
	assert test2.read_text() == '1'
	dir1 = tmpdir / 'dir1'
	dir2 = tmpdir / 'dir2'
	dir1.mkdir()
	dir2.mkdir()
	fs.copy(test1, dir1 / 'test1')
	with pytest.raises(OSError):
		fs.copy(dir1, dir2, False)
	fs.copy(dir1, dir2)
	fs.exists(dir1 / 'test1')
	fs.exists(dir2 / 'test2')

	# copy same file, don't do anything
	fs.link(test1, test2)
	assert fs.samefile(test1, test2)
	assert fs.islink(test2)
	fs.copy(test2, test1)
	assert fs.samefile(test1, test2)
	assert fs.islink(test2)

def test_link(tmpdir):
	tmpdir = Path(tmpdir)
	test1 = tmpdir / 'testlink1'
	test2 = tmpdir / 'testlink2'
	test1.write_text('')
	test2.write_text('')
	with pytest.raises(OSError):
		fs.link(test1, test2, False)
	fs.link(test1, test2)
	assert fs.islink(test2)

	# same file
	fs.link(test2, test1)
	assert fs.samefile(test1, test2)
	assert fs.islink(test1)
	fs.link(test1, test2)
	assert fs.samefile(test1, test2)
	assert fs.islink(test2)

def test_samefile(tmpdir):
	tmpdir = Path(tmpdir)
	test1 = tmpdir / 'testlink1'
	test2 = tmpdir / 'testlink1'
	test3 = tmpdir / 'testlink3'
	assert fs.samefile(test1, test2)
	test1.write_text('')
	assert not fs.samefile(test1, test3)
	fs.link(test1, test3)
	assert fs.samefile(test1, test3)

def test_mkdir(tmpdir):
	tmpdir = Path(tmpdir)
	dir1 = tmpdir / 'testdir1'
	dir1.mkdir()
	with pytest.raises(OSError):
		fs.mkdir(dir1, False)
	fs.mkdir(dir1)
	assert fs.isdir(dir1)

def test_gzip(tmpdir):
	tmpdir = Path(tmpdir)
	test1 = tmpdir / 'test1.gz'
	test2 = tmpdir / 'test2'
	test3 = tmpdir / 'test3'
	test2.write_text('1')
	with pytest.raises(OSError):
		fs.gzip(test1, test2, False)
	fs.gzip(test2, test1)
	assert fs.exists(test1)
	fs.gunzip(test1, test3)
	assert fs.exists(test3)
	assert test3.read_text() == '1'

	dir1 = tmpdir / 'dir1'
	dir2 = tmpdir / 'dir2'
	tgz = tmpdir / 'dir1.tgz'
	fs.mkdir(dir1)
	test3 = dir1 / 'test'
	test3.write_text('2')
	fs.gzip(dir1, tgz)
	assert fs.exists(tgz)
	fs.gunzip(tgz, dir2)
	assert fs.isdir(dir2)
	assert fs.exists(dir2 / 'test')
	with pytest.raises(OSError):
		fs.gunzip(tgz, dir2, False)


