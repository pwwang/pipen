"""List available profiles."""
from __future__ import annotations
from typing import TYPE_CHECKING

import rtoml  # type: ignore
from rich import print
from rich.panel import Panel
from rich.syntax import Syntax
from simpleconf import ProfileConfig

from ._hooks import CLIPlugin
from ..defaults import CONFIG, CONFIG_FILES

if TYPE_CHECKING:
    from argx import ArgumentParser
    from argparse import Namespace

__all__ = ("CLIProfilePlugin",)


class CLIProfilePlugin(CLIPlugin):
    """List available profiles."""

    name = "profile"

    def __init__(
        self,
        parser: ArgumentParser,
        subparser: ArgumentParser,
    ) -> None:
        super().__init__(parser, subparser)
        subparser.add_argument(
            "-n",
            "--name",
            default="",
            help="The name of the profile to show. Show all if not provided.",
        )
        subparser.add_argument(
            "-l",
            "--list",
            action="store_true",
            default=False,
            help="List the names of all available profiles (-n won't work).",
        )

    def exec_command(self, args: Namespace) -> None:
        """Run the command"""

        config = ProfileConfig.load(
            {"default": CONFIG},
            *CONFIG_FILES,
            ignore_nonexist=True,
        )

        if args.list:
            print("\n".join(ProfileConfig.profiles(config)))
            return

        print("Configurations loaded from:")
        print("- pipen.defaults.CONFIG (python dictionary)")
        for conffile in reversed(CONFIG_FILES):
            print(f"- {conffile}")
        print("")

        print("Note:")
        print(
            "- The same profile from different configuration files "
            "are inherited."
        )
        print(
            "- These configurations can still be overriden by "
            "Pipen constructor and process definition."
        )
        print("")

        if not args.name:
            for profile in ProfileConfig.profiles(config):
                with ProfileConfig.with_profile(config, profile):
                    conf = ProfileConfig.detach(config)
                    print(
                        Panel(
                            Syntax(rtoml.dumps(conf), "toml"),
                            title=f"Profile: {profile}",
                            title_align="left",
                        )
                    )

        else:
            if not ProfileConfig.has_profile(config, args.name):
                raise ValueError(f"No such profile: {args.name}")

            ProfileConfig.use_profile(config, args.name)
            conf = ProfileConfig.detach(config)
            print(
                Panel(
                    Syntax(rtoml.dumps(conf), "toml"),
                    title=f"Profile: {args.name}",
                    title_align="left",
                )
            )
