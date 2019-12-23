"""Check the status of a process."""
import math
from glob import glob
from os import path
from ..plugin import hookimpl
from ..logger import logger

@hookimpl
def cli_addcmd(commands):
	"""Add command"""
	commands.status               = 'Check the status of a running process.'
	commands.status.ncol          = 5
	commands.status.ncol.desc     = 'Number of jobs to show in a row.'
	commands.status.proc.required = True
	commands.status.proc.desc     = 'The process working directory. ' + \
									'If path separator exists, then `-wdir` will be ignored.'
	commands.status.wdir          = commands.list.wdir

@hookimpl
def cli_execcmd(command, opts):
	"""Run the command"""
	if command == 'status':
		if path.sep in opts.proc:
			procdir = opts.proc
		else:
			proc = opts.proc if opts.proc.startswith('PyPPL.') else 'PyPPL.' + opts.proc
			proc = glob(path.join(opts.wdir, proc + '*'))
			if len(proc) > 1:
				logger.warning(f'There are more than 1 processes named with "{opts.proc}", ' + \
					'first one used.', 'yellow')
			procdir = proc[0]
		logger.workdir(procdir)

		jobdirs = list(sorted(glob(path.join(procdir, '*', '')),
			key = lambda x: int(path.basename(x[:-1]))))
		nnn = int(math.ceil(math.log(len(jobdirs), 10))) + 1 if jobdirs else 1
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
			jstat   = 'Unknown'
			rc      = '-'
			if not path.isfile(pidfile) or not path.isfile(outfile) or not path.isfile(errfile):
				jstat = 'Pending'
			else:
				rcfile = path.join(jobdir, 'job.rc')
				if not path.isfile(rcfile):
					jstat = 'Running'
				else:
					with open(rcfile) as frc:
						rc = frc.read().strip()
					rc = 'Done' if jstat == '0' else 'Failed'
			counts[jstat] += 1
			jobstr = ('Job ' + jobid).ljust(nnn + 4)
			logger.info(jobstr, end = ': ')
			logger.info(jstat.ljust(8) + ('[' + rc + ']    ').rjust(8),
				decors = colors[jstat], end = '' if int(jobid) % opts.ncol > 0 else '\n')

		logger.info('')
		logger.info('Total: ', end = '')
		for key, count in counts.items():
			logger.info('- ' + key + ': ' + str(count), decors = colors[key], end = ', ')
		logger.info('')
