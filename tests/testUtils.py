import testly, helpers

import traceback
import gzip, tarfile
import filelock
from glob import glob
from copy import deepcopy
from os import path, symlink, remove, rename, makedirs, utime, X_OK, access, W_OK, getcwd, chdir
from pyppl import utils
from pyppl.utils import Box, uid, ps
from pyppl.utils.cmd import Cmd
from pyppl.utils.safefs import SafeFs
from pyppl.utils.parallel import Parallel
from time import time, sleep
from shutil import copyfile, rmtree, copyfileobj
from subprocess import Popen
from tempfile import gettempdir

class TestSafeFs(testly.TestCase):

	def setUpMeta(self):
		self.tmpdir  = gettempdir()
		self.testdir = path.join(gettempdir(), 'PyPPL_unittest', 'TestSafeFs')
		if path.exists(self.testdir):
			rmtree(self.testdir)
		makedirs(self.testdir)

	def testStaticVars(self):
		self.assertEqual(SafeFs.TMPDIR, self.tmpdir)
		self.assertEqual(SafeFs.FILETYPE_UNKNOWN, -1)
		self.assertEqual(SafeFs.FILETYPE_NOENT, 0)
		self.assertEqual(SafeFs.FILETYPE_NOENTLINK, 1)
		self.assertEqual(SafeFs.FILETYPE_FILE, 2)
		self.assertEqual(SafeFs.FILETYPE_FILELINK, 3)
		self.assertEqual(SafeFs.FILETYPE_DIR, 4)
		self.assertEqual(SafeFs.FILETYPE_DIRLINK, 5)
		self.assertEqual(SafeFs.FILES_DIFF_BOTHNOENT, 0)
		self.assertEqual(SafeFs.FILES_DIFF_NOENT1, 1)
		self.assertEqual(SafeFs.FILES_DIFF_NOENT2, 2)
		self.assertEqual(SafeFs.FILES_DIFF_BOTHENT, 3)
		self.assertEqual(SafeFs.FILES_SAME_STRNOENT, 4)
		self.assertEqual(SafeFs.FILES_SAME_STRENT, 5)
		self.assertEqual(SafeFs.FILES_SAME_BOTHLINKS, 6)
		self.assertEqual(SafeFs.FILES_SAME_BOTHLINKS1, 7)
		self.assertEqual(SafeFs.FILES_SAME_BOTHLINKS2, 8)
		self.assertEqual(SafeFs.FILES_SAME_REAL1, 9)
		self.assertEqual(SafeFs.FILES_SAME_REAL2, 10)

	def test_filetype(self, filepath, filetype):
		ft = SafeFs._filetype(filepath)
		self.assertEqual(ft, filetype)

	def dataProvider_test_filetype(self):
		# a file
		file1 = path.join(self.testdir, 'test_filetype1')
		# a file link
		file2 = path.join(self.testdir, 'test_filetype2')
		# a dead link
		file3 = path.join(self.testdir, 'test_filetype3')
		# a dir
		file4 = path.join(self.testdir, 'test_filetype4')
		# a dir link
		file5 = path.join(self.testdir, 'test_filetype5')
		# not exists
		file6 = path.join(self.testdir, 'test_filetype6')
		# unknown
		file7 = None
		helpers.writeFile(file1)
		symlink(file1, file2)
		helpers.createDeadlink(file3)
		makedirs(file4)
		symlink(file4, file5)
		yield file1, SafeFs.FILETYPE_FILE
		yield file2, SafeFs.FILETYPE_FILELINK
		yield file3, SafeFs.FILETYPE_NOENTLINK
		yield file4, SafeFs.FILETYPE_DIR
		yield file5, SafeFs.FILETYPE_DIRLINK
		yield file6, SafeFs.FILETYPE_NOENT
		yield file7, SafeFs.FILETYPE_UNKNOWN
		yield '/dev/null', SafeFs.FILETYPE_UNKNOWN

	def test_lockfile(self, filepath, real, tmpdir, lockfile):
		self.assertEqual(SafeFs._lockfile(filepath, real, tmpdir = tmpdir), lockfile)

	def dataProvider_test_lockfile(self):
		yield None, True, self.tmpdir, None
		# a file
		file1 = path.join(self.testdir, 'test_lockfile1')
		# a file link
		file2 = path.join(self.testdir, 'test_lockfile2')
		# a dead link
		file3 = path.join(self.testdir, 'test_lockfile3')
		helpers.writeFile(file1)
		symlink(file1, file2)
		helpers.createDeadlink(file3)
		yield file2, False, self.tmpdir, path.join(self.tmpdir, uid(file2, 16) + '.lock')
		yield file2, True, self.tmpdir, path.join(self.tmpdir, uid(file1, 16) + '.lock')
		yield file3, True, self.tmpdir, path.join(self.tmpdir, uid(file3, 16) + '.lock')

	def test_exists(self, filepath, exists):
		self.assertEqual(SafeFs._exists(filepath), exists)

	def dataProvider_test_exists(self):
		# a file
		file1 = path.join(self.testdir, 'test_exists1')
		# a file link
		file2 = path.join(self.testdir, 'test_exists2')
		# a dead link
		file3 = path.join(self.testdir, 'test_exists3')
		# a dir
		file4 = path.join(self.testdir, 'test_exists4')
		# a dir link
		file5 = path.join(self.testdir, 'test_exists5')
		# not exists
		file6 = path.join(self.testdir, 'test_exists6')
		# unknown
		file7 = None
		helpers.writeFile(file1)
		symlink(file1, file2)
		helpers.createDeadlink(file3)
		makedirs(file4)
		symlink(file4, file5)
		yield file1, True
		yield file2, True
		yield file3, False
		yield file4, True
		yield file5, True
		yield file6, False
		yield file7, False

	def test_filerel(self, file1, file2, filerel):
		self.assertEqual(SafeFs._filerel(file1, file2), filerel)

	def dataProvider_test_filerel(self):
		# a file
		file1 = path.join(self.testdir, 'test_filerel1')
		# a file link
		file2 = path.join(self.testdir, 'test_filerel2')
		# a dead link
		file3 = path.join(self.testdir, 'test_filerel3')
		# a dir
		file4 = path.join(self.testdir, 'test_filerel4')
		# a dir link
		file5 = path.join(self.testdir, 'test_filerel5')
		# not exists
		file6 = path.join(self.testdir, 'test_filerel6')
		# link to file2
		file10 = path.join(self.testdir, 'test_filerel10')
		# another link to file1
		file11 = path.join(self.testdir, 'test_filerel11')
		# unknown
		file7 = None

		helpers.writeFile(file1)
		symlink(file1, file2)
		symlink(file1, file11)
		helpers.createDeadlink(file3)
		makedirs(file4)
		symlink(file4, file5)
		symlink(file2, file10)

		file8 = file1
		yield file1, file8, SafeFs.FILES_SAME_STRENT
		file9 = file6
		yield file6, file9, SafeFs.FILES_SAME_STRNOENT
		yield file3, file6, SafeFs.FILES_DIFF_BOTHNOENT
		yield file3, file1, SafeFs.FILES_DIFF_NOENT1
		yield file1, file3, SafeFs.FILES_DIFF_NOENT2
		yield file1, file4, SafeFs.FILES_DIFF_BOTHENT
		yield file2, file10, SafeFs.FILES_SAME_BOTHLINKS2
		yield file10, file2, SafeFs.FILES_SAME_BOTHLINKS1
		yield file2, file11, SafeFs.FILES_SAME_BOTHLINKS
		yield file1, file2, SafeFs.FILES_SAME_REAL1
		yield file2, file1, SafeFs.FILES_SAME_REAL2

	def test_remove(self, filepath):
		exists = SafeFs._exists(filepath)
		r = SafeFs._remove(filepath)
		if exists:
			self.assertTrue(r)
			self.assertFalse(path.exists(filepath))
		else:
			self.assertFalse(r)

	def dataProvider_test_remove(self):
		# a file
		file1 = path.join(self.testdir, 'test_remove1')
		# a file link
		file2 = path.join(self.testdir, 'test_remove2')
		# a dead link
		file3 = path.join(self.testdir, 'test_remove3')
		# a dir
		file4 = path.join(self.testdir, 'test_remove4')
		# a dir link
		file5 = path.join(self.testdir, 'test_remove5')
		# not exists
		file6 = path.join(self.testdir, 'test_remove6')
		# unknown
		file7 = None
		helpers.writeFile(file1)
		symlink(file1, file2)
		helpers.createDeadlink(file3)
		makedirs(file4)
		symlink(file4, file5)

		yield file1,
		yield file2,
		yield file3,
		yield file4,
		yield file5,
		yield file6,
		yield file7,

	def test_copy(self, file1, file2, overwrite, rout):
		r = SafeFs._copy(file1, file2, overwrite)
		self.assertEqual(r, rout)
		if r:
			if path.isdir(file1):
				self.assertListEqual(glob(path.join(file1, '*')), glob(path.join(file2, '*')))
			else:
				with open(file1) as f1, open(file2) as f2:
					helpers.assertTextEqual(self, f1.read(), f2.read())

	def dataProvider_test_copy(self):
		# a file
		file1 = path.join(self.testdir, 'test_copy1')
		# a file link
		file2 = path.join(self.testdir, 'test_copy2')
		# a dead link
		file3 = path.join(self.testdir, 'test_copy3')
		# a dir
		file4 = path.join(self.testdir, 'test_copy4')
		# a dir link
		file5 = path.join(self.testdir, 'test_copy5')
		# not exists
		file6 = path.join(self.testdir, 'test_copy6')
		# link to file2
		file10 = path.join(self.testdir, 'test_copy10')
		# another link to file1
		file11 = path.join(self.testdir, 'test_copy11')
		# unknown
		file7 = None
		file8 = file1
		file9 = file6

		helpers.writeFile(file1)
		symlink(file1, file2)
		symlink(file1, file11)
		helpers.createDeadlink(file3)
		makedirs(file4)
		symlink(file4, file5)
		symlink(file2, file10)

		yield file6, file9, True, False
		yield file3, file6, True, False
		yield file10, file2, True, False
		yield file3, file1, True, False
		yield file1, file8, True, True
		yield file2, file1, True, True
		yield file4, file1, False, False
		yield file1, file6, True, True
		yield file1, file2, True, True
		yield file1, file10, True, True
		yield file4, file11, True, True

	def test_link(self, file1, file2, overwrite, rout):
		r = SafeFs._link(file1, file2, overwrite)
		self.assertEqual(r, rout)
		if r:
			rel = SafeFs._filerel(file1, file2)
			self.assertIn(rel, [SafeFs.FILES_SAME_BOTHLINKS2, SafeFs.FILES_SAME_REAL1, SafeFs.FILES_SAME_STRENT])

	def dataProvider_test_link(self):
		# a file
		file1 = path.join(self.testdir, 'test_link1')
		# a file link
		file2 = path.join(self.testdir, 'test_link2')
		# a dead link
		file3 = path.join(self.testdir, 'test_link3')
		# a dir
		file4 = path.join(self.testdir, 'test_link4')
		# a dir link
		file5 = path.join(self.testdir, 'test_link5')
		# not exists
		file6 = path.join(self.testdir, 'test_link6')
		# link to file2
		file10 = path.join(self.testdir, 'test_link10')
		# another link to file1
		file11 = path.join(self.testdir, 'test_link11')
		# unknown
		file7 = None
		file8 = file1
		file9 = file6

		helpers.writeFile(file1)
		symlink(file1, file2)
		symlink(file1, file11)
		helpers.createDeadlink(file3)
		makedirs(file4)
		symlink(file4, file5)
		symlink(file2, file10)

		yield file6, file9, True, False
		yield file3, file6, True, False
		yield file10, file2, True, False
		yield file3, file1, True, False
		yield file2, file1, True, False
		yield file1, file8, True, True
		yield file1, file2, True, True
		yield file2, file10, True, True
		yield file1, file4, False, False
		yield file1, file11, False, True

	def test_move(self, file1, file2, overwrite, rout):
		r = SafeFs._move(file1, file2, overwrite)
		self.assertEqual(r, rout)
		if r and file1 != file2:
			self.assertFalse(path.exists(file1))
			self.assertTrue(path.exists(file2))

	def dataProvider_test_move(self):
		# a file
		file1 = path.join(self.testdir, 'test_move1')
		# a file link
		file2 = path.join(self.testdir, 'test_move2')
		# a dead link
		file3 = path.join(self.testdir, 'test_move3')
		# a dir
		file4 = path.join(self.testdir, 'test_move4')
		# a dir link
		file5 = path.join(self.testdir, 'test_move5')
		# not exists
		file6 = path.join(self.testdir, 'test_move6')
		# link to file2
		file10 = path.join(self.testdir, 'test_move10')
		# another link to file1
		file11 = path.join(self.testdir, 'test_move11')
		# unknown
		file7 = None
		file8 = file1
		file9 = file6

		helpers.writeFile(file1)
		symlink(file1, file2)
		symlink(file1, file11)
		helpers.createDeadlink(file3)
		makedirs(file4)
		symlink(file4, file5)
		symlink(file2, file10)

		yield file6, file9, True, False
		yield file6, file1, True, False
		yield file6, file3, True, False
		yield file10, file2, True, False
		yield file2, file1, True, False
		yield file1, file8, True, True
		yield file1, file4, False, False
		yield file1, file10, True, True

	def test_gz(self, file1, file2, overwrite, rout):
		r = SafeFs._gz(file1, file2, overwrite)
		self.assertEqual(r, rout)
		if r:
			if path.isfile(file1):
				with open(file1) as f1, gzip.open(file2) as f2:
					helpers.assertTextEqual(self, utils.asStr(f1.read()), utils.asStr(f2.read()))
			else:
				# test tar.gz
				self.assertTrue(path.isdir(file1))
				self.assertTrue(path.isfile(file2))

	def dataProvider_test_gz(self):
		# a file
		file1 = path.join(self.testdir, 'test_gz1')
		# a file link
		file2 = path.join(self.testdir, 'test_gz2')
		# a dead link
		file3 = path.join(self.testdir, 'test_gz3')
		# a dir
		file4 = path.join(self.testdir, 'test_gz4')
		# a dir link
		file5 = path.join(self.testdir, 'test_gz5')
		# not exists
		file6 = path.join(self.testdir, 'test_gz6')
		# link to file2
		file10 = path.join(self.testdir, 'test_gz10')
		# another link to file1
		file11 = path.join(self.testdir, 'test_gz11')
		# gzipped file1
		file12 = path.join(self.testdir, 'test_gz12.gz')
		# tar gzipped file4
		file13 = path.join(self.testdir, 'test_gz13.tgz')
		# unknown
		file7 = None
		file8 = file1
		file9 = file6

		helpers.writeFile(file1, 'whatever')
		symlink(file1, file2)
		symlink(file1, file11)
		helpers.createDeadlink(file3)
		makedirs(file4)
		symlink(file4, file5)
		symlink(file2, file10)

		yield file3, file6, True, False
		yield file3, file1, True, False
		yield file6, file9, True, False
		yield file2, file1, True, False
		yield file10, file2, True, False
		yield file1, file4, False, False
		yield file4, file13, True, True
		yield file1, file12, True, True

	def test_ungz(self, file1, file2, overwrite, rout):
		r = SafeFs._ungz(file1, file2, overwrite)
		self.assertEqual(r, rout)
		if r:
			if path.isfile(file2):
				with gzip.open(file1) as f1, open(file2) as f2:
					helpers.assertTextEqual(self, utils.asStr(f1.read()), utils.asStr(f2.read()))
			else:
				# test tar.gz
				self.assertTrue(path.isfile(file1))
				self.assertTrue(path.isdir(file2))
	
	def dataProvider_test_ungz(self):
		# a file
		file1 = path.join(self.testdir, 'test_ungz1')
		# a file link
		file2 = path.join(self.testdir, 'test_ungz2')
		# a dead link
		file3 = path.join(self.testdir, 'test_ungz3')
		# a dir
		file4 = path.join(self.testdir, 'test_ungz4')
		# a dir link
		file5 = path.join(self.testdir, 'test_ungz5')
		# not exists
		file6 = path.join(self.testdir, 'test_ungz6')
		# link to file2
		file10 = path.join(self.testdir, 'test_ungz10')
		# another link to file1
		file11 = path.join(self.testdir, 'test_ungz11')
		# gzipped file1
		file12 = path.join(self.testdir, 'test_ungz12.gz')
		# tar gzipped file4
		file13 = path.join(self.testdir, 'test_ungz13.tgz')
		# unknown
		file7 = None
		file8 = file1
		file9 = file6

		helpers.writeFile(file1, 'whatever')
		symlink(file1, file2)
		symlink(file1, file11)
		helpers.createDeadlink(file3)
		makedirs(file4)
		symlink(file4, file5)
		symlink(file2, file10)
		with open(file1, 'rb') as f1, gzip.open(file12, 'wb') as f2:
			copyfileobj(f1, f2)
		remove(file1)
		tar = tarfile.open(file13, 'w:gz')
		cwd = getcwd()
		chdir(file4)
		for name in glob('./*'):
			tar.add(name)
		tar.close()
		chdir(cwd)
		rmtree(file4)

		yield file3, file6, True, False
		yield file3, file1, True, False
		yield file6, file9, True, False
		yield file2, file1, True, False
		yield file10, file2, True, False
		yield file12, file13, False, False
		yield file13, file4, True, True
		yield file12, file1, True, True
		

	def testDirmtime(self, d, mt):
		self.assertEqual(int(SafeFs._dirmtime(d)), int(mt))

	def dataProvider_testDirmtime(self):
		"""
		#0 Empty directory
		"""
		file0 = path.join(self.testdir, 'testDirmtime0.dir')
		makedirs(file0)
		m0    = path.getmtime(file0)
		yield file0, m0

		"""
		#1 A newer file created
		"""
		dir1  = path.join(self.testdir, 'testDirmtime1.dir')
		file1 = path.join(dir1, 'mtime1.txt')
		makedirs(dir1)
		helpers.writeFile(file1)
		t     = time()
		utime(file1, (t+2, t+2))
		yield dir1, t+2

		"""
		#2 dir touched
		"""
		dir2  = path.join(self.testdir, 'testDirmtime2.dir')
		file2 = path.join(dir2, 'mtime2.dir')
		makedirs(file2)
		t = time()
		utime(file2, (t+10, t+10))
		yield dir2, t+10

	def testInit(self, file1, file2):
		sfs = SafeFs(file1, file2, self.tmpdir)
		self.assertEqual(sfs.file1, file1)
		self.assertEqual(sfs.file2, file2)
		self.assertEqual(sfs.filetype1, SafeFs._filetype(file1))
		self.assertEqual(sfs.filetype2, SafeFs._filetype(file2))
		self.assertEqual(sfs.tmpdir, self.tmpdir)
		self.assertEqual(sfs.locks, [])
	
	def dataProvider_testInit(self):
		file1 = path.join(self.testdir, 'testInit1')
		file2 = path.join(self.testdir, 'testInit2')
		yield None, None
		yield file1, None
		yield file1, file2

	def testUnlock(self, sfs):
		sfs._lock()
		self.assertTrue(all([l.is_locked for l in sfs.locks]))
		sfs._unlock()
		self.assertFalse(any([l.is_locked for l in sfs.locks]))
	
	def dataProvider_testUnlock(self):
		yield SafeFs('a', 'b'),

	def testExists(self, filepath, rout, callback = None, outcb = None):
		sfs = SafeFs(filepath)
		r = sfs.exists(callback)
		self.assertFalse(any([l.is_locked for l in sfs.locks]))
		for lock in sfs.locks:
			self.assertFalse(lock.is_locked)
		self.assertEqual(r, rout)
		if callable(outcb):
			self.assertTrue(outcb(sfs.file1))

	def dataProvider_testExists(self):
		# a file
		file1 = path.join(self.testdir, 'testExists1')
		# a file link
		file2 = path.join(self.testdir, 'testExists2')
		helpers.writeFile(file1)
		symlink(file1, file2)

		def callbackRemove(r, fs):
			assert all([l.is_locked for l in fs.locks]) is True
			if r: SafeFs._remove(fs.file1)
		
		def callbackOut(f):
			return not SafeFs._exists(f)

		yield file1, True
		yield file2, True, callbackRemove, callbackOut

	def testSamefile(self, file1, file2, rout, callback = None, outcb = None):
		sfs = SafeFs(file1, file2, self.tmpdir)
		r = sfs.samefile(callback)
		self.assertFalse(any([l.is_locked for l in sfs.locks]))
		if callable(outcb):
			self.assertTrue(outcb(sfs.file1))

	def dataProvider_testSamefile(self):
		# a file
		file1 = path.join(self.testdir, 'testSamefile1')
		# a file link
		file2 = path.join(self.testdir, 'testSamefile2')
		# a dead link
		file3 = path.join(self.testdir, 'testSamefile3')
		# a dir
		file4 = path.join(self.testdir, 'testSamefile4')
		# a dir link
		file5 = path.join(self.testdir, 'testSamefile5')
		# not exists
		file6 = path.join(self.testdir, 'testSamefile6')
		# link to file2
		file10 = path.join(self.testdir, 'testSamefile10')
		# another link to file1
		file11 = path.join(self.testdir, 'testSamefile11')
		# unknown
		file7 = None
		file8 = file1
		file9 = file6

		helpers.writeFile(file1)
		symlink(file1, file2)
		symlink(file1, file11)
		helpers.createDeadlink(file3)
		makedirs(file4)
		symlink(file4, file5)
		symlink(file2, file10)

		def callbackRemove(r, fs):
			assert all([l.is_locked for l in fs.locks]) is True
			if r: SafeFs._remove(fs.file1)
		
		def callbackOut(f):
			return not SafeFs._exists(f)

		yield file11, file2, True
		yield file10, file2, True
		yield file2, file10, True
		yield file2, file1, True
		yield file1, file2, True
		yield file6, file9, True
		yield file1, file8, True, callbackRemove, callbackOut
	
	def testRemove(self, filepath, callback = None):
		sfs = SafeFs(filepath, tmpdir = self.tmpdir)
		r = sfs.remove(callback)
		self.assertFalse(any([l.is_locked for l in sfs.locks]))
		if r:
			self.assertFalse(path.exists(filepath))
	
	def dataProvider_testRemove(self):
		file1 = path.join(self.testdir, 'testRemove1')
		helpers.writeFile(file1)
		
		def callbackCreate(r, fs):
			assert all([l.is_locked for l in fs.locks]) is True
		
		yield file1, callbackCreate

	def testMove(self, file1, file2, callback = None):
		sfs = SafeFs(file1, file2, tmpdir = self.tmpdir)
		r = sfs.move(callback)
		self.assertFalse(any([l.is_locked for l in sfs.locks]))
		self.assertTrue(r)
		if r:
			self.assertFalse(path.exists(file1))
			self.assertTrue(path.exists(file2))
	
	def dataProvider_testMove(self):
		file1 = path.join(self.testdir, 'testMove1')
		file2 = path.join(self.testdir, 'testMove2')
		helpers.writeFile(file1)
		
		def callbackCreate(r, fs):
			assert all([l.is_locked for l in fs.locks]) is True
		
		yield file1, file2, callbackCreate

	def testMoveWithLink(self, file1, file2, callback = None):
		sfs = SafeFs(file1, file2, tmpdir = self.tmpdir)
		r = sfs.moveWithLink(callback)
		self.assertFalse(any([l.is_locked for l in sfs.locks]))
		self.assertTrue(r)
		if r:
			self.assertTrue(path.samefile(file1, file2))
			self.assertTrue(path.islink(file1))
			self.assertFalse(path.islink(file2))
		
	
	def dataProvider_testMoveWithLink(self):
		file1 = path.join(self.testdir, 'testMoveWithLink1')
		file2 = path.join(self.testdir, 'testMoveWithLink2')
		helpers.writeFile(file1)
		
		def callbackCreate(r, fs):
			assert all([l.is_locked for l in fs.locks]) is True
		
		yield file1, file2, callbackCreate

	def testGz(self, file1, file2, callback = None):
		sfs = SafeFs(file1, file2, tmpdir = self.tmpdir)
		r = sfs.gz(callback)
		self.assertFalse(any([l.is_locked for l in sfs.locks]))
		self.assertTrue(r)
		if r:
			self.assertTrue(path.isfile(file1))
			self.assertTrue(path.isfile(file2))		
	
	def dataProvider_testGz(self):
		file1 = path.join(self.testdir, 'testGz1')
		file2 = path.join(self.testdir, 'testGz1.gz')
		helpers.writeFile(file1)
		
		def callbackCreate(r, fs):
			assert all([l.is_locked for l in fs.locks]) is True
		
		yield file1, file2, callbackCreate

	def testUngz(self, file1, file2, callback = None):
		sfs = SafeFs(file1, file2, tmpdir = self.tmpdir)
		r = sfs.ungz(callback)
		self.assertFalse(any([l.is_locked for l in sfs.locks]))
		self.assertTrue(r)
		if r:
			self.assertTrue(path.isfile(file1))
			self.assertTrue(path.isfile(file2))		
	
	def dataProvider_testUngz(self):
		file1 = path.join(self.testdir, 'testUngz1')
		file2 = path.join(self.testdir, 'testUngz1.gz')
		helpers.writeFile(file1)
		SafeFs._gz(file1, file2)
		remove(file1)
		
		def callbackCreate(r, fs):
			assert all([l.is_locked for l in fs.locks]) is True
		
		yield file2, file1, callbackCreate

	def dataProvider_testFilesig(self):
		"""
		#0: Empty string
		"""
		yield '', ['', 0]

		"""
		#1: Path not exists
		"""
		yield '/a/b/pathnotexists', False

		"""
		#2: A file
		"""
		filesig1 = path.join(self.testdir, 'testFilesig1.txt')
		helpers.writeFile(filesig1)
		sig1     = [filesig1, int(path.getmtime(filesig1))]
		yield filesig1, sig1

		"""
		#3: A Link to file
		"""
		filesig2 = path.join(self.testdir, 'testFilesig2.txt')
		symlink(filesig1, filesig2)
		sig2 = [filesig2, sig1[1]]
		yield filesig2, sig2

		"""
		#4: A link to directory
		"""
		filesig3 = path.join(self.testdir, 'testFilesig3.dir')
		filesig4 = path.join(self.testdir, 'testFilesig4.dir')
		makedirs(filesig3)
		symlink(filesig3, filesig4)
		t = int(time())
		utime(filesig3, (t - 10, t - 10))
		sig3 = [filesig4, t - 10]
		yield filesig4, sig3

		"""
		#5: A newer file created
		"""
		filesig5 = path.join(self.testdir, 'testFilesig5.dir')
		filesig6 = path.join(filesig5, 'testFilesig6.txt')
		makedirs(filesig5)
		helpers.writeFile(filesig6)
		t = int(path.getmtime(filesig6))
		utime(filesig6, (t + 10, t + 10))
		sig5 = [filesig5, t+10]
		yield filesig5, sig5

		"""
		#6: Don't go into the dir
		"""
		yield filesig5, [filesig5, t], False

	def testFilesig(self, f, sig, dirsig = True):
		sfs = SafeFs(f)
		self.assertEqual(sfs.filesig(dirsig), sig)
		self.assertFalse(any([l.is_locked for l in sfs.locks]))

	def dataProvider_testChmodX(self):
		"""
		#0: plain file, can be made as executable
		"""
		fileChmodx1 = path.join(self.testdir, 'testChmodX1.txt')
		helpers.writeFile(fileChmodx1)
		yield fileChmodx1, [fileChmodx1]

		"""
		#1:  plain file, cannot be made as executable
		"""
		fileChmodx2 = '/usr/bin/ldd'
		if path.exists(fileChmodx2):
			if access(fileChmodx2, W_OK):
				yield fileChmodx2, [fileChmodx2], True
			else:
				yield fileChmodx2, ['/bin/bash', fileChmodx2]
		
		#2: a dir, raise OSError
		fileChmodx3 = path.join(self.testdir, 'testChmodX.dir')
		makedirs(fileChmodx3)
		yield fileChmodx3, None, OSError

	def testChmodX(self, f, ret, exception = None):
		sfs = SafeFs(f)
		if exception:
			self.assertRaises(exception, sfs.chmodX)
		else:
			self.assertListEqual(sfs.chmodX(), ret)
			self.assertTrue(path.isfile(ret[-1]) and access(ret[-1], X_OK))
			self.assertFalse(any([l.is_locked for l in sfs.locks]))

	def dataProvider_testChmodXException(self):
		file1 = '/bin/ls'
		if path.exists(file1):
			yield file1,

	def testChmodXException(self, f):
		if not access(f, W_OK): # what if I am root?
			self.assertRaises(OSError, SafeFs(f).chmodX)

	
	def dataProvider_testFlushFile(self):
		file1 = path.join(self.testdir, 'testFlushFile1.txt')
		file2 = path.join(self.testdir, 'testFlushFile2.txt')
		file3 = path.join(self.testdir, 'testFlushFile3.txt')
		file4 = path.join(self.testdir, 'testFlushFile4.txt')

		yield (
			file1, [
				('', [], '', False), # string append to the file, lines flushed, and remaining string
				('abcde', [], 'abcde', False),
				('ccc\ne1', ['abcdeccc\n', 'e1\n'], '', True),
			]
		)
		yield (
			file2, [
				('a\nb', ['a\n'], 'b', False), # string append to the file, lines flushed, and remaining string
				('c', [], 'bc', False),
				('d\n', ['bcd\n'], '', True),
			]
		)
		yield (
			file3, [
				('\n', ['\n'], '', False), # string append to the file, lines flushed, and remaining string, end
				('\n', ['\n'], '', False),
				('\na', ['\n', 'a\n'], '', True),
			]
		)
		yield (
			file4, [
				('123', [], '123', False),
				('', ['123\n'], '', True)
			]
		)

	def testFlushFile(self, fn, appends):
		fa = open(fn, 'a')
		fr = open(fn, 'r')
		lastmsg = ''
		for app in appends:
			a, l, r, e = app
			fa.write(a)
			fa.flush()
			lines, lastmsg = SafeFs.flush(fr, lastmsg, e)
			self.assertEqual(l, lines)
			self.assertEqual(r, lastmsg)
		fa.close()
		fr.close()

	def testBasename(self, filepath, basename):
		self.assertEqual(SafeFs.basename(filepath), basename)
	
	def dataProvider_testBasename(self):
		yield '/a/b/c', 'c'
		filepath = path.join(self.testdir, 'testBasename')
		makedirs(filepath)
		yield path.join(self.testdir, 'testBasename/'), 'testBasename'

class TestUtils (testly.TestCase):

	def setUpMeta(self):
		self.testdir = path.join(gettempdir(), 'PyPPL_unittest', 'TestUtils')
		if path.exists(self.testdir):
			rmtree(self.testdir)
		makedirs(self.testdir)
		
	def dataProvider_testBox(self):
		box = Box()
		yield box, {}
		box1 = Box()
		box1.a = Box()
		yield box1, dict(a = {})
		box2 = Box()
		box2.a = Box()
		box2.a.b = 1
		yield box2, dict(a = dict(b = 1))
		box3 = Box()
		box3._OrderedDict__a = 1
		# absorbed by the object!!
		yield box3, dict()
		box4 = Box()
		box4.__a = 1
		yield box4, dict(_TestUtils__a = 1)

	def testBox(self, box, out):
		self.assertDictEqual(box, out)


	def dataProvider_testParallel(self):
		yield ([(1,2), (3,4), (5,6), (7,8)], 4, 'thread')
		yield ([(1,2), (3,4), (5,6), (7,8)], 4, 'process')
		yield ([(1,0), (3,4), (5,6), (7,8)], 4, 'process', ZeroDivisionError)

	def testParallel(self, data, nthread, method, exception = None):
		globalVars = []
		interval   = .2
		def func(a, b):
			sleep(interval)
			globalVars.append(a)
			globalVars.append(b)
			a/b # raise exception

		if exception:
			self.assertRaises(exception, utils.parallel.run, func, data, nthread, method)
		else:
			t0 = time()
			#Parallel(nthread, method).run(func, data)
			utils.parallel.run(func, data, nthread, method)
			t = time() - t0
			if method == 'thread':
				self.assertCountEqual(utils.reduce(lambda x, y: list(x) + list(y), data), globalVars)
			else: # globalVars not shared between processes
				self.assertListEqual([], globalVars)
			self.assertLess(t, interval * nthread * 2)

	def dataProvider_testVarname(self):
		class Klass(object):
			def __init__(self, default='', d2=''):
				self.id = utils.varname()

			def copy(self, *arg):
				return utils.varname()

		def func():
			return utils.varname()

		h = Klass()
		h2 = Klass()
		h3 = Klass(
			default = 'a',
			d2 = 'c'
		)
		h4 = [Klass()]
		v1 = h.copy()
		v2 = h2.copy(
			2,
			3,
			4
		)
		v3 = [h3.copy(
			1, 2,
			4
		)]
		f = func()
		f2 = [func()]

		yield (h.id, 'h')
		yield (h2.id, 'h2')
		yield (h3.id, 'h3')
		yield (h4[0].id, 'var_0')
		yield (v1, 'v1')
		yield (v2, 'v2')
		yield (v3[0], 'var_1')
		yield (f, 'f')
		yield (f2[0], 'var_2')

	def testVarname(self, idExpr, idVal):
		self.assertEqual(idExpr, idVal)

	def dataProvider_testMap(self):
		yield ([1, 0, False, '', '0', 2], str, ['1', '0', 'False', '', '0', '2'])
		yield ([1, 0, False, '', '0', 2], bool, [True, False, False, False, True, True])
		yield ([1, 0, False, '1', '0', 2], int, [1, 0, 0, 1, 0, 2])

	def testMap(self, l, func, ret):
		self.assertEqual(utils.map(func, l), ret)

	def dataProvider_testReduce(self):
		yield ([1, 0, False, '1', '0', 2], lambda x, y: str(x) + str(y), '10False102')
		yield ([1, 0, False, '1', '0', 2], lambda x, y: int(x) + int(y), 4)
		yield ([1, 0, False, '1', '0', 2], lambda x, y: bool(x) and bool(y), False)

	def testReduce(self, l, func, ret):
		self.assertEqual(utils.reduce(func, l), ret)

	def dataProvider_testFilter(self):
		yield ([1, 0, False, '1', '0', 2], lambda x: isinstance(x, int), [1, 0, False, 2])
		yield ([1, 0, False, '1', '0', 2], None, [1, '1', '0', 2])
		yield ([1, 0, False, '1', '0', 2], lambda x: not bool(x), [0, False])

	def testFilter(self, l, func, ret):
		self.assertEqual(utils.filter(func, l), ret)

	def dataProvider_testSplit(self):
		yield ("a|b|c", "|", ["a", "b", "c"])
		yield ('a|b\|c', "|", ["a", "b\\|c"])
		yield ('a|b\|c|(|)', "|", ["a", "b\\|c", "(|)"])
		yield ('a|b\|c|(\)|)', "|", ["a", "b\\|c", "(\\)|)"])
		yield ('a|b\|c|(\)\\\'|)', "|", ["a", "b\\|c", "(\\)\\'|)"])
		yield ('outdir:dir:{{in.pattern | lambda x: __import__("glob").glob(x)[0] | fn }}_etc', ':', ["outdir", "dir", "{{in.pattern | lambda x: __import__(\"glob\").glob(x)[0] | fn }}_etc"])

	def testSplit (self, s, d, a):
		self.assertEqual(utils.split(s, d), a)

	def dataProvider_testDictUpdate(self):
		yield (
			{"a":1, "b":{"c": 3, "d": 9}},       # original dict
			{"b":{"c": 4}, "c":8},               # replacement
			{"a":1, "b":{"c":4, "d":9}, "c":8},  # result of utils.update
			{"a":1, "b":{"c": 4}, "c":8},        # result of naive update
		)
		yield (
			{'args': {'inopts': {'ftype': 'head'}}},
			{'args': {'inopts': {'ftype': 'nometa'}}},
			{'args': {'inopts': {'ftype': 'nometa'}}},
			{'args': {'inopts': {'ftype': 'nometa'}}}
		)
		yield (
			{},
			{"b":{"c": 4}, "c":8},
			{"b":{"c": 4}, "c":8},
			{"b":{"c": 4}, "c":8},
		)
		yield (
			{'a':1,'b':2,'c':[3,4],'d':{'a':0}},
			{'a':1,'b':2,'c':[1,4],'d':{'a':1}},
			{'a':1,'b':2,'c':[1,4],'d':{'a':1}},
			{'a':1,'b':2,'c':[1,4],'d':{'a':1}},
		)
		yield (
			{'runner': 'local'},
			{'runner': 'local'},
			{'runner': 'local'},
			{'runner': 'local'}
		)

	def testDictUpdate (self, odict, rdict, uodict, nodict):
		dict_utilsupdate = deepcopy(odict)
		dict_naiveupdate = deepcopy(odict)

		utils.dictUpdate(dict_utilsupdate, rdict)
		dict_naiveupdate.update(rdict)
		#print rdict
		self.assertDictEqual(dict_utilsupdate, uodict)
		self.assertDictEqual(dict_naiveupdate, nodict)

	def dataProvider_testFuncSig(self):
		def func1():
			pass
		func2 = lambda x: x
		func3 = ""
		func4 = "A"
		yield (func1, "def func1():\n\t\t\tpass")
		yield (func2, "func2 = lambda x: x")
		yield (func3, "None")
		yield (func4, "None")

	def testFuncSig (self, func, src):
		self.assertEqual (utils.funcsig(func).strip(), src)

	def dataProvider_testUid(self):
		yield ('a', 'O4JnVAW7')
		yield ('', '6SFsQFoW')

	def testUid(self, s, uid):
		self.assertEqual(utils.uid(s), uid)

	def testUidUnique (self):
		import random, string

		def randomword(length):
		   return ''.join(random.choice(list('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890')) for i in range(length)).encode('utf-8')

		uids = {}
		for _ in range (10000):
			s = randomword (10)
			uid = utils.uid (s)
			self.assertEqual(uid, utils.uid(s))
			uids[uid] = 1
		self.assertEqual (len (uids.keys()), 10000)

	def dataProvider_testFormatsecs(self):
		yield (1, "00:00:01.000")
		yield (1.001, "00:00:01.001")
		yield (100, "00:01:40.000")
		yield (7211, "02:00:11.000")

	def testFormatsecs(self, sec, secstr):
		self.assertEqual (utils.formatSecs(sec), secstr)

	def dataProvider_testRange(self):
		yield (utils.range(3), [0,1,2])
		yield (utils.range(1), [0])
		yield (utils.range(0), [])

	def testRange(self, r1, r2):
		self.assertEqual (type(r1), type(r2))
		self.assertEqual (r1, r2)

	def dataProvider_testAlwayslist(self):
		yield ("a, b,c", ['a', 'b', 'c'])
		yield (["a, b,c"], ['a', 'b', 'c'])
		yield (["a, b,c", 'd'], ['a', 'b', 'c', 'd'])
		yield ("a,b, c, 'd,e'", ['a', 'b', 'c', "'d,e'"])
		yield (
			["o1:var:{{c1}}", "o2:var:{{c2 | __import__('math').pow(float(_), 2.0)}}", "o3:file:{{c3.fn}}2{{c3.ext}}"],
			["o1:var:{{c1}}", "o2:var:{{c2 | __import__('math').pow(float(_), 2.0)}}", "o3:file:{{c3.fn}}2{{c3.ext}}"]
		)
		yield (
			["o1:var:{{c1}}", "o2:var:c2 | __import__('math').pow float(_), 2.0)}}", "o3:file:{{c3.fn}}2{{c3.ext}}"],
			#                                                             ^ comma is not quoted
			["o1:var:{{c1}}", "o2:var:c2 | __import__('math').pow float(_)", "2.0)}}", "o3:file:{{c3.fn}}2{{c3.ext}}"]
		)

	def testAlwayslist(self, albefore, alafter):
		self.assertSequenceEqual (utils.alwaysList (albefore), alafter)

	def dataProvider_testAlwayslistException(self):
		yield ({'a': 1}, )
		yield (None, )
		yield ((1,2), )

	def testAlwayslistException(self, albefore):
		self.assertRaises(ValueError, utils.alwaysList, albefore)

	def dataProvider_test1FS(self):

		def _int(s):
			return 0 if not s else int(s)

		def _write(r, f):
			if isinstance(f, SafeFs):
				f = f.file1
			if not r:
				helpers.writeFile(f, 1)
			else:
				i = helpers.readFile(f, _int)
				helpers.writeFile(f, i+1)

		def _delayRemove(r, f):
			if isinstance(f, SafeFs):
				f = f.file1
			sleep(.1)
			if r: remove(f)

		"""
		Simple file exists: 0-2
		"""
		file01 = path.join(self.testdir, 'testFileExists01.txt')
		file02 = path.join(self.testdir, 'testFileExists02.txt')
		file03 = path.join(self.testdir, 'testFileExists03.dir')
		flag01 = path.join(self.testdir, 'testFileExists01-flag.txt')
		flag02 = path.join(self.testdir, 'testFileExists02-flag.txt')
		flag03 = path.join(self.testdir, 'testFileExists03-flag.txt')
		helpers.writeFile(file01)
		makedirs(file03)
		def func01(f):
			#if SafeFs(f, tmpdir = self.testdir).exists():
			# shortcut
			if utils.safefs.exists(f):
				helpers.writeFile(flag01)
		def func02(f):
			if SafeFs(f, tmpdir = self.testdir).exists():
				helpers.writeFile(flag02)
		def func03(f):
			if SafeFs(f, tmpdir = self.testdir).exists():
				helpers.writeFile(flag03)
		yield (func01, file01, 2,  lambda: path.exists(flag01))
		yield (func02, file02, 2,  lambda: not path.exists(flag02))
		yield (func03, file03, 2,  lambda: path.exists(flag03))

		"""
		Thread-safe file exists, increment the number in a file: 3
		"""
		file1 = path.join(self.testdir, 'testFileExists1.txt')
		# thread-safe, so number accumulates
		def func1(f):
			SafeFs(f, tmpdir = self.testdir).exists(_write)
		yield (func1,  file1,  20, lambda: helpers.readFile(file1, _int) == 20)

		"""
		Thread-unsafe file exists, number will not accumulated to max: 4
		"""
		file2 = path.join(self.testdir, 'testFileExists2.txt')
		# non-thread-safe, so number may be lost
		def func2(f):
			_write(path.exists(f), f)
		yield (func2,  file2,  20, lambda: helpers.readFile(file2, _int) < 20)

		"""
		Thread-safe file exists, remove a file in multiple thread, no error: 5
		"""
		file3 = path.join(self.testdir, 'testFileExists3.txt')
		flag3 = path.join(self.testdir, 'testFileExists3-flag.txt')
		helpers.writeFile(file3)
		# thread-safe, so no flag file generated
		def func3(f):
			try:
				SafeFs(f, tmpdir = self.testdir).exists(_delayRemove)
			except OSError as ex:
				helpers.writeFile(flag3)
		yield (func3,  file3,  10, lambda: not path.exists(flag3))

		"""
		Thread-unsafe file exists, remove a file in multiple thread, error happens
		"""
		file4 = path.join(self.testdir, 'testFileExists4.txt')
		flag4 = path.join(self.testdir, 'testFileExists4-flag.txt')
		helpers.writeFile(file4)
		# thread-safe, so no flag file generated
		def func4(f):
			try:
				_delayRemove(path.exists(f), f)
			except OSError:
				helpers.writeFile(flag4)
		yield (func4,  file4,  10, lambda: path.exists(flag4))

		"""
		Thread-safe file remove, remove file in multiple thread, no error
		"""
		file5 = path.join(self.testdir, 'testFileRemove1.txt')
		flag5 = path.join(self.testdir, 'testFileRemove1-flag.txt')
		helpers.writeFile(file5)
		def func5(f):
			try:
				SafeFs(f, tmpdir = self.testdir).remove(lambda r, fs: r and helpers.writeFile(fs.file1))
			except OSError:
				helpers.writeFile(flag5)
		yield (func5,  file5,  10, lambda: not path.exists(flag5))

		"""
		Thread-safe file remove, remove directory in multiple thread, no error
		"""
		file51 = path.join(self.testdir, 'testFileRemove1.dir')
		flag51 = path.join(self.testdir, 'testFileRemove1dir-flag.txt')
		makedirs(file51)
		def func51(f):
			try:
				#SafeFs(f, tmpdir = self.testdir).remove()
				utils.safefs.remove(f)
			except OSError as ex:
				helpers.writeFile(flag51, ex)
		yield (func51, file51, 10, lambda: not path.exists(file51) and not path.exists(flag51))

		"""
		Thread-unsafe file remove, remove file in multiple thread, error happens
		"""
		file6 = path.join(self.testdir, 'testFileRemove2.txt')
		flag6 = path.join(self.testdir, 'testFileRemove2-flag.txt')
		helpers.writeFile(file6)
		def func6(f):
			try:
				_delayRemove(path.exists(f), f)
			except OSError:
				helpers.writeFile(flag6)
		yield (func6,  file6,  10, lambda: path.exists(flag6))

	def test1FS(self, func, f, length, state):
		Parallel(length, 'thread').run(func, [(f, ) for _ in range(length)])
		self.assertTrue(state())

	def dataProvider_test2FS(self):

		def _int(s):
			return 0 if not s else int(s)

		def _write(r, f1, f2 = None):
			if isinstance(f1, SafeFs):
				f1, f2 = f1.file1, f1.file2
			if not r:
				helpers.writeFile(f1, 1)
			else:
				i = helpers.readFile(f1, _int)
				helpers.writeFile(f1, i+1)

		def _delayRemove(r, f):
			if isinstance(f, SafeFs):
				f = f.file1
			sleep(.1)
			if r: remove(f)

		"""
		#0,1 Simple samefile
		"""
		file01 = path.join(self.testdir, 'testSamefile01.txt')
		file02 = path.join(self.testdir, 'testSamefile02.txt')
		flag0  = path.join(self.testdir, 'testSamefileFlag0.txt')
		helpers.writeFile(file01)
		symlink(file01, file02)
		def func0(f1, f2):
			#if not utils.samefile(f1, f2, tmpdir = self.testdir):
			if not SafeFs(f1, f2, tmpdir = self.testdir).samefile():
				helpers.writeFile(flag0)
		yield (func0, file01, file02, 10, lambda: not path.exists(flag0))

		file11 = path.join(self.testdir, 'testSamefile11.txt')
		file12 = path.join(self.testdir, 'testSamefile12.txt')
		flag1  = path.join(self.testdir, 'testSamefileFlag1.txt')
		def func1(f1, f2):
			if not SafeFs(f1, f2, tmpdir = self.testdir).samefile():
				helpers.writeFile(flag1)
		yield (func1, file11, file12, 10, lambda: path.exists(flag1))

		"""
		#2 Thread-safe samefile, increment the number in a file
		"""
		file21 = path.join(self.testdir, 'testSamefile21.txt')
		file22 = path.join(self.testdir, 'testSamefile22.txt')
		helpers.writeFile(file21)
		symlink(file21, file22)
		# thread-safe, so number accumulates
		def func2(f1, f2):
			SafeFs(f1, f2, tmpdir = self.testdir).samefile(_write)
		yield (func2, file21, file22, 20, lambda: helpers.readFile(file21, _int) == 20)

		"""
		#3 Thread-unsafe samefile, number will not accumulated to max
		"""
		file31 = path.join(self.testdir, 'testSamefile31.txt')
		file32 = path.join(self.testdir, 'testSamefile32.txt')
		helpers.writeFile(file31)
		symlink(file31, file32)
		# non-thread-safe, so number may be lost
		def func3(f1, f2):
			_write(path.samefile(f1, f2), f1, f2)
		yield (func3, file31, file32, 20, lambda: helpers.readFile(file31, _int) < 20)

		"""
		#4 Thread-safe samefile, remove a file in multiple thread, no error
		"""
		file41 = path.join(self.testdir, 'testSamefile41.txt')
		file42 = path.join(self.testdir, 'testSamefile42.txt')
		flag4  = path.join(self.testdir, 'testSamefile4-flag.txt')
		helpers.writeFile(file41)
		symlink(file41, file42)
		# thread-safe, so no flag file generated
		def func4(f1, f2):
			try:
				SafeFs(f1, f2, tmpdir = self.testdir).samefile(callback = lambda r, fs: _delayRemove(r, fs.file2))
			except OSError as ex:
				helpers.writeFile(flag4, ex)
		yield (func4, file41, file42, 10, lambda: not path.exists(flag4))


		"""
		#5 Thread-safe samefile, remove a file in multiple thread, error happens
		"""
		file51 = path.join(self.testdir, 'testSamefile51.txt')
		file52 = path.join(self.testdir, 'testSamefile52.txt')
		flag5  = path.join(self.testdir, 'testSamefile5-flag.txt')
		helpers.writeFile(file51)
		symlink(file51, file52)
		# thread-safe, so no flag file generated
		def func5(f1, f2):
			try:
				_delayRemove(path.samefile(f1, f2), f2)
			except OSError as ex:
				helpers.writeFile(flag5, ex)
		yield (func5, file51, file52, 10, lambda: path.exists(flag5))

		"""
		#6 Thread-safe move, move one file in multiple thread, no error
		"""
		file61 = path.join(self.testdir, 'testMove1.txt')
		file62 = path.join(self.testdir, 'testMove2.txt')
		flag6  = path.join(self.testdir, 'testMove1-flag.txt')
		helpers.writeFile(file61)

		def func6(f1, f2):
			try:
				#SafeFs(f1, f2, tmpdir = self.testdir).move()
				utils.safefs.move(f1, f2)
			except OSError as ex:
				helpers.writeFile(flag6, ex)
		yield (func6, file61, file62, 10, lambda: not path.exists(flag6) and path.exists(file62) and not  path.exists(file61))

		"""
		#7 Thread-safe move, move the a file to its link, overwritten
		"""
		file63 = path.join(self.testdir, 'testMove63.txt')
		file64 = path.join(self.testdir, 'testMove64.txt')
		helpers.writeFile(file63)
		symlink(file63, file64)
		def func63(f1, f2):
			SafeFs(f1, f2, tmpdir = self.testdir).move()
		yield (func63, file63, file64, 1, lambda: not path.exists(file63) and path.isfile(file64) and not path.islink(file64))

		"""
		#8 Thread-safe move, move the file, without overwrite
		"""
		file65 = path.join(self.testdir, 'testMove5.txt')
		file66 = path.join(self.testdir, 'testMove6.txt')
		helpers.writeFile(file65, 65)
		helpers.writeFile(file66, 66)
		def func65(f1, f2):
			SafeFs(f1, f2, tmpdir = self.testdir).move(overwrite = False)
		yield (func65, file65, file66, 1, lambda: helpers.readFile(file66, int) == 66)

		"""
		#9 Thread-safe move, move the file, with overwrite
		"""
		file67 = path.join(self.testdir, 'testMove7.txt')
		file68 = path.join(self.testdir, 'testMove8.txt')
		helpers.writeFile(file67, 67)
		helpers.writeFile(file68, 68)
		def func67(f1, f2):
			SafeFs(f1, f2, tmpdir = self.testdir).move(overwrite = True)
		yield (func67, file67, file68, 1, lambda: helpers.readFile(file68, int) == 67)

		"""
		#10 Thread-unsafe move, move one file in multiple thread, error happens
		"""
		file71 = path.join(self.testdir, 'testMove3.txt')
		file72 = path.join(self.testdir, 'testMove4.txt')
		flag7  = path.join(self.testdir, 'testMove3-flag.txt')
		helpers.writeFile(file71)

		def func7(f1, f2):
			try:
				rename(f1, f2)
			except OSError as ex:
				helpers.writeFile(flag7, ex)
		yield (func7, file71, file72, 10, lambda: path.exists(flag7) and path.exists(file72) and not  path.exists(file71))

		"""
		#11 Thread-safe safeMoveWithLink
		"""
		file81 = path.join(self.testdir, 'testMoveWithLink81.txt')
		file82 = path.join(self.testdir, 'testMoveWithLink82.txt')
		flag8  = path.join(self.testdir, 'testMoveWithLink8-flag.txt')
		helpers.writeFile(file81)
		def func8(f1, f2):
			try:
				SafeFs(f1, f2, tmpdir = self.testdir).moveWithLink()
			except OSError as ex:
				helpers.writeFile(flag8, ex)
		yield (func8, file81, file82, 2, lambda: not path.exists(flag8) and path.exists(file81) and  path.islink(file81) and path.exists(file82) and not path.islink(file82))

		"""
		#12 Thread-unsafe safeMoveWithLink
		"""
		file91 = path.join(self.testdir, 'testMoveWithLink21.txt')
		file92 = path.join(self.testdir, 'testMoveWithLink22.txt')
		flag9  = path.join(self.testdir, 'testMoveWithLink2-flag.txt')
		helpers.writeFile(file91)
		def func9(f1, f2):
			try:
				rename(f1, f2)
				sleep (.05)
				symlink(f2, f1)
			except OSError as ex:
				helpers.writeFile(flag9, ex)
		yield (func9, file91, file92, 20, lambda: path.exists(flag9))

		"""
		#13 Thread-safe copy
		"""
		file101 = path.join(self.testdir, 'testSafeCopy11.txt')
		file102 = path.join(self.testdir, 'testSafeCopy12.txt')
		flag10  = path.join(self.testdir, 'testSafeCopy10-flag.txt')
		helpers.writeFile(file101)
		def func10(f1, f2):
			try:
				SafeFs(f1, f2, tmpdir = self.testdir).copy(callback = _delayRemove)
				#utils.safeCopy(f1, f2, lambda r, f1, f2: remove(f1) if r else None, tmpdir = self.testdir)
			except OSError as ex:
				helpers.writeFile(flag10, ex)
		yield (func10, file101, file102, 10, lambda: not path.exists(flag10) and not path.isfile(file101) and path.isfile(file102))

		"""
		#14 Thread-unsafe copy
		"""
		file111 = path.join(self.testdir, 'testSafeCopy21.txt')
		file112 = path.join(self.testdir, 'testSafeCopy22.txt')
		flag11  = path.join(self.testdir, 'testSafeCopy11-flag.txt')
		helpers.writeFile(file111)
		def func11(f1, f2):
			try:
				copyfile(f1, f2)
				remove(f1)
			except (OSError, IOError) as ex:
				helpers.writeFile(flag11, ex)
		yield (func11, file111, file112, 10, lambda: path.exists(flag11) and not path.isfile(file111) and  path.isfile(file112))

		"""
		#15 Thread-safe link
		"""
		file121 = path.join(self.testdir, 'testSafeLink11.txt')
		file122 = path.join(self.testdir, 'testSafeLink12.txt')
		flag12  = path.join(self.testdir, 'testSafeLink1-flag.txt')
		helpers.writeFile(file121)
		def func12(f1, f2):
			try:
				SafeFs(file121, file122, tmpdir = self.testdir).link(callback = _delayRemove)
			except OSError as ex:
				helpers.writeFile(flag12, ex)
		yield (func12, file121, file122, 10, lambda: not path.exists(flag12) and not path.isfile(file121) and not path.exists(file122))

		"""
		#16 Thread-unsafe link
		"""
		file131 = path.join(self.testdir, 'testSafeLink21.txt')
		file132 = path.join(self.testdir, 'testSafeLink22.txt')
		flag13  = path.join(self.testdir, 'testSafeLink2-flag.txt')
		helpers.writeFile(file131)
		def func13(f1, f2):
			try:
				symlink(f1, f2)
				remove(f1)
			except OSError as ex:
				helpers.writeFile(flag13, ex)
		yield (func13, file131, file132, 10, lambda: path.exists(flag13) and not path.isfile(file131) and  path.islink(file132))

		"""
		#17 Thread-safe file exists, dead link removed
		"""
		file141 = path.join(self.testdir, 'testFileExists141.txt')
		file142 = path.join(self.testdir, 'testFileExists142.txt')
		flag141 = path.join(self.testdir, 'testFileExists141-flag.txt')
		helpers.writeFile(file141)
		symlink(file141, file142)
		remove(file141)
		flag142 = not path.exists(file141) and not path.exists(file142) and path.islink(file142)
		# now file21 is a dead link
		def func14(f1, f2):
			r = SafeFs(f2, tmpdir = self.testdir).exists()
			if r or path.exists(f1) or path.exists(f2) or path.islink(f2):
				helpers.writeFile(flag141)
		yield (func14, file141, file142, 1, lambda: flag142 and not path.exists(flag141))

		"""
		#18 Thread-unsafe file exists, dead link not removed
		"""
		file151 = path.join(self.testdir, 'testFileExists151.txt')
		file152 = path.join(self.testdir, 'testFileExists152.txt')
		flag151 = path.join(self.testdir, 'testFileExists151-flag.txt')
		helpers.writeFile(file151)
		symlink(file151, file152)
		remove(file151)
		flag152 = not path.exists(file151) and not path.exists(file152) and path.islink(file152)
		# now file21 is a dead link
		def func15(f1, f2):
			r = path.exists(f2)
			if r or path.exists(f1) or path.exists(f2) or path.islink(f2):
				helpers.writeFile(flag151)
		yield (func15, file151, file152, 1, lambda: flag152 and path.exists(flag151))

		"""
		#19 Targz: source is not a dir
		"""
		filetgz1 = path.join(self.testdir, 'testTgz1.txt')
		filetgz2 = path.join(self.testdir, 'testTgz2.tgz')
		filetgzflag1 = path.join(self.testdir, 'testTgz1-flag.txt')
		def functgz1(f1, f2):
			#if SafeFs(f1, f2, tmpdir = self.testdir).gz():
			if utils.safefs.gz(f1, f2):
				helpers.writeFile(filetgzflag1)
		yield (functgz1, filetgz1, filetgz2, 2, lambda: not path.exists(filetgzflag1))

		"""
		#20 Targz: overwrite target
		"""
		filetgz3 = path.join(self.testdir, 'testTgz3.dir')
		filetgz4 = path.join(self.testdir, 'testTgz3.tgz')
		makedirs(filetgz3)
		helpers.writeFile(filetgz4, '1')
		def functgz3(f1, f2):
			SafeFs(f1, f2, tmpdir = self.testdir).gz()
		yield (functgz3, filetgz3, filetgz4, 2, lambda: helpers.readFile(filetgz4) != '1')

		"""
		#21 Targz and untargz
		"""
		filetgz5 = path.join(self.testdir, 'testTgz5.dir')
		filetgz6 = path.join(self.testdir, 'testTgz6.tgz')
		filetgz7 = path.join(filetgz5, 'testTgz7.txt')
		filetgz8 = path.join(filetgz5, 'testTgz8.dir')
		filetgz51 = path.join(self.testdir, 'testTgz51.dir')
		filetgz9 = path.join(filetgz51, 'testTgz7.txt')
		makedirs(filetgz5)
		makedirs(filetgz8)
		helpers.writeFile(filetgz7, 'Hello')
		def functgz5(f1, f2):
			SafeFs(f1, f2, tmpdir = self.testdir).gz(callback = lambda r, fs: None)
			SafeFs(f2, filetgz51, tmpdir = self.testdir).ungz(callback = lambda r, fs: None)

		yield (functgz5, filetgz5, filetgz6, 2, lambda: helpers.readFile(filetgz9) == 'Hello')

		"""
		#22 Gz: source is not a file
		"""
		filegz1 = path.join(self.testdir, 'testGz1.txt')
		filegz2 = path.join(self.testdir, 'testGz2.gz')
		filegzflag1 = path.join(self.testdir, 'testGz1-flag.txt')
		def funcgz1(f1, f2):
			if SafeFs(f1, f2, tmpdir = self.testdir).gz():
				helpers.writeFile(filegzflag1)
		yield (funcgz1, filegz1, filegz2, 2, lambda: not path.exists(filegzflag1))

		"""
		#23 Gz: overwrite target
		"""
		filegz3 = path.join(self.testdir, 'testGz3.txt')
		filegz4 = path.join(self.testdir, 'testGz3.gz')
		helpers.writeFile(filegz3, '2')
		helpers.writeFile(filegz4, '1')
		def funcgz3(f1, f2):
			#SafeFs(f1, f2, tmpdir = self.testdir).gz()
			utils.safefs.gz(f1, f2)
		yield (funcgz3, filegz3, filegz4, 2, lambda: helpers.readFile(filegz4) != '1')

		"""
		#24 Gz and ungz
		"""
		filegz5 = path.join(self.testdir, 'testGz5.txt')
		filegz6 = path.join(self.testdir, 'testGz6.gz')
		filegz7 = path.join(self.testdir, 'testGz7.txt')
		helpers.writeFile(filegz5, 'HelloWorld')
		def funcgz5(f1, f2):
			SafeFs(f1, f2, tmpdir = self.testdir).gz()
			#utils.safefs.gz(f1, f2)
			SafeFs(f2, filegz7, tmpdir = self.testdir).ungz()
			#utils.safefs.ungz(f1, f2)
			#dead lock generated when use shortcuts, why?
		yield (funcgz5, filegz5, filegz6, 2, lambda: helpers.readFile(filegz7) == 'HelloWorld')

		"""
		#25 Thread-safe move, move one directory in multiple thread, no error
		"""
		file251 = path.join(self.testdir, 'testMove251.dir')
		file252 = path.join(self.testdir, 'testMove252.dir')
		flag25  = path.join(self.testdir, 'testMove25-flag.txt')
		makedirs(file251)
		makedirs(file252)

		def func25(f1, f2):
			try:
				SafeFs(f1, f2, tmpdir = self.testdir).move(overwrite = True)
			except OSError as ex:
				helpers.writeFile(flag25, ex)
		yield (func25, file251, file252, 10, lambda: not path.exists(flag25) and path.exists(file252) and not  path.exists(file251))

		"""
		#26 Thread-safe safeMoveWithLink, f1, f2 is the same file, f2 is a link
		"""
		file261 = path.join(self.testdir, 'testMoveWithLink261.txt')
		file262 = path.join(self.testdir, 'testMoveWithLink262.txt')
		flag26  = path.join(self.testdir, 'testMoveWithLink26-flag.txt')
		helpers.writeFile(file261)
		symlink(file261, file262)
		def func26(f1, f2):
			try:
				SafeFs(f1, f2, tmpdir = self.testdir).moveWithLink(callback = lambda r, fs: None)
			except OSError:
				helpers.writeFile(flag26, traceback.format_exc())
		yield (func26, file261, file262, 100, lambda: not path.exists(flag26) and path.exists(file261) and  path.islink(file261) and path.exists(file262) and not path.islink(file262))

		"""
		#27 Thread-safe safeMoveWithLink, f1 is link and to be removed
		"""
		file271 = path.join(self.testdir, 'testMoveWithLink271.txt')
		file272 = path.join(self.testdir, 'testMoveWithLink272.txt')
		flag27  = path.join(self.testdir, 'testMoveWithLink27-flag.txt')
		helpers.writeFile(file271)
		helpers.createDeadlink(file272)
		def func27(f1, f2):
			try:
				SafeFs(f1, f2, tmpdir = self.testdir).moveWithLink(overwrite = False)
			except OSError:
				helpers.writeFile(flag27, traceback.format_exc())
		yield (func27, file271, file272, 10, lambda: not path.exists(flag27) and path.exists(file271) and path.islink(file271) and path.exists(file272) and not path.islink(file272))

		"""
		#28 Thread-safe copy
		"""
		file281 = path.join(self.testdir, 'testSafeCopy281.dir')
		file282 = path.join(self.testdir, 'testSafeCopy282.dir')
		flag28  = path.join(self.testdir, 'testSafeCopy28-flag.txt')
		makedirs(file281)
		symlink(file281, file282)
		def func28(f1, f2):
			try:
				SafeFs(f1, f2, tmpdir = self.testdir).copy(overwrite = False)
			except OSError:
				helpers.writeFile(flag28, traceback.format_exc())
		yield (func28, file281, file282, 10, lambda: not path.exists(flag28) and path.isdir(file281) and path.isdir(file282))

		"""
		#29 Thread-safe copy
		"""
		file291 = path.join(self.testdir, 'testSafeCopy291.dir')
		file292 = path.join(self.testdir, 'testSafeCopy292.dir')
		flag29  = path.join(self.testdir, 'testSafeCopy29-flag.txt')
		makedirs(file291)
		makedirs(file292)
		def func29(f1, f2):
			try:
				SafeFs(f1, f2, tmpdir = self.testdir).copy(overwrite = True)
			except OSError:
				helpers.writeFile(flag29, traceback.format_exc())
		yield (func29, file291, file292, 10, lambda: not path.exists(flag29) and path.isdir(file291) and path.isdir(file292))

		"""
		#30 Thread-safe copy
		"""
		file301 = path.join(self.testdir, 'testSafeCopy301.dir')
		file302 = path.join(self.testdir, 'testSafeCopy302.dir')
		flag30  = path.join(self.testdir, 'testSafeCopy30-flag.txt')
		makedirs(file301)
		helpers.writeFile(file302)
		def func30(f1, f2):
			try:
				#SafeFs(f1, f2, tmpdir = self.testdir).copy(overwrite = True)
				utils.safefs.copy(f1, f2, overwrite = True)
			except OSError:
				helpers.writeFile(flag30, traceback.format_exc())
		yield (func30, file301, file302, 10, lambda: not path.exists(flag30) and path.isdir(file301) and path.isdir(file302))

		"""
		#31 Thread-safe link, samefile
		"""
		file311 = path.join(self.testdir, 'testSafeLink311.txt')
		file312 = path.join(self.testdir, 'testSafeLink312.txt')
		flag31  = path.join(self.testdir, 'testSafeLink31-flag.txt')
		helpers.writeFile(file311)
		symlink(file311, file312)
		def func31(f1, f2):
			try:
				#SafeFs(f1, f2, tmpdir = self.testdir).link(overwrite = True)
				utils.safefs.link(f1, f2, overwrite = True)
			except OSError as ex:
				helpers.writeFile(flag31, ex)
		yield (func31, file311, file312, 10, lambda: not path.exists(flag31) and path.isfile(file311) and path.islink(file312))

		"""
		#32 Thread-safe link, not the samefile, f1 is dir
		"""
		file321 = path.join(self.testdir, 'testSafeLink321.dir')
		file322 = path.join(self.testdir, 'testSafeLink322.txt')
		flag32  = path.join(self.testdir, 'testSafeLink32-flag.txt')
		makedirs(file321)
		helpers.writeFile(file322)
		def func32(f1, f2):
			try:
				SafeFs(f1, f2, tmpdir = self.testdir).link(overwrite = True)
			except OSError as ex:
				helpers.writeFile(flag32, ex)
		yield (func32, file321, file322, 10, lambda: not path.exists(flag32) and path.isdir(file321) and path.islink(file322))

		"""
		#33 samefile f1 == f2 with callback
		"""
		file331 = path.join(self.testdir, 'testSamefile331.txt')
		file332 = path.join(self.testdir, 'testSamefile331.txt')
		flag33  = path.join(self.testdir, 'testSamefile33-flag.txt')
		helpers.writeFile(file331)
		def func33(f1, f2):
			SafeFs(f1, f2, tmpdir = self.testdir).samefile(callback = lambda r, fs: r or helpers.writeFile(flag33))
		yield func33, file331, file332, 1, lambda: not path.exists(flag33)

		"""
		#34 move f1 == f2 with callback
		"""
		file341 = path.join(self.testdir, 'testSamefile341.txt')
		file342 = path.join(self.testdir, 'testSamefile341.txt')
		flag34  = path.join(self.testdir, 'testSamefile34-flag.txt')
		helpers.writeFile(file341)
		def func34(f1, f2):
			SafeFs(f1, f2, tmpdir = self.testdir).move(callback = lambda r, fs: r and helpers.writeFile(flag34))
		yield func34, file341, file342, 1, lambda: path.exists(flag34)

		"""
		#35 move f2 is a deak link with callback
		"""
		file351 = path.join(self.testdir, 'testSamefile351.txt')
		file352 = path.join(self.testdir, 'testSamefile352.txt')
		flag35  = path.join(self.testdir, 'testSamefile35-flag.txt')
		helpers.writeFile(file351)
		helpers.createDeadlink(file352)

		def func35(f1, f2):
			SafeFs(f1, f2, tmpdir = self.testdir).move(callback = lambda r, fs: r and helpers.writeFile(flag35))
		yield func35, file351, file352, 1, lambda: path.exists(flag35) and not path.exists(file351) and path.exists(file352)

		"""
		#36 safeMoveWithLink samefile with callback
		"""
		file361 = path.join(self.testdir, 'testSamefile361.txt')
		file362 = path.join(self.testdir, 'testSamefile361.txt')
		flag36  = path.join(self.testdir, 'testSamefile36-flag.txt')
		def func36(f1, f2):
			SafeFs(f1, f2, tmpdir = self.testdir).moveWithLink(callback = lambda r, fs: r and helpers.writeFile(flag36))
		yield func36, file361, file362, 1, lambda: not path.exists(flag36)

		"""
		#37 safeMoveWithLink, overwrite
		"""
		file371 = path.join(self.testdir, 'testMoveWithLink371.txt')
		file372 = path.join(self.testdir, 'testMoveWithLink372.txt')
		flag37  = path.join(self.testdir, 'testMoveWithLink37-flag.txt')
		helpers.writeFile(file371)
		helpers.writeFile(file372)
		def func37(f1, f2):
			try:
				#SafeFs(f1, f2, tmpdir = self.testdir).moveWithLink(overwrite = True)
				utils.safefs.moveWithLink(f1, f2, overwrite = True)
			except OSError as ex:
				helpers.writeFile(flag37, ex)
		yield (func37, file371, file372, 10, lambda: not path.exists(flag37) and path.exists(file371) and  path.islink(file371) and path.exists(file372) and not path.islink(file372))

		"""
		#38 safeMoveWithLink, no overwrite
		"""
		file381 = path.join(self.testdir, 'testMoveWithLink381.txt')
		file382 = path.join(self.testdir, 'testMoveWithLink382.txt')
		flag38  = path.join(self.testdir, 'testMoveWithLink38-flag.txt')
		helpers.writeFile(file381)
		helpers.writeFile(file382)
		def func38(f1, f2):
			try:
				SafeFs(f1, f2, tmpdir = self.testdir).moveWithLink(overwrite = False)
			except OSError as ex:
				helpers.writeFile(flag38, ex)
		yield (func38, file381, file382, 10, lambda: not path.exists(flag38) and path.exists(file381) and not path.islink(file381) and path.exists(file382) and not path.islink(file382))

		"""
		#39 safeMoveWithLink, f2 is a deadlink
		"""
		file391 = path.join(self.testdir, 'testMoveWithLink391.txt')
		file392 = path.join(self.testdir, 'testMoveWithLink392.txt')
		flag39  = path.join(self.testdir, 'testMoveWithLink39-flag.txt')
		helpers.writeFile(file391)
		helpers.createDeadlink(file392)
		def func39(f1, f2):
			try:
				SafeFs(f1, f2, tmpdir = self.testdir).moveWithLink(overwrite = False)
			except OSError as ex:
				helpers.writeFile(flag39, ex)
		yield (func39, file391, file392, 10, lambda: not path.exists(flag39) and path.exists(file391) and path.islink(file391) and path.exists(file392) and not path.islink(file392))

		"""
		#40 Thread-safe copy samefile with callback
		"""
		file401 = path.join(self.testdir, 'testSafeCopy401.txt')
		file402 = path.join(self.testdir, 'testSafeCopy401.txt')
		flag40  = path.join(self.testdir, 'testSafeCopy40-flag.txt')
		helpers.writeFile(file401)
		def func40(f1, f2):
			SafeFs(f1, f2, tmpdir = self.testdir).copy(callback = lambda r, fs: r or helpers.writeFile(flag40))
		yield (func40, file401, file402, 1, lambda: not path.exists(flag40))

		"""
		#41 Thread-safe copy no overwrite
		"""
		file411 = path.join(self.testdir, 'testSafeCopy411.txt')
		file412 = path.join(self.testdir, 'testSafeCopy412.txt')
		helpers.writeFile(file411, 1)
		helpers.writeFile(file412, 2)
		def func41(f1, f2):
			SafeFs(f1, f2, tmpdir = self.testdir).copy(overwrite = False)
		yield (func41, file411, file412, 1, lambda: helpers.readFile(file411, int) == 1 and helpers.readFile(file412, int) == 2)

		"""
		#42 Thread-safe copy deadlink
		"""
		file421 = path.join(self.testdir, 'testSafeCopy421.txt')
		file422 = path.join(self.testdir, 'testSafeCopy422.txt')
		helpers.writeFile(file421, 1)
		helpers.createDeadlink(file422)
		def func42(f1, f2):
			SafeFs(f1, f2, tmpdir = self.testdir).copy()
		yield (func42, file421, file422, 1, lambda: helpers.readFile(file421, int) == 1 and helpers.readFile(file422, int) == 1)

		"""
		#43 Thread-safe link samefile
		"""
		file431 = path.join(self.testdir, 'testSafeLink431.txt')
		file432 = path.join(self.testdir, 'testSafeLink431.txt')
		flag43  = path.join(self.testdir, 'testSafeLink43-flag.txt')
		def func43(f1, f2):
			SafeFs(f1, f2, tmpdir = self.testdir).link(callback = lambda r, fs: r and helpers.writeFile(flag43))
		yield (func43, file431, file432, 1, lambda: not path.exists(flag43))

		"""
		#44 Thread-safe samefile and f2 is a file, f1 is a link
		"""
		file441 = path.join(self.testdir, 'testSafeLink441.txt')
		file442 = path.join(self.testdir, 'testSafeLink442.txt')
		helpers.writeFile(file442)
		symlink(file442, file441)
		def func44(f1, f2):
			SafeFs(f1, f2, tmpdir = self.testdir).link()
		yield (func44, file441, file442, 1, lambda: not path.islink(file442) and path.isfile(file441) and path.islink(file441))

		"""
		#45 untargz, not a file
		"""
		filetgz451 = path.join(self.testdir, 'testTgz451.dir')
		filetgz452 = path.join(self.testdir, 'testTgz452')
		flagtgz45  = path.join(self.testdir, 'testTgz45-flag.txt')
		makedirs(filetgz451)
		def functgz45(f1, f2):
			#if SafeFs(f1, f2, tmpdir = self.testdir).ungz():
			if utils.safefs.ungz(f1, f2):
				helpers.writeFile(flagtgz45)
		yield (functgz45, filetgz451, filetgz452, 1, lambda: not path.exists(flagtgz45))

		"""
		#46 Gz and ungz
		"""
		filegz461 = path.join(self.testdir, 'testGz461.dir')
		filegz462 = path.join(self.testdir, 'testGz462')
		flaggz46  = path.join(self.testdir, 'testGz46.txt')
		makedirs(filegz461)
		def funcgz46(f1, f2):
			if SafeFs(f1, f2, tmpdir = self.testdir).ungz():
				helpers.writeFile(flaggz46)
		yield (funcgz46, filegz461, filegz462, 1, lambda: not path.exists(flaggz46))

		"""
		#47 Thread-safe link no overwrite
		"""
		file431 = path.join(self.testdir, 'testSafeLink431.txt')
		file432 = path.join(self.testdir, 'testSafeLink431.txt')
		flag43  = path.join(self.testdir, 'testSafeLink43-flag.txt')
		def func43(f1, f2):
			SafeFs(f1, f2, tmpdir = self.testdir).link(callback = lambda r, fs: r and helpers.writeFile(flag43))
		yield (func43, file431, file432, 1, lambda: not path.exists(flag43))

		"""
		#48 Thread-safe link no overwrite
		"""
		file481 = path.join(self.testdir, 'testSafeLink481.txt')
		file482 = path.join(self.testdir, 'testSafeLink482.txt')
		helpers.writeFile(file481, 1)
		helpers.writeFile(file482, 2)
		def func48(f1, f2):
			SafeFs(f1, f2, tmpdir = self.testdir).link(overwrite = False)
		yield (func48, file481, file482, 1, lambda: helpers.readFile(file481, int) == 1 and helpers.readFile(file482, int) == 2)

		"""
		#49 Thread-safe copy the same link
		"""
		file491 = path.join(self.testdir, 'testSafeCopySamelink491.txt')
		file492 = path.join(self.testdir, 'testSafeCopySamelink492.txt')
		file493 = path.join(self.testdir, 'testSafeCopySamelink493.txt')
		helpers.writeFile(file493)
		symlink(file493, file491)
		def func49(f1, f2):
			if path.islink(f1):
				utils.safefs.copy(f1, f2)
			else:
				uitls.safefs.moveWithLink(f1, f2)
		yield func49, file491, file492, 100, lambda: path.islink(file491) and path.isfile(file492) and not path.islink(file492)


	def test2FS(self, func, f1, f2, length, state, msg = None):
		Parallel(length, 'thread').run(func, [(f1, f2) for _ in range(length)])
		self.assertTrue(state(), msg)

	def dataProvider_testDumbPopen(self):
		yield 'ls', 0
		yield 'bash -c "exit 1"', 1
		yield 'ls2', 1

	def testDumbPopen(self, cmd, rc = 0):
		with helpers.captured_output() as (out, err):
			p = Cmd(cmd, raiseExc = False).run()
			r = p.rc

		if p.p:
			self.assertIsInstance(p.p, Popen)
		self.assertEqual(out.getvalue(), '')
		self.assertEqual(err.getvalue(), '')
		self.assertEqual(r, rc)

	def dataProvider_testBriefList(self):
		yield ([0, 1, 2, 3, 4, 5, 6, 7], "0-7")
		yield ([1, 3, 5, 7, 9], "1, 3, 5, 7, 9")
		yield ([1, 3, 5, 7, 9, 4, 8, 12, 13], "1, 3-5, 7-9, 12, 13")
		yield ([13, 9, 5, 7, 4, 3, 8, 1, 12], "1, 3-5, 7-9, 12, 13")

	def testBriefList(self, list2Brief, collapsedStr):
		self.assertEqual(utils.briefList(list2Brief), collapsedStr)

class TestCmd(testly.TestCase):

	def setUpMeta(self):
		self.testdir = path.join(gettempdir(), 'PyPPL_unittest', 'TestCmd')
		if path.exists(self.testdir):
			rmtree(self.testdir)
		makedirs(self.testdir)

	def testInit(self, cmd, raiseExc = True, kwargs = None, exception = None):
		kwargs = kwargs or {}
		if exception:
			self.assertRaises(exception, Cmd, cmd, raiseExc, **kwargs)
		else:
			c = Cmd(cmd, raiseExc, **kwargs)
			self.assertEqual(c.cmd, cmd)
			self.assertIsInstance(c.p, Popen)
			self.assertIsNone(c.stdout)
			self.assertIsNone(c.stderr)
			self.assertEqual(c.rc, 1)
			self.assertGreater(c.pid, 0)
			self.assertEqual(repr(c), '<Cmd {!r}>'.format(cmd))

	def dataProvider_testInit(self):
		yield 'ls',
		yield 'ls2', True, None, OSError

	def testRunPipe(self, cmd, bg, rc, stdout, stderr):
		cmd.run(bg)
		self.assertEqual(cmd.rc, rc)
		self.assertEqual(cmd.stdout, stdout)
		self.assertEqual(cmd.stderr, stderr)

	def dataProvider_testRunPipe(self):
		yield Cmd('echo 1'), False, 0, '1\n', ''
		yield Cmd('echo 1'), True, 1, None, None
		yield Cmd('seq 1 3').pipe('grep 1'), False, 0, '1\n', ''
		yield Cmd('seq 1 3').pipe('grep 1'), True, 1, None, None

	def testStd2file(self, cmd, fout, out):
		with open(fout, 'w') as f:
			c = utils.cmd.run(cmd, stdout = f)
		with open(fout, 'r') as f:
			helpers.assertTextEqual(self, f.read(), out)

	def dataProvider_testStd2file(self):
		yield 'seq 1 3', path.join(self.testdir, 'testStd2file'), '1\n2\n3\n'

class TestPs(testly.TestCase):

	def testExists(self, pid, ret, exception = None):
		if exception:
			self.assertRaises(exception, ps.exists, pid)
		else:
			self.assertEqual(ps.exists(pid), ret)

	def dataProvider_testExists(self):
		yield 0, True
		yield 123456, False
		yield 1, True

	def testChild(self, pid, child):
		self.assertIn(child, ps.child(pid))
		self.assertIn(child, ps.children(pid))

	def dataProvider_testChild(self):
		from os import getpid
		c = Cmd('sleep .5').run(bg = True)
		yield getpid(), str(c.pid)

	def testKill(self):
		c = Cmd('sleep .5').run(bg = True)
		self.assertTrue(ps.exists(c.pid))
		c2 = Cmd('ps --no-heading -p ' + str(c.pid)).pipe('grep -v defunct').run()
		self.assertIn(str(c.pid), c2.stdout)
		ps.killtree(c.pid)
		# The process will become a <defunct> process
		# ps.exists can still detect it
		# self.assertFalse(ps.exists(r.pid))
		# use ps command instead
		c3 = Cmd('ps --no-heading -p ' + str(c.pid)).pipe('grep -v defunct').run()
		self.assertEqual(c3.stdout, '')

if __name__ == '__main__':
	testly.main(verbosity=2, failfast = True)
