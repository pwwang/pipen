
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

See [here](./api/#pyppl.runner) for all available APIs for runners

## Runner gallery

