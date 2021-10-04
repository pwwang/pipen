A pipeline consists of many processes, which could own multiple jobs that run in parallel.

## Defining/Creating processes

`pipen` has two (preferred) ways to define processes:

### Subclassing `pipen.Proc`

```python
from pipen import Proc

class MyProcess(Proc):
    ... # process configurations
```

The configurations are specified as class variables of the class.



### Using class method `Proc.from_proc()`

If you want to reuse a defined process, you can either subclass it:

```python
class MyOtherProcess(MyProcess):
    ... # configurations inherited from MyProcess
```

Or use `Proc.from_proc()`:

```python
# You can also pass the configurations you want to override
MyOtherProcess = Proc.from_proc(MyProcess, ...)
```

Note that `Proc.from_proc()` cannot override all configurations/class variables, because we assume that there are some shared configurations if you want to "copy" from another process.

These shared configurations are:

1. Template engine and its options (`template` and `template_opts`)
2. Script template (`script`)
3. Input keys (`input`)
4. Language/Interpreter of the script (`lang`)
5. Output keys (`output`)


All other configurations can be passed to `Proc.from_proc()` to override the old ones.

For all configurations/class variables for a process, see next section.

You don't need to specify the new name of the new process, the variable name on the left-handle side will be used if `name` argument is not provided to `Proc.from_proc()`. For example:

```python
NewProc = Proc.from_proc(OldProc)
# NewProc.name == "NewProc"
```

But you are able to assign a different name to a new process if you want. For example:

```python
NewProc = Proc.from_proc(OldProc, name="NewProc2")
# NewProc.name = "NewProc2"
```

### How about instantiation of `Proc` directly?

You are not allowed to do that. `Proc` is an abstract class, which is designed to be subclassed.

### How about instantiation of a `Proc` subclass?

Nope, in `pipen`, a process is a `Proc` subclass itself. The instances of the subcleasses are used internally, and they are singletons. In most cases, you don't need to use the instances, unless you want to access the computed properties of the instances, including:

- `pipeline`: The pipeline, which is a `Pipen` object
- `pbar`: The progress bar for the process, indicating the job status of this process
- `jobs`: The jobs of this process
- `xqute`: The `Xqute` object to manage the job running.
- `template`: The template engine (a `pipen.template.Template` object)
- `template_opts`: The template options (overwritten from config by the `template_opts` class variable)
- `input`: The sanitized input keys and types
- `output`: The compiled output template, ready for the jobs to render with their own data
- `scheduler`: The scheduler object (inferred from the name or sheduler object from the `scheduler` class variable)
- `script`: The compiled script template, ready for the jobs to render with their own data

### How about copy/deep-copy of a `Proc` subclass?

Nope. Copy or deep-copy of a `Proc` subclass won't trigger `__init_subclass__()`, where consolidate the process name from the class name if not specified and connect the required processes with the current one. Copy or deep-copy keeps all properties, but disconnect the relationships between current process and the dependency processes, even with a separate assignment, such as `MyProcess.requires = ...`.

## process configurations and `Proc` class variables

The configurations of a process are specified as class variables of subclasses of `Proc`.

|Name|Meaning|Can be overwritten by `Proc.from_proc()`|
|-|-|-|
|`name`|The name of the process. Will use the class name by default.|Yes|
|`desc`|The description of the process. Will use the summary from the docstring by default.|Yes|
|`envs`|The env variables that are job-independent, useful for common options across jobs.|Yes, and old ones will be inherited|
|`cache`|Should we detect whether the jobs are cached?|Yes|
|`dirsig`|When checking the signature for caching, whether should we walk through the content of the directory? This is sometimes time-consuming if the directory is big.|Yes|
|`export`|When True, the results will be exported to `<pipeline.outdir>` Defaults to None, meaning only end processes will export. You can set it to True/False to enable or disable exporting for processes|Yes|
|`error_strategy`|How to deal with the errors: retry, ignore, halt|Yes|
|`num_retries`|How many times to retry to jobs once error occurs|Yes|
|`template`|Define the template engine to use.|No|
|`template_opts`|Options to initialize the template engine.|No|
|`forks`|How many jobs to run simultaneously?|Yes|
|`input`|The keys and types for the input channel|No|
|`input_data`|The input data (will be computed for dependent processes)|Yes|
|`lang`|The language for the script to run.|No|
|`output`|The output keys for the output channel|No|
|`plugin_opts`|Options for process-level plugins|Yes|
|`requires`|The dependency processes|Yes|
|`scheduler`|The scheduler to run the jobs|Yes|
|`scheduler_opts`|The options for the scheduler|Yes|
|`script`|The script template for the process|No|
|`submission_batch`|How many jobs to be submited simultaneously|Yes|
