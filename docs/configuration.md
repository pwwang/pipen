
There are a couple of ways to configure `PyPPL`:

- Load configuration dictionary before you start writing your pipeline

  ```python
  from pyppl import load_config
  # you will need profile names
  load_config({'default': {'forks': 10}})

  # you awesome pipeline goes here
  ```

- Load configuration file before you start writing your pipeline

  ```toml
  # pyppl.toml
  [default]
  forks = 10
  ```

  ```python
  from pyppl import load_config
  # you will need profile names
  load_config('pyppl.toml')

  # you awesome pipeline goes here
  ```

  By default, `PyPPL` will load the configurations from `~/.PyPPL.toml`, `./.PyPPL.toml` and environment variables that start with `PYPPL_`.

  !!! hint

      `PyPPL` uses [`toml`](https://github.com/toml-lang/toml) as configuration language.

- Specify configuration at runtime

  ```python
  from pyppl import PyPPL

  PyPPL(config = {'default': {'forks': 10}})
  # too complicated? use kwargs:
  PyPPL(forks = 10) # it will automatically be profiled as default
  # You can also load configuration from file at runtime
  PyPPL(config_files = ['pyppl.toml'])
  ```

  ```python
  PyPPL(logger = {'level': 'debug'})
  # still too complicated? use a underline to connect the item and sub-item:
  PyPPL(logger_level = 'debug')
  ```

  !!! note

      Some configuration items can be overridden by running configurations, some can't.

      1. If a configuration item is set as a `Proc` property explicitly, it won't be overridden:
         ```python
         pXXX.forks = 20
         PyPPL(forks = 10)
         # will not change forks of pXXX
         # pXXX.forks == 20

         # But if forks is initialized in construct
         pYYY = Proc(forks = 20)
         PyPPL(forks = 10)
         # pYYY == 10
         ```
      2. If a configuration item is a dictionary, it will be updated
        ```python
        pXXX.envs.a = 1
        pXXX.envs.b = 2

        PyPPL(envs_a = 3)
        # pXXX.envs == {'a': 3, 'b': 2}
        ```
      3. Otherwise, properties for ALL processes in this pipeline will be overwritten by the runtime configurations.

## Full configurations

```python
dict(default = dict(
	# plugins
	plugins = ['no:flowchart', 'no:report'],
	# logger options
	logger = dict(
		file       = None,
		theme      = 'green_on_black',
		level      = 'info',
		leveldiffs = []
	),
	# The cache option, True/False/export
	cache      = True,
	# Whether expand directory to check signature
	dirsig     = True,
	# How to deal with the errors
	# retry, ignore, halt
	# halt to halt the whole pipeline, no submitting new jobs
	# terminate to just terminate the job itself
	errhow     = 'terminate',
	# How many times to retry to jobs once error occurs
	errntry    = 3,
	# The directory to export the output files
	forks      = 1,
	# Default shell/language
	lang       = 'bash',
	# number of threads used to build jobs and to check job cache status
	nthread    = min(int(cpu_count() / 2), 16),
	# Where cache file and workdir located
	ppldir     = './workdir',
	# Select the runner
	runner     = 'local',
	# The tag of the job
	tag        = 'notag',
	# The template engine (name)
	template   = 'liquid',
	# The template environment
	envs       = Diot(),
	# configs for plugins
	plugin_config = {},
))
```

!!! note

    For `plugins` and `logger` configurations:

    1. They should be ALWAYS specified in profile `default`
    2. `plugins` can only affect plugins APIs at runtime if configrations passed at runtime.
       For example, if a plugin only runs at `Proc` definition, it won't be affected by runtime configurations
