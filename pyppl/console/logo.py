"""Show PyPPL logo, version and loaded plugins and runners, based on default configurations."""
from ..plugin import hookimpl
from ..pyppl import _logo

@hookimpl
def cli_addcmd(commands):
	"""Add logo command"""
	commands.logo._hbald = False
	commands.logo        = __doc__

@hookimpl
def cli_execcmd(command, opts): # pylint: disable=unused-argument
	"""Run the command"""
	if command == 'logo':
		_logo()
