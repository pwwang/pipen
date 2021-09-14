`pipen` uses [`simplug`][1] for plugin support. There are very enriched hooks available for you to write your own plugins to extend `pipen`.

## Plugin hooks

To implement a function in your plugin, just simply:

```python
from pipen import plugin

@plugin.impl
[async ]def hook(...):
    ...
```

Note that you have to use keyword-arguments and they have to match the hook signature.

See [`simplug`][1] for more details.

### Pipeline-level hooks

- `on_setup(config)` (sync):

    Setup for the plugin, mainly used for initalization and set the default values for the plugin configuration items.

    This is only called once even when you have multiple pipelines (`Pipen` objects) in a python session.

- `on_init(pipen)` (async)

    Called when all pipeline-level configurations are calculated. You can access the configurations by `pipen.config.xxx`.

    Be careful to use the process-level configurations here, as they can be overridden by process definition.

- `on_start(pipen)` (async)

    Right before the pipeline starts to run. The process relationships are inferred here.
    You can access the start processes by `pipen.starts` and all processes by `pipen.procs` in the sequence of the execution order.

- `on_complete(pipen, succeeded)` (async)

    After all processes finish. `succeeded` indicates whether all processes/jobs finish successfully.

### Process-level hooks

- `on_proc_start(proc)` (async)

    When process object initialization completes, including the `xqute` and job initialization. The `output_data` is also accessible here. The process is ready to run.

- `on_proc_shutdown(proc, sig)` (sync)

    When the process is shut down (i.e. by `<ctrl-c>`). You can access the signal that shuts the process down by `sig`. Only first plugin (based on the priority) that implements this hook will get called.

- `on_proc_done(proc, succeeded)` (async)

    When a process is done.

### Job-level hooks

- `on_job_init(proc, job)` (async)

    When a job is initialized

- `on_job_queued(proc, job)` (async)

    When a job is queued in xqute. Note it might not be queued yet in the scheduler system.

- `on_job_submitting(proc, job)` (async)

    When a job is submitting.

    The first plugin (based on priority) have this hook return `False` will cancel the submission


- `on_job_submitted(proc, job)` (async)

    When a job is submitted in the scheduler system.

- `on_job_running(proc, job)` (async)

    When a job starts to run in then scheduler system.

- `on_job_killing(proc, job)` (async)

    When a job is being killed.

    The first plugin (based on priority) have this hook return `False` will cancel the killing

- `on_job_killed(proc, job)` (async)

    When a job is killed

- `on_job_succeeded(proc, job)` (async)

    When a job completes successfully


- `on_job_failed(proc, job)` (async)

    When a job is done but failed (i.e. return_code == 1).


## Loading plugins

You can specify the plugins to be loaded by specifying the names or the plugin itself in `plugins` configuration. With names, the plugins will be loaded from [entry points][2].

You can also disable some plugins if they are set in the lower-priority configurations. For example, you want to disable `pipen_verbose` (enabled in a configuration file) for a pipeline:

```python
Pipen(..., plugins=["no:pipen_verbose"])
```

!!! note

    When use `no:` in `plugins`, it should be all negated or positive. The best practice is that, enabled many plugins in configuration files and disable some for specific pipelines, or enable as few as possible plugins in configuration files, and enable some for specific pipelines.

## Writing a plugin

You can write your own plugin by implementing some of the above hooks. You can import the plugin directly and add it to `Pipen(..., plugins=[...]). For example:

```python
from pipen import plugin, Pipen

class PipenPlugin:

    @plugin.impl
    [async ]def hook(...):
        ...

Pipen(..., plugins=[PipenPlugin])


You can also use the entry point to register your plugin using the group name `pipen`

For `setup.py`, you will need:
```python
setup(
	# ...
	entry_points={"pipen": ["pipen_verbose = pipen_verbose"]},
	# ...
)
```

For `pyproject.toml`:
```toml
[tool.poetry.plugins.pipen]
pipen_verbose = "pipen_verbose"
```

Then the plugin `pipen_verbose` can be loaded by `plugins=["pipen_verbose"]` or disabled by `plugins=["no:pipen_verbose"]`

### Logging to the console from a plugin

Of course you can do arbitrary logging from a plugin. However, to keep the consistency with main logger of `pipen`, The best practice is:

```python
from pipen.utils import get_logger

logger = get_logger("verbose", "info")

# do some logging inside the hooks
```

The above code will produce some logging on the console like this:

```
11-04 12:00:19 I main    ╭═══════════════════════════ Process ═══════════════════════════╮
11-04 12:00:19 I main    ║ Undescribed.                                                  ║
11-04 12:00:19 I main    ╰═══════════════════════════════════════════════════════════════╯
11-04 12:00:19 I main    Process: Workdir: '.pipen/process'
11-04 12:00:19 I verbose Process: size: 10
11-04 12:00:19 I verbose Process: [0/9] in.a: 0
11-04 12:00:19 I verbose Process: [0/9] out.b: pipeline-0-output/Process/0/a.txt
```

## Plugin gallery

- [`pipen-verbose`][3]: Add verbosal information in logs for pipen.
- [`pipen-report`][4]: Generate report for pipen
- [`pipen-diagram`][5]: Draw pipeline diagrams for pipen
- More to add ...


[1]: https://github.com/pwwang/simplug
[2]: https://packaging.python.org/specifications/entry-points/
[3]: https://github.com/pwwang/pipen-verbose
[4]: https://github.com/pwwang/pipen-report
[5]: https://github.com/pwwang/pipen-diagram
