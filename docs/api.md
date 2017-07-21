
# API
<!-- toc -->

## Module `pyppl`  
> The pyppl class
	
	@static variables:
		`tips`: The tips for users
	

#### `__init__ (self, config, cfile) `
  
Constructor  

- **params:**  
`config`: the configurations for the pipeline, default: {}  
`cfile`:  the configuration file for the pipeline, default: `~/.pyppl.json`  
  
#### `flowchart (self, dotfile, fcfile, dot) `
  
Generate graph in dot language and visualize it.  

- **params:**  
`dotfile`: Where to same the dot graph. Default: `None` (`os.path.splitext(sys.argv[0])[0] + ".pyppl.dot"`)  
`fcfile`:  The flowchart file. Default: `None` (`os.path.splitext(sys.argv[0])[0] + ".pyppl.svg"`)  
- For example: run `python pipeline.py` will save it to `pipeline.pyppl.svg`  
`dot`:     The dot visulizer. Default: "dot -Tsvg {{dotfile}} > {{fcfile}}"  

- **returns:**  
The pipeline object itself.  
  
#### `run (self, profile) `
  
Run the pipeline  

- **params:**  
`profile`: the profile used to run, if not found, it'll be used as runner name. default: 'local'  

- **returns:**  
The pipeline object itself.  
  
#### `starts (self, *arg) `
  
Set the starting processes of the pipeline  

- **params:**  
`args`: the starting processes  

- **returns:**  
The pipeline object itself.  
  

## Module `channel`  
> The channen class, extended from `list`
	

#### `_cbindOne (self, col) `
  
Like R's cbind, do a column bind to a channel  

- **params:**  
`col`: the column to be bound to channel  

- **returns:**  
The combined channel  
Note, self is also changed  
  
#### `_rbindOne (self, row) `
  
Like R's rbind, do a row bind to a channel  

- **params:**  
`row`: the row to be bound to channel  

- **returns:**  
The combined channel  
Note, self is also changed  
  
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
  
#### `cbind (self, *cols) `
  
The multiple-argument versoin of `cbind`  

- **params:**  
`cols`: the columns to be bound to channel  

- **returns:**  
The combined channel  
Note, self is also changed  
  
#### `colAt (self, index) `
  
Fetch one column of a channel  

- **params:**  
`index`: which column to fetch  

- **returns:**  
The channel with that column  
  
#### `collapse (self, col) `
  
Do the reverse of expand  
length: N -> 1  
width:  M -> M  

- **params:**  
`col`:     the index of the column used to collapse  

- **returns:**  
The collapsed channel  
Note, self is also changed  
  
#### `copy (self) `
  
Copy a channel using `copy.copy`  

- **returns:**  
The copied channel  
  
#### `create (l) [@staticmethod]`
  
Create a channel from a list  

- **params:**  
`l`: The list, default: []  

- **returns:**  
The channel created from the list  
  
#### `expand (self, col, pattern) `
  
expand the channel according to the files in <col>, other cols will keep the same  
`[(dir1/dir2, 1)].expand (0, "*")` will expand to  
`[(dir1/dir2/file1, 1), (dir1/dir2/file2, 1), ...]`  
length: 1 -> N  
width:  M -> M  

- **params:**  
`col`:     the index of the column used to expand  
`pattern`: use a pattern to filter the files/dirs, default: `*`  

- **returns:**  
The expanded channel  
Note, self is also changed  
  
#### `filter (self, func) `
  
Alias of python builtin `filter`  

- **params:**  
`func`: the function  

- **returns:**  
The transformed channel  
  
#### `fold (self, n) `
  
Fold a channel. Make a row to n-length chunk rows  
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
The new channel  
  
#### `fromArgv () [@staticmethod]`
  
Create a channel from `sys.argv[1:]`  
"python test.py a b c" creates a width=1 channel  
"python test.py a,1 b,2 c,3" creates a width=2 channel  

- **returns:**  
The channel created from the command line arguments  
  
#### `fromChannels (*args) [@staticmethod]`
  
Create a channel from channels  

- **params:**  
`args`: The channels  

- **returns:**  
The channel merged from other channels  
  
#### `fromFile (fn, delimit) [@staticmethod]`
  
Create channel from the file content  
It's like a matrix file, each row is a row for a channel.  
And each column is a column for a channel.  

- **params:**  
`fn`:      the file  
`delimit`: the delimit for columns  

- **returns:**  
A channel created from the file  
  
#### `fromPairs (pattern) [@staticmethod]`
  
Create a width = 2 channel from a pattern  

- **params:**  
`pattern`: the pattern  

- **returns:**  
The channel create from every 2 files match the pattern  
  
#### `fromPath (pattern, t) [@staticmethod]`
  
Create a channel from a path pattern  

- **params:**  
`pattern`: the pattern with wild cards  
`t`:       the type of the files/dirs to include  

- **returns:**  
The channel created from the path  
  
#### `insert (self, index, col) `
  
Insert a column to a channel  

- **params:**  
`index`:  at which position to insert  
`col`:    The column to be inserted  

- **returns:**  
The channel with the column inserted  
Note, self is also changed  
  
#### `length (self) `
  
Get the length of a channel  
It's just an alias of `len(chan)`  

- **returns:**  
The length of the channel  
  
#### `map (self, func) `
  
Alias of python builtin `map`  

- **params:**  
`func`: the function  

- **returns:**  
The transformed channel  
  
#### `merge (self, *chans) `
  
Also do column bind, but with channels, and also you can have multiple with channels as arguments  

- **params:**  
`chans`: the channels to be bound to channel  

- **returns:**  
The combined channel  
Note, self is also changed  
  
#### `rbind (self, *rows) `
  
The multiple-argument versoin of `rbind`  

- **params:**  
`rows`: the rows to be bound to channel  

- **returns:**  
The combined channel  
Note, self is also changed  
  
#### `reduce (self, func) `
  
Alias of python builtin `reduce`  

- **params:**  
`func`: the function  

- **returns:**  
The transformed channel  
  
#### `slice (self, start, length) `
  
Fetch some columns of a channel  

- **params:**  
`start`:  from column to start  
`length`: how many columns to fetch, default: None (from start to the end)  

- **returns:**  
The channel with fetched columns  
  
#### `split (self) `
  
Split a channel to single-column channels  

- **returns:**  
The list of single-column channels  
  
#### `toList (self) `
  
Convert a single-column channel to a list (remove the tuple signs)  
`[(a,), (b,)]` to `[a, b]`, only applicable when width=1  

- **returns:**  
The list converted from the channel.  
  
#### `unfold (self, n) `
  
Do the reverse thing as self.fold does  

- **params:**  
`n`: How many rows to combind each time. default: 2  

- **returns:**  
The unfolded channel  
  
#### `width (self) `
  
Get the width of a channel  

- **returns:**  
The width of the channel  
  

## Module `job`  
> Job class, defining a job in a process

	@static variables:
		`FAILED_RC`: Jobs failed to submit, no return code available
		`EMPTY_RC`:  Rc file not generated, not is empty
		`NOOUT_RC`:  Outfile not generated
		`RC_MSGS`:   The messages when job failed
	

#### `__init__ (self, index, proc) `
  
Constructor  

- **params:**  
`index`:   The index of the job in a process  
`proc`:    The process  
  
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
3. dict: `{"output:var:{{input}}": channel1, "outfile:file:{{infile.bn}}.txt": channel2}`  
or    `{"output:var:{{input}}, output:file:{{infile.bn}}.txt" : channel3}`  
for 1,2 channels will be the property channel for this proc (i.e. p.channel)  
  
#### `_prepScript (self) `
  
Build the script, interpret the placeholders  
  
#### `cache (self) `
  
Truly cache the job (by signature)  
  
#### `checkOutfiles (self) `
  
Check whether output files are generated, if not, add - to rc.  
  
#### `done (self) `
  
Do some cleanup when job finished  
  
#### `export (self) `
  
Export the output files  
  
#### `id (self, val) `
  
Get/Set the job id (pid or the id from queue system)  

- **params:**  
`val`: The id to be set  
  
#### `init (self) `
  
Initiate a job, make directory and prepare input, brings, output and script.  
  
#### `isExptCached (self) `
  
Prepare to use export files as cached information  
True if succeed, otherwise False  
  
#### `isTrulyCached (self) `
  
Check whether a job is truly cached (by signature)  
  
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
  
#### `reset (self) `
  
Clear the intermediate files and output files  
  
#### `showError (self, lenfailed) `
  
Show the error message if the job failed.  
  
#### `signature (self) `
  
Calculate the signature of the job based on the input/output and the script  

- **returns:**  
The signature of the job  
  
#### `succeed (self) `
  
Tell if the job is successful by return code  
  

## Module `proc`  
> The proc class defining a process
	
	@static variables:
		`RUNNERS`:       The regiested runners
		`PROCS`:         The "<id>.<tag>" initialized processes, used to detected whether there are two processes with the same id and tag.
		`ALIAS`:         The alias for the properties
		`LOG_NLINE`:     The limit of lines of logging information of same type of messages
		
	@magic methods:
		`__getattr__(self, name)`: get the value of a property in `self.props`
		`__setattr__(self, name, value)`: set the value of a property in `self.config`
	

#### `__init__ (self, tag, desc, id) `
  
Constructor  

- **params:**  
`tag`: The tag of the process  
  
#### `_buildInput (self) `
  
Build the input data  
Input could be:  
1. list: ['input', 'infile:file'] <=> ['input:var', 'infile:path']  
2. str : "input, infile:file" <=> input:var, infile:path  
3. dict: {"input": channel1, "infile:file": channel2}  
or    {"input:var, input:file" : channel3}  
for 1,2 channels will be the combined channel from dependents, if there is not dependents, it will be sys.argv[1:]  
  
#### `_buildJobs (self) `
  
#### `_buildProcVars (self) `
  
also add proc.props, mostly scalar values  
  
#### `_buildProps (self) `
  
Compute some properties  
  
#### `_checkCached (self) `
  
Tell whether the jobs are cached  

- **returns:**  
True if all jobs are cached, otherwise False  
  
#### `_name (self, incAggr) `
  
Get my name include `aggr`, `id`, `tag`  

- **returns:**  
the name  
  
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
  
#### `_suffix (self) `
  
Calcuate a uid for the process according to the configuration  

- **returns:**  
The uid  
  
#### `_tidyAfterRun (self) `
  
Do some cleaning after running jobs  
  
#### `_tidyBeforeRun (self) `
  
Do some preparation before running jobs  
  
#### `copy (self, tag, newid) `
  
Copy a process  

- **params:**  
`newid`: The new id of the process, default: `None` (use the varname)  
`tag`:   The tag of the new process, default: `None` (used the old one)  

- **returns:**  
The new process  
  
#### `log (self, msg, level, flag, key) `
  
The log function with aggregation name, process id and tag integrated.  

- **params:**  
`msg`:   The message to log  
`level`: The log level  
`flag`:  The flag  
`key`:   The type of messages  
  
#### `registerRunner (runner) [@staticmethod]`
  
Register a runner  

- **params:**  
`runner`: The runner to be registered.  
  
#### `run (self, config) `
  
Run the jobs with a configuration  

- **params:**  
`config`: The configuration  
  

## Module `utils`  
> A set of utitities for pyppl


#### `class: PyPPLLogFormatter`
```
logging formatter for pyppl
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
  
#### `class: basestring`
```
Type basestring cannot be instantiated; it is the base for str and unicode.
```
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
  
#### `filesig (fn) `
  
Calculate a signature for a file according to its path and mtime  

- **params:**  
`fn`: the file  

- **returns:**  
The md5 deigested signature.  
  
#### `format (tpl, args) `
  
Format a string with placeholders  

- **params:**  
`tpl`:  The string with placeholders  
`args`: The data for the placeholders  

- **returns:**  
The formatted string  
  
#### `formatTime (seconds) `
  
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
  
#### `getLogger (level, name, colored, logfile) `
  
Get the default logger  

- **params:**  
`level`: The log level, default: info  
`name`:  The name of the logger, default: PyPPL  

- **returns:**  
The logger  
  
#### `gz (gzfile, srcfile) `
  
Do a "gzip"-like for a file  

- **params:**  
`gzfile`:  the final .gz file  
`srcfile`: the source file  
  
#### `isSamefile (f1, f2) `
  
Tell whether two paths pointing to the same file  

- **params:**  
`f1`: the first path  
`f2`: the second path  

- **returns:**  
True if yes, otherwise False  
If any of the path does not exist, return False  
  
#### `padBoth (s, length, left, right) `
  
Pad at left and right sides of a string with different strings  

- **params:**  
`s`:      The string to be padded  
`length`: The total length of the final string  
`left`:   The string to be added on the left side  
`right`:  The string to be added on the right side.  
If it is None, will be the same as `left`.  

- **returns:**  
The logger  
  
#### `randstr (length) `
  
Generate a random string  

- **params:**  
`length`: the length of the string, default: 8  

- **returns:**  
The random string  
  
#### `range2list (r) `
  
Convert a range to list, because in python3, range is not a list  

- **params:**  
`r`: the range data  

- **returns:**  
The converted list  
  
#### `reduce (r) `
reduce(function, sequence[, initial]) -> value  
  
Apply a function of two arguments cumulatively to the items of a sequence,  
from left to right, so as to reduce the sequence to a single value.  
For example, reduce(lambda x, y: x+y, [1, 2, 3, 4, 5]) calculates  
((((1+2)+3)+4)+5).  If initial is present, it is placed before the items  
of the sequence in the calculation, and serves as a default when the  
sequence is empty.  
#### `split (s, delimter) `
  
Split a string using a single-character delimter  

- **params:**  
`s`: the string  
`delimter`: the single-character delimter  

- **examples:**  
```python  
ret = split("'a,b',c", ",")  
# ret == ["'a,b'", "c"]  
# ',' inside quotes will be recognized.  
```  

- **returns:**  
The list of substrings  
  
#### `targz (tgzfile, srcdir) `
  
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
  
#### `ungz (gzfile, dstfile) `
  
Do a "gunzip"-like for a .gz file  

- **params:**  
`gzfile`:  the .gz file  
`dstfile`: the extracted file  
  
#### `untargz (tfile, dstdir) `
  
Do a "tar zxf"-like for .tgz file  

- **params:**  
`tfile`:  the .tgz file  
`dstdir`: which directory to extract the file to  
  
#### `varname (func, maxline) `
  
Get the variable name inside the function or class __init__  

- **params**  
`func`: the name of the function. Use self.__class__.__name__ for __init__, func.__name__ for functions  
`maxline`: max no. of lines to retrieve if it cannot be retrived in current line (i.e. line breaks between arguments)  
**Note:** use less number to avoid:  
```python  
a = func ()  
...  
func ()  
```  
No variable used in second call, but if maxline to large, it will be wrongly report varable name as `a`  

- **examples:**  
```python  
def func (a, b):  
print varname (func.__name__)  
funcVar = func(1,2) # prints funcVar  
funcVar2 = func (1,  
2)   # prints funcVar2  
func(3,3) # also prints funcVar2, as it retrieve 10 lines above this line!  
def func2 ():  
print varname(func.__name__, 0) # no args, don't retrive  
funcVar3 = func2() # prints funcVar3  
func2() # prints func2_xxxxxxxx, don't retrieve  
class stuff (object):  
def __init__ (self):  
print varname (self.__class__.__name__)  
def method (self):  
print varname (r'\w+\.' + self.method.__name__, 0)  
```  

- **returns:**  
The variable name  
  

## Module `aggr`  
> The aggregation of a set of processes

	@static variables:
		`commprops`: The common properties. If you set these properties to an aggregation, all the processes in this aggregation will have it.
	@magic methods:
		`__setattr__(self, name, value)`: Set property value of an aggregation.
		- if it's a common property, set it to all processes
		- if it is `input` set it to starting processes
		- if it is `depends` set it to the end processes
		- if it is related to `export` (startswith `ex`), set it to the end processes
		- if it is in ['starts', 'ends', 'id'], set it to the aggregation itself.
		- Otherwise a `ValueError` raised.
		- You can use `[aggr].[proc].[prop]` to set/get the properties of a processes in the aggregation.

	

#### `__init__ (self, *arg) `
  
Constructor  

- **params:**  
`arg`: the set of processes  
  
#### `addProc (self, p, where) `
  
Add a process to the aggregation.  
Note that you have to adjust the dependencies after you add processes.  

- **params:**  
`p`:     The process  
`where`: Add to where: 'starts', 'ends', 'both' or None (default)  

- **returns:**  
the aggregation itself  
  
#### `copy (self, tag, copyDeps, newid) `
  
Like `proc`'s `copy` function, copy an aggregation. Each processes will be copied.  

- **params:**  
`tag`:      The new tag of all copied processes  
`copyDeps`: Whether to copy the dependencies or not. Default: True  
- dependences for processes in starts will not be copied  
`newid`:    Use a different id if you don't want to use the variant name  

- **returns:**  
The new aggregation  
  
#### `set (self, propname, propval, procs) `
  
Set property for procs  

- **params:**  
propname: The property name  
propval:  The property value  
procs:    The ids of the procs to set  
  
#### `updateArgs (self, arg, procs) `
  
update args for procs  

- **params:**  
arg:   the arg to update  
procs: The ids of the procs to update  
  

## Module `runner`  
> The base runner class
	

#### `__init__ (self, job) `
  
Constructor  

- **params:**  
`job`:    The job object  
  
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
  
#### `wait (self) `
  
Wait for the job to finish  
  

## Module `runner_queue`  
> The base queue runner class
	@static variables:
		maxsubmit: Maximum jobs submitted at one time. Default cpu_count()/2
		interval:  The interval to submit next batch of jobs. Default 30
	

#### `__init__ (self, job) `
  
Constructor  

- **params:**  
`job`:    The job object  
  
#### `wait (self) `
  
Wait for the job to finish  
  

## Module `runner_local`  
> The local runner
	


## Module `runner_ssh`  
> The ssh runner

	@static variables:
		`serverid`: The incremental number used to calculate which server should be used.
		- Don't touch unless you know what's going on!

	

#### `__init__ (self, job) `
  
Constructor  

- **params:**  
`job`:    The job object  
`config`: The properties of the process  
  

## Module `runner_sge`  
> The sge runner
	

#### `__init__ (self, job) `
  
Constructor  

- **params:**  
`job`:    The job object  
`config`: The properties of the process  
  
#### `getpid (self) `
  
#### `isRunning (self) `
  
Tell whether the job is still running  
  
