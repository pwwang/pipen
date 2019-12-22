from ..plugin import hookimpl
from ..config import config

@hookimpl
def cli_addcmd(commands):
	commands.profile = 'List available profiles.'

@hookimpl
def cli_execcmd(command, opts):
	if command == 'profile':
		print(config._profiles)