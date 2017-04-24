# Configure your pipeline
<!-- toc -->

To configure your pipeline, you just pass the configurations (a `dict`) to the constructor:
```python
ppl = pyppl (config)
```
Here is the full structure of the configurations:
```json
{
    "loglevel": "info",  // the log level
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
- `loglevel` defines which level of log information to output, please refer to [python logging levels][1]. You may just use the lowercase. 
- `proc` defines the shared configurations of processes in this pipeline. [All the properties][2] of a process can be set here, but just some common one are recommended. Obviously, `input` is not suitable to be set here, except some extreme cases.
- `profiles` defines some profiles that may be shared by part of the processes. 

## Use a configuration file


## Priority of configure items

## Starting processes

[1]: https://docs.python.org/2/library/logging.html#logging-levels
[2]: https://pwwang.gitbooks.io/pyppl/content/set-other-properties-of-a-process.html