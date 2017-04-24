# Runners
<!-- toc -->

We have 3 built-in runners (`runner_local`, `runner_ssh`, `runner_sge`), you can also define you own runners.

You can either tell a process to user a runner, or even, you can tell the pipeline to use the runner for all the process. That means each process can have the same runner or a different one. To tell a process which runner to use, just specify the runner name to `p.runner` (for example, `p.runner = "sge"`: use the sge srunner). Each process may use different configuration for the runner (`p.sgeRunner`) or the same one by [configuring the pipeline](https://pwwang.gitbooks.io/pyppl/content/configure-a-pipeline.html).

## Configurations for `runner_ssh`
Ssh runner take the advantage to use the computing resources from other servers that can be connected via `ssh`. The `ssh` command allows us to pass the command to the server and execute it: `ssh [options] [command]`

> NOTE: 
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

To configure it for a pipeline:
```python
pyppl ({
    'proc': {
        'sshRunner': {"servers": ["user1@server1", "user2@server2", ...]}
    }
})
```
Also see "[configuring a pipeline](https://pwwang.gitbooks.io/pyppl/content/configure-a-pipeline.html)" for more details.

The constructor of the runner will change the script to run to the following (`<workdir>/scripts/script.0.ssh`):

```bash
#!/usr/bin/env bash
trap "status=\$?; echo \$status > <workdir>/scripts/script.0.rc; exit \$status" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT
ssh user1@server1 "cd <cwd>; <workdir>/scripts/script.0"
```

`trap` command makes sure a return code file will be generated. `script.0` is the actually script you specified to `p.script` with the placeholders replaced.

## Configurations for `runner_sge`
Similarly, you can also submit your jobs to SGE servers using `qsub`. To set the options for a process:
```python
p.sgeRunner = {
    "sge_q" : "1-day",          # the queue
    "sge_M" : "user@domain.com",# The email for notification
    "sge_l" : "h_vmem=4G",        
    "sge_l ": "h_stack=512M",   # Remember to add an extra space 
                                # so that it won't override the previous "sge_l"
    "sge_m" : "abe",            # When to notify
    "sge_notify": True,
    "preScript":  "source /home/user/.bash_profile >&/dev/null; mkdir /tmp/my",  # load the environment and create the temporary directory
    "postScript": "rm -rf /tmp/my" # clean up
}
```
Please check `man qsub` to find other options. Remember to add a `sge_` prefix to the option name.

To set them for a pipeline:
```python
pyppl ({
    'proc': {
        'sgeRunner': {
            "sge_q" : "1-day",          # the queue
            "sge_M" : "user@domain.com",# The email for notification
            "sge_l" : "h_vmem=4G",        
            "sge_l ": "h_stack=512M",   # Remember to add an extra space 
                                        # so that it won't override the previous "sge_l"
            "sge_m" : "abe",            # When to notify
            "sge_notify": True,
            "preScript":  "source /home/user/.bash_profile >&/dev/null; mkdir /tmp/my",  # load the environment and create the temporary directory
            "postScript": "rm -rf /tmp/my" # clean up
        }
    }
})
```
Also see "[configuring a pipeline](https://pwwang.gitbooks.io/pyppl/content/configure-a-pipeline.html)" for more details.



The constructor of the runner will change the script to run to the following (`<workdir>/scripts/script.0.sge`):
```bash
#!/usr/bin/env bash
#$ -N <id>.<tag>.0
#$ -q 1-day
#$ -o <workdir>/PyPPL.pMuTect2.nothread.51SoVk6Y/scripts/script.0.stdout
#$ -e <workdir>/PyPPL.pMuTect2.nothread.51SoVk6Y/scripts/script.0.stderr
#$ -cwd
#$ -M wang.panwen@mayo.edu
#$ -m abe
#$ -l h_vmem=4G
#$ -l h_stack=512M
#$ -notify

trap "status=\$?; echo \$status > <workdir>/script.0.rc; exit \$status" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT
source /home/m161047/.bash_profile >&/dev/null; mkdir /tmp/my

<workdir>/scripts/script.0
rm -rf /tmp/my
```

## Define your own runner
You are also able to define your own runner, which should be a class extended `runner_local`. There are server methods and variables you may need to redefine (You may check the [API documentation](https://pwwang.gitbooks.io/pyppl/content/API.html#runner_local) for all available methods and variables):

- The constructor: `__init__(self, job, config={})`  
This initializes the runner using the a `job` project and the properties of the process. You would like firstly initialize some basic properties of the runner by using the super constructor: 
```python
super(runner_sge, self).__init__(job, config)
```
Then the main purpose of the constructor is to construct the script (`self.script`) to submit the job. In `runner_local`, it uses `utils.chmodX` to make it suitable for first argument of [`Popen`](https://docs.python.org/2/library/subprocess.html#popen-constructor) with `shell=False`. If the file is executable, no interpreters will be added, otherwise, the interpreter will be inferred from shebang (see [API](https://pwwang.gitbooks.io/pyppl/content/API.html#chmodX)).
For example, you want to delay to submit jobs:
```python
class runner_delay(runner_local):
    def __init__ (self, job, config = {}):
        super(runner_sge, self).__init__(job, config)
        scriptfile = self.job.script + ".delay"
        with open (scriptfile, "w") as f:
            f.write ("#!/usr/bin/env bash\n")
            f.write ("sleep 10\n")                              # delay for 10 seconds
            f.write ("%s\n" % subprocess.list2cmd(self.script)) # submit the job
        self.script = utils.chmodX (scriptfile)
```

- Submit the job: `submit (self)`
The defines how you submit your job. You may use `Popen` to run the script and assign the `Popen` object to `self.p`.
> NOTE: 
> 1. make sure write "-1" if you fail to submit the job. Always use a `try-except` block.
> 2. confirm whether you need to wait until the script finishes or not:
```python
p  = Popen (self.script, ...)
rc = p.wait()
```
> If the job runs immediately after you submit it (local/ssh runner, for example), you should wait until it finishes. Well if the job is put into a queue, and needs some time to start, then you should be do `p.wait()`, just keep submitting, but you may have to specify the static variables `maxsubmit` and `interval` (see below).

- Wait for the job to finish: `wait (self, checkP = True)`
Wait until the job finishes. If `checkP` is `True`, then it will check `self.p` and make sure it's not `None`, so that we can extract `stdout` and `stderr` from it. If it is `False`, we directly detect the return code from `script.<index>.rc` and wait until it's not `-99` (no return code generated).

- Tell whether a job is still running: `isRunning(self)`
This function is used to detect whether a job is running. 
For example, ssh runner will use the command submitted to the server to detect whether a job is still running. Because the command actually running is `cd <cwd>; [interpreter] <workdir>/scripts/script.0`, which has a unique id in `<workdir>` and the job index `0`, so it won't be mixed with other running processes.
The sge runner uses `qstat` according to the `jobname`, which is compose of process id, process tag and job index: `<id>.<tag>.<index>` if you don't specify the `jobname` through the configuration (`sge_N` in `sgeRunner`)(NOT recommended).
**This function is specially useful when you try to run the pipeline again if some of the jobs are still running but the main thread (pipeline) quite unintentionally.**

- How many jobs to submit at one time (static variable): `maxsubmit` 
This variable defines how many jobs to submit at one time. It defaults to `p.forks` if you don't have the value for your runner, which means it will submit all the jobs you want to run simultaneously at one time. But if you want to run 100 jobs on the SGE, and submit them at one time, the local machine will get stuck to run `qsub` 100 times concurrently. So the recommended number is `int(multiprocessing.cpu_count()/2)`, using half of the cpus. Then wait for sometime (`interval`, see below), and submit another batch.

- How long should I wait if `maxsubmit` reached (static variable): `interval` 
As explained in `maxsubmit`, this value is used for wait some time when submitting different batches of jobs. The default value is `0.1` if you don't have one.

## Register your runner
It very easy to register your runner, just do `proc.registerRunner (runner_my)` (static method) before you define run the pipeline.
The 3 built-in runners have already been registered: 
```python
proc.registerRunner (runner_local)
proc.registerRunner (runner_ssh)
proc.registerRunner (runner_sge)
```
After registration, you are able to ask a process to use it: `p.runner = "my"`
