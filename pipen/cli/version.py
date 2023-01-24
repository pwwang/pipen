"""Print help for commands"""
from typing import Any, Mapping

from rich import print
from pyparam import Params

from ._hooks import CLIPlugin

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

    @property
    def params(self) -> Params:
        """Define the params"""
        pms = Params(
            desc=self.__class__.__doc__,
            help_on_void=False,
        )
        return pms

    def exec_command(self, args: Mapping[str, Any]) -> None:
        """Run the command"""
        import sys
        from .. import __version__

        versions = {"python": sys.version, "pipen": __version__}

        for pkg in (
            "liquidpy",
            "pandas",
            "python-slugify",
            "enlighten",
            "pyparam",
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
            for verline in verlines:
                print(f"{' ' * keylen}  {verline}")
