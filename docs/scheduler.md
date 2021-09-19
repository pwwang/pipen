
`pipen` can send jobs to different scheduler system to run. To specify the scheduler, use `scheduler` and `scheduler_opts` configurations.

## Default supported schedulers

`pipen` uses [`xqute`][1] for scheduler backend support. By default, the `local` and `sge` schedulers are supported by `xqute`. They are also the supported schedulers supported by `pipen`.

### `local`

This is the default scheduler used by `pipen`. The jobs will be run on the local machine.

No scheduler-specific options are available.

### `sge`

Send the jobs to run on `sge` scheduler.

The `scheduler_opts` will be the ones supported by `qsub`.

## Writing your own scheduler plugin

To write a scheduler plugin, you need to subclass `xqute.schedulers.scheduler.Scheduler`.

You may also want to implement a class for jobs, by subclassing `xqute.schedulers.job.Job`, and assign it to the class variable `job_class` to your `xqute.schedulers.scheduler.Scheduler` subclass.

For examples of a scheduler plugin, see [local_scheduler][2] and [sge_scheduler][3].

The `xqute.schedulers.scheduler.Scheduler` subclass can be passed to `scheduler` configuration directly to be used as a scheduler. But you can also register it with entry points:

For `setup.py`, you will need:
```python
setup(
	# ...
	entry_points={"pipen_sched": ["slurm = pipen_slurm"]},
	# ...
)
```

For `pyproject.toml`:
```toml
[tool.poetry.plugins.pipen_sched]
slurm = "pipen_slurm"
```

Then you can switch the scheduler to slurm by `scheduler="slurm"`


[1]: https://github.com/pwwang/xqute
[2]: https://github.com/pwwang/xqute/blob/master/xqute/schedulers/local_scheduler.py
[3]: https://github.com/pwwang/xqute/blob/master/xqute/schedulers/sge_scheduler.py
