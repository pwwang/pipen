"""List plugins"""
from __future__ import annotations
from typing import TYPE_CHECKING, Any, Iterable, List, Tuple

from rich import print

from ._hooks import CLIPlugin
from ..defaults import (
    CLI_ENTRY_GROUP,
    SCHEDULER_ENTRY_GROUP,
    TEMPLATE_ENTRY_GROUP,
)
from ..utils import load_entrypoints

if TYPE_CHECKING:
    from argx import ArgumentParser
    from argparse import Namespace


COMMAND = "plugins"
GROUPS = [
    "pipen",
    SCHEDULER_ENTRY_GROUP,
    TEMPLATE_ENTRY_GROUP,
    CLI_ENTRY_GROUP,
]
GROUP_NAMES = {
    "pipen": "Pipen",
    SCHEDULER_ENTRY_GROUP: "Scheduler",
    TEMPLATE_ENTRY_GROUP: "Template",
    CLI_ENTRY_GROUP: "CLI",
}

__all__ = ("CliPluginsPlugin",)


def _get_plugins_by_group(group: str) -> Iterable[Tuple[str, Any]]:
    """Get plugins from entry points by group name

    Args:
        group: The name of the group

    Returns:
        A list of tuples with the plugin name and the plugin itself
    """
    for name, obj in load_entrypoints(group):
        yield name, obj


def _list_group_plugins(
    group: str,
    plugins: List[Tuple[str, Any]],
) -> None:
    """List plugins in a single group

    Args:
        group: The group of the plugins
        plugins: A list of tuples with name and plugin
    """
    print("")
    print(f"[bold][u]{GROUP_NAMES[group]} plugins:[/u][/bold]")
    namelen = max(len(name) for name, _ in plugins) if plugins else 0
    for name, plugin in plugins:
        try:
            ver = plugin.version
        except AttributeError:
            try:
                ver = plugin.__version__
            except AttributeError:
                ver = "unknown"
        print(f"- {name.ljust(namelen)}: (version: {ver})")


def _list_plugins(plugins: List[Tuple[str, str, Any]]) -> None:
    """List plugins

    Args:
        plugins: A list of tuples with group, name and plugin
    """
    pipen_plugins = [
        (name, plugin) for group, name, plugin in plugins if group == "pipen"
    ]
    sched_plugins = [
        (name, plugin)
        for group, name, plugin in plugins
        if group == SCHEDULER_ENTRY_GROUP
    ]
    tpl_plugins = [
        (name, plugin)
        for group, name, plugin in plugins
        if group == TEMPLATE_ENTRY_GROUP
    ]
    cli_plugins = [
        (name, plugin)
        for group, name, plugin in plugins
        if group == CLI_ENTRY_GROUP
    ]
    _list_group_plugins("pipen", pipen_plugins)
    _list_group_plugins(SCHEDULER_ENTRY_GROUP, sched_plugins)
    _list_group_plugins(TEMPLATE_ENTRY_GROUP, tpl_plugins)
    _list_group_plugins(CLI_ENTRY_GROUP, cli_plugins)


class CliPluginsPlugin(CLIPlugin):
    """List installed plugins"""

    name = "plugins"

    def __init__(
        self,
        parser: ArgumentParser,
        subparser: ArgumentParser,
    ) -> None:
        super().__init__(parser, subparser)
        subparser.add_argument(
            "-g",
            "--group",
            choices=GROUPS + ["all"],
            default="all",
            help="The name of the entry point group. Show all if not provided",
        )

    def exec_command(self, args: Namespace) -> None:
        """Execute the command"""
        from ..version import __version__
        print("Pipen version:", __version__)

        plugins: List[Tuple[str, str, Any]] = []

        if args.group and args.group != "all":
            for name, plugin in _get_plugins_by_group(args.group):
                plugins.append((args.group, name, plugin))

        else:  # args.name
            for group in GROUPS:
                for name, plugin in _get_plugins_by_group(group):
                    plugins.append((group, name, plugin))

        _list_plugins(plugins)
