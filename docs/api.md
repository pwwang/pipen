
# API
<!-- toc -->

## Module `PyPPL`  
> The PyPPL class

	@static variables:
		`TIPS`: The tips for users
		`RUNNERS`: Registered runners
		`DEFAULT_CFGFILES`: Default configuration file
	

#### `__init__ (self, config, cfgfile) `
  
Constructor  

- **params:**  
`config`: the configurations for the pipeline, default: {}  
`cfgfile`:  the configuration file for the pipeline, default: `~/.PyPPL.json` or `./.PyPPL`  
  
#### `_any2procs (*args) [@staticmethod]`
  
Get procs from anything (aggr.starts, proc, procs, proc names)  

- **params:**  
`arg`: anything  

- **returns:**  
A set of procs  
  
#### `_checkProc (proc) [@staticmethod]`
  
Check processes, whether 2 processes have the same id and tag  

- **params:**  
`proc`: The process  

- **returns:**  
If there are 2 processes with the same id and tag, raise `ValueError`.  
  
#### `_registerProc (proc) [@staticmethod]`
  
Register the process  

- **params:**  
`proc`: The process  
  
#### `_resume (self, *args, **kwargs) `
  
Mark processes as to be resumed  

- **params:**  
`args`: the processes to be marked. The last element is the mark for processes to be skipped.  
  
#### `flowchart (self, fcfile, dotfile) `
  
Generate graph in dot language and visualize it.  

- **params:**  
`dotfile`: Where to same the dot graph. Default: `None` (`path.splitext(sys.argv[0])[0] + ".pyppl.dot"`)  
`fcfile`:  The flowchart file. Default: `None` (`path.splitext(sys.argv[0])[0] + ".pyppl.svg"`)  
- For example: run `python pipeline.py` will save it to `pipeline.pyppl.svg`  
`dot`:     The dot visulizer. Default: "dot -Tsvg {{dotfile}} > {{fcfile}}"  

- **returns:**  
The pipeline object itself.  
  
#### `registerRunner (runner) [@staticmethod]`
  
Register a runner  

- **params:**  
`runner`: The runner to be registered.  
  
#### `resume (self, *args) `
  
Mark processes as to be resumed  

- **params:**  
`args`: the processes to be marked  

- **returns:**  
The pipeline object itself.  
  
#### `resume2 (self, *args) `
  
Mark processes as to be resumed  

- **params:**  
`args`: the processes to be marked  

- **returns:**  
The pipeline object itself.  
  
#### `run (self, profile) `
  
Run the pipeline  

- **params:**  
`profile`: the profile used to run, if not found, it'll be used as runner name. default: 'default'  

- **returns:**  
The pipeline object itself.  
  
#### `showAllRoutes (self) `
  
#### `start (self, *args) `
  
Set the starting processes of the pipeline  

- **params:**  
`args`: the starting processes  

- **returns:**  
The pipeline object itself.  
  

## Module `Proc`  
> The Proc class defining a process

	@static variables:
		`RUNNERS`:       The regiested runners
		`ALIAS`:         The alias for the properties
		`LOG_NLINE`:     The limit of lines of logging information of same type of messages

	@magic methods:
		`__getattr__(self, name)`: get the value of a property in `self.props`
		`__setattr__(self, name, value)`: set the value of a property in `self.config`
	

#### `__init__ (self, tag, desc, id, **kwargs) `
  
Constructor  

- **params:**  
`tag`:  The tag of the process  
`desc`: The description of the process  
`id`:   The identify of the process  

- **config:**  
id, input, output, ppldir, forks, cache, cclean, rc, echo, runner, script, depends, tag, desc, dirsig  
exdir, exhow, exow, errhow, errntry, lang, beforeCmd, afterCmd, workdir, args, aggr  
callfront, callback, expect, expart, template, tplenvs, resume, nthread  

- **props**  
input, output, rc, echo, script, depends, beforeCmd, afterCmd, workdir, expect  
expart, template, channel, jobs, ncjobids, size, sets, procvars, suffix, logs  
  
#### `_buildInput (self) `
  
Build the input data  
Input could be:  
1. list: ['input', 'infile:file'] <=> ['input:var', 'infile:path']  
2. str : "input, infile:file" <=> input:var, infile:path  
3. dict: {"input": channel1, "infile:file": channel2}  
or    {"input:var, input:file" : channel3}  
for 1,2 channels will be the combined channel from dependents, if there is not dependents, it will be sys.argv[1:]  
  
#### `_buildJobs (self) `
  
Build the jobs.  
  
#### `_buildOutput (self) `
  
Build the output data templates waiting to be rendered.  
  
#### `_buildProcVars (self) `
  
Build proc attribute values for template rendering,  
and also echo some out.  
  
#### `_buildProps (self) `
  
Compute some properties  
  
#### `_buildScript (self) `
  
Build the script template waiting to be rendered.  
  
#### `_checkCached (self) `
  
Tell whether the jobs are cached  

- **returns:**  
True if all jobs are cached, otherwise False  
  
#### `_readConfig (self, profile, profiles) `
  
Read the configuration  

- **params:**  
`config`: The configuration  
  
#### `_runCmd (self, key) `
  
Run the `beforeCmd` or `afterCmd`  

- **params:**  
`key`: "beforeCmd" or "afterCmd"  

- **returns:**  
The return code of the command  
  
#### `_runJobs (self) `
  
Submit and run the jobs  
  
#### `_saveSettings (self) `
  
Save all settings in proc.settings, mostly for debug  
  
#### `_suffix (self) `
  
Calcuate a uid for the process according to the configuration  
The philosophy:  
1. procs from different script must have different suffix (sys.argv[0])  
2. procs from the same script:  
- procs with different id or tag have different suffix  
- procs with different input have different suffix (depends, input)  

- **returns:**  
The uniq id of the process  
  
#### `_tidyAfterRun (self) `
  
Do some cleaning after running jobs  
self.resume can only be:  
- '': normal process  
- skip+: skipped process but required workdir and data exists  
- resume: resume pipeline from this process, no requirement  
- resume+: get data from workdir/proc.settings, and resume  
  
#### `_tidyBeforeRun (self) `
  
Do some preparation before running jobs  
  
#### `copy (self, tag, desc, id) `
  
Copy a process  

- **params:**  
`id`: The new id of the process, default: `None` (use the varname)  
`tag`:   The tag of the new process, default: `None` (used the old one)  
`desc`:  The desc of the new process, default: `None` (used the old one)  

- **returns:**  
The new process  
  
#### `log (self, msg, level, key) `
  
The log function with aggregation name, process id and tag integrated.  

- **params:**  
`msg`:   The message to log  
`level`: The log level  
`key`:   The type of messages  
  
#### `name (self, aggr) `
  
Get my name include `aggr`, `id`, `tag`  

- **returns:**  
the name  
  
#### `run (self, profile, profiles) `
  
Run the jobs with a configuration  

- **params:**  
`config`: The configuration  
  

## Module `Channel`  
> The channen class, extended from `list`
	

#### `_tuplize (tu) [@staticmethod]`
  
A private method, try to convert an element to tuple  
If it's a string, convert it to `(tu, )`  
Else if it is iterable, convert it to `tuple(tu)`  
Otherwise, convert it to `(tu, )`  
Notice that string is also iterable.  

- **params:**  
`tu`: the element to be converted  

- **returns:**  
The converted element  
  
#### `attach (self, *names, **kwargs) `
  
Attach columns to names of Channel, so we can access each column by:  
`ch.col0` == ch.colAt(0)  

- **params:**  
`names`: The names. Have to be as length as channel's width. None of them should be Channel's property name  
`flatten`: Whether flatten the channel for the name being attached  
  
#### `cbind (self, *cols) `
  
Add columns to the channel  

- **params:**  
`cols`: The columns  

- **returns:**  
The channel with the columns inserted.  
  
#### `colAt (self, index) `
  
Fetch one column of a Channel  

- **params:**  
`index`: which column to fetch  

- **returns:**  
The Channel with that column  
  
#### `collapse (self, col) `
  
Do the reverse of expand  
length: N -> 1  
width:  M -> M  

- **params:**  
`col`:     the index of the column used to collapse  

- **returns:**  
The collapsed Channel  
  
#### `copy (self) `
  
Copy a Channel using `copy.copy`  

- **returns:**  
The copied Channel  
  
#### `create (l) [@staticmethod]`
  
Create a Channel from a list  

- **params:**  
`l`: The list, default: []  

- **returns:**  
The Channel created from the list  
  
#### `expand (self, col, pattern, t, sortby, reverse) `
  
expand the Channel according to the files in <col>, other cols will keep the same  
`[(dir1/dir2, 1)].expand (0, "*")` will expand to  
`[(dir1/dir2/file1, 1), (dir1/dir2/file2, 1), ...]`  
length: 1 -> N  
width:  M -> M  

- **params:**  
`col`:     the index of the column used to expand  
`pattern`: use a pattern to filter the files/dirs, default: `*`  
`t`:       the type of the files/dirs to include  
- 'dir', 'file', 'link' or 'any' (default)  
`sortby`:  how the list is sorted  
- 'name' (default), 'mtime', 'size'  
`reverse`: reverse sort. Default: False  

- **returns:**  
The expanded Channel  
  
#### `filter (self, func) `
  
Alias of python builtin `filter`  

- **params:**  
`func`: the function. Default: None  

- **returns:**  
The filtered Channel  
  
#### `filterCol (self, func, col) `
  
Just filter on the first column  

- **params:**  
`func`: the function  
`col`: the column to filter  

- **returns:**  
The filtered Channel  
  
#### `flatten (self, col) `
  
Convert a single-column Channel to a list (remove the tuple signs)  
`[(a,), (b,)]` to `[a, b]`  

- **params:**  
`col`: The column to flat. None for all columns (default)  

- **returns:**  
The list converted from the Channel.  
  
#### `fold (self, n) `
  
Fold a Channel. Make a row to n-length chunk rows  
```  
a1	a2	a3	a4  
b1	b2	b3	b4  
if n==2, fold(2) will change it to:  
a1	a2  
a3	a4  
b1	b2  
b3	b4  
```  

- **params:**  
`n`: the size of the chunk  

- **returns**  
The new Channel  
  
#### `fromArgv () [@staticmethod]`
  
Create a Channel from `sys.argv[1:]`  
"python test.py a b c" creates a width=1 Channel  
"python test.py a,1 b,2 c,3" creates a width=2 Channel  

- **returns:**  
The Channel created from the command line arguments  
  
#### `fromChannels (*args) [@staticmethod]`
  
Create a Channel from Channels  

- **params:**  
`args`: The Channels  

- **returns:**  
The Channel merged from other Channels  
  
#### `fromFile (fn, header, skip, delimit) [@staticmethod]`
  
Create Channel from the file content  
It's like a matrix file, each row is a row for a Channel.  
And each column is a column for a Channel.  

- **params:**  
`fn`:      the file  
`header`:  Whether the file contains header. If True, will attach the header  
- So you can use `channel.<header>` to fetch the column  
`skip`:    first lines to skip  
`delimit`: the delimit for columns  

- **returns:**  
A Channel created from the file  
  
#### `fromPairs (pattern) [@staticmethod]`
  
Create a width = 2 Channel from a pattern  

- **params:**  
`pattern`: the pattern  

- **returns:**  
The Channel create from every 2 files match the pattern  
  
#### `fromParams (*pnames) [@staticmethod]`
  
Create a Channel from params  

- **params:**  
`*pnames`: The names of the option  

- **returns:**  
The Channel  
  
#### `fromPattern (pattern, t, sortby, reverse) [@staticmethod]`
  
Create a Channel from a path pattern  

- **params:**  
`pattern`: the pattern with wild cards  
`t`:       the type of the files/dirs to include  
- 'dir', 'file', 'link' or 'any' (default)  
`sortby`:  how the list is sorted  
- 'name' (default), 'mtime', 'size'  
`reverse`: reverse sort. Default: False  

- **returns:**  
The Channel created from the path  
  
#### `get (self, idx) `
  
Get the element of a flattened channel  

- **params:**  
`idx`: The index of the element to get. Default: 0  

- **return:**  
The element  
  
#### `insert (self, cidx, *cols) `
  
Insert columns to a channel  

- **params:**  
`cidx`: Insert into which index of column?  
`cols`: the columns to be bound to Channel  

- **returns:**  
The combined Channel  
Note, self is also changed  
  
#### `length (self) `
  
Get the length of a Channel  
It's just an alias of `len(chan)`  

- **returns:**  
The length of the Channel  
  
#### `map (self, func) `
  
Alias of python builtin `map`  

- **params:**  
`func`: the function  

- **returns:**  
The transformed Channel  
  
#### `mapCol (self, func, col) `
  
Map for a column  

- **params:**  
`func`: the function  
`col`: the index of the column. Default: 0  

- **returns:**  
The transformed Channel  
  
#### `nones (length, width) [@staticmethod]`
  
Create a channel with `None`s  

- **params:**  
`length`: The length of the channel  
`width`:  The width of the channel  

- **returns:**  
The created channel  
  
#### `rbind (self, *rows) `
  
The multiple-argument versoin of `rbind`  

- **params:**  
`rows`: the rows to be bound to Channel  

- **returns:**  
The combined Channel  
Note, self is also changed  
  
#### `reduce (self, func) `
  
Alias of python builtin `reduce`  

- **params:**  
`func`: the function  

- **returns:**  
The reduced value  
  
#### `reduceCol (self, func, col) `
  
Reduce a column  

- **params:**  
`func`: the function  
`col`: the column to reduce  

- **returns:**  
The reduced value  
  
#### `repCol (self, n) `
  
Repeat column and return a new channel  

- **params:**  
`n`: how many times to repeat.  

- **returns:**  
The new channel with repeated columns  
  
#### `repRow (self, n) `
  
Repeat row and return a new channel  

- **params:**  
`n`: how many times to repeat.  

- **returns:**  
The new channel with repeated rows  
  
#### `rowAt (self, index) `
  
Fetch one row of a Channel  

- **params:**  
`index`: which row to fetch  

- **returns:**  
The Channel with that row  
  
#### `slice (self, start, length) `
  
Fetch some columns of a Channel  

- **params:**  
`start`:  from column to start  
`length`: how many columns to fetch, default: None (from start to the end)  

- **returns:**  
The Channel with fetched columns  
  
#### `split (self, flatten) `
  
Split a Channel to single-column Channels  

- **returns:**  
The list of single-column Channels  
  
#### `t (self) `
  
Transpose a channel  
  
#### `transpose (self) `
  
Transpose a channel  
  
#### `unfold (self, n) `
  
Do the reverse thing as self.fold does  

- **params:**  
`n`: How many rows to combind each time. default: 2  

- **returns:**  
The unfolded Channel  
  
#### `unique (self) `
  
Make the channel unique, remove duplicated rows  
Try to keep the order  
  
#### `width (self) `
  
Get the width of a Channel  

- **returns:**  
The width of the Channel  
  

## Module `Job`  
> Job class, defining a job in a process
	

#### `__init__ (self, index, proc) `
  
Constructor  

- **params:**  
`index`:   The index of the job in a process  
`proc`:    The process  
  
#### `_indexIndicator (self) `
  
Get the index indicator in the log  

- **returns:**  
The "[001/100]" like indicator  
  
#### `_linkInfile (self, orgfile) `
  
Create links for input files  

- **params:**  
`orgfile`: The original input file  

- **returns:**  
The link to the original file.  
  
#### `_prepInput (self) `
  
Prepare input, create link to input files and set other placeholders  
  
#### `_prepOutput (self) `
  
Build the output data.  
Output could be:  
1. list: `['output:var:{{input}}', 'outfile:file:{{infile.bn}}.txt']`  
or you can ignore the name if you don't put it in script:  
`['var:{{input}}', 'path:{{infile.bn}}.txt']`  
or even (only var type can be ignored):  
`['{{input}}', 'file:{{infile.bn}}.txt']`  
2. str : `'output:var:{{input}}, outfile:file:{{infile.bn}}.txt'`  
3. OrderedDict: `{"output:var:{{input}}": channel1, "outfile:file:{{infile.bn}}.txt": channel2}`  
or    `{"output:var:{{input}}, output:file:{{infile.bn}}.txt" : channel3}`  
for 1,2 channels will be the property channel for this proc (i.e. p.channel)  
  
#### `_prepScript (self) `
  
Build the script, interpret the placeholders  
  
#### `_reportItem (self, key, maxlen, data, loglevel) `
  
Report the item on logs  

- **params:**  
`key`: The key of the item  
`maxlen`: The max length of the key  
`data`: The data of the item  
`loglevel`: The log level  
  
#### `cache (self) `
  
Truly cache the job (by signature)  
  
#### `checkOutfiles (self, expect) `
  
Check whether output files are generated, if not, add - to rc.  
  
#### `done (self) `
  
Do some cleanup when job finished  
  
#### `export (self) `
  
Export the output files  
  
#### `init (self) `
  
Initiate a job, make directory and prepare input, output and script.  
  
#### `isExptCached (self) `
  
Prepare to use export files as cached information  
True if succeed, otherwise False  
  
#### `isTrulyCached (self) `
  
Check whether a job is truly cached (by signature)  
  
#### `pid (self, val) `
  
Get/Set the job id (pid or the id from queue system)  

- **params:**  
`val`: The id to be set  
  
#### `rc (self, val) `
  
Get/Set the return code  

- **params:**  
`val`: The return code to be set. If it is None, return the return code. Default: `None`  
If val == -1000: the return code will be negative of current one. 0 will be '-0'  

- **returns:**  
The return code if `val` is `None`  
If rcfile does not exist or is empty, return 9999, otherwise return -rc  
A negative rc (including -0) means output files not generated  
  
#### `report (self) `
  
Report the job information to logger  
  
#### `reset (self, retry) `
  
Clear the intermediate files and output files  
  
#### `showError (self, totalfailed) `
  
Show the error message if the job failed.  
  
#### `signature (self) `
  
Calculate the signature of the job based on the input/output and the script  

- **returns:**  
The signature of the job  
  
#### `succeed (self) `
  
Tell if the job is successful by return code, and output file expectations.  

- **returns:**  
True if succeed else False  
  

## Module `Jobmgr`  
> Job Manager
	

#### `__init__ (self, proc, runner) `
  
Job manager constructor  

- **params:**  
`proc`     : The process  
`runner`   : The runner class  
  
#### `_exit (self) `
  
#### `allJobsDone (self) `
  
Tell whether all jobs are done.  
No need to lock as it only runs in one process (the watcher process)  

- **returns:**  
`True` if all jobs are done else `False`  
  
#### `canSubmit (self) `
  
Tell whether we can submit jobs.  

- **returns:**  
`True` if we can, otherwise `False`  
  
#### `halt (self, halt_anyway) `
  
Halt the pipeline if needed  
  
#### `progressbar (self, jid, loglevel) `
  
#### `run (self) `
  
Start to run the jobs  
  
#### `runPool (self, rq, sq) `
  
The pool to run jobs (wait jobs to be done)  

- **params:**  
`rq`: The run queue  
`sq`: The submit queue  
  
#### `submitPool (self, sq) `
  
The pool to submit jobs  

- **params:**  
`sq`: The submit queue  
  
#### `watchPool (self, rq, sq) `
  
The watchdog, checking whether all jobs are done.  
  

## Module `Aggr`  
> The aggregation of a set of processes

	@magic methods:
		`__setattr__(self, name, value)`: Set property value of an aggregation.
		- if it's a common property, set it to all processes
		- if it is `input` set it to starting processes
		- if it is `depends` set it to the end processes
		- if it is related to `export` (startswith `ex`), set it to the end processes
		- if it is in ['starts', 'ends', 'id'], set it to the aggregation itself.
		- Otherwise a `ValueError` raised.
		- You can use `[aggr].[proc].[prop]` to set/get the properties of a processes in the aggregation.

	

#### `__init__ (self, *args, **kwargs) `
  
Constructor  

- **params:**  
`args`: the set of processes  
`depends`: Whether auto deduce depends. Default: True  
`id`: The id of the aggr. Default: None (the variable name)  
`tag`: The tag of the processes. Default: None (a unique 4-char str according to the id)  
  
#### `_select (self, key, forceList, flatten) `
  
Select processes  
```  
# self._procs = OrderedDict([  
#	('a', Proc(id = 'a')),  
#	('b', Proc(id = 'b')),  
#	('c', Proc(id = 'c')),  
#	('d', Proc(id = 'd'))  
# ])  
  
self['a'] # proc a  
self[0]   # proc a  
self[1:2] # _Proxy of (proc b, proc c)  
self[1,3] # _Proxy of (proc b, proc d)  
self['b', 'c'] # _Proxy of (proc b, proc c)  
self['b,c'] # _Proxy of (proc b, proc c)  
self[Proc(id = 'd')] # proc d  
  
#### `addEnd (self, *procs) `
  
#### `addProc (self, p, tag, where, copy) `
  
Add a process to the aggregation.  
Note that you have to adjust the dependencies after you add processes.  

- **params:**  
`p`:     The process  
`where`: Add to where: 'starts', 'ends', 'both' or None (default)  

- **returns:**  
the aggregation itself  
  
#### `addStart (self, *procs) `
  
#### `copy (self, tag, depends, id, delegates, modules) `
  
Like `proc`'s `copy` function, copy an aggregation. Each processes will be copied.  

- **params:**  
`tag`:      The new tag of all copied processes  
`depends`: Whether to copy the dependencies or not. Default: True  
- dependences for processes in starts will not be copied  
`id`:    Use a different id if you don't want to use the variant name  
`delegates`: Copy delegates? Default: `True`  
`configs`: Copy configs? Default: `True`  

- **returns:**  
The new aggregation  
  
#### `delEnd (self, *procs) `
  
#### `delStart (self, *procs) `
  
#### `delegate (self, attrs, procs) `
  
Delegate the procs to have the attributes set by:  
`aggr.args.a.b = 1`  
Instead of setting `args.a.b` of all processes, `args.a.b` of only delegated processes will be set.  
`procs` can be `starts`/`ends`, but it cannot be set with other procs, which means you can do:  
`aggr.delegate('args', 'starts')`, but not `aggr.delegate('args', ['starts', 'pXXX'])`  
  
#### `module (self, name, starts, depends, ends, starts_shared, depends_shared, ends_shared) `
  
Define a function for aggr.  
The "shared" parameters will be indicators not to remove those processes  
when the shared function is on.  

- **params:**  
`name`          : The name of the function  
`starts`        : A list of start processes.  
`depends`       : A dict of dependences of the procs  
`ends`          : A list of end processes  
`starts_shared` : A dict of functions that shares the same starts  
`depends_shared`: A dict of functions that shares the same depends  
`ends_shared`   : A dict of functions that shares the same ends  
- For example: `{<procs>: <func>}`  
  
#### `moduleFunc (self, name, on, off) `
  
#### `off (self, *names) `
  
#### `on (self, *names) `
  

## Module `flowchart.Flowchart`  
> Draw flowchart for pipelines

	@static variables:
		`THEMES`: predefined themes
	

#### `__init__ (self, fcfile, dotfile) `
  
The constructor  

- **params:**  
`fcfile`: The flowchart file. Default: `path.splitext(sys.argv[0])[0] + '.pyppl.svg'`  
`dotfile`: The dot file. Default: `path.splitext(sys.argv[0])[0] + '.pyppl.dot'`  
  
#### `_assemble (self) `
  
Assemble the graph for printing and rendering  
  
#### `addLink (self, node1, node2) `
  
Add a link to the chart  

- **params:**  
`node1`: The first node.  
`node2`: The second node.  
  
#### `addNode (self, node, role) `
  
Add a node to the chart  

- **params:**  
`node`: The node  
`role`: Is it a starting node, an ending node or None. Default: None.  
  
#### `generate (self) `
  
Generate the dot file and graph file.  
  
#### `setTheme (self, theme, base) `
  
Set the theme to be used  

- **params:**  
`theme`: The theme, could be the key of Flowchart.THEMES or a dict of a theme definition.  
`base` : The base theme to be based on you pass custom theme  
  

## Module `parameters.Parameter`  
> The class for a single parameter
	

#### `__init__ (self, name, value) `
  
Constructor  

- **params:**  
`name`:  The name of the parameter  
`value`: The initial value of the parameter  
  
#### `_forceType (self) `
  
Coerce the value to the type specified  
TypeError will be raised if error happens  
  
#### `_printName (self, prefix, keylen) `
  
Get the print name with type for the parameter  

- **params:**  
`prefix`: The prefix of the option  
  
#### `setDesc (self, d) `
  
Set the description of the parameter  

- **params:**  
`d`: The description  
  
#### `setName (self, n) `
  
Set the name of the parameter  

- **params:**  
`n`: The name  
  
#### `setRequired (self, r) `
  
Set whether this parameter is required  

- **params:**  
`r`: True if required else False. Default: True  
  
#### `setShow (self, s) `
  
Set whether this parameter should be shown in help information  

- **params:**  
`s`: True if it shows else False. Default: True  
  
#### `setType (self, t) `
  
Set the type of the parameter  

- **params:**  
`t`: The type of the value. Default: str  
- Note: str rather then 'str'  
  
#### `setValue (self, v) `
  
Set the value of the parameter  

- **params:**  
`v`: The value  
  

## Module `parameters.Parameters`  
> A set of parameters
	

#### `__init__ (self) `
  
Constructor  
  
#### `_coerceValue (value, t) [@staticmethod]`
  
#### `_getType (self, argname, argtype) `
  
#### `_parseName (self, argname) `
  
If `argname` is the name of an option  

- **params:**  
`argname`: The argname  

- **returns:**  
`an`: clean argument name  
`at`: normalized argument type  
`av`: the argument value, if `argname` is like: `-a=1`  
  
#### `_putValue (self, argname, argtype, argval) `
  
#### `_shouldPrintHelp (self, args) `
  
#### `asDict (self) `
  
Convert the parameters to Box object  

- **returns:**  
The Box object  
  
#### `help (self, error, printNexit) `
  
Calculate the help page  

- **params:**  
`error`: The error message to show before the help information. Default: `''`  
`printNexit`: Print the help page and exit the program? Default: `False` (return the help information)  

- **return:**  
The help information  
  
#### `loadDict (self, dictVar, show) `
  
Load parameters from a dict  

- **params:**  
`dictVar`: The dict variable.  
- Properties are set by "<param>.required", "<param>.show", ...  
`show`:    Whether these parameters should be shown in help information  
- Default: False (don't show parameter from config object in help page)  
- It'll be overwritten by the `show` property inside dict variable.  
- If it is None, will inherit the param's show value  
  
#### `loadFile (self, cfgfile, show) `
  
Load parameters from a json/config file  
If the file name ends with '.json', `json.load` will be used,  
otherwise, `ConfigParser` will be used.  
For config file other than json, a section name is needed, whatever it is.  

- **params:**  
`cfgfile`: The config file  
`show`:    Whether these parameters should be shown in help information  
- Default: False (don't show parameter from config file in help page)  
- It'll be overwritten by the `show` property inside the config file.  
  
#### `parse (self, args) `
  
Parse the arguments from `sys.argv`  
  

## Module `logger`  
> A customized logger for pyppl


#### `class: Box`
```
Allow dot operation for OrderedDict
```
#### `class: LoggerThemeError`
```
Theme errors for logger
```
#### `class: PyPPLLogFilter`
```
logging filter by levels (flags)
```
#### `class: PyPPLLogFormatter`
```
logging formatter for pyppl
```
#### `class: TemplatePyPPL`
```
Built-in template wrapper.
```
#### `_formatTheme (theme) [@staticmethod]`
  
Make them in the standard form with bgcolor and fgcolor in raw terminal color strings  
If the theme is read from file, try to translate "COLORS.xxx" to terminal color strings  

- **params:**  
`theme`: The theme  

- **returns:**  
The formatted colors  
  
#### `_getColorFromTheme (level, theme) [@staticmethod]`
  
Get colors from a them  

- **params:**  
`level`: Our own log record level  
`theme`: The theme  

- **returns:**  
The colors  
  
#### `_getLevel (record) [@staticmethod]`
  
Get the flags of a record  

- **params:**  
`record`:  The logging record  
  
#### `getLogger (levels, theme, logfile, lvldiff, name) [@staticmethod]`
  
Get the default logger  

- **params:**  
`levels`: The log levels(tags), default: basic  
`theme`:  The theme of the logs on terminal. Default: True (default theme will be used)  
- False to disable theme  
`logfile`:The log file. Default: None (don't white to log file)  
`lvldiff`:The diff levels for log  
- ["-depends", "jobdone", "+debug"]: show jobdone, hide depends and debug  
`name`:   The name of the logger, default: PyPPL  

- **returns:**  
The logger  
  

## Module `utils`  
> A set of utitities for PyPPL


#### `class: Box`
```
Allow dot operation for OrderedDict
```
#### `alwaysList (data) `
  
Convert a string or a list with element  

- **params:**  
`data`: the data to be converted  

- **examples:**  
```python  
data = ["a, b, c", "d"]  
ret  = alwaysList (data)  
# ret == ["a", "b", "c", "d"]  
```  

- **returns:**  
The split list  
  
#### `asStr (s, encoding) `
  
Convert everything (str, unicode, bytes) to str with python2, python3 compatiblity  
  
#### `briefList (l) `
  
Briefly show an integer list, combine the continuous numbers.  

- **params:**  
`l`: The list  

- **returns:**  
The string to show for the briefed list.  
  
#### `dictUpdate (origDict, newDict) `
  
Update a dictionary recursively.  

- **params:**  
`origDict`: The original dictionary  
`newDict`:  The new dictionary  

- **examples:**  
```python  
od1 = {"a": {"b": {"c": 1, "d":1}}}  
od2 = {key:value for key:value in od1.items()}  
nd  = {"a": {"b": {"d": 2}}}  
od1.update(nd)  
# od1 == {"a": {"b": {"d": 2}}}, od1["a"]["b"] is lost  
dictUpdate(od2, nd)  
# od2 == {"a": {"b": {"c": 1, "d": 2}}}  
```  
  
#### `filter (func, vec) `
  
Python2 and Python3 compatible filter  

- **params:**  
`func`: The filter function  
`vec`:  The list to be filtered  

- **returns:**  
The filtered list  
  
#### `formatSecs (seconds) `
  
Format a time duration  

- **params:**  
`seconds`: the time duration in seconds  

- **returns:**  
The formated string.  
For example: "01:01:01.001" stands for 1 hour 1 min 1 sec and 1 minisec.  
  
#### `funcsig (func) `
  
Get the signature of a function  
Try to get the source first, if failed, try to get its name, otherwise return None  

- **params:**  
`func`: The function  

- **returns:**  
The signature  
  
#### `map (func, vec) `
  
Python2 and Python3 compatible map  

- **params:**  
`func`: The map function  
`vec`: The list to be maped  

- **returns:**  
The maped list  
  
#### `range (i, *args, **kwargs) `
  
Convert a range to list, because in python3, range is not a list  

- **params:**  
`r`: the range data  

- **returns:**  
The converted list  
  
#### `reduce (func, vec) `
  
Python2 and Python3 compatible reduce  

- **params:**  
`func`: The reduce function  
`vec`: The list to be reduced  

- **returns:**  
The reduced value  
  
#### `split (s, delimter, trim) `
  
Split a string using a single-character delimter  

- **params:**  
`s`: the string  
`delimter`: the single-character delimter  
`trim`: whether to trim each part. Default: True  

- **examples:**  
```python  
ret = split("'a,b',c", ",")  
# ret == ["'a,b'", "c"]  
# ',' inside quotes will be recognized.  
```  

- **returns:**  
The list of substrings  
  
#### `uid (s, l, alphabet) `
  
Calculate a short uid based on a string.  
Safe enough, tested on 1000000 32-char strings, no repeated uid found.  
This is used to calcuate a uid for a process  

- **params:**  
`s`: the base string  
`l`: the length of the uid  
`alphabet`: the charset used to generate the uid  

- **returns:**  
The uid  
  
#### `varname (maxline, incldot) `
  
Get the variable name for ini  

- **params:**  
`maxline`: The max number of lines to retrive. Default: 20  
`incldot`: Whether include dot in the variable name. Default: False  

- **returns:**  
The variable name  
  

## Module `utils.box`  
> .

#### `class: Box`
```
Allow dot operation for OrderedDict
```

## Module `utils.cmd`  
> .

#### `class: Cmd`
```
A command (subprocess) wapper
```
#### `class: Timeout`
```

```
#### `run (cmd, bg, raiseExc, timeout, **kwargs) [@staticmethod]`
  
A shortcut of `Command.run`  
To chain another command, you can do:  
`run('seq 1 3', bg = True).pipe('grep 1')`  

- **params:**  
`cmd`     : The command, could be a string or a list  
`bg`      : Run in background or not. Default: `False`  
- If it is `True`, `rc` and `stdout/stderr` will be default (no value retrieved).  
`raiseExc`: raise the expcetion or not  
`**kwargs`: other arguments for `Popen`  

- **returns:**  
The `Command` instance  
  
#### `sleep (cmd, bg, raiseExc, timeout, **kwargs, **kwargs) `
sleep(seconds)  
  
Delay execution for a given number of seconds.  The argument may be  
a floating point number for subsecond precision.  
#### `time (cmd, bg, raiseExc, timeout, **kwargs, **kwargs, **kwargs) `
time() -> floating point number  
  
Return the current time in seconds since the Epoch.  
Fractions of a second may be present if the system clock provides them.  

## Module `utils.parallel`  
> .

#### `class: Parallel`
```
A parallel runner
```
#### `run (func, args, nthread, backend, raiseExc) [@staticmethod]`
  
A shortcut of `Parallel.run`  

- **params:**  
`func`    : The function to run  
`args`    : The arguments for the function, should be a `list` with `tuple`s  
`nthread` : Number of jobs to run simultaneously. Default: `1`  
`backend` : The backend, either `process` (default) or `thread`  
`raiseExc`: Whether raise exception or not. Default: `True`  

- **returns:**  
The merged results from each job.  
  

## Module `utils.safefs`  
> .

#### `class: ChmodError`
```
OS system call failed.
```
#### `Lock () [@staticmethod]`
  
Returns a non-recursive lock object  
  
#### `class: SafeFs`
```
A thread-safe file system
	
	@static variables:
		
		`TMPDIR`: The default temporary directory to store lock files

		# file types
		`FILETYPE_UNKNOWN`  : Unknown file type
		`FILETYPE_NOENT`    : File does not exist
		`FILETYPE_NOENTLINK`: A dead link (a link links to a non-existent file.
		`FILETYPE_FILE`     : A regular file
		`FILETYPE_FILELINK` : A link to a regular file
		`FILETYPE_DIR`      : A regular directory
		`FILETYPE_DIRLINK`  : A link to a regular directory

		# relation of two files
		`FILES_DIFF_BOTHNOENT` : Two files are different and none of them exists
		`FILES_DIFF_NOENT1`    : Two files are different but file1 does not exists
		`FILES_DIFF_NOENT2`    : Two files are different but file2 does not exists
		`FILES_DIFF_BOTHENT`   : Two files are different and both of them exist
		`FILES_SAME_STRNOENT`  : Two files are the same string and it does not exist
		`FILES_SAME_STRENT`    : Two files are the same string and it exists
		`FILES_SAME_BOTHLINKS` : Two files link to one file
		`FILES_SAME_BOTHLINKS1`: File1 links to file2, file2 links to a regular file
		`FILES_SAME_BOTHLINKS2`: File2 links to file1, file1 links to a regular file
		`FILES_SAME_REAL1`     : File2 links to file1, which a regular file
		`FILES_SAME_REAL2`     : File1 links to file2, which a regular file

		`LOCK`: A global lock ensures the locks are locked at the same time
```
#### `copy (file1, file2, overwrite, callback) [@staticmethod]`
  
A shortcut of `SafeFs.copy`  

- **params:**  
`file1`    : File 1  
`file2`    : File 2  
`overwrite`: Whether overwrite file 2. Default: `True`  
`callback` : The callback. arguments:  
- `r` : Whether the file exists  
- `fs`: This instance  

- **returns:**  
`True` if succeed else `False`  
  
#### `exists (filepath, callback) [@staticmethod]`
  
A shortcut of `SafeFs.exists`  

- **params:**  
`filepath`: The filepath  
`callback`: The callback. arguments:  
- `r` : Whether the file exists  
- `fs`: This instance  

- **returns:**  
`True` if the file exists else `False`  
  
#### `gz (file1, file2, overwrite, callback) [@staticmethod]`
  
A shortcut of `SafeFs.gz`  

- **params:**  
`file1`    : File 1  
`file2`    : File 2  
`overwrite`: Whether overwrite file 2. Default: `True`  
`callback` : The callback. arguments:  
- `r` : Whether the file exists  
- `fs`: This instance  

- **returns:**  
`True` if succeed else `False`  
  
#### `link (file1, file2, overwrite, callback) [@staticmethod]`
  
A shortcut of `SafeFs.link`  

- **params:**  
`file1`    : File 1  
`file2`    : File 2  
`overwrite`: Whether overwrite file 2. Default: `True`  
`callback` : The callback. arguments:  
- `r` : Whether the file exists  
- `fs`: This instance  

- **returns:**  
`True` if succeed else `False`  
  
#### `moveWithLink (file1, file2, overwrite, callback) [@staticmethod]`
  
A shortcut of `SafeFs.moveWithLink`  

- **params:**  
`file1`    : File 1  
`file2`    : File 2  
`overwrite`: Whether overwrite file 2. Default: `True`  
`callback` : The callback. arguments:  
- `r` : Whether the file exists  
- `fs`: This instance  

- **returns:**  
`True` if succeed else `False`  
  
#### `osremove (file1, file2, overwrite, callback) `
remove(path)  
  
Remove a file (same as unlink(path)).  
#### `readlink (file1, file2, overwrite, callback) `
readlink(path) -> path  
  
Return a string representing the path to which the symbolic link points.  
#### `shmove (src, dst) [@staticmethod]`
Recursively move a file or directory to another location. This is  
similar to the Unix "mv" command.  
  
If the destination is a directory or a symlink to a directory, the source  
is moved inside the directory. The destination path must not already  
exist.  
  
If the destination already exists but is not a directory, it may be  
overwritten depending on os.rename() semantics.  
  
If the destination is on our current filesystem, then rename() is used.  
Otherwise, src is copied to the destination and then removed.  
A lot more could be done here...  A look at a mv.c shows a lot of  
the issues this implementation glosses over.  
  
  
#### `ungz (file1, file2, overwrite, callback) [@staticmethod]`
  
A shortcut of `SafeFs.ungz`  

- **params:**  
`file1`    : File 1  
`file2`    : File 2  
`overwrite`: Whether overwrite file 2. Default: `True`  
`callback` : The callback. arguments:  
- `r` : Whether the file exists  
- `fs`: This instance  

- **returns:**  
`True` if succeed else `False`  
  

## Module `proctree.ProcNode`  
> The node for processes to manage relations between each other
	

#### `__init__ (self, proc) `
  
Constructor  

- **params:**  
`proc`: The `Proc` instance  
  
#### `sameIdTag (self, proc) `
  
Check if the process has the same id and tag with me.  

- **params:**  
`proc`: The `Proc` instance  

- **returns:**  
`True` if it is.  
`False` if not.  
  

## Module `proctree.ProcTree`  
> .

#### `__init__ (self) `
  
Constructor, set the status of all `ProcNode`s  
  
#### `check (proc) [@staticmethod]`
  
Check whether a process with the same id and tag exists  

- **params:**  
`proc`: The `Proc` instance  
  
#### `checkPath (self, proc) `
  
Check whether paths of a process can start from a start process  

- **params:**  
`proc`: The process  

- **returns:**  
`True` if all paths can pass  
The failed path otherwise  
  
#### `getAllPaths (self) `
  
#### `getEnds (self) `
  
Get the end processes  

- **returns:**  
The end processes  
  
#### `getNext (proc) [@staticmethod]`
  
Get next processes of process  

- **params:**  
`proc`: The `Proc` instance  

- **returns:**  
The processes depend on this process  
  
#### `getNextStr (proc) [@staticmethod]`
  
Get the names of processes depend on a process  

- **params:**  
`proc`: The `Proc` instance  

- **returns:**  
The names  
  
#### `getNextToRun (self) `
  
Get the process to run next  

- **returns:**  
The process next to run  
  
#### `getPaths (self, proc, proc0) `
  
Infer the path to a process  

- **params:**  
`proc`: The process  
`proc0`: The original process, because this function runs recursively.  

- **returns:**  
```  
p1 -> p2 -> p3  
p4  _/  
Paths for p3: [[p4], [p2, p1]]  
```  
  
#### `getPathsToStarts (self, proc) `
  
Filter the paths with start processes  

- **params:**  
`proc`: The process  

- **returns:**  
The filtered path  
  
#### `getPrevStr (proc) [@staticmethod]`
  
Get the names of processes a process depends on  

- **params:**  
`proc`: The `Proc` instance  

- **returns:**  
The names  
  
#### `getStarts (self) `
  
Get the start processes  

- **returns:**  
The start processes  
  
#### `register (proc) [@staticmethod]`
  
Register the process  

- **params:**  
`proc`: The `Proc` instance  
  
#### `reset () [@staticmethod]`
  
Reset the status of all `ProcNode`s  
  
#### `setStarts (self, starts) `
  
Set the start processes  

- **params:**  
`starts`: The start processes  
  
#### `unranProcs (self) `
  

## Module `templates.TemplatePyPPL`  
> Built-in template wrapper.
	

#### `__init__ (self, source, **envs) `
  
Initiate the engine with source and envs  

- **params:**  
`source`: The souce text  
`envs`: The env data  
  
#### `_render (self, data) `
  
Render the template  

- **params:**  
`data`: The data used for rendering  

- **returns:**  
The rendered string  
  

## Module `templates.TemplateJinja2`  
> Jinja2 template wrapper
	

#### `__init__ (self, source, **envs) `
  
Initiate the engine with source and envs  

- **params:**  
`source`: The souce text  
`envs`: The env data  
  
#### `_render (self, data) `
  
Render the template  

- **params:**  
`data`: The data used for rendering  

- **returns:**  
The rendered string  
  

## Module `runners.Runner`  
> The base runner class
	

#### `__init__ (self, job) `
  
Constructor  

- **params:**  
`job`:    The job object  
  
#### `_flush (self, fout, ferr, lastout, lasterr, end) `
  
Flush stdout/stderr  

- **params:**  
`fout`: The stdout file handler  
`ferr`: The stderr file handler  
`lastout`: The leftovers of previously readlines of stdout  
`lasterr`: The leftovers of previously readlines of stderr  
`end`: Whether this is the last time to flush  
  
#### `finish (self) `
  
#### `getpid (self) `
  
Get the job id  
  
#### `isRunning (self) `
  
Try to tell whether the job is still running.  

- **returns:**  
`True` if yes, otherwise `False`  
  
#### `kill (self) `
  
Try to kill the running jobs if I am exiting  
  
#### `retry (self) `
  
#### `run (self) `
  

- **returns:**  
True: success/fail  
False: needs retry  
  
#### `submit (self) `
  
Try to submit the job  
  

## Module `runners.RunnerLocal`  
> Constructor
	@params:
		`job`:    The job object
		`config`: The properties of the process
	

#### `__init__ (self, job) `
  

## Module `runners.RunnerSsh`  
> The ssh runner

	@static variables:
		`SERVERID`: The incremental number used to calculate which server should be used.
		- Don't touch unless you know what's going on!

	

#### `__init__ (self, job) `
  
Constructor  

- **params:**  
`job`:    The job object  
  
#### `isServerAlive (server, key) [@staticmethod]`
  

## Module `runners.RunnerSge`  
> The sge runner
	

#### `__init__ (self, job) `
  
Constructor  

- **params:**  
`job`:    The job object  
`config`: The properties of the process  
  

## Module `runners.RunnerSlurm`  
> The slurm runner
	

#### `__init__ (self, job) `
  
Constructor  

- **params:**  
`job`:    The job object  
`config`: The properties of the process  
  

## Module `runners.RunnerDry`  
> The dry runner
	

#### `__init__ (self, job) `
  
Constructor  

- **params:**  
`job`:    The job object  
  
#### `finish (self) `
  
Do some cleanup work when jobs finish  
  
