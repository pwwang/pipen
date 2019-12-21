from pyppl.config import config, DEFAULT_CONFIG
from pyppl.plugin import pluginmgr

config.clear()
config._load(DEFAULT_CONFIG)

for plugin in pluginmgr.get_plugins():
	pluginmgr.unregister(plugin)
