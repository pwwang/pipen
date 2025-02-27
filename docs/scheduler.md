
`pipen` can send jobs to different scheduler system to run. To specify the scheduler, use `scheduler` and `scheduler_opts` configurations.

## Default supported schedulers

`pipen` uses [`xqute`][1] for scheduler backend support. By default, the `local` and `sge` schedulers are supported by `xqute`. They are also the supported schedulers supported by `pipen`.

### `local`

This is the default scheduler used by `pipen`. The jobs will be run on the local machine.

No scheduler-specific options are available.

### `sge`

Send the jobs to run on `sge` scheduler.

The `scheduler_opts` will be the ones supported by `qsub`.

### `slurm`

Send the jobs to run on `slurm` scheduler.

The `scheduler_opts` will be the ones supported by `sbatch`.

### `ssh`

Send the jobs to run on a remote machine via `ssh`.

The `scheduler_opts` will be the ones supported by `ssh`.

See also [xqute][1].

### `gbatch`

Send the jobs to run using Google Batch Jobs.

The `scheduler_opts` will be used to construct the job configuration (json) file.

By default, `taskGroups[0].taskSpec.runnables[0].script.text` is set to run the job script, and `taskGroups[0].taskSpec.volumes[0]` and `taskGroups[0].taskSpec.volumes[1]` will be set to mount the workdir and output directory to the VM.
The `scheduler_opts` will be used to set the other fields in the job configuration file.

`gbatch` scheduler also supports a `fast_mount` option to speed up the mounting a cloud directory to the VM. For example, `scheduler_opts={"fast_mount": "gs://bucket/path:/mnt/dir"}` will mount `gs://bucket/path` to `/mnt/dir` on the VM.

## Writing your own scheduler plugin

To write a scheduler plugin, you need to subclass both `xqute.schedulers.scheduler.Scheduler` and `pipen.scheduler.SchedulerPostInit`.

For examples of a scheduler plugin, see [local_scheduler][2], [sge_scheduler][3], [slurm_scheduler][4], [ssh_scheduler][5], and [gbatch_scheduler][6], and also `pipen.scheduler`.


A scheduler class can be passed to `scheduler` configuration directly to be used as a scheduler. But you can also register it with entry points:

For `setup.py`, you will need:
```python
setup(
	# ...
	entry_points={"pipen_sched": ["mysched = pipen_mysched"]},
	# ...
)
```

For `pyproject.toml`:
```toml
[tool.poetry.plugins.pipen_sched]
mysched = "pipen_mysched"
```

Then you can switch the scheduler to `mysched` by `scheduler="mysched"`


[1]: https://github.com/pwwang/xqute
[2]: https://github.com/pwwang/xqute/blob/master/xqute/schedulers/local_scheduler.py
[3]: https://github.com/pwwang/xqute/blob/master/xqute/schedulers/sge_scheduler.py
[4]: https://github.com/pwwang/xqute/blob/master/xqute/schedulers/slurm_scheduler.py
[5]: https://github.com/pwwang/xqute/blob/master/xqute/schedulers/ssh_scheduler/
[4]: https://github.com/pwwang/xqute/blob/master/xqute/schedulers/gbatch_scheduler.py
