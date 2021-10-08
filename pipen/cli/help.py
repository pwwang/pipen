"""Print help for commands"""
from typing import Any, Mapping

from rich import print
from pyparam import Params, POSITIONAL

from ._hooks import CLIPlugin, cli_plugin

__all__ = ("CLIHelpPlugin", )


class CLIHelpPlugin(CLIPlugin):
    """Print help for commands"""

    name = "help"

    @property
    def params(self) -> Params:
        """Define the params"""
        pms = Params(
            desc=self.__class__.__doc__,
            help_on_void=False,
        )
        pms.add_param(
            POSITIONAL,
            default="",
            desc="The command to show help for",
        )
        return pms

    def exec_command(self, args: Mapping[str, Any]) -> None:
        """Run the command"""
        command = args[POSITIONAL]
        commands = sorted(
            cli_plugin.get_enabled_plugin_names(),
            key=lambda cmd: 999 if cmd == "help" else 0,
        )
        if command not in commands:
            from ._main import _print_help
            print(
                "[red][b]ERROR: [/b][/red]No such command: "
                f"[green]{command}[/green]"
            )
            _print_help(commands)

        plg = cli_plugin.get_plugin(args[POSITIONAL], raw=True)()
        plg.params.print_help()
