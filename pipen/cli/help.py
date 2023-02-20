"""Print help for commands"""
from __future__ import annotations
from typing import TYPE_CHECKING

from ._hooks import CLIPlugin, cli_plugin

if TYPE_CHECKING:
    from argx import ArgumentParser
    from argparse import Namespace

__all__ = ("CLIHelpPlugin",)


class CLIHelpPlugin(CLIPlugin):
    """Print help for commands"""

    name = "help"

    def __init__(self, parser: ArgumentParser, subparser: ArgumentParser):
        super().__init__(parser, subparser)
        subparser.add_argument(
            "cmd",
            nargs="?",
            choices=cli_plugin.get_enabled_plugin_names(),
            help="The command to show help for",
        )

    def exec_command(self, args: Namespace) -> None:
        """Run the command"""

        if not args.cmd:
            self.parser.parse_args(["--help"])
        else:
            self.parser.parse_args([args.cmd, "--help"])
