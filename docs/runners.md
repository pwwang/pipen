
# Running profile
A running profile defines the parameters that needed for a pipeline to run. Generally it contains the runner, the parameters for the runner and the common settings for the processes.
A typical running profile is as follows:
```python
{
    'runner': 'sge',
    'sgeRunner': {
        'queue': '1-day'
    },
    'forks': 32
}
```

!!! caution
    You may also put other settings of processes into a running profile, but keep in mind:
    1. The value will not be overridden if the attribute is set explicitly (i.e: `p.forks = 10`)
    2. Only set common attributes for all processes in a pipeline to avoid unexprected behavior. For example, you probably don't want this in general cases to set the same script for all processes:
    ```python
    {
        'script': 'file:/path/to/script'
    }
    ```

# Defining running profiles
You may pre-define some profiles so that you can easily swith them by:
```python
PyPPL().start(pXXX).run('profile1')
PyPPL().start(pXXX).run('profile2')
```
You can define profiles in `PyPPL`'s default configuration files: `$HOME/.PyPPL.yaml`, `$HOME/.PyPPL` and/or `$HOME/.PyPPL.json`. The latter ones have high priorities. `$HOME/.PyPPL` should also be in `JSON` format. Take `$HOME/.PyPPL.yaml` (requiring `pyyaml`) for example, the content is like:
```yaml
default:
    runner: local
    forks: 1
    echo: stderr
profile1:
    runner: sge
    sgeRunner:
        queue: 1-day
profile2:
    runner: sge
    sgeRunner:
        queue: 7-days
```


You may also define some profiles in a file somewhere else, say `/path/to/myprofiles.yaml`. Just pass the file to `PyPPL` constructor:
```python
PyPPL(cfgfile = '/path/to/myprofiles.yaml').start(pXXX).run('profile1')
```

!!! note
    This has higher priority than default configuration files.

You can also pass a temporary to `PyPPL` constructor directly:
```python
PyPPL({
    'runner': 'sge',
    'sgeRunner': {'queue': '1-day'}
}).start(pXXX).run()
```

!!! note
    In this way, the profiles have higher priorities than the ones defined in configuration files.

Or even, you can also specify a profile to `run` function to ask the pipeline run with the profile directly:
```python
PyPPL().start(pXXX).run({
    'runner': 'sge',
    'sgeRunner': {
        'queue': '1-day'
    }
})
```

!!! note
    This has the even higher priority. If both specified, the one in `run` will overwrite the on in `PyPPL`

# Built-in runners
We have 5 built-in runners (`RunnerLocal`, `RunnerSsh`, `RunnerSge`, `RunnerSlurm`, `runnerDry`), you can also define you own runners.

You can either tell one process to use a runner, or even, you can tell the pipeline to use one runner for all the processes. That means each process can have the same runner or a different one. To tell a process which runner to use, just specify the runner name to `pXXX.runner` (for example, `pXXX.runner = "sge"` to use the sge runner). Each process may use different configuration for the runner (`pXXX.sgeRunner`) or the same one by [configuring the pipeline](./configure-a-pipeline/).

# Configurations for ssh runner
Ssh runner takes the advantage to use the computing resources from other servers that can be connected via `ssh`. The `ssh` command allows us to pass the command to the server and execute it: `ssh [options] [command]`

!!! caution
    1. ssh runner only works when the servers share the same file system.
    2. you have to [configure](http://www.linuxproblem.org/art_9.html) so that you don't need a password to log onto the servers, or use a private key to connect to the ssh servers.
    3. The jobs will be distributed equally to the servers.

To tell a process the available ssh servers:
```python
pXXX.sshRunner = {
    "servers": ["server1", "server2", ...],
    "keys": ["/path/to/keyfile1", "/path/to/keyfile2", ...],
    "checkAlive": False
}
```
`checkAlive` is to tell the pipeline to check whether the `servers` are alive, then use only the alive servers. Otherwise use all the `servers`.
You may also specify a number for `checkAlive` to set a timeout. (see: https://pwwang.github.io/PyPPL/api/#module-pypplrunnersrunner_ssh)

You can have complicated ssh configurations which can be set by the system ssh config subsystem:

`$HOME/.ssh/config`:
```
# contents of $HOME/.ssh/config
Host dev
    HostName dev.example.com
    Port 22000
    User fooey
```

If you use different usernames to log on the servers, you may also specify the usernames as well:
```python
pXXX.sshRunner = {"servers": ["user1@server1", "user2@server2", ...]}
```

You can also add `preScript` and `postScript` for all jobs:
```python
pXXX.sshRunner = {
    "servers":[...],
    "preScript": "mkdir some/dir/to/be/made",
    "postScript": "rm -rf /path/to/job/tmp/dir"
}
```

To make a running profile with it for a pipeline for all processes:
```python
PyPPL ({
    # default profile
    'default': {
        'sshRunner': {"servers": ["user1@server1", "user2@server2", ...]}
    },
    'ssh3': {
        'runner': 'ssh',
        'sshRunner': {
            "servers": ["server1", "server2", "server3"],
            "keys": ["/path/to/key1", "/path/to/key2", "/path/to/key3"]
        }
    }
})
```
Also see "[pipeline configration](./configure-a-pipeline/)" for more details.

The constructor of the runner will change the actual script to run the following (`<workdir>/0/job.script.ssh`):

```bash
#!/usr/bin/env bash
ssh -i "/path/to/key1" user1@server1 "cd <cwd>; <workdir>/0/job.script"
```

# Configurations for sge runner
Similarly, you can also submit your jobs to SGE servers using `qsub`. To set the options for a process:
```python
pXXX.sgeRunner = {
    "sge.q" : "1-day",          # the queue
    "sge.M" : "user@domain.com",# The email for notification
    "sge.l" : "h_vmem=4G",
    "sge.l ": "h_stack=512M",   # Remember to add an extra space
                                # so that it won't override the previous "sge.l"
    "sge.m" : "abe",            # When to notify
    "sge.notify": True,
    "preScript":  "source /home/user/.bash_profile >&/dev/null; mkdir /tmp/my",  # load the environment and create the temporary directory
    "postScript": "rm -rf /tmp/my" # clean up
}
```
Please check `man qsub` to find other options. Remember to add a `sge.` prefix to the option name.

To make a running profile with it for a pipeline for all processes:
```python
PyPPL({
    'proc': {
        'sgeRunner': {
            #...
        }
    }
})
```
Also see "[pipeline configuration](./configure-a-pipeline/)" for more details.

The constructor of the runner will change the script to run to the following (`<workdir>/0/job.script.sge`):
```bash
#!/usr/bin/env bash
#$ -N <id>.<tag>.0
#$ -q 1-day
#$ -o <workdir>/PyPPL.pMuTect2.nothread.51SoVk6Y/0/job.stdout
#$ -e <workdir>/PyPPL.pMuTect2.nothread.51SoVk6Y/0/job.stderr
#$ -cwd
#$ -M wang.panwen@mayo.edu
#$ -m abe
#$ -l h_vmem=4G
#$ -l h_stack=512M
#$ -notify

trap "status=\$?; echo \$status > <workdir>/0/job.rc; exit \$status" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT
source /home/whoever/.bash_profile >&/dev/null; mkdir /tmp/my

<workdir>/0/job.script
rm -rf /tmp/my
```

# Configurations for slurm runner
**Where to configure it:**
For single process:
```python
pXXX.slurmRunner = {...}
```
For running profiles:
```python
config = {
  "default": {
    ... # other configurations
    "runner": "slurm", # all processes run with slurm
    "slurmRunner": {
       ...
    }
  }, # or you can also create a profile
  "runWithSlurm": {
    ... # other configurations
    "runner": "slurm",
    "slurmRunner": {
       ...
    }
  }
}
PyPPL(config).start(...).run() # uses configurations of 'proc'
# for profile:
# PyPPL(config).start(...).run('runWithSlurm')
```

**The full configuration:**
```javascript
"slurmRunner": {
  "preScript": "export PATH=$PATH:/path/to/add", // default: ''
  "postScript": "# some cleanup",                // default: ''
  // commands (some slurm systems have variants of commands)
  "sbatch": "yhbatch",                           // default: sbatch
  "srun": "yhrun",                               // default: srun
  "squeue": "yhqueue",                           // default: squeue
  // the prefix add to command you want to run
  // i.e "srun -n8 hostname"
  // it defaults to the command you specified to slurmRunner['srun']
  // In this case: "yhrun"
  "cmdPrefix": "srun -n8",                       // default: slurmRunner['srun']
  // sbatch options (with prefix "slurm."):
  "slurm.p": "normal",
  "slurm.mem": "1GB",
  // other options
  // ......
  // Note that job name (slurm.J), stdout (slurm.o), stderr file (slurm.e) is calculated by the runner.
  // Although you can, you are not recommended to set them here.
}
```

# Dry-run a pipeline
You can use dry runner to dry-run a pipeline. The real script will not be running, instead, it just tries to touch the output files and create the output directories.

!!! note "When `RunnerDry` is being used"

    - All processes are running on local machine.
    - Expectations won't be checked.
    - Processes won't be cached.
    - Output files/directories won't be exported.
    - Better set runner of all processes in a pipeline to `dry`. (`pyppl().starts(...).run('dry')`), since empty file/directory will be created for output. Problems will happen if you have a non-dry-run process depending on dry-run processes.

# Define your own runner
You are also able to define your own runner, which should be a class extends `Runner` (jobs run immediately after submission) or `RunnerQueue` (jobs are put into a queue after submission). There are several methods and variables you may need to redefine (You may check the [API documentation](./API/#runner) for all available methods and variables).

The class name **MUST** start with `Runner` and end with the runner name with first letter capitalized. For example, to define the runner `my`:
```python
from pyppl.runners import Runner
class RunnerMy (Runner):
    pass
```

The base class `Runner` defines the runners where the jobs will immediately run after submission; while `RunnerQueue` defines the runners where the jobs will be put into a queue and wait for its turn to run (for example, clusters).

Example: a delay runner:
```python
class RunnerDelay (Runner):
    def __init__ (self, job):
        """
        Constructor
        @params:
            `job`: The job object
        """
        super(RunnerDelay, self).__init__(job)

        # construct an local script
        delayfile = self.job.script + '.delay'
        delaysrc  = ['#!/usr/bin/env bash']
        delaysrc.append('sleep 10')
        delaysrc.append(self.cmd2run)

        with open (delayfile, 'w') as f:
            f.write ('\n'.join(delaysrc) + '\n')

        self.script = delayfile
```

**Key points in writing your own runner**:

- Write a proper `__init__` function
- Write proper functions (`submit`, `kill` and `isRunning`) to submit, kill a job and tell if a job is running.
- Compose the right script to run the job (`self.script`) in `__init__`.
- MAKE SURE you save the identity of the job to `job.pidfile`, rc to `job.rcfile`, stdout to `job.outfile` and `stderr` to `job.errfile`

# Register your runner
It very easy to register your runner, just do `PyPPL.registerRunner (RunnerMy)` (static method) before you start to run the pipeline.
The 5 built-in runners have already been registered:
```python
PyPPL.registerRunner (RunnerLocal)
PyPPL.registerRunner (RunnerSsh)
PyPPL.registerRunner (RunnerSge)
PyPPL.registerRunner (RunnerSlurm)
PyPPL.registerRunner (RunnerDry)
```
To register yours:
```python
PyPPL.registerRunner(RunnerMy)
```
After registration, you are able to ask a process to use it: `pXXX.runner = "my"`



