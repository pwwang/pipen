# Documentataion of pyppl

## `proc`
`proc` is the basic unit in `pyppl`, it defines process running within a pipeline.
### Initialize `proc`
```python
someproc = proc (tag = 'notag')
```
When initialize a `proc`, you can specify a `tag`. Processes are identified by `id` and `tag`. `Id` is the variable name of the instance (`someproc` here for example)

> Basically, `pyppl` doesn't allow to declare two processes with the same `id` and `tag`, but you can use different `tag`s with the same `id`

### Properties of a `proc`
You can set the property of a `proc` instance simply by:
```
someproc.tag = 'newtag'
```

#### Property `tag`
A tag to mark the process.

#### Property `tmpdir`
The directory where the cache file and default work directory (`PyPPL_<id>_<tag>.<suffix>` will be stored.

#### Property `workdir`
The work directory of the process. You can, but not recommended to, set `workdir`. Instead, you can just set `tmpdir`, the work directory will be automatically generated.

The structure of work directory:
- work directory
  - Symbol links of input files/directories
  - Output files
  - `.scripts`
    - `script.<index>` (scripts for the process)
	- `script.<index>.stdout`
	- `script.<index>.stderr`
	- `script.<index>.rc` (return value) 

> You can check and run `script.<index>` to debug the script for the process

#### Property `retcodes`
In most case, we expect our script return `0` when it completes successfully. But this allow you to have other return codes as valid. Invalid return codes will cause:
- Retry to run the script (if `errorhow` is set to `retry`)
- Process not to be cached
- Still not valid after retry, process terminated.

> You can set `retcodes` by either `p.retcodes = [0, 1]` or `p.retcodes = "0,1"`

#### Property `errorhow`
Defines what to do if a script failed (return codes invalid). 
- `retry`: try to run the script again (see `errorntry`)
- `ignore`: ignore the process and continue running the next process
- `terminate`: terminate the whole pipeline

#### Property `errorntry`
How many times we should retry the script if it fails.

#### Property `cache`
Whether we should cache the process or not. `pyppl` will not cache a process when:
- Property `cache` set to `False`
- Cache file not exists
- Input file not exists
- Input file is newer than output file
- Expected output file not exists
- Dependent processes not cached
- Process failed

#### Property `echo`
Whether to show the stdout of the process (stderr is always showing).

#### Property `forks`
How many processes are allow to run simultaneously.

 

