"""CLI main entrance"""

import re
import asyncio
import importlib
from pathlib import Path

from argx import ArgumentParser

from ._hooks import cli_plugin, AsyncCLIPlugin
from ..version import __version__

parser = ArgumentParser(
    prog="pipen",
    description=f"CLI Tool for pipen v{__version__}",
)


def load_builtin_clis() -> None:
    """Load builtin cli plugins in this directory"""
    for clifile in Path(__file__).parent.glob("*.py"):
        if clifile.stem.startswith("_"):
            continue
        cli = importlib.import_module(f".{clifile.stem}", __package__)
        plg = getattr(cli, cli.__all__[0])
        cli_plugin.register(plg)


async def _main() -> None:
    """Main function of pipen CLI"""
    cli_plugin.load_entrypoints()
    # builtin plugins have the highest priority
    # so they are loaded later to override the entrypoints
    load_builtin_clis()

    plugin_names = sorted(
        cli_plugin.get_enabled_plugin_names(),
        key=lambda cmd: 999 if cmd == "help" else 0,
    )
    plugins = {}
    for name in plugin_names:
        plg = cli_plugin.get_plugin(name, raw=True)

        docstr = plg.__doc__
        if docstr is not None:
            docstr = docstr.strip()

        subparser = parser.add_command(
            plg.name,
            help=(
                None if docstr is None else re.sub(r"\s+", " ", docstr.splitlines()[0])
            ),
            description=docstr,
        )
        plugins[plg.name] = plg(parser, subparser)

    known_parsed, unparsed_argv = parser.parse_known_args()
    plugin = plugins[known_parsed.COMMAND]
    if isinstance(plugin, AsyncCLIPlugin):
        await plugin.post_init()

    parsed = plugin.parse_args(known_parsed, unparsed_argv)
    if isinstance(plugin, AsyncCLIPlugin):
        parsed = await parsed

    exected = plugin.exec_command(parsed)
    if isinstance(plugin, AsyncCLIPlugin):
        await exected


def main() -> None:
    """The main function of pipen CLI"""
    asyncio.run(_main())
