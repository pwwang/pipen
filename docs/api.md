
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
  
#### `_getProfile (self, profile) `
  
Get running profile according to profile name  

- **params:**  
`profile`: The profile name  

- **returns:**  
The running configuration  
  
#### `_registerProc (proc) [@staticmethod]`
  
Register the process  

- **params:**  
`proc`: The process  
  
#### `_resume (self, *args, **kwargs) `
  
Mark processes as to be resumed  

- **params:**  
`args`: the processes to be marked. The last element is the mark for processes to be skipped.  
  
#### `flowchart (self, dotfile, fcfile, dot) `
  
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
`profile`: the profile used to run, if not found, it'll be used as runner name. default: 'local'  

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
	

#### `__init__ (self, tag, desc, id) `
  
Constructor  

- **params:**  
`tag`:  The tag of the process  
`desc`: The description of the process  
`id`:   The identify of the process  

- **config:**  
id, input, output, ppldir, forks, cache, cclean, rc, echo, runner, script, depends, tag, desc  
exdir, exhow, exow, errhow, errntry, lang, beforeCmd, afterCmd, workdir, args, aggr  
callfront, callback, brings, expect, expart, template, tplenvs, resume, nthread  

- **props**  
input, output, rc, echo, script, depends, beforeCmd, afterCmd, workdir, brings, expect  
expart, template, channel, jobs, ncjobids, size, sets, procvars, suffix, logs  
  
#### `_buildBrings (self) `
  
Build the bring-file templates waiting to be rendered.  
  
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
and also print some out.  
  
#### `_buildProps (self) `
  
Compute some properties  
  
#### `_buildScript (self) `
  
Build the script template waiting to be rendered.  
  
#### `_checkCached (self) `
  
Tell whether the jobs are cached  

- **returns:**  
True if all jobs are cached, otherwise False  
  
#### `_readConfig (self, config) `
  
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

- **returns:**  
The uniq id of the process  
  
#### `_tidyAfterRun (self) `
  
Do some cleaning after running jobs  
  
#### `_tidyBeforeRun (self) `
  
Do some preparation before running jobs  
  
#### `copy (self, tag, newid, desc) `
  
Copy a process  

- **params:**  
`newid`: The new id of the process, default: `None` (use the varname)  
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
  
#### `run (self, config) `
  
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
  
#### `attach (self, *names) `
  
Attach columns to names of Channel, so we can access each column by:  
`ch.col0` == ch.colAt(0)  

- **params:**  
`names`: The names. Have to be as length as channel's width. None of them should be Channel's property name  
  
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
  
#### `unfold (self, n) `
  
Do the reverse thing as self.fold does  

- **params:**  
`n`: How many rows to combind each time. default: 2  

- **returns:**  
The unfolded Channel  
  
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
  
#### `_linkInfile (self, orgfile) `
  
Create links for input files  

- **params:**  
`orgfile`: The original input file  

- **returns:**  
The link to the original file.  
  
#### `_prepBrings (self) `
  
Build the brings to bring some files to indir  
The brings can be set as: `p.brings = {"infile": "{{infile.bn}}*.bai"}`  
If you have multiple files to bring in:  
`p.brings = {"infile": "{{infile.bn}}*.bai", "infile#": "{{infile.bn}}*.fai"}`  
You can use wildcards to search the files, but only the first file will return  
To access the brings in your script: {% raw %}`{{ brings.infile }}`, `{{ brings.infile# }}`{% endraw %}  
If original input file is a link, will try to find it along each directory the link is in.  
  
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
  
Initiate a job, make directory and prepare input, brings, output and script.  
  
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
  
#### `showError (self, lenfailed) `
  
Show the error message if the job failed.  
  
#### `signature (self) `
  
Calculate the signature of the job based on the input/output and the script  

- **returns:**  
The signature of the job  
  
#### `succeed (self) `
  
Tell if the job is successful by return code, and output file expectations.  

- **returns:**  
True if succeed else False  
  

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
  
#### `addProc (self, p, tag, where, copy) `
  
Add a process to the aggregation.  
Note that you have to adjust the dependencies after you add processes.  

- **params:**  
`p`:     The process  
`where`: Add to where: 'starts', 'ends', 'both' or None (default)  

- **returns:**  
the aggregation itself  
  
#### `copy (self, tag, deps, newid) `
  
Like `proc`'s `copy` function, copy an aggregation. Each processes will be copied.  

- **params:**  
`tag`:      The new tag of all copied processes  
`deps`: Whether to copy the dependencies or not. Default: True  
- dependences for processes in starts will not be copied  
`newid`:    Use a different id if you don't want to use the variant name  

- **returns:**  
The new aggregation  
  
#### `delegate (self, attr, procs, pattr) `
  
Delegate attributes of processes to aggr.  

- **params**  
`attr` : The attribute of the aggregation  
`procs`: The ids of the processes. Default: None (all processes)  
`pattr`: The attr of the processes. Default: None (same as `attr`)  
  

## Module `Flowchart`  
> Draw flowchart for pipelines

	@static variables:
		`THEMES`: predefined themes
	

#### `__init__ (self, fcfile, dotfile, dot) `
  
The constructor  

- **params:**  
`fcfile`: The flowchart file. Default: `path.splitext(sys.argv[0])[0] + '.pyppl.svg'`  
`dotfile`: The dot file. Default: `path.splitext(sys.argv[0])[0] + '.pyppl.dot'`  
`dot`: The dot command. Default: `'dot -Tsvg {{dotfile}} -o {{fcfile}}'`  
  
#### `_dotgroups (self) `
  
Convert groups to dot language.  

- **returns:**  
The string in dot language for all groups.  
  
#### `_dotlinks (self) `
  
Convert links to dot language.  

- **returns:**  
The string in dot language for all links.  
  
#### `_dotnodes (self) `
  
Convert nodes to dot language.  

- **returns:**  
The string in dot language for all nodes.  
  
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
  
Generate the flowchart.  
  
#### `setTheme (self, theme) `
  
Set the theme to be used  

- **params:**  
`theme`: The theme, could be the key of Flowchart.THEMES or a dict of a theme definition.  
  

## Module `Parameter`  
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
  

## Module `Parameters`  
> A set of parameters
	

#### `__init__ (self) `
  
Constructor  
  
#### `desc (self, d) `
  
Set the description of the program  

- **params:**  
`d`: The description  
  
#### `example (self, e) `
  
Set the examples of the program  

- **params:**  
`e`: The examples. Multiple examples in multiple lines  
  
#### `help (self) `
  
Calculate the help page  

- **return:**  
The help information  
  
#### `helpOpts (self, h) `
  
The options to popup help information  
An empty string '' implys help information pops up when no arguments specified  

- **params:**  
`h`: The options. It could be either list or comma separated.  
  
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
  
#### `parse (self) `
  
Parse the arguments from `sys.argv`  
  
#### `prefix (self, p) `
  
Set the prefix of options  

- **params:**  
`p`: The prefix. No default, but typically '--param-'  
  
#### `toDict (self) `
  
Convert the parameters to Box object  

- **returns:**  
The Box object  
  
#### `usage (self, u) `
  
Set the usage of the program. Otherwise it'll be automatically calculated.  

- **params**  
`u`: The usage, no program name needed. Multiple usages in multiple lines.  
  

## Module `logger`  
> A customized logger for pyppl


#### `_formatTheme (theme) [@staticmethod]`
  
Make them in the standard form with bgcolor and fgcolor in raw terminal color strings  
If the theme is read from file, try to translate "colors.xxx" to terminal color strings  

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
  
#### `class: pFilter`
```
logging filter by levels (flags)
```
#### `class: pFormatter`
```
logging formatter for pyppl
```

## Module `utils`  
> A set of utitities for PyPPL


#### `JoinableQueue (maxsize) `
  
Returns a queue object  
  
#### `class: Thread`
```
A class that represents a thread of control.

    This class can be safely subclassed in a limited fashion.
```
#### `_fileExists (f, callback) `
  
Tell whether a path exists  

- **params:**  
`f`: the path  
`callback`: the callback  

- **returns:**  
True if yes, otherwise False  
If any of the path does not exist, return False  
  
#### `_lockfile (f) `
  
Get the path of lockfile of a file  

- **params:**  
`f`: The file  

- **returns:**  
The path of the lock file  
  
#### `_safeCopy (src, dst, overwrite) `
  
Copy a file/dir  

- **params:**  
`src`: The source file  
`dst`: The destination  
`overwrite`: Whether overwrite the destination  

- **return:**  
True if succeed else False  
  
#### `_safeLink (src, dst, overwrite) `
  
Symlink a file/dir  

- **params:**  
`src`: The source file  
`dst`: The destination  
`overwrite`: Whether overwrite the destination  

- **return:**  
True if succeed else False  
  
#### `_safeMove (src, dst, overwrite) `
  
Move a file/dir  

- **params:**  
`src`: The source file  
`dst`: The destination  
`overwrite`: Whether overwrite the destination  

- **return:**  
True if succeed else False  
  
#### `_safeMoveWithLink (src, dst, overwrite) `
  
Move a file/dir and leave a link the source file  

- **params:**  
`src`: The source file  
`dst`: The destination  
`overwrite`: Whether overwrite the destination  

- **return:**  
True if succeed else False  
  
#### `_samefile (f1, f2, callback) `
  
Tell whether two paths pointing to the same file  

- **params:**  
`f1`: the first path  
`f2`: the second path  
`callback`: the callback  

- **returns:**  
True if yes, otherwise False  
If any of the path does not exist, return False  
  
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
  
#### `briefList (l) `
  
Briefly show an integer list, combine the continuous numbers.  

- **params:**  
`l`: The list  

- **returns:**  
The string to show for the briefed list.  
  
#### `chmodX (thefile) `
  
Convert script file to executable or add extract shebang to cmd line  

- **params:**  
`thefile`: the script file  

- **returns:**  
A list with or without the path of the interpreter as the first element and the script file as the last element  
  
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
  
#### `dirmtime (d) `
  
Calculate the mtime for a directory.  
Should be the max mtime of all files in it.  

- **params:**  
`d`:  the directory  

- **returns:**  
The mtime.  
  
#### `dumbPopen (cmd, shell) `
  
A dumb Popen (no stdout and stderr)  

- **params:**  
`cmd`: The command for `Popen`  
`shell`: The shell argument for `Popen`  

- **returns:**  
The process object  
  
#### `fileExists (f, callback) `
  
Tell whether a path exists under a lock  

- **params:**  
`f`: the path  
`callback`: the callback  

- **returns:**  
True if yes, otherwise False  
If any of the path does not exist, return False  
  
#### `filesig (fn) `
  
Calculate a signature for a file according to its path and mtime  

- **params:**  
`fn`: the file  

- **returns:**  
The md5 deigested signature.  
  
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
  
#### `gz (srcfile, gzfile, overwrite) `
  
Do a "gzip"-like for a file  

- **params:**  
`gzfile`:  the final .gz file  
`srcfile`: the source file  
  
#### `map (func, vec) `
  
Python2 and Python3 compatible map  

- **params:**  
`func`: The map function  
`vec`: The list to be maped  

- **returns:**  
The maped list  
  
#### `parallel (func, args, nthread, method) `
  
Call functions in a parallel way.  
If nthread == 1, will be running in single-threading manner.  

- **params:**  
`func`: The function  
`args`: The arguments, in list. Each element should be the arguments for the function in one thread.  
`nthread`: Number of threads  
`method`: use multithreading (thread) or multiprocessing (process)  
  
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
  
#### `safeCopy (src, dst, overwrite) `
  
Copy a file/dir with locks  

- **params:**  
`src`: The source file  
`dst`: The destination  
`overwrite`: Whether overwrite the destination  

- **return:**  
True if succeed else False  
  
#### `safeLink (src, dst, overwrite) `
  
Symlink a file/dir with locks  

- **params:**  
`src`: The source file  
`dst`: The destination  
`overwrite`: Whether overwrite the destination  

- **return:**  
True if succeed else False  
  
#### `safeMove (src, dst, overwrite) `
  
Move a file/dir with locks  

- **params:**  
`src`: The source file  
`dst`: The destination  
`overwrite`: Whether overwrite the destination  

- **return:**  
True if succeed else False  
  
#### `safeMoveWithLink (src, dst, overwrite) `
  
Move a file/dir and leave a link the source file with locks  

- **params:**  
`src`: The source file  
`dst`: The destination  
`overwrite`: Whether overwrite the destination  

- **return:**  
True if succeed else False  
  
#### `safeRemove (f) `
  
Safely remove a file/dir.  

- **params:**  
`f`: the file or dir.  
  
#### `samefile (f1, f2, callback) `
  
Tell whether two paths pointing to the same file under locks  

- **params:**  
`f1`: the first path  
`f2`: the second path  
`callback`: the callback  

- **returns:**  
True if yes, otherwise False  
If any of the path does not exist, return False  
  
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
  
#### `targz (srcdir, tgzfile, overwrite) `
  
Do a "tar zcf"-like for a directory  

- **params:**  
`tgzfile`: the final .tgz file  
`srcdir`:  the source directory  
  
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
  
#### `ungz (gzfile, dstfile, overwrite) `
  
Do a "gunzip"-like for a .gz file  

- **params:**  
`gzfile`:  the .gz file  
`dstfile`: the extracted file  
  
#### `untargz (tgzfile, dstdir, overwrite) `
  
Do a "tar zxf"-like for .tgz file  

- **params:**  
`tgzfile`:  the .tgz file  
`dstdir`: which directory to extract the file to  
  
#### `varname (maxline, incldot) `
  
Get the variable name for ini  

- **params:**  
`maxline`: The max number of lines to retrive. Default: 20  
`incldot`: Whether include dot in the variable name. Default: False  

- **returns:**  
The variable name  
  

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
  
#### `getAllPaths (self, withStarts) `
  
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
  
#### `getNode (proc) [@staticmethod]`
  
Get the `ProcNode` instance by `Proc` instance  

- **params:**  
`proc`: The `Proc` instance  

- **returns:**  
The `ProcNode` instance  
  
#### `getPaths (self, proc, proc0) `
  
Infer the path to a process  

- **params:**  
`proc`: The process  
`proc0`: The original process  

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
  
#### `_flushOut (self, fout, ferr, lastout, lasterr, end) `
  
Flush stdout/stderr  

- **params:**  
`fout`: The stdout file handler  
`ferr`: The stderr file handler  
`lastout`: The leftovers of previously readlines of stdout  
`lasterr`: The leftovers of previously readlines of stderr  
  
#### `finish (self) `
  
Do some cleanup work when jobs finish  
  
#### `getpid (self) `
  
Get the job id  
  
#### `isRunning (self) `
  
Try to tell whether the job is still running.  

- **returns:**  
`True` if yes, otherwise `False`  
  
#### `retry (self) `
  
Retry to submit and run the job if failed  
  
#### `submit (self) `
  
Try to submit the job use Popen  
  
#### `wait (self, rc, infout, inferr) `
  
Wait for the job to finish  

- **params:**  
`rc`: Whether to write return code in rcfile  
`infout`: The file handler for stdout file  
`inferr`: The file handler for stderr file  
- If infout or inferr is None, will open the file and close it before function returns.  
  

## Module `runners.RunnerQueue`  
> The base queue runner class

	@static variables:
		`maxsubmit`: Maximum jobs submitted at one time. Default cpu_count()/2
		`interval` :  The interval to submit next batch of jobs. Default 30
	

#### `__init__ (self, job) `
  
Constructor  

- **params:**  
`job`:    The job object  
  
#### `wait (self) `
  
Wait for the job to finish  
  

## Module `runners.RunnerLocal`  
> The local runner
	


## Module `runners.RunnerSsh`  
> The ssh runner

	@static variables:
		`serverid`: The incremental number used to calculate which server should be used.
		- Don't touch unless you know what's going on!

	

#### `__init__ (self, job) `
  
Constructor  

- **params:**  
`job`:    The job object  
  

## Module `runners.RunnerSge`  
> The sge runner
	

#### `__init__ (self, job) `
  
Constructor  

- **params:**  
`job`:    The job object  
`config`: The properties of the process  
  
#### `getpid (self) `
  
Get the job identity and save it to job.pidfile  
  
#### `isRunning (self) `
  
Tell whether the job is still running  

- **returns:**  
True if it is running else False  
  

## Module `runners.RunnerSlurm`  
> The slurm runner
	

#### `__init__ (self, job) `
  
Constructor  

- **params:**  
`job`:    The job object  
`config`: The properties of the process  
  
#### `getpid (self) `
  
Get the job identity and save it to job.pidfile  
  
#### `isRunning (self) `
  
Tell whether the job is still running  

- **returns:**  
True if it is running else False  
  

## Module `runners.RunnerDry`  
> The dry runner
	

#### `__init__ (self, job) `
  
Constructor  

- **params:**  
`job`:    The job object  
  
#### `finish (self) `
  
Do some cleanup work when jobs finish  
  
