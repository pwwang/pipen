"""List all available plugins, including runners, even they are temporarily disabled."""
from ..plugin import hookimpl, pluginmgr
from ..runner import runnermgr, _runner_name
from ..logger import logger

@hookimpl
def cli_addcmd(commands):
	"""Add plugins command"""
	commands.plugins._hbald = False
	commands.plugins        = __doc__

@hookimpl
def cli_execcmd(command, opts): # pylint: disable=unused-argument
	"""Run the command"""
	if command == 'plugins':
		logger.init({'level': 'notset'})
		for plugin in sorted(pluginmgr.get_plugins(),
			key = lambda plug: pluginmgr.get_name(plug)):

			logger.plugin('Plugin %s: v%s',
				pluginmgr.get_name(plugin),
				'Unknown' if not hasattr(plugin, '__version__') else plugin.__version__)

		for plugin in sorted(runnermgr.get_plugins(),
			key = lambda plug: _runner_name(plug)):

			logger.plugin('Runner %s: v%s',
				_runner_name(plugin),
				'Unknown' if not hasattr(plugin, '__version__') else plugin.__version__)
