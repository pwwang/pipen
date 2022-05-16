"""List available profiles."""
from typing import Any, Mapping

import rtoml  # type: ignore
from rich import print
from rich.panel import Panel
from rich.syntax import Syntax
from simpleconf import ProfileConfig

from ._hooks import CLIPlugin
from ..defaults import CONFIG, CONFIG_FILES

from pyparam import Params

__all__ = ("CLIProfilePlugin",)


class CLIProfilePlugin(CLIPlugin):
    """List available profiles."""

    name = "profile"

    @property
    def params(self) -> Params:
        """Define the params"""
        pms = Params(
            desc=self.__class__.__doc__,
            help_on_void=False,
        )
        pms.add_param(
            "n,name",
            default="",
            desc="The name of the profile to show. "
            "If not provided, show all profiles.",
        )
        return pms

    def exec_command(self, args: Mapping[str, Any]) -> None:
        """Run the command"""

        config = ProfileConfig.load(
            {"default": CONFIG},
            *CONFIG_FILES,
            ignore_nonexist=True,
        )

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
