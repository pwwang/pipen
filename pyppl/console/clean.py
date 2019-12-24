"""Remove some pipeline directories."""
from concurrent.futures import ThreadPoolExecutor
from glob import glob
from os import path
from ..utils import fs
from ..plugin import hookimpl
from ..logger import logger
from .list import get_procs, show_proc

def remove_proc(proc, nthread = 1, force = False):
	"""Remove process from directory"""
	if force:
		with ThreadPoolExecutor(max_workers = nthread) as executor:
			for folder in glob(path.join(proc, '*')):
				if path.isdir(folder):
					executor.submit(fs.remove, folder)
		try:
			fs.remove(proc)
			logger.warning('  Removed!           ')
		# pylint: disable=broad-except
		except BaseException as ex: # pragma: no cover
			#shutil.rmtree(proc)
			logger.error('  %s!           ' % ex)

	else:
		ans = input('  Remove it? [Y/n] ')
		print('\r')
		while ans not in ('', 'Y', 'y', 'N', 'n'):
			ans = input('  Remove it? [Y/n] ')
			print('\r')
		if ans in ['', 'Y', 'y']:
			remove_proc(proc, nthread, True)

def clean_procs(procs, nthread, force, wdir, one):
	"""Cleanup processes"""
	logger.workdir(wdir)
	procname = None
	for proc, mtime, fail in procs:
		process_name = '.'.join(path.basename(proc).split('.')[1:3])
		if process_name != procname:
			procname = process_name
			logger.process(process_name)
			show_proc(proc, mtime, fail)
			if not one:
				remove_proc(proc, nthread, force)
		else:
			show_proc(proc, mtime, fail)
			remove_proc(proc, nthread, force)

@hookimpl
def cli_addcmd(commands):
	"""Add command"""
	commands.clean              = __doc__
	commands.clean.nthread      = 1
	commands.clean.nthread.desc = 'Number of threads used to clean up the work directories.'
	commands.clean.proc         = commands.list.proc
	commands.clean.ago          = commands.list.ago
	commands.clean.before       = commands.list.before
	commands.clean.nocheck      = commands.list.nocheck
	commands.clean.force        = False
	commands.clean.force.desc   = 'Don`t ask when remove work directories.'
	commands.clean.error        = commands.list.error
	commands.clean.wdir         = commands.list.wdir
	commands.clean.one          = False
	commands.clean.one.desc     = 'Just keep one process under a process group.'

@hookimpl
def cli_execcmd(command, opts):
	"""Run the command"""
	if command == 'clean':
		clean_procs(get_procs(opts),
			opts.nthread, opts.force, opts.wdir, opts.one)
