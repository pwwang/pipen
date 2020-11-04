import pytest
from pathlib import Path
import pipen
from pipen.utils import brief_list, get_logger, get_mtime, get_plugin_context
from pipen.exceptions import ConfigurationError
from pipen.plugin import plugin

def test_get_logger(caplog):
    logger = get_logger('test', 'info')
    logger.debug('debug message')
    assert 'debug message' not in caplog.text

def test_plugin_context():
    with pytest.raises(ConfigurationError):
        get_plugin_context(['a', 'no:b'])

    plugin.get_plugin('main').enable()
    context = get_plugin_context(['no:main'])

    with context:
        assert plugin.get_plugin('main').enabled is False

    assert plugin.get_plugin('main').enabled is True

def test_brief_list():
    assert brief_list([1]) == '1'

def test_get_mtime_dir():
    package_dir = Path(pipen.__file__).parent
    mtime = get_mtime(package_dir, 2)
    assert mtime > 0
