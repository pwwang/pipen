"""List plugins"""

from typing import TYPE_CHECKING, Any, Iterable, List, Mapping, Tuple

from rich import print

from ._hooks import cli_plugin
from ..defaults import (
    CLI_ENTRY_GROUP,
    SCHEDULER_ENTRY_GROUP,
    TEMPLATE_ENTRY_GROUP,
)
from ..utils import load_entrypoints

if TYPE_CHECKING:  # pragma: no cover
    from pyparam import Params

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
    print(f"{GROUP_NAMES[group]} plugins:")
    for name, plugin in plugins:
        try:
            ver = plugin.version
        except AttributeError:
            try:
                ver = plugin.__version__
            except AttributeError:
                ver = "unknown"
        print(f"- {name}: (version: {ver})")


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


@cli_plugin.impl
def add_commands(params: "Params"):
    """Add plugins command"""
    cmd = params.add_command(COMMAND, desc=__doc__, help_on_void=False)
    cmd.add_param(
        "g,group",
        default="",
        desc="The name of the entry point group. "
        "If not provided, show all plugins. "
        f"Avaiable groups are: {' '.join(GROUPS)}",
    )


@cli_plugin.impl
def exec_command(command: str, args: Mapping[str, Any]) -> None:
    """Run the command"""
    if command != COMMAND:
        return  # pragma: no cover, need more sub-commands to test

    plugins: List[Tuple[str, str, Any]] = []

    if args.group:
        for name, plugin in _get_plugins_by_group(args.group):
            plugins.append((args.group, name, plugin))

    else:  # args.name
        for group in GROUPS:
            for name, plugin in _get_plugins_by_group(group):
                plugins.append((group, name, plugin))

    _list_plugins(plugins)
