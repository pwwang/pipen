"""Provide Cli class"""

from typing import TYPE_CHECKING, Any, Mapping

from simplug import Simplug

from ..defaults import CLI_ENTRY_GROUP

if TYPE_CHECKING:  # pragma: no cover
    from pyparam import Params

cli_plugin = Simplug(CLI_ENTRY_GROUP)


@cli_plugin.spec
def add_commands(params: "Params") -> None:
    """Add options for the command

    Args:
        params: The params to add commands and options to
    """


@cli_plugin.spec
def exec_command(command: str, args: Mapping[str, Any]) -> None:
    """Execute the command with given sub-command and parsed arguments

    Args:
        command: The sub-command, should be one of those added by
            `add_commands()`
        args: The parsed arguments
    """
