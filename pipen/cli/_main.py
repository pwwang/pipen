"""CLI main entrance"""
import importlib
from pathlib import Path
from typing import List

from pyparam import Params

from ._hooks import cli_plugin
from ..version import __version__


def load_builtin_clis() -> None:
    """Load builtin cli plugins in this directory"""
    for clifile in Path(__file__).parent.glob("*.py"):
        if clifile.stem.startswith("_"):
            continue
        cli = importlib.import_module(f".{clifile.stem}", __package__)
        cli_plugin.register(cli)


cli_plugin.load_entrypoints()
# builtin plugins have the highest priority
load_builtin_clis()

params = Params(desc=f"CLI Tool for pipen v{__version__}")
cli_plugin.hooks.add_commands(params=params)


def main(args: List[str] = None) -> None:
    """Main function of pipen CLI

    Args:
        args: Provide arguments to parse. Only for testing.
    """
    parsed = params.parse(args)
    cli_plugin.hooks.exec_command(
        command=parsed.__command__,
        args=parsed[parsed.__command__],
    )
