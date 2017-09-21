# Configure your pipeline
<!-- toc -->

{% raw %}
To configure your pipeline, you just pass the configurations (a `dict`) to the constructor:
```python
ppl = PyPPL(config)
```
Here is the full structure of the configurations:
```json
{
    "log": {
        "levels": "basic",  // the log levels
        "theme": true,    // use colored log information
        "lvldiff": ["+DEBUG"],  // modify the loglevels group
        "file": false,    // disable logfile, or specify a different logfile
    },
    "flowchart": {
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

> **Info** Settings for `profiles` are actually the same as for `proc`. They just make you easy to switch the profiles back and forth. For example, you want to run with sge runner this time, but ssh runner next time, what you need to do is just change from `...run("profile_sge")` to `...run("profile_ssh")`
> **Note** You may also use the runner name as a profile. That means, following profiles are implied in the configuration:
```json
{
    "sge"  : {"runner": "sge"},
    "ssh"  : {"runner": "ssh"},
    "slurm": {"runner": "slurm"},
    "local": {"runner": "local"},
    "dry"  : {"runner": "dry"},
}
```
> **Caution** You cannot define profiles with names `flowchar` and `log`

## Use a configuration file
You can also put some commonly used configurations into a `json` file (for example, `/a/b/pyppl.config.json`), and then specify it to `PyPPL` constructor:
```python
PyPPL({}, "/a/b/pyppl.config.json")
# or 
PyPPL (cfgfile = "/a/b/pyppl.config.json")
```

If not configuration file is specified, it will look for one at `~/.pyppl.json` (if not available, check `~/.pyppl`).  
You can also overwrite some options in the configuration file by specify them in the first argument:
```python
PyPPL({
    "proc": {forks: 5}
})
```
All other options will be inherited from `~/.pyppl.json`.

## Priority of configuration items
Now you have 3 ways to set options for a process: 
- directly set the process properties _(1)_, 
- set in the first argument of `pyppl` constructor _(2)_, and 
- set in a configuration file _(3)_.  

**The priority is: (1) > (2) > (3).**
Once you set the property of the process, it will never be changed by `pyppl` constructor or the configuration file. But the first argument can overwrite the options in configuration files.
Here are an examples to illustrate the priority:

** Example 1:**
```python
# ~/.pyppl.json
"""
{
    "proc": {"forks": 5}
}
"""

p = proc()
p.forks = 1

ppl = pyppl ({"proc": {forks: 10}})

# p.forks == 1
```
** Example 2:**
```python
# we also have ~/.pyppl.json as previous example
p = proc()

ppl = pyppl ({"proc": {forks: 10}})

# p.forks == 10
```
** Example 3:**
```python
# we also have ~/.pyppl.json as previous example
p = proc()

ppl = pyppl ()

# p.forks == 5
```

## Starting processes
It's very easy to set the starting processes of the pipeline, just pass them to `starts` function. A pipeline can have multiple starting processes:
```python
pyppl ().starts(p1,p2,p3).run()
```
> **Caution** 
> 1. If a process is depending on other processes, you are not supposed to set it as starting process.
> 2. If a process is not depending on any other processes, you have to set it as starting process. Otherwise, it won't start to run.

[1]: https://docs.python.org/2/library/logging.html#logging-levels
[2]: https://pwwang.gitbooks.io/pyppl/content/set-other-properties-of-a-process.html
[3]: https://pwwang.gitbooks.io/pyppl/configure-your-logs.html
[4]: https://pwwang.gitbooks.io/pyppl/draw-flowchart-of-a-pipeline.html
{% endraw %}

