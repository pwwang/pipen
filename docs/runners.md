
## Runners

Runners now for `PyPPL` are also implemented as plugins.
Same as `plugins`, if runners are written as modules, they are enabled once they are installed.

Runners should be named as `pyppl-runner-xxx` or `pyppl_runner_xxx` and be used while `pXXX.runner = "xxx"`.
If a runner needs configurations, then the runner should be specified as `pXXX.runner = dict(runner="xxx", ...<other configurations>)`

Runners can be specified using configuration profile. For example:

```toml
# pyppl.toml
[default.runner]
runner = "local"
ssh_servers = ["server1", "server2"]
sge_q = "1-day"

[longerq]
forks = 32
runner = "sge"
sge_q = "4-days"
```

```python
PyPPL(config_files = 'pyppl.toml').start(pXXX).run('longerq')
pXXX.forks == 32
pXXX.runner == dict(runner = "sge", sge_q = "4-days", ssh_servers = ["server1", "server2"])
```

If a profile does not exist, it will be fallen back to a real runner name. For example:
```python
PyPPL().start(pXXX).run('ssh')
pXXX.runner == dict(runner = "ssh")
```

## Runner APIs

See [here](https://pyppl.readthedocs.io/en/latest/api/#pypplrunner) for all available APIs for runners

## Entry point

You can register plugins by yourself using `pyppl.register_runner`. However, if you want to expose your runner to `PyPPL` by adding entrypoint to your `setup.py`, `pyproject.toml` or other equivalent packaging setting files:

For `setup.py`, you will need:
```python
setup(
	# ...
	entry_points={"pyppl_runner": [
		"pyppl_runner_dry = pyppl_runners:dry",
		"pyppl_runner_ssh = pyppl_runners:ssh",
		"pyppl_runner_sge = pyppl_runners:sge",
		"pyppl_runner_slurm = pyppl_runners:slurm",
	]},
	# ...
)
```

For `pyproject.toml`:
```toml
[tool.poetry.plugins.pyppl_runner]
pyppl_runner_dry   = "pyppl_runners:dry"
pyppl_runner_ssh   = "pyppl_runners:ssh"
pyppl_runner_sge   = "pyppl_runners:sge"
pyppl_runner_slurm = "pyppl_runners:slurm"
```


## Runner gallery

- [pyppl_runners](https://github.com/pwwang/pyppl_runners): Common runners for PyPPL
