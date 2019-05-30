from os import utime
from shutil import rmtree
from time import time
import pytest

@pytest.fixture(scope="module")
def tmp_test_dir(tmp_path_factory):
	t = tmp_path_factory.mktemp('test_channel')
	t.mkdir(exist_ok = True)
	return t

@pytest.fixture(scope="module")
def pattern_files(tmp_test_dir):
	pfiles = ['testFromPattern0_FDir.ext2', # 0 dir
		'testFromPattern1_File.ext1', # 1 file
		'testFromPattern2_Link.ext1', # 2 link 1
		'testFromPattern3_File.ext1', # 3 file
		'testFromPattern4_Link.ext1', # 4 link 3
		'testFromPattern5_FDir.ext1', # 5 dir
		'testFromPattern6_FDir.ext2', # 6 dir
		'testFromPattern7_Link.ext2', # 7 link 5
		'testFromPattern8_Link.ext2', # 8 link 6
		'testFromPattern9_File.ext2'] # 9 file
	tmpdir = tmp_test_dir / 'test_frompattern'
	if tmpdir.exists():
		rmtree(tmpdir.as_posix())
	tmpdir.mkdir()
	files = [tmpdir / f for f in pfiles]

	t = time() - 30
	files[9].write_text('1')
	utime(files[9], (t,t))
	files[3].write_text('111')
	utime(files[3], (t+1, t+1))
	files[1].write_text('11')
	utime(files[1], (t+2, t+2))
	files[0].mkdir()
	utime(files[0], (t+3, t+3))
	files[5].mkdir()
	utime(files[5], (t+4, t+4))
	files[6].mkdir()
	utime(files[6], (t+5, t+5))
	files[7].symlink_to(files[5])
	files[8].symlink_to(files[6])
	files[4].symlink_to(files[3])
	files[2].symlink_to(files[1])
	return pfiles

@pytest.fixture(scope="module")
def paired_files(tmp_test_dir):
	pfiles = ['testFromPairs1%s.txt' % i for i in range(4)] + \
			 ['testFromPairs2%s.txt' % i for i in range(4)]

	tmpdir = tmp_test_dir / 'test_frompairs'
	if tmpdir.exists():
		rmtree(tmpdir.as_posix())
	tmpdir.mkdir()
	files = [tmpdir / f for f in pfiles]

	for f in files:
		f.write_text('')
	return pfiles
