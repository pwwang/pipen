# Runners
<!-- toc -->

{% raw %}
We have 3 built-in runners (`runner_local`, `runner_ssh`, `runner_sge`), you can also define you own runners.

You can either tell a process to use a runner, or even, you can tell the pipeline to use the runner for all the process. That means each process can have the same runner or a different one. To tell a process which runner to use, just specify the runner name to `p.runner` (for example, `p.runner = "sge"`: use the sge srunner). Each process may use different configuration for the runner (`p.sgeRunner`) or the same one by [configuring the pipeline](https://pwwang.gitbooks.io/pyppl/content/configure-a-pipeline.html).

## Configurations for `runner_ssh`
Ssh runner take the advantage to use the computing resources from other servers that can be connected via `ssh`. The `ssh` command allows us to pass the command to the server and execute it: `ssh [options] [command]`

> **Caution** 
1. ssh runner only works when the servers share the same file system.
2. you have to [configure](http://www.linuxproblem.org/art_9.html) so that you don't need a password to log onto the servers.
3. The jobs will be distributed equally to the servers.


To tell a process the available ssh servers:
```python
p.sshRunner: {"servers": ["server1", "server2", ...]}
``` 

If you use different usernames to log on the servers, you may also specify the usernames as well:
```python
p.sshRunner= {"servers": ["user1@server1", "user2@server2", ...]}
```

You can also add `preScript` and `postScript` for all jobs:
```python
p.sshRunner = {"servers":[...], "preScript": "mkdir some/dir/to/be/made", "postScript": "rm -rf /path/to/job/tmp/dir"}
```

To configure it for a pipeline:
```python
pyppl ({
    'proc': {
        'sshRunner': {"servers": ["user1@server1", "user2@server2", ...]}
    }
})
```
Also see "[configuring a pipeline](https://pwwang.gitbooks.io/pyppl/content/configure-a-pipeline.html)" for more details.

The constructor of the runner will change the script to run the following (`<workdir>/0/job.script.ssh`):

```bash
#!/usr/bin/env bash
trap "status=\$?; echo \$status > <workdir>/scripts/script.0.rc; exit \$status" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT
ssh user1@server1 "cd <cwd>; <workdir>/0/job.script"
```

`trap` command makes sure a return code file will be generated. `job.script` is the actually script you specified to `p.script` with the placeholders replaced.

## Configurations for `runner_sge`
Similarly, you can also submit your jobs to SGE servers using `qsub`. To set the options for a process:
```python
p.sgeRunner = {
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

To set them for a pipeline:
```python
pyppl ({
    'proc': {
        'sgeRunner': {
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
    }
})
```
Also see "[configuring a pipeline](https://pwwang.gitbooks.io/pyppl/content/configure-a-pipeline.html)" for more details.

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

trap "status=\$?; echo \$status > <workdir>/script.0.rc; exit \$status" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT
source /home/whoever/.bash_profile >&/dev/null; mkdir /tmp/my

<workdir>/0/job.script
rm -rf /tmp/my
```

## Define your own runner
You are also able to define your own runner, which should be a class extends `runner` or `runner_queue`. There are several methods and variables you may need to redefine (You may check the [API documentation](https://pwwang.gitbooks.io/pyppl/content/API.html#runner) for all available methods and variables).

The class name **MUST** start with `runner_` and end with the runner name. For example, to define the runner `my`:
```python
import pyppl
class runner_my (pyppl.runner):
	pass
```

The base class `runner` defines the runners where the jobs will immediately run after submitted; while `runner_queue` defines the runners where the jobs will be put into a queue and wait for its turn to run (for example, clusters).

Some import method to be redefined:

- The constructor: `__init__(self, job)`  
This initializes the runner using the a `job` project and the properties of the process. You would like firstly initialize some basic properties of the runner by using the super constructor: 
```python
super(runner_local, self).__init__(job)
```
Then the main purpose of the constructor is to construct the script (`self.script`) to submit the job. In `runner`, it uses `utils.chmodX` to make it suitable for first argument of [`Popen`](https://docs.python.org/2/library/subprocess.html#popen-constructor) with `shell=False`. If the file is executable, no interpreters will be added, otherwise, the interpreter will be inferred from shebang (see [API](https://pwwang.gitbooks.io/pyppl/content/API.html#chmodX)).
For example, you want to delay to submit jobs:
```python
class runner_delay(pyppl.runner):
    def __init__ (self, job):
        super(runner_delay, self).__init__(job)
        scriptfile = self.job.script + ".delay"
        with open (scriptfile, "w") as f:
            f.write ("#!/usr/bin/env bash\n")
            f.write ("sleep 10\n")          # delay for 10 seconds
            f.write ("%s\n" % self.cmd2run) # submit the job
        self.script = utils.chmodX (scriptfile)
```
> **Note** For queue runners, the script is used to submit the job and you may also have to specify the static variables `maxsubmit` and `interval` (see below).
> 
> **Checklist (What you have to do in the constructor):**
> - choose the right base class (`pyppl.runner` or `pyppl.runner_queue`)
> - `super(runner_my, self).__init__(job)`
> - setup the right `self.script` for submission.
> - if it is a queue runner, make sure the return code is written to `self.job.rcfile`, stdout to `self.job.outfile` and stderr to `self.job.errilfe`

- Submit the job: `submit (self)`
The defines how you submit your job. You may use `Popen` to run the script and assign the `Popen` object to `self.p`.
> **Caution** make sure set `job.FAILED_RC` as return code (`self.job.rc(job.FAILED_RC)`) if you fail to submit the job. Always use a `try-except` block.
> `runner` has already done pretty much for the submission if you have the right `self.script`. You don't to rewrite the function, however, you can also do it if you want to add more actions there.

- Wait for the job to finish: `wait (self)`
Wait until the job finishes. The basic work it does is to wait and write the `stdout` and `stderr` to `self.job.outfile` and `self.job.errfile`, respectively.  

| `self.p` | Base class | When this happens? | What to do? | Where to get `stdout`/`stderr`? |  
|----------|------------|--------------------|-------------|---------------------------------|  
| `None` | `runner` | Main thread dead | Nothing to do, jobs also quit | - |  
| `None` | `runner_queue` | Main thread dead, jobs alive | Use `self.isRunning()` to tell whether jobs are truly alive. If yes, wait; otherwise quit | `.stdout/.stderr` files |  
| `Not None` | `runner` | All alive | `p.wait()` | `.stdout`/`.stderr` files |  
| `Not None` | `runner_queue` | All alive | Use `self.isRunning()` to tell whether jobs are truly alive. If yes, wait; otherwise quit | `.stdout/.stderr` files |
  
  `runner`/`runner_queue` has also done most of the job, in general case you don't need to rewrite it.

- Finish the job: `finish (self)`
The work it does:
  - Cleanup for jobs
  - Reset `self.p`
  - Try to retry the jobs if failed
  `runner_local` has also done them, generally you don't need to rewrite it.

- Tell whether a job is still running: `isRunning(self)`  
This function is used to detect whether a job is running. 
For example, ssh runner will use the command submitted to the server to detect whether a job is still running. Because the command actually running is `cd <cwd>; [interpreter] <workdir>/0/job.script`, which has a unique id in `<workdir>` and the job index `0`, so it won't be mixed with other running processes.  
The sge runner uses `qstat` according to the `jobname`, which is compose of process id, process tag, process uid and job index: `<id>.<tag>.<uid>.<index>` if you don't specify the `jobname` through the configuration (`sge.N` in `sgeRunner`)(NOT recommended).
**This function is specially useful when you try to run the pipeline again if some of the jobs are still running but the main thread (pipeline) quite unintentionally.**

- How many jobs to submit at one time (static variable): `maxsubmit` (only for `runner_queue`)  
This variable defines how many jobs to submit at one time. It defaults to `multiprocessing.cpu_count()/2` if you don't have the value for your runner, which means it will use half of the cpus to submit the jobs you want to run simultaneously at one time. Then wait for sometime (`interval`, see below), and submit another batch.

- How long should I wait if `maxsubmit` reached (static variable): `interval`  (only for `interval`)
As explained in `maxsubmit`, this value is used for wait some time when submitting different batches of jobs. The default value is `30` if you don't have one.

  **Key points in writing your own runner**:
  1. Choose the right base class (`pyppl.runner` or `pyppl.runner_queue`)
  2. Compose the right script to submit the job (`self.script`) in `__init__`.
  3. Tell `pyppl` how to judge when the jobs are still running (`self.isRunning()`). (Not necessary if `pyppl.checkrun` is set as `False`)
  4. Set the static value for `maxsubmit` and `interval` if necessary (only for `runner_queue`).
  5. For queue runners, make sure the `stdout`/`stderr` will be written to the right file (`.stdout`/`.stderr` file), and the right return code to `.rc` file.

## Return code in `pyppl` and the actual number in `job.rc`
When you try to set return code using `job.rc(val)`, it will basically write the number to `job.rc`. If `rc < 0` (output file is not generated, in this case) and the script returns `abs(rc)`. If the script returns 0, but output files are not generated, a warning of return code `-0` will be shown, but in `job.rcfile`, the content is `-1000`
the number in `script.<index>.rc` is positive, then make if negative; if it is negative, `job.failedRc`, or `job.emptyRc`, keep it unchanged. When try to get the return code from the file, just get the number from the file. When the file does not exist or is empty, return `job.emptyRc`. If any of the output files are not generated, the number will just become negative, you will get a negative number using `job.rc()`. So this makes sure a negative number from `job.rc()` (`-0` from the file will return `-1000`) meaning output file not generated.


| `job.rc()` | Content of `job.rcfile` | Value in log | Script return code | Meaning |
|------------|-------------------------|--------------|--------------------|---------|
| `-x` | `-x` | `-x` | `x` | Script returns `x` and output files not generated |
| `-1000 (job.NOOUT_RC)` | `-1000` | `-0` | `0` | Script returns `0` and output files not generated |
| `0` | `0` |`0`|`0`| job return code 0 with output files generated |
| `x` |  `x` |`x`|`x`| job return code x with output files generated |
| `9998 (job.EMPTY_RC)` |  `-` |`9998`|`-`| `rcfile` generated |
| `9999 (job.FAILED_RC)` |  `9999` |`9999`|`-`| Failed to submit the job |

## Register your runner
It very easy to register your runner, just do `proc.registerRunner (runner_my)` (static method) before you define run the pipeline.
The 3 built-in runners have already been registered: 
```python
proc.registerRunner (runner_local)
proc.registerRunner (runner_ssh)
proc.registerRunner (runner_sge)
```
After registration, you are able to ask a process to use it: `p.runner = "my"`

{% endraw %}
