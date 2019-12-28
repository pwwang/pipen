"""List available profiles."""
import toml
from ..plugin import hookimpl
from ..config import config
from ..logger import logger as plogger
@hookimpl
def logger_init(logger):
	"""Add log levels"""
	logger.add_level('PROFILE', 'TITLE')
	logger.add_level(' ', 'SUBTITLE')

@hookimpl
def cli_addcmd(commands):
	"""Add profile command"""
	commands.profile._hbald = False
	commands.profile        = __doc__
	commands.runner         = commands.profile

@hookimpl
def cli_execcmd(command, opts): # pylint: disable=unused-argument
	"""Run the command"""
	if command == 'profile':
		plogger.init()
		for profile in config._profiles:
			with config._with(profile):
				plogger.profile('>>> ' + profile)
				for line in toml.dumps(config.dict()).splitlines():
					plogger[' ']('    ' + line)
