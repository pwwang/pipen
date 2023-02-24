"""Print help for commands"""
from __future__ import annotations
from typing import TYPE_CHECKING

from ._hooks import CLIPlugin

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
            choices=[
                n
                for n in parser._subparsers._group_actions[0].choices
                if n != "help"
            ],
            help="The command to show help for",
        )

    def exec_command(self, args: Namespace) -> None:
        """Run the command"""

        if not args.cmd:
            self.parser.parse_args(["--help"])
        else:
            self.parser.parse_args([args.cmd, "--help"])
