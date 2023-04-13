"""Print help for commands"""
from __future__ import annotations
from typing import TYPE_CHECKING

from rich import print

from ._hooks import CLIPlugin

if TYPE_CHECKING:
    from argparse import Namespace

__all__ = ("CLIVersionPlugin",)


class CLIVersionPlugin(CLIPlugin):
    """Print versions of pipen and its dependencies"""

    name = "version"

    def exec_command(self, args: Namespace) -> None:
        """Run the command"""
        import sys
        from importlib.metadata import version
        from .. import __version__

        versions = {"python": sys.version, "pipen": __version__}

        for pkg in (
            "liquidpy",
            "pandas",
            "enlighten",
            "argx",
            "xqute",
            "python-simpleconf",
            "pipda",
            "varname",
        ):
            versions[pkg] = version(pkg)

        keylen = max(map(len, versions))
        for key in versions:
            ver = versions[key]
            verlines = ver.splitlines()
            print(f"{key.ljust(keylen)}: {verlines.pop(0)}")
            for verline in verlines:  # pragma: no cover
                print(f"{' ' * keylen}  {verline}")
