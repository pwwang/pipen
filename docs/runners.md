
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
You can define profiles in `PyPPL`'s default configuration files: `$HOME/.PyPPL.yaml`, `$HOME/.PyPPL.toml`, `./.PyPPL.yaml` and `./.PyPPL.toml`. The latter ones have high priorities.  Take `$HOME/.PyPPL.yaml` for example, it is like:
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

Beyond the configuration files, we may also use environment variables, for example, we want to run all jobs using `ssh` but with `default` profile:
```shell
PYPPL_default_runner="ssh" python pipeline.py ...
```

You may also define some profiles in a file somewhere else, say `/path/to/myprofiles.yaml`. Just pass the file to `PyPPL` constructor:
```python
PyPPL(cfgfile = '/path/to/myprofiles.yaml').start(pXXX).run('profile1')
```

!!! note
    This has higher priority than default configuration files (including the environment variables).

You can also pass a temporary to `PyPPL` constructor directly:
```python
PyPPL({'sge': {
    'runner': 'sge',
    'sgeRunner': {'queue': '1-day'}
}}).start(pXXX).run('sge')
```

!!! note
    In this way, the profiles have higher priorities than the ones defined in configuration files.

Or even, you can also specify a profile to `run` function to ask the pipeline run with the profile directly (WITHOUT profile name):
```python
PyPPL().start(pXXX).run({
    'runner': 'sge',
    'sgeRunner': {
        'queue': '1-day'
    }
})
```

!!! note
    This has the even higher priority.

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
You can use dry runner to dry-run a pipeline. The real script (`<job.dir>/job.script`) will not be running, instead, it just tries to touch the output files and create the output directories.

!!! note "When `RunnerDry` is being used"

    - All processes are running on local machine.
    - Expectations won't be checked.
    - Processes won't be cached.
    - Output files/directories won't be exported.
    - Better set runner of all processes in a pipeline to `dry`. (`pyppl().starts(...).run('dry')`), since empty file/directory will be created for output. Problems will happen if you have a non-dry-run process depending on dry-run processes.

# Define your own runner
You are also able to define your own runner, which should be a class extends `Job`.

The class name **MUST** start with `Runner` and end with the runner name with first letter capitalized. For example, to define the runner `my`:
```python
from pyppl import Job
class RunnerMy (Runner):
    pass
```

Example: a delay runner:
```python
class RunnerDelay (Runner):
    @property
    def scriptParts(self):
        parts = super().scriptParts()
        parts.pre += 'sleep 10\n'
        return parts
```
And then that's it!

Things you may need to redefine with your own runner:
- How to kill a job (`killImpl`)
  You can use the `pid` to kill the job. For example, kill a local job:
  ```python
  def killImple(self):
      import cmdy
      cmdy.kill('-9', self.pid)
  ```
  Or kill an SGE job:
  ```python
  def killImple(self):
      cmdy.qdel(self.pid)
  ```

- How to submit a job (`submitImpl`)
  The wrapper script is at `self.script`, defaults to `<job.dir>/job.script.<suffix>`. The `suffix` is decided by the runner name, for example, your `RunnerMy` will have `self.script` at `<job.dir>/job.script.my`. What you need in `submitImpl` is to submit that script in BACKGROUND mode, otherwise the program will hang there until the job is done. And also don't forget to save your job id (pid) by `self.pid = <pid>`

- Tell if a job is running (`isRunningImpl`)
  For example, tell if a local job is running:
  ```python
  def isRunningImpl(self):
      return psutil.pid_exists(int(self.pid))
  ```
- How to wrap the script (`@property scriptParts`)
  The structure of wrapped script looks like:
  ```shell
  #!/usr/bin/env bash
  # 1. header
  <header>
  trap command to capture return code
  # 2. pre
  <pre script>
  # 3. command   4. saveoe
  <command to run the real script> [1> <job.stdout> 2> <job.stderr>]
  # 5. post
  <post script>
  ```
  You can redefine the whole wrapper by overriding `wrapScript` to make sure you have the right thing written in `self.script`, including running the real script and capture the return code to `<job.dir>/job.rc` at exit. However here, we have a template for the wrapper, what you need to do is just to redefine those 5 parts:

  ```python
  @property
  def scriptParts(self):
      parts = super().scriptParts
      parts.header = ...
      parts.pre = ...
      parts.command = ...
      parts.saveoe = True/False
      parts.post = ...
      return parts
  ```
  1. `header`: We have nothing for it by default. You may use it to define some arguments, for example, arguments for `qsub` or `sbatch`.
  2. `pre`: The pre script used to load some environments. By default, it will use the `preScript` defined in running configuration. For example: `pXXX.sgeRunner = {'preScript': 'source $HOME/.bash_profile'}`
  3. `command`: Command to run the real script. By default, we will use the shebang or try to make the file executable and submit it.
  4. `saveoe`: Whether we should redirect the stdout and stderr. It's `True` by default, however, for instance, `qsub` can do it if we have `#$ -o` and `#$ -e` in the `header`. In this case, we may set `saveoe` to `False`
  5. `post`: Similar as `pre`.

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
