# Loading plugins

You can use configurations to enable plugins:
```yaml
default:
	_plugins: ['pyppl_report', 'pyppl_flowchart']
```

Remember the plugins have to on the `$PYPHONPATH`.

Order of plugin registering: FIFO. That means later registered plugin has higher prioity. In the above example, `pyppl_flowchart` has higher prioity. If they use the same `Proc` attribute, while with `__setattr__` and `__getattr__`, `pyppl_flowchart` will overwrite the one that has been set/get by `pyppl_report`.

!!! hint

	By default, we will have [`pyppl_report`](https://github.com/pwwang/pyppl_report) and [`pyppl_flowchart`](https://github.com/pwwang/pyppl_flowchart) enabled. However, if you want to disable all plugins, you can set `_plugins` with `None`. For example, you can use environment variable:
	```shell
	PYPPL_default__plugins="py:None" python your-pipeline.py
	```

# Plugin hooks

The plugin system is implemented with [`pluggy`](https://github.com/pytest-dev/pluggy)

- `setup(config)`

	Some configuration setups.

	__:params__\
	`config (simpleconf.Config)`: The global config object

- `procSetAttr(proc, name, value)`

	Define how to set attributes of a process

	__:params__\
	`proc (Proc)`: The process object\
	`name (str)`: The name of the attribute\
	`value (any)`: The value of the attribute

- `procGetAttr(proc, name)`

	Get the value of the attribute

	__:params__\
	`proc (Proc)`: The process object\
	`name (str)`: The name of the attribute

	!!! warning

		You basically cannot set/get an attribute other than the existing keys of `Proc.config` and `Proc.props`. However, since global configs will be loaded and `Proc.config`, so you can create an attribute in `setup` first. For example:
		```python
		from os import path
		from pyppl.plugin import hookimpl
		@hookimpl
		def setup(config):
			config['report'] = ''

		@hookimpl
		def procGetAttr(proc, name):
			return path.realpath(proc.config.report)
		```

- `procPreRun(proc)`

	Before a process starts to run

	__:params__\
	`proc (Proc)`: The process object

- `procPostRun(proc)`

	After a process finishes

	__:params__\
	`proc (Proc)`: The process object

- `procFail(proc)`

	When a process fails

	__:params__\
	`proc (Proc)`: The process object

- `pypplInit(ppl)`

	Right after a pipeline initiates

	__:params__\
	`ppl (PyPPL)`: The pipeline object

- `pypplPreRun(ppl)`

	Before the pipeline starts to run

	__:params__\
	`ppl (PyPPL)`: The pipeline object

- `pypplPostRun(ppl)`

	After the pipeline finishes

	__:params__\
	`ppl (PyPPL)`: The pipeline object

- `jobPreRun(job)`

	Before a job starts to run

	__:params__\
	`job (Job)`: The job object

- `jobPostRun(job)`

	After a job finishes

	__:params__\
	`job (Job)`: The job object

- `jobFail(job)`

	When job fails

	__:params__\
	`job (Job)`: The job object

# Some help functions

- `addmethod(ppl, name, method)`

	Add a method to `PyPPL` object. This wrapper enables method chaining for the object. For example, you can do `PyPPL().start().flowchart().run().report()` with this help function:
	```python
	@hookimpl
	def pypplInit(ppl):
		addmethod(ppl, 'flowchart', pypplFlowchart)
		addmethod(ppl, 'report', pypplReport)
	```

- `prerun`/`postrun`

	Decorators to make sure the method is called at the right position (before `.run()` or after it).
	For example:
	```python
	@prerun
	def pypplFlowchart(ppl, fcfile = None, dotfile = None):
		"""Generating flowchart for PyPPL"""
	```
	When you call it like:
	```python
	PyPPL().run().flowchart()
	```
	A `PyPPLFuncWrongPositionError` exception will be raised.
