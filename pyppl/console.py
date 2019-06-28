import sys
import re
import copy
from os import path
from glob import glob
from pprint import pformat
from datetime import date, timedelta, datetime
from concurrent.futures import ThreadPoolExecutor
import cmdy
from colorama import Fore, Style
from pyparam import commands, Helps, HelpAssembler
from .utils import Box, config, fs

HELP_ASSEMBLER = HelpAssembler()

commands._prefix = '-'
commands._desc   = 'PyPPL command line tool'

commands._inherit    = True

commands.list             = 'list work directories under <wdir>'
commands.list._hbald      = False
commands.list.proc.desc   = 'The process name to show or to compare.'
commands.list.ago.type    = 'int'
commands.list.ago.desc    = 'Work directories to be removed when modified N days ago.'
commands.list.before.desc = [
	'Before when the work directories to be removed.',
	'Supported format: m/d, m-d, m/d/y and y-m-d'
]
commands.list.all          = False
commands.list.all.desc     = 'List all processes if # processes > 100.'
commands.list.nocheck      = False
commands.list.nocheck.desc = 'Don`t check failure of processes.'
commands.list.error        = False
commands.list.error.desc   = 'Remove directories if any job failed or do error check when listing them.'
commands.list.wdir         = './workdir'
commands.list.wdir.desc    = 'The <ppldir> containing process work directories.'

commands.clean              = 'remove some work directories'
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

commands.compare            = 'compare two processes from different directories'
commands.compare.proc       = 'The base process name to compare.'
commands.compare.proc1.desc = 'The first full process name to compare.'
commands.compare.proc2.desc = 'The second full process name to compare.'
commands.compare.wdir       = commands.list.wdir

commands.runner              = 'List available runners.'
commands.runner._hbald       = False
commands.runner.cfgfile.desc = 'An extra configuration file.'
commands.runner.profile.desc = 'Show the runner information of given profile.'

commands.status               = 'Check the status of a running process.'
commands.status.ncol          = 5
commands.status.ncol.desc     = 'Number of jobs to show in a row.'
commands.status.proc.required = True
commands.status.proc.desc     = 'The process working directory. If path separator exists, then `-wdir` will be ignored.'
commands.status.wdir          = commands.list.wdir

commands.profile        = 'List available running profiles.'
commands.profile._hbald = False
commands.profile._.desc = 'Additional configurations.'

# command: completion
commands.completion = 'Generate completions for pyppl.'
commands.completion._hbald = False
commands.completion.shell = 'auto'
commands.completion.shell.desc = 'The shell'
commands.completion.auto = False
commands.completion.auto.desc = 'Whether automatically deploy the completion script.'
commands.completion.s = commands.completion.shell
commands.completion.a = commands.completion.auto
commands.completions  = commands.completion

def subtractDict(bigger, smaller, prefix = ''):
	"""Subtract a dict from another"""
	ret = bigger.copy()
	for key, val in smaller.items():
		if key not in ret:
			continue
		if isinstance(ret[key], dict) and isinstance(val, dict) and ret[key] != val:
			ret[key] = subtractDict(ret[key], val, prefix + '  ')
		elif ret[key] == val:
			del ret[key]
	return ret

def checkdate(value):
	msg = 'Malformat date format.'
	if not value:
		value = '{today.year}-{today.month}-{today.day}'.format(today = date.today())
	dateregx1 = r'^(0?[1-9]|1[012])/(0?[1-9]|[12][0-9])(?:/(\d{4}))?$'
	dateregx2 = r'^(?:(\d{4})-)?(0?[1-9]|1[012])-(0?[1-9]|[12][0-9])$'
	m1 = re.match(dateregx1, value)
	if m1:
		y = m1.group(3) or date.today().year
		m = m1.group(1)
		d = m1.group(2)
		return datetime(int(y), int(m), int(d), 23, 59, 59)
	m2 = re.match(dateregx2, value)
	if m2:
		y = m2.group(3) and m2.group(1) or date.today().year
		m = m2.group(3) and m2.group(2) or m2.group(1)
		d = m2.group(3) or m2.group(2)
		return datetime(int(y), int(m), int(d), 23, 59, 59)
	return msg

commands.compare.proc.callback = lambda pm, ps: \
	'-proc and -proc1/proc2 are mutually exclusive.' \
		if pm.value and (ps.proc1.value or ps.proc2.value) else \
	'Missing either -proc1 or -proc2.' \
		if not (ps.proc1.value and ps.proc2.value) and (ps.proc1.value or ps.proc2.value) else \
	'Nothing to compare, expecting -proc or -proc1/-proc2.' \
		if not (ps.proc1.value and ps.proc2.value) and not pm.value else None

commands.clean.before.callback = lambda pm, ps: \
	'-ago and -before are mutually exclusive' \
		if pm.value and ps.ago.value else \
	checkdate(pm.value) if isinstance(checkdate(pm.value), str) else \
		pm.setValue(checkdate(pm.value))

def streamout(msg, decors = None, end = '\n'):
	decors = decors or []
	if not isinstance(decors, list):
		decors = [decors]
	sys.stdout.write(''.join([getattr(Fore, dec.upper()) for dec in decors]) + str(msg) + Style.RESET_ALL + end)

def proc_mtime(proc):
	setfile = path.join(proc, 'proc.settings.yaml')
	if not path.isfile(setfile):
		return datetime.fromtimestamp(0)
	return datetime.fromtimestamp(path.getmtime(setfile))

def proc_failed(proc):
	for job in glob(path.join(proc, '*')):
		if not path.basename(job).isdigit():
			continue
		rcfile = path.join(job, 'job.rc')
		if not path.isfile(rcfile):
			return True
		with open(rcfile) as f:
			rc = f.read().strip()
		if rc != '0':
			return True
	return False

# list
def list_procs(procs, listall, wdir):
	if not procs:
		streamout('WARNING: No process found in workdir: {}.'.format(wdir), 'yellow')
		sys.exit(1)
	if len(procs) > 100 and not listall:
		streamout('WARNING: Got {} processes, listing first 100. Use -all to list all.'.format(len(procs)), 'yellow')
		procs = procs[:100]
	procgroups = {}
	for proc, mtime, fail in procs:
		pname = '.'.join(path.basename(proc).split('.')[1:3])
		if pname not in procgroups:
			procgroups[pname] = []
		procgroups[pname].append((proc, mtime, fail))

	streamout('WORKDIR: {} ({} query processes)'.format(wdir, len(procs)), 'yellow')
	for pname in sorted(procgroups.keys()):
		streamout('\nPROCESS: {}'.format(pname))
		for proc, mtime, fail in sorted(procgroups[pname], key = lambda p: p[1]):
			streamout('{} {}: {}'.format(
				'x' if fail else '-',
				path.basename(proc),
				mtime.strftime("%Y-%m-%d %H:%M:%S")
			), 'red' if fail else 'green')

def read_sections (sfile):
	ret = {}
	sec = ''
	with open(sfile) as f:
		for line in f:
			if line.startswith('['):
				sec = line.strip()[1:-1]
			elif sec:
				if sec not in ret:
					ret[sec] = []
				ret[sec].append(line)
	return ret

def compare_procs(proc1, proc2):
	setfile1 = path.join(proc1, 'proc.settings.yaml')
	setfile2 = path.join(proc2, 'proc.settings.yaml')
	streamout('1. {}'.format(setfile1), 'green')
	streamout('2. {}'.format(setfile2), 'red')
	streamout('-' * (max(len(setfile1), len(setfile2), 80) + 3))

	if path.isfile(setfile1) and path.isfile(setfile2):
		cmdy.diff(setfile1, setfile2, _fg = True)
	else:
		streamout('ERROR: proc.settings.yaml of either processes not exists.', 'red')

def remove_proc(proc, nthread = 1, msg = '', lock = None):
	if msg:
		if lock:
			with lock:
				streamout(msg)
	#parallel.run(rmtree, [(d, ) for d in glob(path.join(proc, '*')) if path.isdir(d)], nthread, 'thread')
	with ThreadPoolExecutor(max_workers = nthread) as executor:
		for d in glob(path.join(proc, '*')):
			if path.isdir(d):
				executor.submit(fs.remove, d)
	fs.remove(proc)

def clean_procs(procs, nthread, force, wdir):
	if not procs:
		streamout('WARNING: No query processes found in workdir: {}.'.format(wdir), 'yellow')
		sys.exit(1)

	if force:
		lock = Lock()
		lenprocs = len(procs)
		with ThreadPoolExecutor(max_workers = nthread) as executor:
			for i, procinfo in enumerate(procs):
				executor.submit(remove_proc, procinfo[0], 1, 'Removeing [{}/{}]: {}'.format(i, lenprocs, procinfo[0]), lock)
		#parallel.run(remove_proc, [(procinfo[0], 1, 'Removeing [{}/{}]: {}'.format(i, lenprocs, procinfo[0]), lock) for i, procinfo in enumerate(procs)], nthread, 'thread')
	else:
		procgroups = {}
		for proc, mtime, fail in procs:
			pname = '.'.join(path.basename(proc).split('.')[1:3])
			if pname not in procgroups:
				procgroups[pname] = []
			procgroups[pname].append((proc, mtime, fail))

		ans = ['', 'Y', 'y', 'N', 'n']
		streamout('WORKDIR: {} ({} query processes)'.format(wdir, len(procs)), 'yellow')
		for pname in sorted(procgroups.keys()):
			streamout('\nPROCESS: {}'.format(pname))
			for proc, mtime, fail in sorted(procgroups[pname], key = lambda p: p[1]):
				streamout('{} {}: {}'.format(
					'x' if fail else '-',
					path.basename(proc),
					mtime.strftime("%Y-%m-%d %H:%M:%S")
				), 'red' if fail else 'green')
				r = input('  Remove it? [Y/n] ')
				while r not in ans:
					r = input('  Remove it? [Y/n] ')
				if r in ['', 'Y', 'y']:
					remove_proc(proc, nthread)
					streamout('\x1b[1A  Removed!           ', 'green')

def profile(opts):
	"""List avaiable running profiles"""
	if opts._:
		config._load(opts._)

	base = { '_flowchart': {},
		'_log': {},
		'args': {},
		'sgeRunner': {},
		'sshRunner': {},
		'tplenvs': {}}

	helps = Helps()
	helps.add('Profile: "default"', sectype = 'plain')
	helps.select('Profile: "default"').add(
		pformat(subtractDict(config, base), indent = 2, width = 100))

	default = copy.deepcopy(config)
	for prof in config._profiles:
		if prof == 'default':
			continue
		helps.add('Profile: "%s"' % prof, sectype = 'plain')

		with config._with(prof, copy = True) as profconf:
			profconf = subtractDict(profconf, default)
			profconf = subtractDict(profconf, base)
			helps.select('Profile: "%s"' % prof).add(
				pformat(profconf, indent = 2, width = 100))
		config.update(default)

	print('\n'.join(HELP_ASSEMBLER.assemble(helps)), end = '')

def status(opts):
	if path.sep in opts.proc:
		procdir = opts.proc
	else:
		proc = opts.proc if opts.proc.startswith('PyPPL.') else 'PyPPL.' + opts.proc
		proc = glob(path.join(opts.wdir, proc + '*'))
		if len(proc) > 1:
			streamout('WARNING: There are more than 1 processes named with "{}", first one used.'.format(opts.proc), 'yellow')
		procdir = proc[0]
	streamout('')
	streamout('Working with directory: {}'.format(procdir))
	streamout('-' * (len(procdir) + 24))
	lockfile = path.join(procdir, 'proc.lock')
	if not path.isfile(lockfile):
		streamout('WARNING: Lock file does not exist. It is not a process directory or the process is not running.', 'yellow')
	else:
		import math
		jobdirs = list(sorted(glob(path.join(procdir, '*', '')), key = lambda x: int(path.basename(x[:-1]))))
		n = int(math.ceil(math.log(len(jobdirs), 10))) + 1
		colors = {
			'Unknown': 'magenta',
			'Pending': 'white',
			'Running': 'green',
			'Done'   : 'cyan',
			'Failed' : 'red',
		}
		counts = {
			'Unknown': 0,
			'Pending': 0,
			'Running': 0,
			'Done'   : 0,
			'Failed' : 0,
		}
		for jobdir in jobdirs:
			jobdir  = path.normpath(jobdir)
			pidfile = path.join(jobdir, 'job.pid')
			outfile = path.join(jobdir, 'job.stdout')
			errfile = path.join(jobdir, 'job.stderr')
			jobid   = path.basename(jobdir)
			status  = 'Unknown'
			rc      = '-'
			if not path.isfile(pidfile) or not path.isfile(outfile) or not path.isfile(errfile):
				status = 'Pending'
			else:
				rcfile = path.join(jobdir, 'job.rc')
				if not path.isfile(rcfile):
					status = 'Running'
				else:
					with open(rcfile) as f:
						rc = f.read().strip()
					if rc == '0':
						status = 'Done'
					else:
						status = 'Failed'
			counts[status] += 1
			jobstr = ('Job ' + jobid).ljust(n + 4)
			streamout(jobstr, end = ': ')
			streamout(status.ljust(8) + ('[' + rc + ']    ').rjust(8), decors = colors[status], end = '' if int(jobid) % opts.ncol > 0 else '\n')

		streamout('')
		streamout('-' * (opts.ncol * (n + 22) - 4))
		streamout('Total: ', end = '')
		for key, c in counts.items():
			streamout(key + ': ' + str(c), decors = colors[key], end = ', ')
		streamout('')

def getProcs(opts):
	if opts.proc:
		pattern = path.join(opts.wdir, 'PyPPL.{}.*'.format(opts.proc))
	else:
		pattern = path.join(opts.wdir, 'PyPPL.*')

	procs   = glob(pattern)
	before  = None
	if opts.ago:
		before = date.today() - timedelta(days = opts.ago)
		before = datetime(before.year, before.month, before.day)
	elif opts.before:
		before = opts.before

	procs2 = []
	for proc in procs:
		mtime = proc_mtime(proc)
		if before and mtime >= before:
			continue

		if opts.nocheck:
			procs2.append((proc, mtime, False))
		else:
			fail = proc_failed(proc)
			if opts.error and not fail:
				continue
			procs2.append((proc, mtime, fail))
	return procs2

def compare(opts):
	if opts.proc:
		pattern = path.join(opts.wdir, 'PyPPL.{}.*'.format(opts.proc))
		procs   = glob(pattern)
		if len(procs) < 2:
			streamout('ERROR: Not enough processes to compare: {}'.format(opts.proc), 'red')
			sys.exit(1)
		procs = procs[:2]
		compare_procs(*procs)
	else:
		pattern1 = path.join(opts.wdir, 'PyPPL.{}*'.format(opts.proc1))
		proc1 = glob(pattern1)
		if not proc1:
			streamout('ERROR: No such process: {}'.format(opts.proc1), 'red')
			sys.exit(1)
		proc1 = proc1[0]

		pattern2 = path.join(opts.wdir, 'PyPPL.{}*'.format(opts.proc2))
		proc2 = glob(pattern2)
		if not proc2:
			streamout('ERROR: No such process: {}'.format(opts.proc2), 'red')
			sys.exit(1)
		proc2 = proc2[0]
		compare_procs(proc1, proc2)

def main():
	command, opts, _ = commands._parse(dict_wrapper = Box)
	if command == 'runner':
		command = 'profile'
	if command == 'completions':
		command = 'completion'
	if command in ('clean', 'list'):
		procs = getProcs(opts)
		if command == 'clean':
			clean_procs(procs, opts.nthread, opts.force, opts.wdir)
		else:
			list_procs(procs, opts.all, opts.wdir)
	elif command == 'completion':
		comp = commands._complete(shell = opts.s, auto = opts.a)
		if not opts.a:
			print(comp)
	else:
		globals()[command](opts)