## Loading plugins

If plugins are written as modules, once they are installed, they are enabled.

You can use configurations to disable some plugins:
```toml
[default]
plugins = ['no:pyppl_rich', 'no:pyppl_export']
```

You can also load plugins manually if they are written as a class object:
```python
from pyppl import config_plugins

# enable pyppl_rich, but disable pyppl_export
config_plugins('pyppl_rich', 'no:pyppl_export')
```

## Plugin hooks

The plugin system is implemented with [`pluggy`](https://github.com/pytest-dev/pluggy)

See all available plugins APIs [here](./api/#pyppl.plugin).

## Plugin gallery


