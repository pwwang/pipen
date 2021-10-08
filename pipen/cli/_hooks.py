"""Provide Cli class"""

from abc import ABC, abstractmethod, abstractproperty
from typing import TYPE_CHECKING, Any, List, Mapping

from simplug import Simplug

from ..defaults import CLI_ENTRY_GROUP

if TYPE_CHECKING:  # pragma: no cover
    from pyparam import Params

cli_plugin = Simplug(CLI_ENTRY_GROUP)


class CLIPlugin(ABC):
    """The abc for cli plugin"""

    @abstractproperty
    def name(self) -> str:
        """The name/command of this plugin"""

    @abstractproperty
    def params(self) -> "Params":
        """Define parameters"""

    @abstractmethod
    def exec_command(self, args: Mapping[str, Any]) -> None:
        """Execute the command"""

    def parse_args(self, args: List[str]) -> Mapping[str, Any]:
        """Parse the arguments"""
        return self.params.parse(args)
