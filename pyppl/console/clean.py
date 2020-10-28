"""Remove some pipeline directories."""
from concurrent.futures import ThreadPoolExecutor
from glob import glob
from os import path
from ..utils import fs
from ..plugin import hookimpl
from ..logger import logger
from .list import get_procs, show_proc


def remove_proc(proc, nthread=1, force=False):
    """Remove process from directory"""
    if force:
        with ThreadPoolExecutor(max_workers=nthread) as executor:
            for folder in glob(path.join(proc, '*')):
                if path.isdir(folder):
                    executor.submit(fs.remove, folder)
        try:
            fs.remove(proc)
            logger.warning('  Removed!           ')
        # pylint: disable=broad-except
        except BaseException as ex:  # pragma: no cover
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
def cli_addcmd(params):
    """Add command"""
    cmd = params.add_command('clean', desc=__doc__)
    cmd.add_param('nthread', default=1,
                  desc=('Number of threads used to clean up '
                        'the work directories.'))
    cmd.add_param('proc', desc='The process name to show or to compare.')
    cmd.add_param('ago', type=int,
                  desc=('Work directories to be removed when '
                        'modified N days ago.'))
    cmd.add_param('before', desc=[
        'Before when the work directories to be listed.',
        'Supported format: m/d, m-d, m/d/y and y-m-d'
    ])
    cmd.add_param('nocheck', default=False,
                  desc='Don`t check failure of processes.')
    cmd.add_param('error', default=False,
                  desc=('Remove directories if any job failed '
                        'or do error check when listing them.'))
    cmd.add_param('force', default=False,
                  desc='Don`t ask when remove work directories.')
    cmd.add_param('wdir', default='./workdir',
                  desc=('The <ppldir> containing process work directories.'))
    cmd.add_param('one', default=False,
                  desc='Just keep one process under a process group.')

@hookimpl
def cli_execcmd(command, opts):
    """Run the command"""
    if command == 'clean':
        clean_procs(get_procs(opts), opts.nthread, opts.force, opts.wdir,
                    opts.one)
