from pyppl.plugin import pluginmgr
for plugin in pluginmgr.get_plugins():
	pluginmgr.unregister(plugin)
