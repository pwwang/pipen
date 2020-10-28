"""List available profiles."""
import toml
from ..plugin import hookimpl
from ..config import config
from ..logger import logger as plogger

@hookimpl
def logger_init(logger):
    """Add log levels"""
    config.logger.level = 'debug'
    logger.add_level('PROFILE', 'TITLE')
    logger.add_level('-', 'DEBUG')
    logger.add_level('=', 'WARNING')


@hookimpl
def cli_addcmd(params):
    """Add profile command"""
    cmd = params.add_command('profile, runner',
                             desc=__doc__, help_on_void=False)
    cmd.add_param('name', default='', desc='The name of the profile to show')
    cmd.add_param('nodefault', default=False,
                  desc='Hide default configuration items or not.')

def _get_defaults():
    config._use('default')
    defaults = config.dict()
    for _, cached in config._protected['cached'].items():
        if 'default' in cached:
            del cached['default']

    return defaults

def _show_profile(profile, defaults, nodefault):
    plogger.profile('>>> %s', profile)
    config._use(profile)
    confs = config.dict() if profile != 'default' else defaults
    conflines = toml.dumps(confs).splitlines()
    if nodefault:
        for line in conflines:
            plogger['=']('    %s', line)
    else:
        defaults = defaults.copy()
        defaults.update(confs)
        for line in toml.dumps(defaults).splitlines():
            if line in conflines or profile == 'default':
                plogger['=']('    %s' % line)
            else:
                plogger['-']('    %s' % line)

@hookimpl
def cli_execcmd(command, opts):  # pylint: disable=unused-argument
    """Run the command"""
    if command in ('runner', 'profile'):
        defaults = _get_defaults()

        if opts.name:
            _show_profile(opts.name, defaults, opts.nodefault)
            return

        for profile in sorted(config._profiles,
                              key=lambda prof: ('_'
                                                if prof == 'default'
                                                else prof)):
            _show_profile(profile, defaults, opts.nodefault)
