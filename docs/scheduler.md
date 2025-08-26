
`pipen` can send jobs to different scheduler system to run. To specify the scheduler, use `scheduler` and `scheduler_opts` configurations.

## Default supported schedulers

`pipen` uses [`xqute`][1] for scheduler backend support. The following schedulers are supported by `pipen`:

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

### `container`

Send the jobs to run in a container (Docker/Podman/Apptainer).
The `scheduler_opts` will be used to construct the container command.

They include:
- `image`: The container image to use.
- `entrypoint`: The entrypoint of the container to run the wrapped job script. If not specified, the default entrypoint `/bin/sh` will be used.
- `bin`: The container command to use. If not specified, it will use `docker`.
- `volumes`: A list of volumes to mount to the container. The default volumes are:
  - `workdir`: The working directory of the pipeline, mounted to `/mnt/disks/pipen-pipeline/workdir`.
  - `outdir`: The output directory of the pipeline, mounted to `/mnt/disks/pipen-pipeline/outdir`.
- `envs`: A dictionary of environment variables to set in the container.
- `remove`: Whether to remove the container after the job is done. Default is `True`. Only supported by Docker and Podman.
- `user`: The user to run the container as. Default is the current user. Only supported by Docker and Podman.
- `bin_args`: Additional arguments to pass to the container command. For example, `{"bin_args": ["--privileged"]}` will run the container in privileged mode. Only supported by Docker and Podman.

### `gbatch`

Send the jobs to run using Google Cloud Batch.

The `scheduler_opts` will be used to construct the job configuration. This scheduler requires that the pipeline's `outdir` is a Google Cloud Storage path (e.g., `gs://bucket/path`).

The scheduler options include:
- `project`: Google Cloud project ID
- `location`: Google Cloud region or zone
- `mount`: GCS path to mount (e.g. `gs://my-bucket:/mnt/my-bucket`). You can pass a list of mounts.
- `service_account`: GCP service account email (e.g. `test-account@example.com`)
- `network`: GCP network (e.g. `default-network`)
- `subnetwork`: GCP subnetwork (e.g. `regions/us-central1/subnetworks/default`)
- `no_external_ip_address`: Whether to disable external IP address
- `machine_type`: GCP machine type (e.g. `e2-standard-4`)
- `provisioning_model`: GCP provisioning model (e.g. `SPOT`)
- `image_uri`: Container image URI (e.g. `ubuntu-2004-lts`)
- `entrypoint`: Container entrypoint (e.g. `/bin/bash`)
- `commands`: The command list to run in the container.
	There are three ways to specify the commands:
	1. If no entrypoint is specified, the final command will be
	[commands, wrapped_script], where the entrypoint is the wrapper script
	interpreter that is determined by `JOBCMD_WRAPPER_LANG` (e.g. /bin/bash),
	commands is the list you provided, and wrapped_script is the path to the
	wrapped job script.
	2. You can specify something like "-c", then the final command
	will be ["-c", "wrapper_script_interpreter, wrapper_script"]
	3. You can use the placeholders `{lang}` and `{script}` in the commands
	list, where `{lang}` will be replaced with the interpreter (e.g. /bin/bash)
	and `{script}` will be replaced with the path to the wrapped job script.
	For example, you can specify ["{lang} {script}"] and the final command
	will be ["wrapper_interpreter, wrapper_script"]

Additional keyword arguments can be used for job configuration (e.g. `taskGroups`). See more details at [Google Cloud Batch documentation](https://cloud.google.com/batch/docs/get-started).

By default, the pipeline's workdir is mounted to `/mnt/disks/pipen-pipeline/workdir` and the outdir is mounted to `/mnt/disks/pipen-pipeline/outdir` on the VM.

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
