# Runners and running profiles

## Running profile
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

## Defining running profiles
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

!!! note
    If a `key` is not in a profile, then it will be inherited from `default`.

You may also define some profiles in a file somewhere else, say `/path/to/myprofiles.yaml`. Just pass the file to `PyPPL` constructor:
```python
PyPPL(cfgfile = '/path/to/myprofiles.yaml').start(pXXX).run('profile1')
```

!!! note
    This has higher priority than default configuration files.

You can also pass the profiles to `PyPPL` constructor directly:
```python
PyPPL({
    'default': {
        'runner': 'local',
        'forks': 1,
        'echo': 'stderr'
    },
    'profile1': {
        'runner': 'sge',
        'sgeRunner': {
            'queue': '1-day'
        }
    },
    'profile2': {
        'runner': 'sge',
        'sgeRunner': {
            'queue': '7-days'
        }
    }
}).start(pXXX).run('profile1')
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
    This has the highest priority.

## Built-in runners
We have 5 built-in runners (`RunnerLocal`, `RunnerSsh`, `RunnerSge`, `RunnerSlurm`, `runnerDry`), you can also define you own runners.

You can either tell one process to use a runner, or even, you can tell the pipeline to use one runner for all the processes. That means each process can have the same runner or a different one. To tell a process which runner to use, just specify the runner name to `pXXX.runner` (for example, `pXXX.runner = "sge"` to use the sge runner). Each process may use different configuration for the runner (`pXXX.sgeRunner`) or the same one by [configuring the pipeline](./configure-a-pipeline/).

## Configurations for ssh runner
Ssh runner takes the advantage to use the computing resources from other servers that can be connected via `ssh`. The `ssh` command allows us to pass the command to the server and execute it: `ssh [options] [command]`

!!! caution
    1. ssh runner only works when the servers share the same file system.
    2. you have to [configure](http://www.linuxproblem.org/art_9.html) so that you don't need a password to log onto the servers, or use a private key to connect to the ssh servers.
    3. The jobs will be distributed equally to the servers.

To tell a process the available ssh servers:
```python
pXXX.sshRunner = {
    "servers": ["server1", "server2", ...], 
    "keys": ["/path/to/keyfile1", "/path/to/keyfile2", ...]
}
``` 

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
trap "status=\$?; echo \$status > <workdir>/scripts/script.0.rc; exit \$status" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT
ssh -i "/path/to/key1" user1@server1 "cd <cwd>; <workdir>/0/job.script"
```

`trap` command makes sure a return code file will be generated. 

## Configurations for sge runner
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

## Configurations for slurm runner
**Where to configure it:**
For single process:
```python
pXXX.slurmRunner = {...}
```
For running profiles:
```python
config = {
  "proc": {
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

## Dry-run a pipeline
You can use dry runner to dry-run a pipeline. The real script will not be running, instead, it just tries to touch the output files and create the output directories.

!!! note "When `RunnerDry` is being used"

    - All processes are running on local machine.
    - Expectations won't be checked.
    - Processes won't be cached.
    - Output files/directories won't be exported.
    - Better set runner of all processes in a pipeline to `dry`. (`pyppl().starts(...).run('dry')`), since empty file/directory will be created for output. Problems will happen if you have a non-dry-run process depending on dry-run processes.

## Define your own runner
You are also able to define your own runner, which should be a class extends `Runner` (jobs run immediately after submission) or `RunnerQueue` (jobs are put into a queue after submission). There are several methods and variables you may need to redefine (You may check the [API documentation](./API/#runner) for all available methods and variables).

The class name **MUST** start with `Runner` and end with the runner name with first letter capitalized. For example, to define the runner `my`:
```python
from pyppl.runners import Runner
class RunnerMy (Runner):
	pass
```

The base class `Runner` defines the runners where the jobs will immediately run after submission; while `RunnerQueue` defines the runners where the jobs will be put into a queue and wait for its turn to run (for example, clusters).

Some important method to be redefined:

- The constructor: `__init__(self, job)`  
    This initializes the runner using the a `job` object and the properties of the process. You would like firstly initialize some basic properties of the runner by using the super constructor: 
    ```python
    super(RunnerMy, self).__init__(job)
    ```
    Then the main purpose of the constructor is to construct the script (`self.script`) to submit the job. In `Runner`, it uses `utils.chmodX` to make it suitable for first argument of [`Popen`](https://docs.python.org/2/library/subprocess.html#popen-constructor) with `shell=False`. If the file is executable, no interpreters will be added, otherwise, the interpreter will be inferred from shebang (see [API](./API/#chmodX)).
    For example, you want a delay before submitting jobs:
    ```python
    class runnerDelay(Runner):
        def __init__ (self, job):
            super(runnerDelay, self).__init__(job)
            scriptfile = self.job.script + ".delay"
            with open (scriptfile, "w") as f:
                f.write ("#!/usr/bin/env bash\n")
                # save the pid
                f.write ("echo $$ > %s" % self.job.pidfile) 
                # save the rc
                f.write ('trap "status=\\$?; echo \\$status > %s; exit \\$status" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT' % self.job.rcfile)  
                # delay for 10 seconds
                f.write ("sleep 10\n")   
                # save the stdout and stderr       
                f.write ("%s 1>%s 2>%s\n" % (self.cmd2run, self.job.outfile, self.job.errfile)) 
            # make it executable
            utils.chmodX(scriptfile)
            # because we don't have a local job submitter (like qsub for sge), we need to compose one
            submitfile = self.job.script + ".submit"
            with open(submitfile, 'w') as f:
                f.write('#!/usr/bin/env bash\n')
                f.write('%s\n' % scriptfile)
            # ready to submit
            self.script = utils.chmodX (submitfile)
    ```
!!! hint "Checklist (What you have to do in the constructor redefinition)"

    - choose the right base class (`pyppl.runners.Runner` or `pyppl.runners.RunnerQueue`)
    - `super(RunnerMy, self).__init__(job)`
    - setup the right `self.script` for submission.
    - MAKE SURE you save the identity of the job to `job.pidfile`, rc to `job.rcfile`, stdout to `job.outfile` and `stderr` to `job.errfile`

- Get the job identity on the system: `getpid()`
  Sometimes you cannot determin the job identity (e.g. `pid` for local jobs) when you are composing the script file. For example, for `SGE` runner, only after you submit the job, the job id will be saved in `job.pidfile`. In this case, you have to parse the job identity from `job.outfile`. Then you may save it by `self.job.pid(<jobid>)`.  
  The purpose to save the job identity is to tell whether the job is already running before we submit the job. So you can ignore this, but the same job may be submitted twice. 
  Also see `isRunning` below.

- Tell whether a job is still running: `isRunning(self)`  
    This function is used to detect whether a job is running. 
    Basically, it uses the job id got by `getpid()` to tell whether the job is still running.
    **This function is specially useful when you try to run the pipeline again if some of the jobs are still running but the main thread (pipeline) quite unintentionally.**  
    But it's optional, you can make the function always return `False`. Then the jobs are anyway to be submitted. In this case, `getpid` redefinition is not needed.

- How many jobs to submit at one time (static variable): `maxsubmit` (WILL BE DEPRECATED!)
    This variable defines how many jobs to submit at one time. It defaults to `multiprocessing.cpu_count()/2` if you don't have the value for your runner, which means it will use half of the cpus to submit the jobs you want to run simultaneously at one time. Then wait for sometime (`interval`, see below), and submit another batch. The purpose is to avoid local machine to get stuck if you have too many jobs to submit.

**Key points in writing your own runner**:

  1. Choose the right base class (`pyppl.runners.Runner` or `pyppl.runners.RunnerQueue`) (required).
  2. Compose the right script to submit the job (`self.script`) in `__init__`(required).
  3. Use `getpid` to get the job id (optional).
  4. Tell `PyPPL` how to judge when the jobs are still running (`self.isRunning()`) (optional). 
  5. MAKE SURE you save the identity of the job to `job.pidfile`, rc to `job.rcfile`, stdout to `job.outfile` and `stderr` to `job.errfile`

## Register your runner
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



