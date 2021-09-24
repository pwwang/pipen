"""List available profiles."""
from typing import TYPE_CHECKING, Any, Mapping

import toml  # type: ignore
from rich import print
from rich.panel import Panel
from rich.syntax import Syntax
from simpleconf import Config

from ._hooks import cli_plugin
from ..defaults import CONFIG, CONFIG_FILES

if TYPE_CHECKING:  # pragma: no cover
    from pyparam import Params

COMMAND = "profile"


@cli_plugin.impl
def add_commands(params: "Params"):
    """Add profile command"""
    cmd = params.add_command(COMMAND, desc=__doc__, help_on_void=False)
    cmd.add_param(
        "n,name",
        default="",
        desc="The name of the profile to show. "
        "If not provided, show all profiles.",
    )


@cli_plugin.impl
def exec_command(command: str, args: Mapping[str, Any]) -> None:
    """Run the command"""
    if command != COMMAND:
        return  # pragma: no cover, need more sub-commands to test

    config = Config()
    config._load({"default": CONFIG})
    config._load(*CONFIG_FILES)

    print("Configurations loaded from:")
    for conffile in reversed(CONFIG_FILES):
        print(f"- {conffile}")
    print("")

    print("Note:")
    print(
        "- The same profile from different configuration files are inherited."
    )
    print(
        "- These configurations can still be overriden by Pipen constructor "
        "and process definition."
    )
    print("")

    if not args.name:
        for profile in config._profiles:
            with config._with(profile, "default"):
                print(
                    Panel(
                        Syntax(toml.dumps(config), "toml"),
                        title=f"Profile: {profile}",
                        title_align="left",
                    )
                )

    else:
        if args.name not in config._profiles:
            raise ValueError(f"No such profile: {args.name}")

        config._use(args.name)
        print(
            Panel(
                Syntax(toml.dumps(config), "toml"),
                title=f"Profile: {args.name}",
                title_align="left",
            )
        )
