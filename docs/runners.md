# Runners

We have 3 built-in runners (`runner_local`, `runner_ssh`, `runner_sge`), you can also define you own runners.

You can either tell a process to user a runner, or even, you can tell the pipeline to use the runner for all the process. That means each process can have the same runner or a different one. To tell a process which runner to use, just specify the runner name to `p.runner` (for example, `p.runner = "sge"`: use the sge srunner). Each process may use different configuration for the runner (`p.sgeRunner`) or the same one by [configuring the pipeline]().

## Configurations for `runner_ssh`
Ssh runner take the advantage to use the computing resources from other servers that can be connected via `ssh`. The `ssh` command allows us to pass the command to the server and execute it: `ssh [options] [command]`

> NOTE: 
1. ssh runner only works when the servers share the same file system.
2. you have to [configure](http://www.linuxproblem.org/art_9.html) so that you don't need a password to log onto the servers.

You can either tell a process to use 

## Configurations for `runner_sge`

## Define your own runner

## Register your runner