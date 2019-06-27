
To configure your pipeline, you just pass the configurations (a `dict`) to the constructor:
```python
ppl = PyPPL(config)
```
Here is the full structure of the configurations (**`yaml` configuration file is also supported since `0.9.4`**):
```json
{
    "default": {            // default configuration of processes
        "_log": {
            "levels": "basic",  // the log levels
            "theme": true,    // use colored log information
            "leveldiffs": ["+DEBUG"],  // modify the loglevels group
            "file": false,    // disable logfile, or specify a different logfile
            "shorten": 80 // shorten some paths/strings in log
        },
        "_flowchart": {
            "theme": "default"
        },
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
- For log configuration please refer to [log configuration][3]
- For flowchart configuration please refer to [pipeline flowchart][4]
- `default` defines the base running profile for processes in this pipeline. [All the properties][2] of a process can be set here, but just some common one are recommended. Obviously, `input` is not suitable to be set here, except some extreme cases.
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

# Priority of configuration options
See [here][5] for use of configuration files.
Now you have 3 ways to set attributes for a process:

- _(1)_ directly set the process attributes ,
- _(2)_ temporary profile at `ppl.run(<profile>)`,
- _(3)_ set in the first argument (`config`) of `PyPPL.__init__`,
- _(4)_ set in a configuration file in current directory `./.PyPPL.yaml`, and
- _(5)_ set in configuration file `$HOME/.PyPPL.yaml`

[`.toml`][6] for _(4)_ and _(5)_ are also supported, and they have higher priority than the `.yaml` files, respectively.

**The priority is: (1) > (2) > (3) > (4) > (5).**
Once you set the property of the process, it will never be changed by `PyPPL` constructor or the configuration file. But the first argument can overwrite the options in configuration files.
Here are an examples to illustrate the priority:

- **Example 1:**
    ```python
    # ~/.PyPPL.yaml
    """
    default:
        forks: 5
    """

    p = Proc()
    p.forks = 1

    ppl = PyPPL({"default": {"forks": 10}})

    # p.forks == 1
    ```

- **Example 2:**
    ```python
    # we also have ~/.PyPPL.yaml as previous example
    p = Proc()

    ppl = PyPPL({"default": {"forks": 10}})

    # p.forks == 10
    ```

- **Example 3:**
    ```python
    # we also have ~/.PyPPL.yaml as previous example
    p = Proc()

    ppl = PyPPL({"default": {"forks": 10}}).start(pXXX).run({"forks": 8})

    # p.forks == 8
    ```

# Start processes
It's very easy to set the start processes of the pipeline, just pass them to `start` function. A pipeline can have multiple start processes:
```python
PyPPL().start(p1,p2,p3).run()
```
You may also use a common id to set a set of processes:
```python
p1 = Proc(id = 'p', tag = '1st')
p2 = Proc(id = 'p', tag = '2nd')
p3 = Proc(id = 'p', tag = '3rd')
# all p1, p2, p3 will be start processes
PyPPL().start('p').run()
```

!!! caution

    1. If a process is depending on other processes, you are not supposed to set it as start process. Of course you can, but make sure the input channel can be normally constructed.

    2. If a process is not depending on any other processes, you have to set it as start process. Otherwise, it won't start to run.

[1]: https://docs.python.org/2/library/logging.html#logging-levels
[2]: ../defining/
[3]: ../logs/
[4]: ../flowchart/
[5]: ../runners/#defining-running-profiles
[6]: https://github.com/toml-lang/toml
