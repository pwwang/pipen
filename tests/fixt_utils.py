from os import path, getuid, utime
from time import sleep
import cmdy
import pytest
import psutil
from diot import Diot
from pyppl.utils import varname

@pytest.fixture(params = [
	Diot(klass = True, multi = False, docopy = False, array = False),
	Diot(klass = True, multi = True, docopy = False, array = False),
	Diot(klass = True, multi = False, docopy = True, array = False),
	Diot(klass = True, multi = True, docopy = True, array = False),
	Diot(klass = True, multi = False, docopy = False, array = True),
	Diot(klass = False, multi = False, docopy = False, array = False),
	Diot(klass = False, multi = True, docopy = False, array = False),
	Diot(klass = False, multi = False, docopy = False, array = True),
])
def fixt_varname(request):
	#varname.index = 0
	class Klass(object):
		def __init__(self, default='', d2=''):
			self.id = varname()
		def copy(self, *arg):
			return varname()
	def func():
		return varname()

	param = request.param
	if param.klass and not param.multi and \
		not param.docopy and not param.array:
		klass = Klass()
		return Diot(var = klass.id, expt = 'klass')
	if param.klass and param.multi and \
		not param.docopy and not param.array:
		klass = Klass(
			default = 'a',
			d2 = 'b',
		)
		return Diot(var = klass.id, expt = 'klass')
	if param.klass and not param.multi and \
		param.docopy and not param.array:
		klass = Klass()
		klass_copy = klass.copy()
		return Diot(var = klass_copy, expt = 'klass_copy')
	if param.klass and param.multi and \
		param.docopy and not param.array:
		klass = Klass()
		klass_copy = klass.copy(
			1,
			2
		)
		return Diot(var = klass_copy, expt = 'klass_copy')
	if param.klass and not param.multi and \
		not param.docopy and param.array:
		klass = [Klass()]
		return Diot(var = klass[0].id, expt = 'var_0')
	if not param.klass and not param.multi and not param.array:
		fun = func()
		return Diot(var = fun, expt = 'fun')
	if not param.klass and param.multi and not param.array:
		fun = func(

		)
		return Diot(var = fun, expt = 'fun')
	if not param.klass and not param.multi and  param.array:
		fun = [func()]
		return Diot(var = fun[0], expt = 'var_1')

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
	'killme',
	'killchildren',
])
def fixt_killtree(request):
	# spawn subprocesses
	c = cmdy.python(c = 'import cmdy; cmdy.sleep(100)', _hold = True)
	c = cmdy.python(c = 'import cmdy; cmdy.bash(c = "%s")' % c.cmd, _bg = True)

	proc = psutil.Process(c.pid)
	# take some time to spawn
	while len(proc.children(recursive = True)) < 2:
		sleep(.05)

	return Diot(
		pid = c.pid,
		children = [p.pid for p in proc.children(recursive = True)],
		killme = request.param == 'killme')

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

@pytest.fixture
def fd_fileflush(tmp_path):
	tmpfile = tmp_path / 'fileflush.txt'
	tmpfile.write_text('')
	with open(tmpfile, 'r') as fd_read, open(tmpfile, 'a') as fd_append:
		yield fd_read, fd_append

@pytest.fixture(params = range(5))
def fixt_fileflush(request, fd_fileflush):
	fd_read, fd_append = fd_fileflush
	if request.param == 0:
		return Diot(filed = fd_read, residue = '', expt_lines = [], expt_residue = '')
	if request.param == 1:
		fd_append.write('abcde')
		fd_append.flush()
		return Diot(filed = fd_read, residue = '', expt_lines = [], expt_residue = 'abcde')
	if request.param == 2:
		fd_append.write('ccc\ne1')
		fd_append.flush()
		return Diot(filed = fd_read, residue = 'abcde', expt_lines = ['abcdeccc\n'], expt_residue = 'e1')
	if request.param == 3:
		fd_append.write('ccc')
		fd_append.flush()
		return Diot(filed = fd_read, residue = '', end = True, expt_lines = ['ccc\n'], expt_residue = '')
	if request.param == 4:
		return Diot(filed = fd_read, residue = 'end', end = True, expt_lines = ['end\n'], expt_residue = '')


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
