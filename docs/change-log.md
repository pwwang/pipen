# Change log
<!-- toc -->

## June 15, 2017: 0.7.1
- Move pyppl-cli to bin/pyppl
- channel.collapse now return the most common directory of paths
- Report oringinal file of input and bring files
- Show number of omitted logs
- But fixes

## June 13, 2017: 0.7.0
- Add colored log
- Put jobs in different directories (files with same basename can be used as input files, otherwise it will be overwritten).
- Add configuration `checkrun` for `pyppl` allow `runner.isRunning` to be disabled (save resources on local machine).
- Add built-in functions for placeholders; lambda functions do not need to call (just define)
- File placeholders (.fn, .bn, .prefix, etc) removed, please use built-in functions instead.
- Add an alias `p.ppldir` for `p.tmpdir` to avoid confusion.
- Update command line tool accordingly
- Split base runner class into two.

## May 30, 2017: 0.6.2
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

## Apr 27, 2017: 0.6.1
- Overwrite input file if it exists and not the same file; 
- fix varname bug when there are dots in the function name;
- Add brings feature;
- Add features to README, and brings to docs

## Apr 26, 2017: 0.6.0
- Set job signature to False if any of the item is False (that means expected files not exists); - Do cache by job itself; 
- Make it possible to cache and export successful jobs even when some jobs failed
- Host docs in gitbook
- Init job with log func from proc; 
- Add docstring for API generation; 
- Redefine return code for outfile not generated; 
- Error ignore works now; 
- Rewrite runner_local so it fits other runners to extend;
- Fix proc depends on mixed list of procs and aggrs

## Apr 18, 2017: 0.5.0
- Fix local runner not waiting (continuiously submitting jobs);
- Add property alias for aggr; 
- Output cleared if job not cached
- Fix bugs when export if outfiles are links; 
- change default export method to move; 
- add id and tag to calculate suffix for proc; 
- add timer; 
- add isRunning for job so that even if the main thread quit, we can still retrieve the job status;

## Apr 13, 2017: 0.4.0
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

## Mar 14, 2017: 0.2.0
- Basic functions

## Jan 27, 2017: Initiate 
