# 3.0.2 (2020.1.15)
- Add status for plugin API proc_postrun
- Copy input keys while copying a process
- Fix extra empty lines in log
- Add check for threading resource availablility
- Add full traceback for proc definition
- Fix default runner config not loaded if running with different runner profile

# 3.0.1 (2019.12.31)
- Fix job.data.i.x not pointing to files in `<indir>`
- Remove unnecessary job attribute from building `__eq__`
- Fix channel buliding for procs
- Fix `_anything2procs` not using procset argument when a list of ProcSets passed
- Change runner DEFAULT_POLL_INTERVAL to 1 sec
- Fix return value of kill of local runner (must be a bool value).
- Fix `attr.ib` properties not copied during proc coping
- Add proc props for plugins
- Move timer to `pyppl_rich` plugin
- Compute input, output and script for process before jobs created, as they are not thread-safe.

# 3.0.0 (2019.12.26)
- Fundamental:
	- Rewrite `Proc` and `Job` using `attrs` and `attr_property`
- Plugins:
	- Refine plugin system
	- Move some functions to plugins
	- Re-organize log levels and enable plugins to add levels
- Runners:
	- Make runners also plugins
- Other:
	- Optimize and fix other bugs

# 2.3.2 (2019.12.5)
- Infer job cache status when not job.cache file generated (main thread quits before job done)
- Remove force cache mode
- Use `diot` instead of `python-box`

# 2.3.1 (2019.11.29)
- Fix global config.args been overwritten when multiple pipelines in one session
- Wrap long process descriptions in log
- Fix kwargs for Proc constructor not triggering `__setattr__`


# 2.3.0 (2019.11.18)
- Add check for output names
- Fix deepcopy problem in proc.copy
- Remove template functions, as they are not necessary for the framework itself
- Add keys in kwargs of Proc construct in sets
- Fix other bugs

# 2.2.0 (2019.10.23)
- Add forced cache #78
- Add CLI hooks for plugins
- Fix job not submitting while retrying

# 2.1.4 (2019.10.11)
- Optimize CLI "pyppl list/clean" to show results immediately instead of loading all processes.
- Fix CLI option "-before" validation.
- Fix error when some objects cannot be deeply copied while coping a process.
- Fix while @ in job names for sge runner.
- Use TEMPDIR instead for _fsutil to avoid creating a subdirectory under it threading-unsafely.
- Enhance if some SGE fails to generate stdout/err file.

# 2.1.3 (2019.8.21)
- Rename plugins from pyppl-* to pyppl_* due to inability of dashes in entry_point

# 2.1.2 (2019.8.19)
- Save 'var' type of input as string to avoid error when reading it
- Report plugin version in logger

# 2.1.1 (2019.8.8)
- Drop proc.tplenvs, use proc.envs instead

# 2.1.0 (2019.8.5)
- Add plugin system
- Move flowchart and report as separate plugins
- Add template function glob1

# 2.0.0 (2019.6.28)
- Change versioning back to semantic
- Drop support for python <= 3.5
- Adopt more of 3rd-party packages
- Use poetry to manage dependencies and publish package
- Rewrite runner system and make it easier to write a custom runner
- Rewrite logger system
- Migrate `bin/pyppl` to `pyppl/console.py`
- Use a state machine to manage job states
- Rewrite job queue strategy
- Adopt `pytest` for testing
- Change `Aggr` to `ProcSet` and rewrite some methods
- Show a more intuitive example in README
- Move docs to readthedocs
- Optimize `Job` class to save memories
- Fix other bugs

# 2019.2.20
- Use date as version naming.
- Adopt colorama for teminal colors.
- Allow configs to update recursively.
- Remove python 3.3 support.
- Fix #48: unicode loaded when config file is in json

# 1.4.3 (2019.1.28)
- Change path shortening cutoff to total length.
- Fix a bug for template function `fn` (filename/stem).
- Fix logger formatter conflicts.

# 1.4.2 (2019.1.23)
- Add `runner` subcommand for `bin/pyppl` to show available runners.
- Allow length of the progress bar configurable.
- Allow the paths to be shortened in logs.
- Fix other bugs.

# 1.4.1 (2019.1.9)
- Add `render` function for template to allow variables to be rendered in template.
- Allow reset for list parameter in parameters
- Add callback for Parameter

# 1.4.0 (2018.12.20)
- Implement jobmgr with PriorityQueue, and put job building, submission and polling in the same queue
- Remove file locks while job initiation to speed up
- Other bug fixes.

# 1.3.1 (2018.11.8)
- Fix pipeline not quitting if retry times reached.
- Optimize CPU usage.

# 1.3.0 (2018.11.2)
- Use threading instead of multiprocess to save resources and rewrite queue system
- Change `cclean` to `acache` (after cache)
- Change `nthread` to `nsub` (# threads used to submit jobs)
- Remove `six` dependency
- Cleanup pipeline when halt (Ctrl-c hit or error encountered while `errhow = halt`)

# 1.2.0 (2018.9.28)
- Use `liquidpy` as default template engine (see how to migrate in FAQ).
- Fix other bugs.

# 1.1.2 (2018.9.13)
- Optimize check server alive for ssh runner.
- Rwrite command line tool: bin/pyppl
- Add commands to allow subcommand in command line argument parser.
- Allow params to parse arguments arbitrarily.
- Allow help information to be interpolated from outsite for params.
- Add alias support for params and commands.
- Rewrite API generator and regenerate API docs.
- Fix other bugs.

# 1.1.1 (2018.8.30)
- Allow progress bar to be collapsed in stream log.
- Remove loky dependency, so `PyPPL` could run on cygwin/msys2.
- Add `~/pyppl.yml`, `~/pyppl.yaml`, `~/pyppl` and `~/pyppl.json` to default configuration files.
- Update docs.
- Fix other bugs.

# 1.1.0 (2018.8.20)
- Let pipeline halt if any job fails (#33).
- Add KeyboardInterupt handling.
- Add Warning message when a process is locked (another instance is running)
- Clean up utils and runners source codes
- Support and add tests to travis for python2.7 and python3.3+ for both OSX and Linux.
- Allow global functions/values to be used in builtin templates.
- Add shortcut for lambda function in builtin templates.
- Add `nones` and `transpose` method for `Channel`.

# 1.0.1 (2018.7.31)
- Change the default path of flowchart and log from script directory to current directory.
- Rewrite the way of attribute setting for aggregations.
- Introduce modules for aggregations.
- Allow setting attributes from Proc constructor.
- Implement #33, `Ctrl-c` now also halts the pipeline, and hides the exception details.

# 1.0.0 ! (2018.7.10)
- Fix runner name issue #31.
- Use mkdocs to generate documentations and host them on GitHub pages.
- Keep stdout and stderr when a job is cached: #30.
- Allow command line arguments to overwrite Parameter's type.
- Host the testing procedures with Travis.
- Fix other bugs.

# 0.9.6 (2018.6.8)
- Auto-delegate common proc config names to aggr
- Add proc.origin to save the original proc id for copied procs
- Remove brings, add proc.infile to swith '{{in.(infile)}}' to job.indir path, original path or realpath of the input file
- Add process lock to avoid the same processes run simultaneously
- Use built-in Box instead of box.Box
- Merge template function Rvec and Rlist into R, add repr
- Fix #29 and #31, and fix other bugs

# 0.9.5 (2018.3.6)
- Add proc.dirsig to disable/enable calculating signatures from deep directories
- Add Jobmgr class to handle job distribution
- Allow channel.rowAt and colAt to return multiple rows and columns, respectively
- Allow empty channel as input (process will be skipped)
- Refine all tests
- Rewrite thread-safe file system helper functions
- Add specific exception classes
- Report line # when error happens in template
- Add progress bar for jobs
- Allow stdout and stderr file as output

# 0.9.4 (2017.12.27)
- Add yaml support for config file (#26).
- Allow empty list for input files.
- Merge continuous job ids in log (Make the list shorter).
- More details when internal template failed to render (#25)
- Ignore .yaml config files if yaml module is not installed.
- sleep before testing isRunning to avoid all jobs running it at the same time.
- Use repr to output p.args and p.props.
- Merge Proc attributes profile and runner. Profile is now an alias of runner, and will be removed finally.

# 0.9.3 (2017.11.20)
- Beautify parameters help page.
- Enable multithreading for job construction and cache checking (set by proc.nthread).
- Uniform multiprocessing/threading.
- Fix Aggr delegate problems.
- Add ProcTree to manage process relations.
- Report processes will not run due to prior processes not ran.
- Add cclean option for enable/disable cleanup (output check/export) if a job is cached.
- Add tooltip for flowchart svg.
- Fix job id not saved for runner_sge.
- Fix resume assignment issue.
- Rewrite proc.log function so that logs from jobs do not mess up when they are multithreaded.
- Fix params loaded from file get overwriten.
- Add coverage report.

# 0.9.2 (2017.10.23)
- Add profile for Proc so different procs can run with different profiles.
- Add delegate for Aggr.
- Add get, repCol, repRow, rowAt method for Channel.
- Dont't sleep for batch interval if jobs are cached or running.
- Add header argument for Channel.fromFile.
- Fix a bunch of bugs.

# 0.9.1 (2017.10.6)
- Fix issues reported by codacy
- Fix an issue checking whether output files generated
- Deepcopy args and tplenvs when copy a process
- Refer relative path in p.script (with "file:" prefix) where p.script is defined
- Fix a utils.dictUpdate bug
- Template function 'Rlist' now can deal with python list
- Add log for export using move method (previously missed)
- Allow Aggr instance to set input directly
- Switch default showing of parameters loaded from object or file to False
- Optimize utils.varname
- Add warning if more input data columns than number of input keys
- Fix output channel key sequence does not keep
- Use object id instead of name as key for PyPPL nexts/paths in case tag is set in pipeline configrations

# 0.9.0 (2017.9.22)
- Change class name with first letter capitalized
- Add resuming from processes (#20)
- Fix #19
- Group log configuration
- Make flowchart themeable and configurable
- Make attributes of `Proc` clearer
- Add tutorials
- Make tests more robust
- Enhancer templating, support Jinja2
- Set attributes of processes in aggregation with `set`

# 0.8.1 (2017.8.4)
- Add partial echo
- Add interactive log from the script
- Add partial export
- Add log themes and filters
- Add compare to command line tool
- Fix bugs

# 0.8.0 (2017.8.1)
- Add slurm and dry runner
- Fix bugs when more than 2 input files have same basename
- Add indent mark for script, specially useful for python
- Make stdout/stderr flushes out for instant runners when p.echo = True
- Add `sortby`, `reverse` for `channel.fromPath`
- Add command line argument parse
- Fix a bug that threads do not exit after process is done

# 0.7.4 (2017.7.18)
- Docs updated (thanks @marchon for some grammer corrections)
- Some shortcut functions for placeholders added
- Check running during polling removed
- Logfile added
- `p.args['key']` can be set also by `p.args.key` now
- Bug fixes

# 0.7.3 (2017.7.3)
- Config file defaults to `~/.pyppl.json` (`~/.pyppl` also works)
- Callfront added
- Empty input allowed
- Same basename name allowed for input files of a job
- Description of a proc added
- Aggr Optimized
- Bug #9 Fixed
- Private key supported for ssh runner
- Feature #7 Implemented

# 0.7.2 (2017.6.20)
- Optimize isRunning function (using specific job id)
- Support python3 now
- Test on OSX
- More debug information for caching
- Bug fixes

# 0.7.1 (2017.6.15)
- Move pyppl-cli to bin/pyppl
- channel.collapse now return the most common directory of paths
- Report oringinal file of input and bring files
- Show number of omitted logs
- Bug fixes

# 0.7.0 (2017.6.13)
- Add colored log
- Put jobs in different directories (files with same basename can be used as input files, otherwise it will be overwritten).
- Add configuration `checkrun` for `pyppl` allow `runner.isRunning` to be disabled (save resources on local machine).
- Add built-in functions for placeholders; lambda functions do not need to call (just define)
- File placeholders (.fn, .bn, .prefix, etc) removed, please use built-in functions instead.
- Add an alias `p.ppldir` for `p.tmpdir` to avoid confusion.
- Update command line tool accordingly
- Split base runner class into two.

# 0.6.2 (2017.5.30)
- Update docs and fix compilation errors from gitbook
- Change pyppl.dot to pyppl.pyppl.dot;
- Add channel.fromFile method;
- Add aggr.addProc method;
- Fix proc/aggr copy bugs;
- Fix utils.varname bugs;
- Fix bugs: channel._tuplize does not change list to tuple any more.
- Add fold/unfold to channel;
- cache job immediately after it's done;
- remove proc in nexts of its depends when its depends are reset;
- add dir for input files, prefix for output files;
- Fix utilfs.dirmtime if file not exists;
- add pyppl-cli;
- Change rc code, make it consistent with real rc code.

# 0.6.1 (2017.4.27)
- Overwrite input file if it exists and not the same file;
- fix varname bug when there are dots in the function name;
- Add brings feature;
- Add features to README, and brings to docs

# 0.6.0 (2017.4.26)
- Set job signature to False if any of the item is False (that means expected files not exists); - Do cache by job itself;
- Make it possible to cache and export successful jobs even when some jobs failed
- Host docs in gitbook
- Init job with log func from proc;
- Add docstring for API generation;
- Redefine return code for outfile not generated;
- Error ignore works now;
- Rewrite runner_local so it fits other runners to extend;
- Fix proc depends on mixed list of procs and aggrs

# 0.5.0 (2017.4.18)
- Fix local runner not waiting (continuiously submitting jobs);
- Add property alias for aggr;
- Output cleared if job not cached
- Fix bugs when export if outfiles are links;
- change default export method to move;
- add id and tag to calculate suffix for proc;
- add timer;
- add isRunning for job so that even if the main thread quit, we can still retrieve the job status;

# 0.4.0 (2017.4.13)
- Add files (array) support for input;
- Recursive update for configuration;
- Add aggregations;
- Move functions to utils;
- Separate run for runners to submit and wait;
- Add use job class for jobs in a proc;
- Use "1,2 3,4" for channel.fromArgs for multi-width channels;
- Add rbind, cbind, slice for channel;
- Add alias for some proc properties;
- Remove callfront for proc;
- Add export cache mode;
- Add gzip export support (#1);
- Unify loggers;
- Use job cache instead of proc cache so that a proc can be partly cached;
- Rewrite buildInput and buildOutput;
- Use job to construct runners;

# 0.2.0 (2017.3.14)
- Basic functions

# Initiate (2017.1.27)
