"""Provide Cli class"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from simplug import Simplug

from ..defaults import CLI_ENTRY_GROUP

if TYPE_CHECKING:
    from argx import ArgumentParser
    from argparse import Namespace

cli_plugin = Simplug(CLI_ENTRY_GROUP)


class CLIPlugin(ABC):
    """The abc for cli plugin"""

    def __init__(
        self,
        parser: ArgumentParser,
        subparser: ArgumentParser,
    ) -> None:
        self.parser = parser
        self.subparser = subparser

    @property
    @abstractmethod
    def name(self) -> str:
        """The name/command of this plugin"""

    def parse_args(
        self,
        known_parsed: Namespace,
        unparsed_argv: list[str],
    ) -> Namespace:
        """Define arguments for the command"""
        if unparsed_argv:
            # Let parser raise error for unknown args
            return self.parser.parse_args()

        return known_parsed

    @abstractmethod
    def exec_command(self, args: Namespace) -> None:
        """Execute the command"""


class AsyncCLIPlugin(ABC):
    """The abc for cli plugin with async command execution"""

    def __init__(
        self,
        parser: ArgumentParser,
        subparser: ArgumentParser,
    ) -> None:
        self.parser = parser
        self.subparser = subparser

    async def post_init(self) -> None:
        """Async post init function called after all plugins are loaded"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """The name/command of this plugin"""

    async def parse_args(
        self,
        known_parsed: Namespace,
        unparsed_argv: list[str],
    ) -> Namespace:
        """Define arguments for the command"""
        if unparsed_argv:  # pragma: no cover
            # Let parser raise error for unknown args
            return self.parser.parse_args()

        return known_parsed

    @abstractmethod
    async def exec_command(self, args: Namespace) -> None:
        """Execute the command"""
