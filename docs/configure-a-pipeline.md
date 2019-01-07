
To configure your pipeline, you just pass the configurations (a `dict`) to the constructor:
```python
ppl = PyPPL(config)
```
Here is the full structure of the configurations (**`yaml` configuration file is also supported since `0.9.4`**):
```json
{
    "_log": {
        "levels": "basic",  // the log levels
        "theme": true,    // use colored log information
        "lvldiff": ["+DEBUG"],  // modify the loglevels group
        "file": false,    // disable logfile, or specify a different logfile
    },
    "_flowchart": {
        "theme": "default",
        "dot": "dot -Tsvg {{dotfile}} -o {{fcfile}}"
    },
    "proc": {            // shared configuration of processes
        "forks": 10,
        "runner": "sge",
        "sgeRunner": {
            // sge options
        }
    },
    "profile1" : {
        "forks": 20,
        "runner": "ssh",
        "sshRunner": {
            // ssh options
        }
    },
    "profile2": {...},
    "profile3": {...},
    ...
}
```
- For log configuration please refer to [configure your logs][3]
- For flowchart configuration please refer to [pipeline flowchart][4]
- `proc` defines the base running profile for processes in this pipeline. [All the properties][2] of a process can be set here, but just some common one are recommended. Obviously, `input` is not suitable to be set here, except some extreme cases.
- `profiles` defines some profiles that may be shared by the processes. To use a profile, just specify the profile name to `run`: `PyPPL(config).start(process).run(<profile>)`.

!!! note
    You may also use the runner name as a profile. That means, following profiles are implied in the configuration:
    ```json
    {
        "sge"  : {"runner": "sge"},
        "ssh"  : {"runner": "ssh"},
        "slurm": {"runner": "slurm"},
        "local": {"runner": "local"},
        "dry"  : {"runner": "dry"},
    }
    ```

!!! caution
    You cannot define profiles with names `_flowchart` and `_log`

# Priority of configuration options
See [here][5] for use of configuration files.  
Now you have 3 ways to set attributes for a process: 
- directly set the process attributes _(1)_, 
- set in the first argument (`config`) of `PyPPL` constructor _(2)_, 
- set in a configuration file `/a/b/pyppl.config.json` _(3)_,
- set in configuration file `~/.PyPPL.json` _(4)_, and
- set in configuration file `~/.PyPPL` _(5)_

**The priority is: (1) > (2) > (3) > (4) > (5).**
Once you set the property of the process, it will never be changed by `PyPPL` constructor or the configuration file. But the first argument can overwrite the options in configuration files.
Here are an examples to illustrate the priority:

** Example 1:**
```python
# ~/.PyPPL.json
"""
{
    "proc": {"forks": 5}
}
"""

p = Proc()
p.forks = 1

ppl = PyPPL({"proc": {forks: 10}})

# p.forks == 1
```
** Example 2:**
```python
# we also have ~/.PyPPL.json as previous example
p = Proc()

ppl = PyPPL({"proc": {forks: 10}})

# p.forks == 10
```
** Example 3:**
```python
# we also have ~/.PyPPL.json as previous example
p = Proc()

ppl = PyPPL()

# p.forks == 5
```

# Starting processes
It's very easy to set the starting processes of the pipeline, just pass them to `start` function. A pipeline can have multiple starting processes:
```python
PyPPL().start(p1,p2,p3).run()
```
You may also use a common id to set a set of processes:
```python
p1 = Proc(newid = 'p', tag = '1st')
p2 = Proc(newid = 'p', tag = '2nd')
p3 = Proc(newid = 'p', tag = '3rd')
# all p1, p2, p3 will be starting processes
PyPPL().start('p').run()
```
!!! caution
    1. If a process is depending on other processes, you are not supposed to set it as starting process. Of course you can, but make sure the input channel can be normally constructed.
    2. If a process is not depending on any other processes, you have to set it as starting process. Otherwise, it won't start to run.

[1]: https://docs.python.org/2/library/logging.html#logging-levels
[2]: ./set-other-properties-of-a-process/
[3]: ./configure-your-logs/
[4]: ./draw-flowchart-of-a-pipeline/
[5]: ./runners/#defining-running-profiles



