"""List work directories under <wdir>."""
import sys
from os import path
from glob import glob
from datetime import date, timedelta, datetime
from ..plugin import hookimpl
from ..logger import logger

def show_proc(proc, mtime, fail):
	"""Show the status of a process"""
	(logger.error if fail else logger.info)('{} {}: {}'.format(
		'x' if fail else 'v',
		path.basename(proc),
		mtime.strftime("%Y-%m-%d %H:%M:%S")
	))

def list_procs(procs, wdir):
	"""List all processes"""
	logger.workdir(wdir)
	procname = None
	total = 0
	for proc, mtime, fail in procs:
		total += 1
		pname = '.'.join(path.basename(proc).split('.')[1:3])
		if pname != procname:
			procname = pname
			logger.process(pname)
		show_proc(proc, mtime, fail)
	logger.info('TOTAL: {}'.format(total))

def proc_mtime(proc):
	"""Get the modification time of the process"""
	setfile = path.join(proc, 'proc.settings.toml')
	if not path.isfile(setfile):
		return datetime.fromtimestamp(0)
	return datetime.fromtimestamp(path.getmtime(setfile))

def proc_failed(proc):
	"""Tell if the process is failed or not"""
	for job in glob(path.join(proc, '*')):
		if not path.basename(job).isdigit():
			continue
		rcfile = path.join(job, 'job.rc')
		if not path.exists(rcfile):
			return True
		with open(rcfile) as frc:
			rc = frc.read().strip()
		if rc != '0':
			return True
	return False

def get_procs(opts): # pylint: disable=too-many-branches
	"""Get the processes"""
	if opts.proc:
		pattern = path.join(opts.wdir, 'PyPPL.{}.*'.format(opts.proc))
	else:
		pattern = path.join(opts.wdir, 'PyPPL.*')

	procs = sorted(glob(pattern))
	if not procs:
		logger.warning('No query processes found in workdir: {}.'.format(opts.wdir))
		sys.exit(1)

	before  = None
	if opts.ago:
		before = date.today() - timedelta(days = opts.ago)
		before = datetime(before.year, before.month, before.day)
	elif opts.before:
		year = date.today().year
		if opts.before.count('/'):
			parts = opts.before.split('/')
			if len(parts) == 2:
				month, day = parts
			else:
				month, day, year = parts
		else:
			parts = opts.before.split('-')
			if len(parts) == 2:
				month, day = parts
			else:
				year, month, day = parts
		before = datetime(int(year), int(month), int(day))

	for proc in procs:
		mtime = proc_mtime(proc)
		if before and mtime >= before:
			continue

		if opts.nocheck:
			yield (proc, mtime, False)
		else:
			fail = proc_failed(proc)
			if opts.error and not fail:
				continue
			yield (proc, mtime, fail)

@hookimpl
def cli_addcmd(commands):
	"""Add command"""
	commands.list             = __doc__
	commands.list._hbald      = False
	commands.list.proc.desc   = 'The process name to show or to compare.'
	commands.list.ago.type    = 'int'
	commands.list.ago.desc    = 'Work directories to be removed when modified N days ago.'
	commands.list.before.desc = [
		'Before when the work directories to be listed.',
		'Supported format: m/d, m-d, m/d/y and y-m-d'
	]
	commands.list.nocheck      = False
	commands.list.nocheck.desc = 'Don`t check failure of processes.'
	commands.list.error        = False
	commands.list.error.desc   = 'Remove directories if any job failed ' + \
								'or do error check when listing them.'
	commands.list.wdir         = './workdir'
	commands.list.wdir.desc    = 'The <ppldir> containing process work directories.'

@hookimpl
def cli_execcmd(command, opts):
	"""Run the command"""
	if command == 'list':
		list_procs(get_procs(opts), opts.wdir)
