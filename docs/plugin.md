`pipen` uses [`simplug`][1] for plugin support. There are very enriched hooks available for you to write your own plugins to extend `pipen`.

## Runtime plugins

### Plugin hooks

To implement a function in your plugin, just simply:

```python
from pipen import plugin

@plugin.impl
[async ]def hook(...):
    ...
```

Note that you have to use keyword-arguments and they have to match the hook signature.

See [`simplug`][1] for more details.

#### Pipeline-level hooks

- `on_setup(pipen)` (sync):

    Setup for the plugin, mainly used for initalization and set the default values for the plugin configuration items.

    This is only called once even when you have multiple pipelines (`Pipen` objects) in a python session.

- `on_init(pipen)` (async)

    Called when pipeline is initialized. Note that here only default configurations are loaded (from defaults.CONFIG and config files). The configurations from `Pipen` constructor and the processes are not loaded yet. It's useful for plugins to change the default configurations.

- `on_start(pipen)` (async)

    Right before the pipeline starts to run. The process relationships are inferred here.
    You can access the start processes by `pipen.starts` and all processes by `pipen.procs` in the sequence of the execution order.

- `on_complete(pipen, succeeded)` (async)

    After all processes finish. `succeeded` indicates whether all processes/jobs finish successfully.

#### Process-level hooks

- `on_proc_create(proc)` (sync)

    Called before proc get instantiated.
    Enables plugins to modify the default attributes of processes

- `on_proc_input_computed(proc)` (sync)

    Called after process input data is computed.

- `on_proc_script_computed(proc)` (sync)

    Called after process script is computed.

    The script is computed as a string that is about to compiled into a
    template. You can modify the script here.

- `on_proc_start(proc)` (async)

    When process object initialization completes, including the `xqute`. The process is ready to run.
    The jobs will be then initialized and fed to the scheduler.

- `on_proc_shutdown(proc, sig)` (sync)

    When the process is shut down (i.e. by `<ctrl-c>`). You can access the signal that shuts the process down by `sig`. Only first plugin (based on the priority) that implements this hook will get called.

- `on_proc_done(proc, succeeded)` (async)

    When a process is done.

#### Job-level hooks

- `on_job_init(job)` (async)

    When a job is initialized

- `on_job_queued(job)` (async)

    When a job is queued in xqute. Note it might not be queued yet in the scheduler system.

- `on_job_submitting(job)` (async)

    When a job is submitting.

    The first plugin (based on priority) have this hook return `False` will cancel the submission

- `on_job_submitted(job)` (async)

    When a job is submitted in the scheduler system.

- `on_job_started(job)` (async)

    When a job starts to run in then scheduler system.

- `on_job_polling(job)` (async)

    When status of a job is being polled.

- `on_job_killing(job)` (async)

    When a job is being killed.

    The first plugin (based on priority) have this hook return `False` will cancel the killing

- `on_job_killed(job)` (async)

    When a job is killed

- `on_job_succeeded(job)` (async)

    When a job completes successfully

- `on_job_cached(job)` (async)

    When a job is cached

- `on_job_failed(job)` (async)

    When a job is done but failed (i.e. return_code == 1).

- `on_jobcmd_init(job) -> str` (sync)

    When the job command wrapper script is initialized before the prescript is run

    This should return a piece of bash code to be inserted in the wrapped job
    script (template), which is a python template string, with the following
    variables available: `status` and `job`. `status` is the class `JobStatus` from
    `xqute.defaults.py` and `job` is the `Job` instance.

    For multiple plugins, the code will be inserted in the order of the plugin priority.

    The code will replace the `#![jobcmd_init]` placeholder in the wrapped job script.
    See also <https://github.com/pwwang/xqute/blob/master/xqute/defaults.py#L95>

- `on_jobcmd_prep(job) -> str` (sync)

    When the job command right about to be run

    This should return a piece of bash code to be inserted in the wrapped job
    script (template), which is a python template string, with the following
    variables available: `status` and `job`. `status` is the class `JobStatus` from
    `xqute.defaults.py` and `job` is the `Job` instance.

    The bash variable `$cmd` is accessible in the context. It is also possible to
    modify the `cmd` variable. Just remember to assign the modified value to `cmd`.

    For multiple plugins, the code will be inserted in the order of the plugin priority.
    Keep in mind that the `$cmd` may be modified by other plugins.

    The code will replace the `#![jobcmd_prep]` placeholder in the wrapped job script.
    See also <https://github.com/pwwang/xqute/blob/master/xqute/defaults.py#L95>

- `on_jobcmd_end(job) -> str` (sync):

    When the job command finishes and after the postscript is run

    This should return a piece of bash code to be inserted in the wrapped job
    script (template), which is a python template string, with the following
    variables available: `status` and `job`. `status` is the class `JobStatus` from
    `xqute.defaults.py` and `job` is the `Job` instance.

    The bash variable `$rc` is accessible in the context, which is the return code
    of the job command.

    For multiple plugins, the code will be inserted in the order of the plugin priority.

    The code will replace the `#![jobcmd_end]` placeholder in the wrapped job script.
    See also <https://github.com/pwwang/xqute/blob/master/xqute/defaults.py#L95>

### Loading plugins

You can specify the plugins to be loaded by specifying the names or the plugin itself in `plugins` configuration. With names, the plugins will be loaded from [entry points][2].

You can also disable some plugins if they are set in the lower-priority configurations. For example, you want to disable `pipen_verbose` (enabled in a configuration file) for a pipeline:

```python
Pipen(..., plugins=["-pipen_verbose"])
```

!!! note

    You can use `+` as prefix to enable a disabled plugin, or `-` as prefix to disable an enabled plugin. If no prefix is used, only the specified plugins will be enabled and all other plugins will be disabled. You should either use `+` or `-` for all plugins or none of them. If a plugin is not given as a string, it will be treated as `+plugin`.

### Writing a plugin

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

Then the plugin `pipen_verbose` can be loaded by `plugins=["+pipen_verbose"]` or disabled by `plugins=["-pipen_verbose"]`

#### Logging to the console from a plugin

Of course you can do arbitrary logging from a plugin. However, to keep the consistency with main logger of `pipen`, The best practice is:

```python
from pipen.utils import get_logger

logger = get_logger("verbose", "info")

# do some logging inside the hooks
```

The above code will produce some logging on the console like this:

```shell
11-04 12:00:19 I main    ╭═══════════════════════════ Process ═══════════════════════════╮
11-04 12:00:19 I main    ║ Undescribed.                                                  ║
11-04 12:00:19 I main    ╰═══════════════════════════════════════════════════════════════╯
11-04 12:00:19 I main    Process: Workdir: '.pipen/process'
11-04 12:00:19 I verbose Process: size: 10
11-04 12:00:19 I verbose Process: [0/9] in.a: 0
11-04 12:00:19 I verbose Process: [0/9] out.b: pipeline-0-output/Process/0/a.txt
```

## CLI plugins

See [CLI][11] for more details.

## Plugin gallery

- [`pipen-verbose`][3]: Add verbosal information in logs for pipen.
- [`pipen-report`][4]: Generate report for pipen
- [`pipen-filters`][8]: Add a set of useful filters for pipen templates.
- [`pipen-diagram`][5]: Draw pipeline diagrams for pipen
- [`pipen-args`][6]: Command line argument parser for pipen
- [`pipen-dry`][7]: Dry runner for pipen pipelines
- [`pipen-annotate`][12]: Use docstring to annotate pipen processes
- [`pipen-board`][13]: Visualize configuration and running of pipen pipelines on the web
- [`pipen-lock`][14]: Process lock for pipen to prevent multiple runs at the same time.
- [`pipen-log2file`][15]: Save running logs to file for pipen
- [`pipen-poplog`][16]: Populate logs from jobs to running log of the pipeline
- [`pipen-runinfo`][17]: Save running information to file for pipen
- [`pipen-gcs`][9]: A plugin for pipen to handle files in Google Cloud Storage.

[1]: https://github.com/pwwang/simplug
[2]: https://packaging.python.org/specifications/entry-points/
[3]: https://github.com/pwwang/pipen-verbose
[4]: https://github.com/pwwang/pipen-report
[5]: https://github.com/pwwang/pipen-diagram
[6]: https://github.com/pwwang/pipen-args
[7]: https://github.com/pwwang/pipen-dry
[8]: https://github.com/pwwang/pipen-filters
[9]: https://github.com/pwwang/pipen-gcs
[11]: ../cli
[12]: https://github.com/pwwang/pipen-annotate
[13]: https://github.com/pwwang/pipen-board
[14]: https://github.com/pwwang/pipen-lock
[15]: https://github.com/pwwang/pipen-log2file
[16]: https://github.com/pwwang/pipen-poplog
[17]: https://github.com/pwwang/pipen-runinfo
