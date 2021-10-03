
## Configuration items

There are two levels of configuration items in `pipen`: pipeline level and process level.

There are only 3 configuration items at pipeline level:

- `loglevel`: The logging level for the logger (Default: `"info"`)
- `workdir`: Where the metadata and intermediate files are saved for the pipeline (Default: `./.pipen`)
- `plugins`: The plugins to be enabled or disabled for the pipeline

These items cannot be set or changed at process level.

Following items are at process level. They can be set changed at process level so that they can be process-specific. You may also see some of the configuration items introduced [here][1]

- `cache`: Should we detect whether the jobs are cached? See also [here][2]
- `dirsig`: When checking the signature for caching, whether should we walk through the content of the directory? This is sometimes time-consuming if the directory is big.
- `error_strategy`: How to deal with the errors: retry, ignore or halt. See also [here][3]
- `num_retries`: How many times to retry to jobs once error occurs.
- `template`: efine the template engine to use. See also [here][4]
- `template_opts`: Options to initialize the template engine (will inherit from pipeline level)
- `forks`: How many jobs to run simultaneously?
- `lang`: The language for the script to run. See also [here][5]
- `plugin_opts`: Options for process-level plugins, will inherit from pipeline level
- `scheduler`: The scheduler to run the jobs
- `scheduler_opts`: The options for the scheduler, will inherit from pipeline level
- `submission_batch`: How many jobs to be submited simultaneously

## Configuration priorities

There are different places to set values for the configuration items (priorities from low to high):

- The configuration files (priorities from low to high):

  - `~/.pipen.toml`
  - `./.pipen.toml`
  - `PIPEN.osenv`

  See [here][6] for how the configuration files are loaded.
  `pipen` uses `TOML` as configuration language, see [here][7] for more information about `toml` format.

- The arguments of `Pipen` constructor
- The process definition

!!! note

    The configurations from configuration files are with profiles. If the same profile name appears in multiple configuration files, the items will be inherited from the lower-priority files.

!!! note

    Special note for `lang`.

    If it is not set at process level, and there are shebang in the script, whatever you specified at pipeline level (including in the configuration files), it will be ignored and the interpreter in the shebang will be used.

    See also [script][5]

!!! tip

    If you have nothing set at `Pipen` constructor or process definition for a configuration item, the `PIPEN.osenv` is useful to use a different value than the one set in other configuration files. For example, to disable cache for all processes:

    ```
    PIPEN_DEFAULT_cache=0 python ./pipeline.py ...
    ```

## Profiles

You can have different profiles in configuration files:

`~/.pipen.toml`
```toml
[default]
scheduler = "local"

[sge]
scheduler = "sge"

[sge.schduler_opts]
sge_q = "1-day"
```


To use the `sge` profile:

```python
Pipen().run(P1, profile="sge")
```

You can also have a configuration in current directory:

`./.pipen.toml`
```toml
[sge.scheduler_opts]
sge_q = "7-days"
```

Then the queue to run the jobs will be `7-days`. Note that we didn't specify the `scheduler` in `./.pipen.toml`, which is inherited from `~/.pipen.toml`.

[1]: ../defining-proc
[2]: ../caching
[3]: ../error
[4]: ../templating
[5]: ../script
[6]: https://github.com/pwwang/python-simpleconf#loading-configurations
[7]: https://github.com/toml-lang/toml
