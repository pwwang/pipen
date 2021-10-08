"""CLI main entrance"""
import re
import sys
import importlib
from pathlib import Path
from typing import Iterable

from pyparam import Params
from rich import print

from ._hooks import cli_plugin
from ..version import __version__


def load_builtin_clis() -> None:
    """Load builtin cli plugins in this directory"""
    for clifile in Path(__file__).parent.glob("*.py"):
        if clifile.stem.startswith("_"):
            continue
        cli = importlib.import_module(f".{clifile.stem}", __package__)
        plg = getattr(cli, cli.__all__[0])
        cli_plugin.register(plg)


cli_plugin.load_entrypoints()
# builtin plugins have the highest priority
load_builtin_clis()

params = Params(desc=f"CLI Tool for pipen v{__version__}")


def _print_help(commands: Iterable[str]) -> None:
    """Print help of pipen CLI"""
    params.add_param(
        params.help_keys,
        desc="Print help information for the CLI tool.",
    )
    for command in commands:
        plugin = cli_plugin.get_plugin(command, raw=True)
        params.add_command(
            command,
            re.sub(r"\s+", " ", plugin.__doc__.strip()),
            force=True,
        )
    params.print_help()


def main() -> None:
    """Main function of pipen CLI"""
    args = sys.argv
    commands = sorted(
        cli_plugin.get_enabled_plugin_names(),
        key=lambda cmd: 999 if cmd == "help" else 0,
    )
    if len(args) == 1:
        _print_help(commands)

    command = sys.argv[1]
    help_keys = [
        f"-{key}" if len(key) == 1 else f"--{key}" for key in params.help_keys
    ]
    if command in help_keys:
        _print_help(commands)

    if command not in commands:
        print(
            "[red][b]ERROR: [/b][/red]No such command: "
            f"[green]{command}[/green]"
        )
        _print_help(commands)

    plg = cli_plugin.get_plugin(command, raw=True)()
    parsed = plg.parse_args(sys.argv[2:])
    plg.exec_command(parsed)
