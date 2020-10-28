"""Show PyPPL logo, version and loaded plugins and runners,
based on default configurations."""
from ..plugin import hookimpl
from ..pyppl import _logo


@hookimpl
def cli_addcmd(params):
    """Add logo command"""
    params.add_command('logo', desc=__doc__, help_on_void=False)


@hookimpl
def cli_execcmd(command, opts):  # pylint: disable=unused-argument
    """Run the command"""
    if command == 'logo':
        _logo()
