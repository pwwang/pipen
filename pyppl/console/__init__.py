"""Command line tool for PyPPL"""
import importlib
from pathlib import Path
from pyparam import Params
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

# pylint: disable=invalid-name
params = Params(desc='Command Line Tool for PyPPL v{}'.format(__version__))
pluginmgr.hook.cli_addcmd(params=params)


def main():
    """Entry point"""
    parsed = params.parse()
    pluginmgr.hook.logger_init(logger=logger)
    logger.initialize()
    pluginmgr.hook.cli_execcmd(command=parsed.__command__,
                               opts=parsed[parsed.__command__])
