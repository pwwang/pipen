"""Provide Cli class"""
from __future__ import annotations

from abc import ABC, abstractmethod, abstractproperty
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

    @abstractproperty
    def name(self) -> str:
        """The name/command of this plugin"""

    def define_args(self, parser: ArgumentParser):
        """Define arguments for the command"""

    @abstractmethod
    def exec_command(self, args: Namespace) -> None:
        """Execute the command"""
