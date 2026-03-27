# Change Log

## 1.1.13

- chore: bump xqute to 2.0.8
- feat: add null_in_list parameter to update_dict for better list handling

## 1.1.12

- feat: implement duplicate fields check for output_flatten in Job and Proc classes


## 1.1.11

- feat: add Makefile for version management and changelog updates
- chore: bump diot to 0.3.3 and simpleconf to 0.9.2
- feat(proc): add output_flatten option to control job output directory structure

## 1.1.10

- fix: ensure `Proc` class name is set correctly when parent name matches
- chore: update dependencies

## 1.1.9

- deps: update python-simpleconf to version 0.9 (support templated config files)

## 1.1.8

- chore: bump up xqute to 2.0.6
- feat: include script_file in Job template_data
- chore: update version to 1.1.8 and plugin to v1.1.1 in README
- docs: add development guidelines for agentic coding agents
- docs: add contributing guidelines and development workflow
- docs: enhance README with detailed features, target audience, and comparison table
- docs: enhance documentation and examples

## 1.1.7

- fix: handle potential rate limit errors when creating output directories
- style: add type ignore comments for output computation and input data handling

## 1.1.6

- feat: deprecate input_data taking self argument (yank v1.1.5)

## 1.1.5

- feat: allow passing 'self' to input_data callback in Proc class

## 1.1.4

- fix: sort jobs by index before storing output data in DataFrame

## 1.1.3

- docs: update CLI plugin documentation to include AsyncCLIPlugin
- fix: use proc.size instead of len(jobs) to detect the size of procs to accruately detect it due to async operations

## 1.1.2

- feat: implement AsyncCLIPlugin for asynchronous command execution

## 1.1.1

- chore: bump python-simpleconf to 0.8
- chore: update ProfileConfig loading to async method

## 1.1.0

- BREAKING: change on_proc_input_computed and on_proc_script_computed to async
- refactor: migrate to panpath from cloudpatlib (so that path operations can be async)
- refactor: convert get_mtime to async and update related methods and tests
- refactor: streamline process initialization and script computation
- feat: add async versions of from_glob and from_pairs methods in Channel class
- feat: add async_run function and update run to support async execution
- feat: update path handling to use PanPath and add async support for symlink functions
- fix: improve job retry handling in ProcPBar and simplify success/failure updates
- test: add coverage pragma to retry handling methods and comment out flaky test
- style: fix type annotation and flake8 issues
- chore: bump xqute to 2.0
- chore: bump argx to 0.4
- chore: add pipen-verbose dependency to example group
- chore: update multijob example  for increased parallelism and debugging

## 1.0.4

- chore: adjust bar_format alignment for better readability

## 1.0.3

- chore: bump xqute to 1.0.1
- fix: defer setting bar_format to prevent ValueError when rendering counter
- feat: add queued job status to progress bar and update related hooks

## 1.0.2

- fix: make sure on_job_init() hook is called when no script was specified

## 1.0.1

- fix: make sure job.output is computed before on_job_init() hook
- feat: show direct job status for single-job process
- chore: add __slots__ to Template class for improved memory efficiency
- feat: enhance job progress bar to indicate cached jobs for single-job processes

## 1.0.0

- chore: adopt xqute 1.0.0
- feat: optimize the job submission (individual job submitted to scheduler right after initiation instead of waiting for all jobs to finish initiation)
- feat: update documentation links and styles, add script for collapsible sections
- feat: enhance progress bar to display job status counts and update formatting

## 0.17.29

- feat: add job submission progress update to progress bar
- docs: add progress bar section to running documentation

## 0.17.28

- fix: fix job progress bar not showing when jobs are being prepared

## 0.17.27

- fix: sort input list in brief_list function for consistent output

## 0.17.26

- fix: fix progress bar for jobs with submission skipped

## 0.17.25

- chore: update dependencies
- chore: update xqute dependency version to 0.10.19 to use per-scheduler submission_batch by default
- docs: add tip about cloud communication and caching in pipen
- fix: ensure directory creation does not fail if rmtree encounters an error
- fix: enhance symlink check by validating file size before download
- fix: update build system requirements to use poetry-core
- fix: update caching logic to handle missing signature files more gracefully
- test: add DirOutputEmptyProc to handle empty directory output and corresponding test

## 0.17.24

- chore: improve error message for missing output generation

## 0.17.23

- fix: update class reference for setup state to make sure on_setup hook only executes once

## 0.17.22

- BREAKING: change on_setup hook parameter from config to pipen
- chore: upgrade dependencies and bump datar to 0.15.12
- chore: update README with new plugins
- ci: add python 3.13 in build workflow

## 0.17.21

- chore: update fake symlink prefix to 'pipen-symlink'
- chore: update xqute version to 0.10.16

## 0.17.20

- chore: remove unnecessary self argument for the plugin for xqute and the main plugin for pipen itself

## 0.17.19

- chore: update xqute version to 0.10.11

## 0.17.18

- chore: update xqute version to 0.10.10
- feat: add environment variables to job submission

## 0.17.17

- feat: enhance argument parsing in CLI

## 0.17.16

- fix: handle potential error when reading stderr file
- chore: update xqute version to 0.10.7

## 0.17.15

- chore(deps): update xqute dependency version to 0.10.6 in pyproject.toml
- feat: adopt xqute 0.10.6

## 0.17.14

- fix: fix scheduler_opts of processes not full inheriting from pipeline
- style: fix styles in example scripts

## 0.17.13

- fix: update on_job_polling signature to include counter parameter

## 0.17.12

- chore(deps): bump xqute to 0.10.4

## 0.17.11

- fix: mapping the pipeline workdir for gbatch scheduler instead of process workdir to enable communications between processes
- chore: fix no argument ignore errors for path.rmtree
- tests: update gbatch scheduler volume paths
- chore(deps): bump xqute to 0.10.3
- chore: update .gitignore to include git bundle files

## 0.17.10

- fix: lowercase labels in GbatchScheduler

## 0.17.9

- feat: add pipeline and proc names to labels for GbatchScheduler
- chore(deps): bump xqute to 0.10.1
- chore: standardize log message for workdir

## 0.17.8

- chore(deps): bump up xqute to 0.10.0
- feat: add container scheduler support for Docker/Podman/Apptainer

## 0.17.7

- chore(deps): bump up xqute to 0.9.4
- fix: optimize path_is_symlink function to check fake symlink faster

## 0.17.6

- style: update type hints

## 0.17.5

- chore: bump xqute to 0.9.3
- fix: update mounted directory paths for GbatchScheduler
- feat: add fast_container for GbatchScheduler

## 0.17.4

- chore: add ipykernel dependency for example pipelines
- chore(deps): bump datar to 0.15.9 (numpy v2)
- fix: prevent adding processes to starts if already included

## 0.17.3

- chore: hide job index prefix in log messages for single-job processes
- chore(deps): update flake8 and other dependencies in pyproject.toml
- docs: fix outfile in the caching example
- docs: add example in README as an example pipeline in the examples folder

## 0.17.2

- fix: handle exceptions (KeyboardInterrupt) when closing counters in progress bar (enlighten v1.14)

## 0.17.1

- docs: update templating documentation to clarify job metadata paths
- fix: ensure iterables other than list/tuple are treated correctly as files/dirs

## 0.17.0

- fix: handle None input case in job caching logic
- chore(deps): update liquidpy to 0.8.4
- refactor: replace DualPath with SpecPath in codebase to adopt xqute 0.9

## 0.16.0

- ci: update build workflow conditions and improve dependency versions
- feat: support gbatch scheduler and cloud workdir/outdir
- refactor: replace cloudpathlib with yunpath and update related code
- refactor: adopt xqute 0.8.0
- chore: add more processes in examples/gbatch.py
- fix: make sure spec is carried for cloud output files so mtime can be check for next processes
- ci: add Google authentication step to CI workflow
- fix: fix specified path not carries to the next processes
- fix: handle missing MOUNTED_OUTDIR gracefully and remove unused test
- test: add fixture for unique ID and update cloud test to support parallel execution
- fix: remove fake symlink output when necessary
- docs: add cloud support documentation
- feat: support mounted paths (e.g. path1:path2) as input
- refactor: remove redundant validation for workdir and outdir path types
- feat: enforce GSPath type for 'gbatch' scheduler as pipeline outdir
- feat: add fast_mount option to GbatchScheduler for cloud directory mounting
- fix: update workdir path to include pipeline name in Pipen class
- chore(deps): bump python-simpleconf to v0.7
- feat: support DualPath output directory in Job class and ensure mounted directory creation
- fix: initialize cmd with a default value to prevent errors when no script is provided
- chore(deps): bump xqute to 0.8.1
- fix: only create mounted output directory when no MOUNTED_OUTDIR with scheduler
- fix: update mountPath index for taskSpec volumes in GbatchScheduler
- feat: support fast_mount to be a list for gbatch scheduler

## 0.15.8

- chore(deps): update package versions for executing, and xqute
- fix: change the input/output path from resolved to absolute for symlinks
- style(tests): update imports and add noqa comment for unused variable

## 0.15.7

- chore(deps): update xqute to version 0.5.5
- chore(deps): update pytest-asyncio to version 0.25.2
- chore: add logging for plugin initialization

## 0.15.6

- chore(deps): bump python-varname to 0.14
- ci: update GitHub Actions to use ubuntu-24.04
- style: fix style issues in test files

## 0.15.5

- fix: fix `kwargs` not updated when pipeline is a `Pipen` object in `utils.load_pipeline()`
- fix: fix type checking in `utils.load_pipeline()`

## 0.15.4

- fix: fix Pipen object not recognized by `utils.load_pipeline()`
- style: fix type annotations in Pipen class
- deps: bump argx to 0.2.11

## 0.15.3

- feat: add `pipen.run()` as a function to run a pipeline
- docs: fix the decorations in the logs in README

## 0.15.2

- deps: update xqute dependency to version 0.5.1
- chore: update pytest options in pyproject.toml to ignore deadlock warnings
- feat: expose on_jobcmd_* hooks for plugins to modify the job wrapper script

## 0.15.1

- deps: bump xqute to 0.5.0
  - xqute v0.5.0 provides 3 more hooks for the plugins to inject bash code to the job wrapper scripts.
  - see <https://github.com/pwwang/xqute?tab=readme-ov-file#plugins>.

## 0.15.0

- BREAKING: remove redundant argument `proc` for job plugin APIs
- deps: bump up dev deps
- deps: bump xqute to version 0.4.1
- refactor: remove `abstractproperty` decorator from `CLIPlugin` class
- feat: add 5 more APIs for plugins to handle files from other platforms (e.g. the cloud)
- ci: add python3.12 to CI
- test: fork each test in test_job.py
- test: fork tests in test_pipen.py and test_proc.py
- docs: correct the documentation about `dirsig`
- enh: make better error message when set wrong type of starts for a pipeline
- docs: add pipen-gcs in plugin gallery

## 0.14.6

- fix: fix error handling in ProcPBar class
- deps: bump up dev deps

## 0.14.5

- fix: fix all plugins being disabled by default

## 0.14.4

- deps: bump xqute to 0.4 (simplug to 0.4.1)
- refactor: refactor `pipen.plugin_context` due to simplug upgrade
- docs: update docs for specifiying plugins due to simplug upgrade
- examples: update examples for specifiying plugins due to simplug upgrade
- tests: add tests for plugins specification
- tests: use pytest v8
- ci: use latest actions

## 0.14.3

- choir: rename argument `args` to `argv` for `utils.is_loading_pipeline()`

## 0.14.2

- feat: allow passing arguments to `utils.is_loading_pipeline()`

## 0.14.1

- feat: add flags (e.g. `--help`) to `utils.is_loading_pipeline` to check arguments in `sys.argv`

## 0.14.0

- deps: drop support for python 3.8
- deps: bump `varname` to 0.13
- docs: update readme for more plugins

## 0.13.3 (yanked)

- deps: bump `varname` to 0.13

## 0.13.2

- style: change max line length to 88
- feat: add `envs_depth` to procs to control the depth of envs to be inherited by subclasses

## 0.13.1

- test: cover `on_job_polling`
- fix: update envs recursively for subclasses
- test: make sure class envs kept intact when subclassed

## 0.13.0

- deps: bump xqute to 0.3.1 and liquidpy to 0.8.2
- breaking: change hook `on_job_running` to `on_job_started` and add `on_job_polling`

## 0.12.5

- deps: bump xqute to 0.2.5
- chore: make utils._excepthook only handle KeyboardInterrupt
- chore: update examples

## 0.12.4

- Modify sys.argv before the module is loaded in `utils.load_pipeline()`

## 0.12.3

- Change cli_args to argv0 and argv1p for utils.load_pipeline

## 0.12.2

- Append `sys.argv[1:]` by default when `cli_args` is `None` in `utils.load_pipeline()`

## 0.12.1

- Add utils.is_loading_pipeline() to check if pipeline is loading

## 0.12.0

- ✨ Add utils.load_pipeline() to load pipeline

## 0.11.1

- Dismiss warning for fillna method for pandas 2.1
- Fix channel.expand_dir() may add new column

## 0.11.0

- Add Dockerfile for codesandbox
- Bump pandas to v2
- Bump argx to 0.2.10

## 0.10.6

- 🐛 Fix "DeprecationWarning: np.find_common_type is deprecated" from pandas (due to numpy 1.25 update)

## 0.10.5

- 🎨 Allow starts to be set as a tuple
- ⬆️ Bump python-simpleconf to 0.6 and other deps to latest versions
- ➕ Add rtoml to deps (as python-simpleconf 0.6 may not depend on rtoml)

## 0.10.4

- ⬆️ Bump xqute to 0.2.3

## 0.10.3

- ⬆️ Bump xqute to 0.2.2

## 0.10.2

- 🐛 Fix exception handling in ProcPBar class update method

## 0.10.1

- ✨ Add `on_proc_script_computed` hook

## 0.10.0

- 💥 Change hook `on_proc_init` to `on_proc_create`
- ✨ Add `on_proc_init` hook back but after the process initialized insteadl of before
- 👷 Add python 3.11 to CI
- 📝 Update documentation about updated hooks⏎

## 0.9.11

- 🐛 Make sure .envs of Proc subclasses are Diot objects

## 0.9.10

- 🐛 Fix `utils.mark` and `get_marked` when `__meta__` is `None`

## 0.9.9

- ⚡️ `utils.mark` and `get_marked` now work with `ProcGroup` and other classes

## 0.9.8

- 🐛 Fix priority of core plugin

## 0.9.7

- 🔧 Allow to inherit doc from base class for Pipen/Proc

## 0.9.6

- 🎨 Let plugins change and create workdir
- 🔧 Change the default outdir suffix from `_results` to `-output`
- 📖 Update README file and add new plugins

## 0.9.5

- 🔧 Fix workdir in log

## 0.9.4

- 🐛 Use class name as pipeline name

## 0.9.3

- 🐛 Set logging.lastResort to null handler
- ✨ Allow to assign process directly to proc groups
- 🔧 Change progress bar description length to 24

## 0.9.2

- 🎨 Rename to main plugin to core
- 🎨 Reformat log of pipeline info so that paths won't be truncated

## 0.9.1

- ⬆️ Bump xqute to 0.2.1

## 0.9.0

- ⬆️ Bump xqute to 0.2 so we can have slurm and ssh schedulers available
- ✨ Add ssh and slurm scheduers
- 🎨 Improve code for dropping python 3.7
- 👷 Use 3.10 as main python version in CI
- 📝 Update docs for slurm and ssh schedulers

## 0.8.0

- ⬆️ Drop support for python3.7
- 🎨 Don't slugify pipen or proc names anymore but require them to be valid filenames
- 🐛 Fix process names being reused
- 📝 Update documentation with new job caching callback.
- 🎨 Move actions to on_job_cached hook for cached jobs

## 0.7.3

- ✨ Add `--list` for `pipen profile` to list the names of available profiles
- ✨ Add exception hook to show uncaught in log
- ✨ Add `on_job_cached` hook

## 0.7.2

- ✨ Add `utils.mark` and `get_marked` to mark a process
    Unlike plugin_opts, template_opts or envs, these marks are not inherited in subclasses

## 0.7.1

- ⬆️ Upgrade simplug to 0.2.3
- 📝 Add pipen-cli-config to plugin gallery

## 0.7.0

- ⬆️ Update liquidpy to 0.8
- ✨ Add `Proc.__meta__` that will not be inherited when subclassing
- 🎨 Put `procgroup` in `Proc.__meta__`
- ⚡️ Do not mutate `Proc.__doc__` when subclassing
- ⚡️ Use mro to detect parent class of a Proc

## 0.6.4

- 🔀 Set desc from docstring if not given for pipelines

## 0.6.3

- 🔊 Trim right spaces of logs

## 0.6.2

- ⬆️ Adopt xqute 0.1.5

## 0.6.1

- 🐛 Fix path expansion for `~/.pipen.toml` in defaults.

## 0.6.0

- ✨ Allow subclassing Pipen to create a pipeline (#151)

## 0.5.2

- 📝 Refactor codebase: unify type annotations and import future features
- 🐛 Allow methods decorated by @ProcGroup.add_proc to return None

## 0.5.1

- 🚑 Remove remaining more-itertools

## 0.5.0

- ➖ Remove more-itertools
- ✨ Add `ProcGroup` to manage groups of processes.

    ```python
    from pipen import Proc, ProcGroup

    class MyGroup(ProcGroup):

        @ProcGroup.add_proc
        def my_proc(self):
            class MyProc(Proc):
                ...
            return MyProc

        @ProcGroup.add_proc
        def my_proc2(self):
            class MyProc2(Proc):
                requires = self.my_proc
                ...
            return MyProc2

    pg = MyGroup()
    # Run as a pipeline
    pg.as_pipen().set_data(...).run()

    # Integrate into a pipeline
    <proc_of_a_pipeline>.requires = pg.my_proc2
    ```

## 0.4.6

- 🐛 Fix plugins command not listing plugins

## 0.4.5

- 🚑 Fix banner alignment in terminal

## 0.4.4

- 🐛 Fix when cli plugin has no docstring
- 🚑 Exclude help from help sub-command itself
- 🚑 Add cli plugin docstring as sub-command description

## 0.4.3

- ⬆️ Bump `argx` to 0.2.2
- 🎨 Expose `parse_args()` to cli plugins

## 0.4.2

- ⬆️ Bump `argx` to 0.2

## 0.4.1

- 🐛 Fix cli plugin name

## 0.4.0

- ⬆️ Upgrade python-slugify to ^0.8
- ⬆️ Upgrade xqute to 0.1.4
- ⬆️ Upgrade varname to 0.11
- 💥 Use argx instead of pyparam

## 0.3.12

- ⬆️ Upgrade python-slugify to ^7

## 0.3.11

- 📝 Fix github workflow badges in README
- 🩹 Fix pandas warning when less-column data passed to channel

## 0.3.10

- ⬆️ Upgrade xqute to 0.1.3
- ⬆️ Upgrade datar to 0.11 and format test files
- ✨ Add cli command version to show versions of deps
- ➖ Remove rich as it is required by xqute already

## 0.3.9

- ⬆️ Bump pipda to 0.11
- ⬆️ Bump xqute to 0.1.2

## 0.3.8

- ⬆️ Pump xqute to 0.1.1

## 0.3.7

- ⬆️ Upgrade varname to 0.10

## 0.3.6

- ⬆️ Upgrade pipda to 0.7.2, varname to 0.9.1, datar to 0.9

## 0.3.5

- 🐛 Fix `nexts` being inherited for `Proc` subclasses

## 0.3.4

- ✨ Print pipen version in CLI: pipen plugins
- 🩹 Make use of full terminal width for non-panel elements in log
- 🩹 Extend width to 256 when terminal width cannot be detected while logging (most likely logging to a text file)

## 0.3.3

- ♿️ Change default log width to 100
- 🩹 Fix broken panel in log content with console width cannot be detected

## 0.3.2

- ⬆️ Upgrade rtoml to v0.8
- ⬆️ Upgrade pipda to v0.6

## 0.3.1

- 🩹 Hide config meta data in pipeline information

## 0.3.0

- ⬆️ Upgrade dependencies
- 📌 Use `rtoml` instead of `toml` (see https://github.com/pwwang/toml-bench)
- 🩹 Dump job signature to file directly instead of dump to a string first
- 👷 Add python 3.10 to CI
- 📝 Add dependencies badge to README.md

## 0.2.16

- 📌 Pin dep versions
- 🩹 Allow to set workdir from Pipen constructor

## 0.2.15

- 🩹 Fix `FutureWarning` in `Proc._compute_input()`
- 🩹 Add `__doc__` for `Proc.from_proc()`
- 📌 Pin deps for docs

## 0.2.14

- 🩹 Shorten pipeline info in log for long config options
- 🐛 Fix cached jobs being put into queue
- 🩹 Shorten job debug messages when hit limits
- 🚑 Remove sort_dicts for pprint.pformat for py3.7

## 0.2.13

- 🩹 Don't require `job.signature.toml` to force cache a job

## 0.2.12

- 🐛 Hotfix for typos in `Proc.__init_subclass__()`

## 0.2.11

- 🩹 Update `envs`, `plugin_opts` and `scheduler_opts` while subclassing processes.

## 0.2.10

- ✨ Add hook `on_proc_input_computed`
- 🩹 Default new process docstring to "Undescribed process."

## 0.2.9

- ✨ Allow `requires` to be set by `__setattr__()`

## 0.2.8

- 🩹 Forward fill na for input data

## 0.2.7

- 🩹 Fix process plugin_opts not inherited from pipeline

## 0.2.6

- 🎨 Make `pipen._build_proc_relationships()` public and don't rebuild the relations
- ✨ Allow pipenline name to be obtained from assignment

## 0.2.5

- 🩹 Allow relative script path to be inherited
- 🐛 Fix column order from depedency processes
- 🩹 Fix __doc__ not inherited for processes

## 0.2.4

- ✨ Add execution order for processes


## 0.2.3

- ⚡️Speed up package importing

## 0.2.2

- 🐛 Load CLI plugins at runtime


## 0.2.1

- 🎨 Allow CLI plugin to have different name than the command

## 0.2.0

- 💥 Restructure CLI plugins

## 0.1.4

- 🩹 Use brackets to indicate cached jobs
- 🩹 Run on_complete hook only when no exception happened
- 🩹 Let `on_proc_init` to modify process `workdir`
- 🐛 Fix when `nexts` affected by parent `nexts` assignment when parent in `__bases__`

## 0.1.3

- ✨ Add `on_proc_init()` hook to enables plugins to modify the default attributes of processes
- 💥 Rename `Proc.args` to `Proc.envs`

## 0.1.2

- 💥 Use `set_starts()` and `set_data()` to set start processes of a pipeline.

## 0.1.1

- 💥 Allow plugins to modify other configs via on_setup() hook
- 🎨 Move progress bar to the last
- 🩹 Warn when no input_data specified for start process
- 💬 Change end to export
- 🚚 Move on_init() so it's able to redefine default configs
- 💥 Change `exec_cmd` hook of cli plugin to `exec_command`


## 0.1.0

It's now fully documented. See documentations.

## 0.0.4
- Clear output if not cached.
- Make process running order fixed

## 0.0.3
- Fix caching issue
- Add singleton to proc to force singleton
- Log an empty line after all processes finish
- Allow input to be None
- Separate channels from different required procs
- Move proc prepare before run
- Change the order proc banner printing, making sure it prints before other logs for the proc
- FIx job not cached if input is missing
- Don't redirect output only if absolute path specified
- Make input files resolved(absolute path)
- Give more detailed ProcDependencyError
- Force job status to be failed when Ctrl + c
- Fix files for input when it is a pandas dataframe
- Add job name prefix for scheduler
- Adopt datar for channels

## 0.0.2
- Add on_proc_property_computed hook
- Add plugin options for pipen construct
- Keep args, envs, scheduler_opts and plugin_opts as Diot object for procs
- Fix shebang not working in script
- Make sure job rendering data are stringified.
- Move starts as a method so that pipelines can be initialized before processes.
- Use plyrda instead of siuba for channel
- Add template rendering error to indicate where the rendering error happens;
- Add succeeded to on_complete hook;
- Add hook on_proc_start;
- Add argument succedded for hook on_proc_done;
- Realign pipeline and proc names in progress bars
- Remove debug log in job preparing, which will appear on the top of the logs

## 0.0.1

- Reimplement PyPPL using asyncio
