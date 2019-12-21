import pytest

from pyppl.plugin import PluginConfig
from pyppl.exception import PluginConfigKeyError

def test_plugin_config():

	pconfig = PluginConfig()
	assert pconfig.__raw__ == {}
	assert pconfig.__cache__ == {}
	assert pconfig.__converter__ == {}

	pconfig.add('a')
	assert pconfig.a == None
	assert pconfig.setcounter('a') == 0

	pconfig.add('b', default = 1, converter = lambda v: v+1)
	assert pconfig.b == 2
	assert pconfig.setcounter('b') == 0
	pconfig.b = 2
	assert pconfig.setcounter('b') == 1
	assert pconfig.b == 3

	pconfig['r.a'] = 4
	assert pconfig.setcounter('r.a') == 1
	assert pconfig['r.a'] == 4

	pconfig.add('x', update = 'ignore')
	pconfig.update({'x': 1})
	assert pconfig.x == 1
	pconfig.x = 10
	pconfig.update({'x': 1})
	assert pconfig.x == 10

	pconfig.add('z', update = 'update', converter = lambda x: x * 2)
	pconfig.z = 10
	assert pconfig.z == 20
	pconfig.update({'z': 1})
	assert pconfig.z == 2
	assert pconfig.z == 2 # use cache

	pconfig.add('c', update = 'update', converter = lambda x: x or {})
	assert pconfig.c == {}
	pconfig.update({'c': {'x': 1}})
	assert pconfig.c['x'] == 1
	pconfig.update({'c': {'x': 2}})
	assert pconfig.c['x'] == 2

	with pytest.raises(PluginConfigKeyError):
		pconfig.update({'y': 2})

