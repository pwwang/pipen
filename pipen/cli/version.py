"""Print help for commands"""
from __future__ import annotations
from typing import TYPE_CHECKING

from rich import print

from ._hooks import CLIPlugin

if TYPE_CHECKING:
    from argparse import Namespace

__all__ = ("CLIVersionPlugin",)


def get_pkg_version(pkg: str) -> str:
    try:
        from importlib.metadata import version
        return version(pkg)
    except ImportError:  # pragma: no cover
        from pkg_resources import get_distribution  # type: ignore
        return get_distribution(pkg).version


class CLIVersionPlugin(CLIPlugin):
    """Print versions of pipen and its dependencies"""

    name = "version"

    def exec_command(self, args: Namespace) -> None:
        """Run the command"""
        import sys
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
            versions[pkg] = get_pkg_version(pkg)

        keylen = max(map(len, versions))
        for key in versions:
            ver = versions[key]
            verlines = ver.splitlines()
            print(f"{key.ljust(keylen)}: {verlines.pop(0)}")
            for verline in verlines:  # pragma: no cover
                print(f"{' ' * keylen}  {verline}")
