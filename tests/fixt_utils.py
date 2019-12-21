from os import path, getuid, utime
from time import sleep
import cmdy
import pytest
import psutil
from diot import Diot

@pytest.fixture(params = range(4))
def fixt_funcsig(request):
	if request.param == 0:
		def func1(): pass
		return Diot(func = func1, expt = "def func1(): pass")
	if request.param == 1:
		func2 = lambda: True
		return Diot(func = func2, expt = 'func2 = lambda: True')
	if request.param == 2:
		return Diot(func = "", expt = "None")
	if request.param == 3:
		return Diot(func = "A", expt = "None")

@pytest.fixture(params = [
	'not_a_file',
	'success',
	'failed_to_chmod',
	'from_shebang',
	'unierr_shebang'
])
def fixt_chmodx(request, tmp_path):
	if request.param == 'not_a_file':
		xfile = tmp_path / 'chmodxtest_not_a_file'
		xfile.mkdir()
		return Diot(file = xfile, expt = OSError)
	elif request.param == 'success':
		xfile = tmp_path / 'chmodxtest_success'
		xfile.write_text('')
		return Diot(file = xfile, expt = [str(xfile)])
	elif getuid() == 0:
		pytest.skip('I am root, I cannot fail chmod and read from shebang')
	elif request.param == 'failed_to_chmod':
		xfile = '/etc/passwd'
		return Diot(file = xfile, expt = OSError)
	elif request.param == 'from_shebang':
		if not path.isfile('/bin/zcat'):
			pytest.skip('/bin/zcat not exists.')
		else:
			return Diot(file = '/bin/zcat', expt = ['/bin/sh', '/bin/zcat'])
	elif request.param == 'unierr_shebang':
		xfile = '/bin/bash'
		if not path.isfile('/bin/bash'):
			pytest.skip('/bin/bash not exists.')
		else:
			return Diot(file = xfile, expt = OSError) # UnicodeDecodeError

@pytest.fixture(params = [
	'',
	'a_file',
	'a_link',
	'nonexists',
	'a_link_to_dir',
	'a_dir_with_subdir',
	'a_dir_with_file',
	'a_dir_subdir_newer',
	'a_dir_subdir_newer_dirsig_false',
])
def fixt_filesig(request, tmp_path):
	if not request.param:
		return Diot(file = '', expt = ['', 0])
	if request.param == 'a_file':
		afile = tmp_path / 'filesig_afile'
		afile.write_text('')
		return Diot(file = afile, expt = [str(afile), int(path.getmtime(afile))])
	if request.param == 'nonexists':
		return Diot(file = '/path/to/__non_exists__', expt = False)
	if request.param == 'a_link':
		alink      = tmp_path / 'filesig_alink'
		alink_orig = tmp_path / 'filesig_alink_orig'
		alink_orig.write_text('')
		alink.symlink_to(alink_orig)
		return Diot(file = alink, expt = [str(alink), int(path.getmtime(alink_orig))])
	if request.param == 'a_link_to_dir':
		alink = tmp_path / 'filesig_alink_to_dir'
		adir  = tmp_path / 'filesig_adir'
		adir.mkdir()
		alink.symlink_to(adir)
		return Diot(file = alink, expt = [str(alink), int(path.getmtime(adir))])
	if request.param == 'a_dir_with_subdir':
		adir = tmp_path / 'filesig_another_dir'
		adir.mkdir()
		utime(adir, (path.getmtime(adir) + 100, ) * 2)
		asubdir = adir / 'filesig_another_subdir'
		asubdir.mkdir()
		return Diot(file = adir, expt = [str(adir), int(path.getmtime(adir))])
	if request.param == 'a_dir_with_file':
		adir = tmp_path / 'filesig_another_dir4'
		adir.mkdir()
		utime(adir, (path.getmtime(adir) - 100, ) * 2)
		afile = adir / 'filesig_another_file4'
		afile.write_text('')
		return Diot(file = adir, expt = [str(adir), int(path.getmtime(afile))])
	if request.param == 'a_dir_subdir_newer':
		adir = tmp_path / 'filesig_another_dir2'
		adir.mkdir()
		utime(adir, (path.getmtime(adir) - 100, ) * 2)
		asubdir = adir / 'filesig_another_subdir2'
		asubdir.mkdir()
		return Diot(file = adir, expt = [str(adir), int(path.getmtime(asubdir))])
	if request.param == 'a_dir_subdir_newer_dirsig_false':
		adir = tmp_path / 'filesig_another_dir3'
		adir.mkdir()
		utime(adir, (path.getmtime(adir) - 100, ) * 2)
		asubdir = adir / 'filesig_another_subdir3'
		asubdir.mkdir()
		return Diot(file = adir, dirsig = False, expt = [str(adir), int(path.getmtime(adir))])

@pytest.fixture(params = [
	'noexc',
	'oserror',
	'runtimeerror'
])
def fixt_threadex(request):
	if request.param == 'noexc':
		def worker():
			pass
		return Diot(worker = worker, expt_ex = None)
	if request.param == 'oserror':
		def worker():
			raise OSError('oserr')
		return Diot(worker = worker, expt_ex = OSError)
	if request.param == 'runtimeerror':
		def worker():
			cmdy.ls('file_not_exists', _raise = True)
		return Diot(worker = worker, expt_ex = RuntimeError)

@pytest.fixture(params = [
	'raise_original',
	'raise_from_cleanup',
	'donot_raise',
	'donot_raise_init',
])
def fixt_threadpool(request):
	if request.param == 'donot_raise_init':
		def initializer():
			sleep(.5)
		return Diot(initializer = initializer, nthread = 3, expt_exc = None)
	if request.param == 'raise_original':
		def initializer():
			raise IOError('')
		return Diot(initializer = initializer, nthread = 3, expt_exc = IOError)
	if request.param == 'donot_raise':
		def initializer():
			raise IOError('')
		def cleanup(ex):
			pass
		return Diot(initializer = initializer, cleanup = cleanup, nthread = 3, expt_exc = None)
	if request.param == 'raise_from_cleanup':
		def initializer():
			raise IOError('')
		def cleanup(ex):
			if isinstance(ex, IOError):
				raise OSError('')
		return Diot(initializer = initializer, cleanup = cleanup, nthread = 3, expt_exc = OSError)
