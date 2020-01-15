"""Command line tool for PyPPL"""
import sys
import importlib
from pathlib import Path
from diot import Diot
from pyparam import commands
from ..logger import logger
from ..plugin import config_plugins, pluginmgr
from .. import __version__

CONSOLE_PLUGINS = [
    importlib.import_module('.' + cmdfile.stem, __name__)
    for cmdfile in Path(__file__).parent.glob('*.py')
    if cmdfile.stem[:1] != '_'
]
for console_plugin in CONSOLE_PLUGINS:
    console_plugin.__version__ = 'builtin'

config_plugins(*CONSOLE_PLUGINS)

commands._desc = 'Command Line Tool for PyPPL v{}'.format(__version__)
pluginmgr.hook.cli_addcmd(commands=commands)


def main():
    """Entry point"""
    command, opts, _ = commands._parse(dict_wrapper=Diot)
    pluginmgr.hook.logger_init(logger=logger)
    logger.init()
    pluginmgr.hook.cli_execcmd(command=command, opts=opts)
