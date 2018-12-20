# module: pyppl
  
The main module of PyPPL  
  
!!! example "class: `PyPPL`"
  
	The PyPPL class  
  

	- **static variables:**  
		`TIPS`: The tips for users  
		`RUNNERS`: Registered runners  
		`DEFAULT_CFGFILES`: Default configuration file  
		`COUNTER`: The counter for `PyPPL` instance  
  
	!!! abstract "method: `__init__ (self, config, cfgfile)`"
  
		Constructor  

		- **params:**  
			`config`: the configurations for the pipeline, default: {}  
			`cfgfile`:  the configuration file for the pipeline, default: `~/.PyPPL.json` or `./.PyPPL`  
  
	!!! abstract "method: `flowchart (self, fcfile, dotfile)`"
  
		Generate graph in dot language and visualize it.  

		- **params:**  
			`dotfile`: Where to same the dot graph. Default: `None` (`path.splitext(sys.argv[0])[0] + ".pyppl.dot"`)  
			`fcfile`:  The flowchart file. Default: `None` (`path.splitext(sys.argv[0])[0] + ".pyppl.svg"`)  
			- For example: run `python pipeline.py` will save it to `pipeline.pyppl.svg`  
			`dot`:     The dot visulizer. Default: "dot -Tsvg {{dotfile}} > {{fcfile}}"  

		- **returns:**  
			The pipeline object itself.  
  
	!!! tip "staticmethod: `registerRunner (r)`"
  
		Register a runner  

		- **params:**  
			`r`: The runner to be registered.  
  
	!!! abstract "method: `resume (self, *args)`"
  
		Mark processes as to be resumed  

		- **params:**  
			`args`: the processes to be marked  

		- **returns:**  
			The pipeline object itself.  
  
	!!! abstract "method: `resume2 (self, *args)`"
  
		Mark processes as to be resumed  

		- **params:**  
			`args`: the processes to be marked  

		- **returns:**  
			The pipeline object itself.  
  
	!!! abstract "method: `run (self, profile)`"
  
		Run the pipeline  

		- **params:**  
			`profile`: the profile used to run, if not found, it'll be used as runner name. default: 'default'  

		- **returns:**  
			The pipeline object itself.  
  
	!!! abstract "method: `showAllRoutes (self)`"
  
		Show all the routes in the log.  
  
	!!! abstract "method: `start (self, *args)`"
  
		Set the starting processes of the pipeline  

		- **params:**  
			`args`: the starting processes  

		- **returns:**  
			The pipeline object itself.  
  
# module: pyppl.proc
  
proc module for PyPPL  
  
!!! example "class: `Proc`"
  
	The Proc class defining a process  
  

	- **static variables:**  
		`ALIAS`:         The alias for the properties  
		`DEPRECATED`:    Deprecated property names  
  
		`OUT_VARTYPE`:    Variable types for output  
		`OUT_FILETYPE`:   File types for output  
		`OUT_DIRTYPE`:    Directory types for output  
		`OUT_STDOUTTYPE`: Stdout types for output  
		`OUT_STDERRTYPE`: Stderr types for output  
  
		`IN_VARTYPE`:   Variable types for input  
		`IN_FILETYPE`:  File types for input  
		`IN_FILESTYPE`: Files types for input  
  
		`EX_GZIP`: `exhow` value to gzip output files while exporting them  
		`EX_COPY`: `exhow` value to copy output files while exporting them  
		`EX_MOVE`: `exhow` value to move output files while exporting them  
		`EX_LINK`: `exhow` value to link output files while exporting them  
  
	!!! abstract "method: `__getattr__ (self, name)`"
  
		Get the value of a property in `self.props`  
		It recognizes alias as well.  

		- **params:**  
			`name`: The name of the property  

		- **returns:**  
			The value of the property  
  
	!!! abstract "method: `__init__ (self, tag, desc, id, **kwargs)`"
  
		Constructor  

		- **params:**  
			`tag`     : The tag of the process  
			`desc`    : The description of the process  
			`id`      : The identify of the process  
			`**kwargs`: Other properties of the process, which can be set by `proc.xxx` later.  

		- **config:**  
			id, input, output, ppldir, forks, cache, acache, rc, echo, runner, script, depends, tag, desc, dirsig  
			exdir, exhow, exow, errhow, errntry, lang, beforeCmd, afterCmd, workdir, args, aggr  
			callfront, callback, expect, expart, template, tplenvs, resume, nthread  

		- **props**  
			input, output, rc, echo, script, depends, beforeCmd, afterCmd, workdir, expect  
			expart, template, channel, jobs, ncjobids, size, sets, procvars, suffix, logs  
  
	!!! abstract "method: `__setattr__ (self, name, value)`"
  
		Set the value of a property in `self.config`  

		- **params:**  
			`name` : The name of the property.  
			`value`: The new value of the property.  
  
	!!! abstract "method: `copy (self, tag, desc, id)`"
  
		Copy a process  

		- **params:**  
			`id`: The new id of the process, default: `None` (use the varname)  
			`tag`:   The tag of the new process, default: `None` (used the old one)  
			`desc`:  The desc of the new process, default: `None` (used the old one)  

		- **returns:**  
			The new process  
  
	!!! abstract "method: `name (self, aggr)`"
  
		Get my name include `aggr`, `id`, `tag`  

		- **returns:**  
			the name  
  
	!!! abstract "method: `run (self, profile, profiles)`"
  
		Run the jobs with a configuration  

		- **params:**  
			`config`: The configuration  
  
# module: pyppl.aggr
  
The aggregation of procs  
  
!!! example "class: `Aggr`"
  
	The aggregation of a set of processes  
  
	!!! abstract "method: `__getattr__ (self, name)`"
  
		Get the property of an aggregation.  

		- **params:**  
			`name`: The name of the property  

		- **returns:**  
			- Return a proc if name in `self._procs`  
			- Return a property value if name in `self.__dict__`  
			- Return a `_Proxy` instance else.  
  
	!!! abstract "method: `__getitem__ (self, key)`"
  
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
		```  
  
	!!! abstract "method: `__init__ (self, *args, **kwargs)`"
  
		Constructor  

		- **params:**  
			`args`: the set of processes  
			`depends`: Whether auto deduce depends. Default: True  
			`id`: The id of the aggr. Default: None (the variable name)  
			`tag`: The tag of the processes. Default: None (a unique 4-char str according to the id)  
  
	!!! abstract "method: `__setattr__ (self, name, value)`"
  
		Set property value of an aggregation.  
			- if it's a common property, set it to all processes  
			- if it is `input` set it to starting processes  
			- if it is `depends` set it to the end processes  
			- if it is related to `export` (startswith `ex`), set it to the end processes  
			- if it is in ['starts', 'ends', 'id'], set it to the aggregation itself.  
			- Otherwise a `ValueError` raised.  
			- You can use `[aggr].[proc].[prop]` to set/get the properties of a processes in the aggregation.  

		- **params:**  
			`name` : The name of the property  
			`value`: The value of the property  
  
	!!! abstract "method: `addEnd (self, *procs)`"
  
		Add end processes  

		- **params:**  
			`procs`: The selector of processes to add  
  
	!!! abstract "method: `addProc (self, p, tag, where, copy)`"
  
		Add a process to the aggregation.  
		Note that you have to adjust the dependencies after you add processes.  

		- **params:**  
			`p`:     The process  
			`where`: Add to where: 'starts', 'ends', 'both' or None (default)  

		- **returns:**  
			the aggregation itself  
  
	!!! abstract "method: `addStart (self, *procs)`"
  
		Add start processes  

		- **params:**  
			`procs`: The selector of processes to add  
  
	!!! abstract "method: `copy (self, tag, depends, id, delegates, modules)`"
  
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
  
	!!! abstract "method: `delEnd (self, *procs)`"
  
		Delete end processes  

		- **params:**  
			`procs`: The selector of processes to delete  
  
	!!! abstract "method: `delStart (self, *procs)`"
  
		Delete start processes  

		- **params:**  
			`procs`: The selector of processes to delete  
  
	!!! abstract "method: `delegate (self, attrs, procs)`"
  
		Delegate the procs to have the attributes set by:  
		`aggr.args.a.b = 1`  
		Instead of setting `args.a.b` of all processes, `args.a.b` of only delegated processes will be set.  
		`procs` can be `starts`/`ends`, but it cannot be set with other procs, which means you can do:  
		`aggr.delegate('args', 'starts')`, but not `aggr.delegate('args', ['starts', 'pXXX'])`  
  
	!!! abstract "method: `module (self, name, starts, depends, ends, starts_shared, depends_shared, ends_shared)`"
  
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
  
	!!! abstract "method: `moduleFunc (self, name, on, off)`"
  
		Define modules using functions  

		- **params:**  
			`name`: The name of the module  
			`on`  : The function when the module is turned on  
			`off` : The function when the module is turned off  
  
	!!! abstract "method: `off (self, *names)`"
  
		Turn off modules  

		- **params:**  
			`names`: The names of the modules.  
  
	!!! abstract "method: `on (self, *names)`"
  
		Turn on modules  

		- **params:**  
			`names`: The names of the modules.  
  
# module: pyppl.channel
  
Channel for pyppl  
  
!!! example "class: `Channel`"
  
	The channen class, extended from `list`  
  
	!!! abstract "method: `attach (self, *names, **kwargs)`"
  
		Attach columns to names of Channel, so we can access each column by:  
		`ch.col0` == ch.colAt(0)  

		- **params:**  
			`names`: The names. Have to be as length as channel's width. None of them should be Channel's property name  
			`flatten`: Whether flatten the channel for the name being attached  
  
	!!! abstract "method: `cbind (self, *cols)`"
  
		Add columns to the channel  

		- **params:**  
			`cols`: The columns  

		- **returns:**  
			The channel with the columns inserted.  
  
	!!! abstract "method: `colAt (self, index)`"
  
		Fetch one column of a Channel  

		- **params:**  
			`index`: which column to fetch  

		- **returns:**  
			The Channel with that column  
  
	!!! abstract "method: `collapse (self, col)`"
  
		Do the reverse of expand  
		length: N -> 1  
		width:  M -> M  

		- **params:**  
			`col`:     the index of the column used to collapse  

		- **returns:**  
			The collapsed Channel  
  
	!!! abstract "method: `copy (self)`"
  
		Copy a Channel using `copy.copy`  

		- **returns:**  
			The copied Channel  
  
	!!! tip "staticmethod: `create (l)`"
  
		Create a Channel from a list  

		- **params:**  
			`l`: The list, default: []  

		- **returns:**  
			The Channel created from the list  
  
	!!! abstract "method: `expand (self, col, pattern, t, sortby, reverse)`"
  
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
  
	!!! abstract "method: `filter (self, func)`"
  
		Alias of python builtin `filter`  

		- **params:**  
			`func`: the function. Default: None  

		- **returns:**  
			The filtered Channel  
  
	!!! abstract "method: `filterCol (self, func, col)`"
  
		Just filter on the first column  

		- **params:**  
			`func`: the function  
			`col`: the column to filter  

		- **returns:**  
			The filtered Channel  
  
	!!! abstract "method: `flatten (self, col)`"
  
		Convert a single-column Channel to a list (remove the tuple signs)  
		`[(a,), (b,)]` to `[a, b]`  

		- **params:**  
			`col`: The column to flat. None for all columns (default)  

		- **returns:**  
			The list converted from the Channel.  
  
	!!! abstract "method: `fold (self, n)`"
  
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
  
	!!! tip "staticmethod: `fromArgv ()`"
  
		Create a Channel from `sys.argv[1:]`  
		"python test.py a b c" creates a width=1 Channel  
		"python test.py a,1 b,2 c,3" creates a width=2 Channel  

		- **returns:**  
			The Channel created from the command line arguments  
  
	!!! tip "staticmethod: `fromChannels (*args)`"
  
		Create a Channel from Channels  

		- **params:**  
			`args`: The Channels  

		- **returns:**  
			The Channel merged from other Channels  
  
	!!! tip "staticmethod: `fromFile (fn, header, skip, delimit)`"
  
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
  
	!!! tip "staticmethod: `fromPairs (pattern)`"
  
		Create a width = 2 Channel from a pattern  

		- **params:**  
			`pattern`: the pattern  

		- **returns:**  
			The Channel create from every 2 files match the pattern  
  
	!!! tip "staticmethod: `fromParams (*pnames)`"
  
		Create a Channel from params  

		- **params:**  
			`*pnames`: The names of the option  

		- **returns:**  
			The Channel  
  
	!!! tip "staticmethod: `fromPattern (pattern, t, sortby, reverse)`"
  
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
  
	!!! abstract "method: `get (self, idx)`"
  
		Get the element of a flattened channel  

		- **params:**  
			`idx`: The index of the element to get. Default: 0  

		- **return:**  
			The element  
  
	!!! abstract "method: `insert (self, cidx, *cols)`"
  
		Insert columns to a channel  

		- **params:**  
			`cidx`: Insert into which index of column?  
			`cols`: the columns to be bound to Channel  

		- **returns:**  
			The combined Channel  
			Note, self is also changed  
  
	!!! abstract "method: `length (self)`"
  
		Get the length of a Channel  
		It's just an alias of `len(chan)`  

		- **returns:**  
			The length of the Channel  
  
	!!! abstract "method: `map (self, func)`"
  
		Alias of python builtin `map`  

		- **params:**  
			`func`: the function  

		- **returns:**  
			The transformed Channel  
  
	!!! abstract "method: `mapCol (self, func, col)`"
  
		Map for a column  

		- **params:**  
			`func`: the function  
			`col`: the index of the column. Default: 0  

		- **returns:**  
			The transformed Channel  
  
	!!! tip "staticmethod: `nones (length, width)`"
  
		Create a channel with `None`s  

		- **params:**  
			`length`: The length of the channel  
			`width`:  The width of the channel  

		- **returns:**  
			The created channel  
  
	!!! abstract "method: `rbind (self, *rows)`"
  
		The multiple-argument versoin of `rbind`  

		- **params:**  
			`rows`: the rows to be bound to Channel  

		- **returns:**  
			The combined Channel  
			Note, self is also changed  
  
	!!! abstract "method: `reduce (self, func)`"
  
		Alias of python builtin `reduce`  

		- **params:**  
			`func`: the function  

		- **returns:**  
			The reduced value  
  
	!!! abstract "method: `reduceCol (self, func, col)`"
  
		Reduce a column  

		- **params:**  
			`func`: the function  
			`col`: the column to reduce  

		- **returns:**  
			The reduced value  
  
	!!! abstract "method: `repCol (self, n)`"
  
		Repeat column and return a new channel  

		- **params:**  
			`n`: how many times to repeat.  

		- **returns:**  
			The new channel with repeated columns  
  
	!!! abstract "method: `repRow (self, n)`"
  
		Repeat row and return a new channel  

		- **params:**  
			`n`: how many times to repeat.  

		- **returns:**  
			The new channel with repeated rows  
  
	!!! abstract "method: `rowAt (self, index)`"
  
		Fetch one row of a Channel  

		- **params:**  
			`index`: which row to fetch  

		- **returns:**  
			The Channel with that row  
  
	!!! abstract "method: `slice (self, start, length)`"
  
		Fetch some columns of a Channel  

		- **params:**  
			`start`:  from column to start  
			`length`: how many columns to fetch, default: None (from start to the end)  

		- **returns:**  
			The Channel with fetched columns  
  
	!!! abstract "method: `split (self, flatten)`"
  
		Split a Channel to single-column Channels  

		- **returns:**  
			The list of single-column Channels  
  
	!!! abstract "method: `t (self)`"
  
		Transpose the channel  

		- **returns:**  
			The transposed channel.  
  
	!!! abstract "method: `transpose (self)`"
  
		Transpose the channel  

		- **returns:**  
			The transposed channel.  
  
	!!! abstract "method: `unfold (self, n)`"
  
		Do the reverse thing as self.fold does  

		- **params:**  
			`n`: How many rows to combind each time. default: 2  

		- **returns:**  
			The unfolded Channel  
  
	!!! abstract "method: `unique (self)`"
  
		Make the channel unique, remove duplicated rows  
		Try to keep the order  
  
	!!! abstract "method: `width (self)`"
  
		Get the width of a Channel  

		- **returns:**  
			The width of the Channel  
  
# module: pyppl.flowchart
  
flowchart module for PyPPL  
  
!!! example "class: `Flowchart`"
  
	Draw flowchart for pipelines  
  

	- **static variables:**  
		`THEMES`: predefined themes  
  
	!!! abstract "method: `__init__ (self, fcfile, dotfile)`"
  
		The constructor  

		- **params:**  
			`fcfile`: The flowchart file. Default: `path.splitext(sys.argv[0])[0] + '.pyppl.svg'`  
			`dotfile`: The dot file. Default: `path.splitext(sys.argv[0])[0] + '.pyppl.dot'`  
  
	!!! abstract "method: `addLink (self, node1, node2)`"
  
		Add a link to the chart  

		- **params:**  
			`node1`: The first node.  
			`node2`: The second node.  
  
	!!! abstract "method: `addNode (self, node, role)`"
  
		Add a node to the chart  

		- **params:**  
			`node`: The node  
			`role`: Is it a starting node, an ending node or None. Default: None.  
  
	!!! abstract "method: `generate (self)`"
  
		Generate the dot file and graph file.  
  
	!!! abstract "method: `setTheme (self, theme, base)`"
  
		Set the theme to be used  

		- **params:**  
			`theme`: The theme, could be the key of Flowchart.THEMES or a dict of a theme definition.  
			`base` : The base theme to be based on you pass custom theme  
  
# module: pyppl.job
  
job module for PyPPL  
  
!!! example "class: `Job`"
  
	PyPPL Job  
  

	- **static variables:**  
		`STATUS_INITIATED`    : Job status when a job has just initiated  
		`STATUS_BUILDING`     : Job status when a job is being built  
		`STATUS_BUILT`        : Job status when a job has been built  
		`STATUS_BUILTFAILED`  : Job status when a job fails to build  
		`STATUS_SUBMITTING`   : Job status when a job is submitting  
		`STATUS_SUBMITTED`    : Job status when a job has submitted  
		`STATUS_SUBMITFAILED` : Job status when a job fails to submit  
		`STATUS_RUNNING`      : Job status when a job is running  
		`STATUS_RETRYING`     : Job status when a job is about to retry  
		`STATUS_DONE`         : Job status when a job has done  
		`STATUS_DONECACHED`   : Job status when a job has cached  
		`STATUS_DONEFAILED`   : Job status when a job fails temporarily (may retry later)  
		`STATUS_ENDFAILED`    : Job status when a job fails finally  
		`STATUS_KILLING`      : Job status when a job is being killed  
		`STATUS_KILLED`       : Job status when a job has been killed  
  
		`RC_NOTGENERATE` : A return code if no rcfile has been generated  
		`RC_SUBMITFAILED`: A return code when a job fails to submit  
  
	!!! abstract "method: `__init__ (self, index, config)`"
  
		Initiate a job  

		- **params:**  
			`index`:  The index of the job.  
			`config`: The configurations of the job.  
  
	!!! abstract "method: `build (self)`"
  
		Initiate a job, make directory and prepare input, output and script.  
  
	!!! abstract "method: `cache (self)`"
  
		Truly cache the job (by signature)  
  
	!!! abstract "method: `done (self, export)`"
  
		Do some cleanup when job finished  

		- **params:**  
			`export`: Whether do export  
  
	!!! abstract "method: `export (self)`"
  
		Export the output files  
  
	!!! abstract "method: `isExptCached (self)`"
  
		Prepare to use export files as cached information  
		True if succeed, otherwise False  
  
	!!! abstract "method: `isTrulyCached (self)`"
  
		Check whether a job is truly cached (by signature)  
  
	!!! abstract "method: `kill (self)`"
  
		Kill the job  
  
	!!! abstract "method: `poll (self)`"
  
		Check the status of a running job  
  
	!!! abstract "method: `report (self)`"
  
		Report the job information to logger  
  
	!!! abstract "method: `reset (self)`"
  
		Clear the intermediate files and output files  
  
	!!! abstract "method: `retry (self)`"
  
		If the job is available to retry  

		- **return:**  
			`True` if it is else `False`  
  
	!!! abstract "method: `signature (self)`"
  
		Calculate the signature of the job based on the input/output and the script  

		- **returns:**  
			The signature of the job  
  
	!!! abstract "method: `submit (self)`"
  
		Submit the job  
  
	!!! abstract "method: `succeed (self)`"
  
		Tell if a job succeeds.  
		Check whether output files generated, expectation met and return code met.  

		- **return:**  
			`True` if succeed else `False`  
  
# module: pyppl.jobmgr
  
jobmgr module for PyPPL  
  
!!! example "class: `Jobmgr`"
  
	A job manager for PyPPL  
  

	- **static variables**  
		`PBAR_SIZE`:  The length of the progressbar  
		`PBAR_MARKS`: The marks for different job status  
		`PBAR_LEVEL`: The log levels for different job status  
		`SMBLOCK`   : The lock used to relatively safely to tell whether jobs can be submitted.  
  
	!!! abstract "method: `__init__ (self, jobs, config)`"
  
		Initialize the job manager  

		- **params:**  
			`jobs`: All the jobs  
			`config`: The configurations for the job manager  
  
	!!! abstract "method: `canSubmit (self)`"
  
		Tell if jobs can be submitted.  

		- **return:**  
			`True` if they can else `False`  
  
	!!! abstract "method: `cleanup (self, ex)`"
  
		Cleanup the pipeline when  
		- Ctrl-c hit  
		- error encountered and `proc.errhow` = 'terminate'  

		- **params:**  
			`ex`: The exception raised by workers  
  
	!!! abstract "method: `killWorker (self, rq)`"
  
		The worker to kill the jobs.  

		- **params:**  
			`rq`: The queue that has running jobs.  
  
	!!! abstract "method: `progressbar (self, jobidx)`"
  
		Generate progressbar.  

		- **params:**  
			`jobidx`: The job index.  
			`loglevel`: The log level in PyPPL log system  

		- **returns:**  
			The string representing the progressbar  
  
	!!! abstract "method: `worker (self, queue)`"
  
		Worker for the queue  

		- **params:**  
			`queue`: The priority queue  
  
	!!! abstract "method: `workon (self, index, queue)`"
  
		Work on a queue item  

		- **params:**  
			`index`: The job index and batch number, got from the queue  
			`queue`: The priority queue  
  
!!! example "class: `PQueue`"
  
	A modified PriorityQueue, which allows jobs to be submitted in batch  
  
	!!! abstract "method: `__init__ (self, maxsize, batch_len)`"
  
		Initialize the queue  

		- **params:**  
			`maxsize`  : The maxsize of the queue  
			`batch_len`: What's the length of a batch  
  
	!!! abstract "method: `get (self, block, timeout)`"
  
		Get an item from the queue  
  
	!!! abstract "method: `get_nowait (self)`"
  
		Get an item from the queue without waiting  
  
	!!! abstract "method: `put (self, item, block, timeout, where)`"
  
		Put item to the queue, just like `PriorityQueue.put` but with an extra argument  

		- **params:**  
			`where`: Which batch to put the item  
  
	!!! abstract "method: `put_nowait (self, item, where)`"
  
		Put item to the queue, just like `PriorityQueue.put_nowait` but with an extra argument  

		- **params:**  
			`where`: Which batch to put the item  
  
# module: pyppl.logger
  
A customized logger for pyppl  
  
!!! example "class: `PyPPLLogFormatter`"
  
	logging formatter for pyppl  
  
	!!! abstract "method: `__init__ (self, fmt, theme, secondary)`"
  
		Constructor  

		- **params:**  
			`fmt`      : The format  
			`theme`    : The theme  
			`secondary`: Whether this is a secondary formatter or not (another formatter applied before this).  
  
	!!! abstract "method: `format (self, record)`"
  
		Format the record  

		- **params:**  
			`record`: The log record  

		- **returns:**  
			The formatted record  
  
!!! example "class: `PyPPLLogFilter`"
  
	logging filter by levels (flags)  
  
	!!! abstract "method: `__init__ (self, name, lvls, lvldiff)`"
  
		Constructor  

		- **params:**  
			`name`: The name of the logger  
			`lvls`: The levels of records to keep  
			`lvldiff`: The adjustments to `lvls`  
  
	!!! abstract "method: `filter (self, record)`"
  
		Filter the record  

		- **params:**  
			`record`: The record to be filtered  

		- **return:**  
			`True` if the record to be kept else `False`  
  
!!! example "class: `PyPPLStreamHandler`"
  
	PyPPL stream log handler.  
	To implement the progress bar for JOBONE and SUBMIT logs.  
  
	!!! abstract "method: `__init__ (self, stream)`"
  
		Constructor  

		- **params:**  
			`stream`: The stream  
  
	!!! abstract "method: `emit (self, record)`"
  
		Emit the record.  
  
!!! example "function: `getLogger`"
  
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
  
# module: pyppl.parameters
  
parameters module for PyPPL  
  
!!! example "class: `Commands`"
  
	Support sub-command for command line argument parse.  
  
	!!! abstract "method: `__getattr__ (self, name)`"
  
		Get the value of the attribute  

		- **params:**  
			`name` : The name of the attribute  

		- **returns:**  
			The value of the attribute  
  
	!!! abstract "method: `__getitem__ (self, name)`"
  
		Alias of `__getattr__`  
  
	!!! abstract "method: `__init__ (self, theme)`"
  
		Constructor  

		- **params:**  
			`theme`: The theme  
  
	!!! abstract "method: `__setattr__ (self, name, value)`"
  
		Set the value of the attribute  

		- **params:**  
			`name` : The name of the attribute  
			`value`: The value of the attribute  
  
	!!! abstract "method: `help (self, error, printNexit)`"
  
		Construct the help page  

		- **params:**  
			`error`: the error message  
			`printNexit`: print the help page and exit instead of return the help information  

		- **returns:**  
			The help information if `printNexit` is `False`  
  
	!!! abstract "method: `parse (self, args, arbi)`"
  
		Parse the arguments.  

		- **params:**  
			`args`: The arguments (list). `sys.argv[1:]` will be used if it is `None`.  
			`arbi`: Whether do an arbitrary parse. If True, options don't need to be defined. Default: `False`  

		- **returns:**  
			A `tuple` with first element the subcommand and second the parameters being parsed.  
  
!!! example "class: `Parameters`"
  
	A set of parameters  
  

	- **static variables:**  
		`ARG_TYPES`           : shortcuts for argument types  
		`ARG_NAME_PATTERN`    : A pattern to recognize an argument name  
		`ARG_VALINT_PATTERN`  : An integer argument pattern  
		`ARG_VALFLOAT_PATTERN`: A float argument pattern  
		`ARG_VALBOOL_PATTERN` : A bool argument pattern  
		`ARG_VALPY_PATTERN`   : A python expression argument pattern  
  
		`VAL_TRUES` : Values translated to `True`  
		`VAL_FALSES`: Values translated to `False`  
  
		`POSITIONAL`   : Flag for positional arguments  
		`ALLOWED_TYPES`: All allowed argument types  
  
	!!! abstract "method: `__call__ (self, option, value)`"
  
		Set options values in `self._props`.  
		Will be deprecated in the future!  

		- **params:**  
			`option`: The key of the option  
			`value` : The value of the option  
			`excl`  : The value is used to exclude (only for `hopts`)  

		- **returns:**  
			`self`  
  
	!!! abstract "method: `__getattr__ (self, name)`"
  
		Get a `Parameter` instance if possible, otherwise return an attribute value  

		- **params:**  
			`name`: The name of the `Parameter` or the attribute  

		- **returns:**  
			A `Parameter` instance if `name` exists in `self._params`, otherwise,  
			the value of the attribute `name`  
  
	!!! abstract "method: `__getitem__ (self, name)`"
  
		Alias of `__getattr__`  
  
	!!! abstract "method: `__init__ (self, command, theme)`"
  
		Constructor  

		- **params:**  
			`command`: The sub-command  
			`theme`: The theme  
  
	!!! abstract "method: `__setattr__ (self, name, value)`"
  
		Change the value of an existing `Parameter` or create a `Parameter` using the `name` and `value`. If `name` is an attribute, return its value.  

		- **params:**  
			`name` : The name of the Parameter  
			`value`: The value of the Parameter  
  
	!!! abstract "method: `__setitem__ (self, name, value)`"
  
		Compose a `Parameter` using the `name` and `value`  

		- **params:**  
			`name` : The name of the `Parameter`  
			`value`: The value of the `Parameter`  
  
	!!! abstract "method: `asDict (self)`"
  
		Convert the parameters to Box object  

		- **returns:**  
			The Box object  
  
	!!! abstract "method: `help (self, error, printNexit)`"
  
		Calculate the help page  

		- **params:**  
			`error`: The error message to show before the help information. Default: `''`  
			`printNexit`: Print the help page and exit the program? Default: `False` (return the help information)  

		- **return:**  
			The help information  
  
	!!! abstract "method: `loadDict (self, dictVar, show)`"
  
		Load parameters from a dict  

		- **params:**  
			`dictVar`: The dict variable.  
			- Properties are set by "<param>.required", "<param>.show", ...  
			`show`:    Whether these parameters should be shown in help information  
				- Default: False (don't show parameter from config object in help page)  
				- It'll be overwritten by the `show` property inside dict variable.  
				- If it is None, will inherit the param's show value  
  
	!!! abstract "method: `loadFile (self, cfgfile, show)`"
  
		Load parameters from a json/config file  
		If the file name ends with '.json', `json.load` will be used,  
		otherwise, `ConfigParser` will be used.  
		For config file other than json, a section name is needed, whatever it is.  

		- **params:**  
			`cfgfile`: The config file  
			`show`:    Whether these parameters should be shown in help information  
				- Default: False (don't show parameter from config file in help page)  
				- It'll be overwritten by the `show` property inside the config file.  
  
	!!! abstract "method: `parse (self, args, arbi)`"
  
		Parse the arguments.  

		- **params:**  
			`args`: The arguments (list). `sys.argv[1:]` will be used if it is `None`.  
			`arbi`: Whether do an arbitrary parse. If True, options don't need to be defined. Default: `False`  

		- **returns:**  
			A `Box`/`dict` object containing all option names and values.  
  
!!! example "class: `HelpAssembler`"
  
	A helper class to help assembling the help information page.  

	- **staticvars**  
		`MAXPAGEWIDTH`: the max width of the help page, not including the leading space  
		`MAXOPTWIDTH` : the max width of the option name (include the type and placeholder, but not the leading space)  
		`THEMES`      : the themes  
  
	!!! abstract "method: `__init__ (self, prog, theme)`"
  
		Constructor  

		- **params:**  
			`prog`: The program name  
			`theme`: The theme. Could be a name of `THEMES`, or a dict of a custom theme.  
  
	!!! abstract "method: `assemble (self, helps, progname)`"
  
		Assemble the whole help page.  

		- **params:**  
			`helps`: The help items. A list with plain strings or tuples of 3 elements, which  
				will be treated as option name, option type/placeholder and option descriptions.  
			`progname`: The program name used to replace '{prog}' with.  

		- **returns:**  
			lines (`list`) of the help information.  
  
	!!! abstract "method: `error (self, msg)`"
  
		Render an error message  

		- **params:**  
			`msg`: The error message  
  
	!!! abstract "method: `optdesc (self, msg)`"
  
		Render the option descriptions  

		- **params:**  
			`msg`: the option descriptions  
  
	!!! abstract "method: `optname (self, msg)`"
  
		Render the option name  

		- **params:**  
			`msg`: The option name  
  
	!!! abstract "method: `opttype (self, msg)`"
  
		Render the option type or placeholder  

		- **params:**  
			`msg`: the option type or placeholder  
  
	!!! abstract "method: `plain (self, msg)`"
  
		Render a plain message  

		- **params:**  
			`msg`: the message  
  
	!!! abstract "method: `prog (self, prog)`"
  
		Render the program name  

		- **params:**  
			`msg`: The program name  
  
	!!! abstract "method: `title (self, msg)`"
  
		Render an section title  

		- **params:**  
			`msg`: The section title  
  
	!!! abstract "method: `warning (self, msg)`"
  
		Render an warning message  

		- **params:**  
			`msg`: The warning message  
  
!!! example "class: `Parameter`"
  
	The class for a single parameter  
  
	!!! abstract "method: `__getattr__ (self, name)`"
  
		Get the value of the attribute  

		- **params:**  
			`name` : The name of the attribute  

		- **returns:**  
			The value of the attribute  
  
	!!! abstract "method: `__init__ (self, name, value)`"
  
		Constructor  

		- **params:**  
			`name`:  The name of the parameter  
			`value`: The initial value of the parameter  
  
	!!! abstract "method: `__setattr__ (self, name, value)`"
  
		Set the value of the attribute  

		- **params:**  
			`name` : The name of the attribute  
			`value`: The value of the attribute  
  
	!!! abstract "method: `setDesc (self, d)`"
  
		Set the description of the parameter  

		- **params:**  
			`d`: The description  
  
	!!! abstract "method: `setName (self, n)`"
  
		Set the name of the parameter  

		- **params:**  
			`n`: The name  
  
	!!! abstract "method: `setRequired (self, r)`"
  
		Set whether this parameter is required  

		- **params:**  
			`r`: True if required else False. Default: True  
  
	!!! abstract "method: `setShow (self, s)`"
  
		Set whether this parameter should be shown in help information  

		- **params:**  
			`s`: True if it shows else False. Default: True  
  
	!!! abstract "method: `setType (self, t)`"
  
		Set the type of the parameter  

		- **params:**  
			`t`: The type of the value. Default: str  
			- Note: str rather then 'str'  
  
	!!! abstract "method: `setValue (self, v)`"
  
		Set the value of the parameter  

		- **params:**  
			`v`: The value  
  
# module: pyppl.proctree
  
Manage process relations  
  
!!! example "class: `ProcTree`"
  
	A tree of processes.  
  
	!!! abstract "method: `__init__ (self)`"
  
		Constructor, set the status of all `ProcNode`s  
  
	!!! tip "staticmethod: `check (proc)`"
  
		Check whether a process with the same id and tag exists  

		- **params:**  
			`proc`: The `Proc` instance  
  
	!!! abstract "method: `checkPath (self, proc)`"
  
		Check whether paths of a process can start from a start process  

		- **params:**  
			`proc`: The process  

		- **returns:**  
			`True` if all paths can pass  
			The failed path otherwise  
  
	!!! abstract "method: `getAllPaths (self)`"
  
		Get all paths of the pipeline  
  
	!!! abstract "method: `getEnds (self)`"
  
		Get the end processes  

		- **returns:**  
			The end processes  
  
	!!! tip "staticmethod: `getNext (proc)`"
  
		Get next processes of process  

		- **params:**  
			`proc`: The `Proc` instance  

		- **returns:**  
			The processes depend on this process  
  
	!!! tip "staticmethod: `getNextStr (proc)`"
  
		Get the names of processes depend on a process  

		- **params:**  
			`proc`: The `Proc` instance  

		- **returns:**  
			The names  
  
	!!! abstract "method: `getNextToRun (cls)`"
  
		Get the process to run next  

		- **returns:**  
			The process next to run  
  
	!!! abstract "method: `getPaths (self, proc, proc0)`"
  
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
  
	!!! abstract "method: `getPathsToStarts (self, proc)`"
  
		Filter the paths with start processes  

		- **params:**  
			`proc`: The process  

		- **returns:**  
			The filtered path  
  
	!!! tip "staticmethod: `getPrevStr (proc)`"
  
		Get the names of processes a process depends on  

		- **params:**  
			`proc`: The `Proc` instance  

		- **returns:**  
			The names  
  
	!!! abstract "method: `getStarts (self)`"
  
		Get the start processes  

		- **returns:**  
			The start processes  
  
	!!! tip "staticmethod: `register (proc)`"
  
		Register the process  

		- **params:**  
			`proc`: The `Proc` instance  
  
	!!! tip "staticmethod: `reset ()`"
  
		Reset the status of all `ProcNode`s  
  
	!!! abstract "method: `setStarts (cls, starts)`"
  
		Set the start processes  

		- **params:**  
			`starts`: The start processes  
  
	!!! abstract "method: `unranProcs (self)`"
  
		Get the unran processes.  

		- **returns:**  
			The processes haven't run.  
  
!!! example "class: `ProcNode`"
  
	The node for processes to manage relations between each other  
  
	!!! abstract "method: `__init__ (self, proc)`"
  
		Constructor  

		- **params:**  
			`proc`: The `Proc` instance  
  
	!!! abstract "method: `sameIdTag (self, proc)`"
  
		Check if the process has the same id and tag with me.  

		- **params:**  
			`proc`: The `Proc` instance  

		- **returns:**  
			`True` if it is.  
			`False` if not.  
  
# module: pyppl.runners.runner
  
The base runner class  
  
!!! example "class: `Runner`"
  
	The base runner class  
  
	!!! abstract "method: `__init__ (self, job)`"
  
		Constructor  

		- **params:**  
			`job`:    The job object  
  
	!!! abstract "method: `isRunning (self)`"
  
		Try to tell whether the job is still running.  

		- **returns:**  
			`True` if yes, otherwise `False`  
  
	!!! abstract "method: `kill (self)`"
  
		Try to kill the running jobs if I am exiting  
  
	!!! abstract "method: `submit (self)`"
  
		Try to submit the job  
  
# module: pyppl.runners.runner_dry
  
Dry runner for PyPPL  
  
!!! example "class: `RunnerDry`"
  
	The dry runner  
  
	!!! abstract "method: `__init__ (self, job)`"
  
		Constructor  

		- **params:**  
			`job`:    The job object  
  
# module: pyppl.runners.runner_local
  
Local runner  
  
!!! example "class: `RunnerLocal`"
  
	Constructor  

	- **params:**  
		`job`:    The job object  
		`config`: The properties of the process  
  
	!!! abstract "method: `__init__ (self, job)`"
  
# module: pyppl.runners.runner_sge
  
SGE runner for PyPPL  
  
!!! example "class: `RunnerSge`"
  
	The sge runner  
  
	!!! abstract "method: `__init__ (self, job)`"
  
		Constructor  

		- **params:**  
			`job`:    The job object  
			`config`: The properties of the process  
  
	!!! abstract "method: `isRunning (self)`"
  
		Tell if the job is alive  

		- **returns:**  
			`True` if it is else `False`  
  
	!!! abstract "method: `kill (self)`"
  
		Kill the job  
  
	!!! abstract "method: `submit (self)`"
  
		Submit the job  

		- **returns:**  
			The `utils.cmd.Cmd` instance if succeed  
			else a `Box` object with stderr as the exception and rc as 1  
  
# module: pyppl.runners.runner_slurm
  
Slurm runner for PyPPL  
  
!!! example "class: `RunnerSlurm`"
  
	The slurm runner  
  
	!!! abstract "method: `__init__ (self, job)`"
  
		Constructor  

		- **params:**  
			`job`:    The job object  
			`config`: The properties of the process  
  
	!!! abstract "method: `isRunning (self)`"
  
		Tell if the job is alive  

		- **returns:**  
			`True` if it is else `False`  
  
	!!! abstract "method: `kill (self)`"
  
		Kill the job  
  
	!!! abstract "method: `submit (self)`"
  
		Submit the job  

		- **returns:**  
			The `utils.cmd.Cmd` instance if succeed  
			else a `Box` object with stderr as the exception and rc as 1  
  
# module: pyppl.runners.runner_ssh
  
The ssh runner  
  
!!! example "class: `RunnerSsh`"
  
	The ssh runner  
  
	!!! abstract "method: `__init__ (self, job)`"
  
		Constructor  

		- **params:**  
			`job`:    The job object  
  
	!!! abstract "method: `isRunning (self)`"
  
		Tell if the job is alive  

		- **returns:**  
			`True` if it is else `False`  
  
	!!! tip "staticmethod: `isServerAlive (server, key)`"
  
		Check if an ssh server is alive  
  
	!!! abstract "method: `kill (self)`"
  
		Kill the job  
  
	!!! abstract "method: `submit (self)`"
  
		Submit the job  

		- **returns:**  
			The `utils.cmd.Cmd` instance if succeed  
			else a `Box` object with stderr as the exception and rc as 1  
  
# module: pyppl.template
  
Template adaptor for PyPPL  
  
!!! example "class: `Template`"
  
	Template wrapper base  
  
	!!! abstract "method: `__init__ (self, source, **envs)`"
  
	!!! abstract "method: `registerEnvs (self, **envs)`"
  
		Register extra environment  

		- **params:**  
			`**envs`: The environment  
  
	!!! abstract "method: `render (self, data)`"
  
		Render the template  

		- **parmas:**  
			`data`: The data used to render  
  
!!! example "class: `TemplateJinja2`"
  
	Jinja2 template wrapper  
  
	!!! abstract "method: `__init__ (self, source, **envs)`"
  
		Initiate the engine with source and envs  

		- **params:**  
			`source`: The souce text  
			`envs`: The env data  
  
!!! example "class: `TemplateLiquid`"
  
	liquidpy template wrapper.  
  
	!!! abstract "method: `__init__ (self, source, **envs)`"
  
		Initiate the engine with source and envs  

		- **params:**  
			`source`: The souce text  
			`envs`: The env data  
  
# module: pyppl.utils
  
A set of utitities for PyPPL  
  
!!! example "function: `uid`"
  
	Calculate a short uid based on a string.  
	Safe enough, tested on 1000000 32-char strings, no repeated uid found.  
	This is used to calcuate a uid for a process  

	- **params:**  
		`s`: the base string  
		`l`: the length of the uid  
		`alphabet`: the charset used to generate the uid  

	- **returns:**  
		The uid  
  
!!! example "function: `reduce`"
  
	Python2 and Python3 compatible reduce  

	- **params:**  
		`func`: The reduce function  
		`vec`: The list to be reduced  

	- **returns:**  
		The reduced value  
  
!!! example "function: `funcsig`"
  
	Get the signature of a function  
	Try to get the source first, if failed, try to get its name, otherwise return None  

	- **params:**  
		`func`: The function  

	- **returns:**  
		The signature  
  
!!! example "function: `formatSecs`"
  
	Format a time duration  

	- **params:**  
		`seconds`: the time duration in seconds  

	- **returns:**  
		The formated string.  
		For example: "01:01:01.001" stands for 1 hour 1 min 1 sec and 1 minisec.  
  
!!! example "function: `split`"
  
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
  
!!! example "function: `briefList`"
  
	Briefly show an integer list, combine the continuous numbers.  

	- **params:**  
		`l`: The list  

	- **returns:**  
		The string to show for the briefed list.  
  
!!! example "function: `map`"
  
	Python2 and Python3 compatible map  

	- **params:**  
		`func`: The map function  
		`vec`: The list to be maped  

	- **returns:**  
		The maped list  
  
!!! example "function: `alwaysList`"
  
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
  
!!! example "function: `varname`"
  
	Get the variable name for ini  

	- **params:**  
		`maxline`: The max number of lines to retrive. Default: 20  
		`incldot`: Whether include dot in the variable name. Default: False  

	- **returns:**  
		The variable name  
  
!!! example "function: `filter`"
  
	Python2 and Python3 compatible filter  

	- **params:**  
		`func`: The filter function  
		`vec`:  The list to be filtered  

	- **returns:**  
		The filtered list  
  
!!! example "function: `dictUpdate`"
  
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
  
!!! example "function: `range`"
  
	Convert a range to list, because in python3, range is not a list  

	- **params:**  
		`r`: the range data  

	- **returns:**  
		The converted list  
  
# module: pyppl.utils.box
  
box module for PyPPL  
  
!!! example "class: `Box`"
  
	Allow dot operation for OrderedDict  
  
	!!! abstract "method: `__getattr__ (self, name)`"
  
	!!! abstract "method: `__setattr__ (self, name, val)`"
  
# module: pyppl.utils.cmd
  
cmd utility for PyPPL  
  
!!! example "function: `run`"
  
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
  
!!! example "class: `Cmd`"
  
	A command (subprocess) wapper  
  
	!!! abstract "method: `__init__ (self, cmd, raiseExc, timeout, **kwargs)`"
  
		Constructor  

		- **params:**  
			`cmd`     : The command, could be a string or a list  
			`raiseExc`: raise the expcetion or not  
			`**kwargs`: other arguments for `Popen`  
  
	!!! abstract "method: `pipe (self, cmd, **kwargs)`"
  
		Pipe another command  

		- **examples:**  
			```python  
			c = Command('seq 1 3').pipe('grep 1').run()  
			c.stdout == '1\n'  
			```  

		- **params:**  
			`cmd`: The other command  
			`**kwargs`: Other arguments for `Popen` for the other command  

		- **returns:**  
			`Command` instance of the other command  
  
	!!! abstract "method: `run (self, bg)`"
  
		Wait for the command to run  

		- **params:**  
			`bg`: Run in background or not. Default: `False`  
				- If it is `True`, `rc` and `stdout/stderr` will be default (no value retrieved).  

		- **returns:**  
			`self`  
  
# module: pyppl.utils.ps
  
ps utility for PyPPL  
  
!!! example "function: `exists`"
  
	Check whether pid exists in the current process table.  
	From https://github.com/kennethreitz/delegator.py/blob/master/delegator.py  
  
!!! example "function: `killtree`"
  
	Kill process and its children  
  
!!! example "function: `kill`"
  
	Kill a batch of processes  
  
!!! example "function: `child`"
  
	Direct children  
  
!!! example "function: `children`"
  
	Find the children of a mother process  
  
# module: pyppl.utils.safefs
  
safefs utility for PyPPL  
  
!!! example "function: `exists`"
  
	A shortcut of `SafeFs.exists`  

	- **params:**  
		`filepath`: The filepath  
		`callback`: The callback. arguments:  
			- `r` : Whether the file exists  
			- `fs`: This instance  

	- **returns:**  
		`True` if the file exists else `False`  
  
!!! example "function: `move`"
  
	A shortcut of `SafeFs.move`  

	- **params:**  
		`file1`    : File 1  
		`file2`    : File 2  
		`overwrite`: Whether overwrite file 2. Default: `True`  
		`callback` : The callback. arguments:  
			- `r` : Whether the file exists  
			- `fs`: This instance  

	- **returns:**  
		`True` if succeed else `False`  
  
!!! example "function: `gz`"
  
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
  
!!! example "class: `SafeFs`"
  
	A thread-safe file system  
  

	- **static variables:**  
  
		`TMPDIR`: The default temporary directory to store lock files  
  
		`FILETYPE_UNKNOWN`  : Unknown file type  
		`FILETYPE_NOENT`    : File does not exist  
		`FILETYPE_NOENTLINK`: A dead link (a link links to a non-existent file.  
		`FILETYPE_FILE`     : A regular file  
		`FILETYPE_FILELINK` : A link to a regular file  
		`FILETYPE_DIR`      : A regular directory  
		`FILETYPE_DIRLINK`  : A link to a regular directory  
  
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
  
	!!! abstract "method: `__init__ (self, file1, file2, tmpdir)`"
  
		Constructor  

		- **params:**  
			`file1`:  File 1  
			`file2`:  File 2. Default: `None`  
			`tmpdir`: The temporary directory used to store lock files. Default: `None` (`SafeFs.TMPDIR`)  
  
	!!! tip "staticmethod: `basename (filepath)`"
  
		Get the basename of a file  
		If it is a directory like '/a/b/c/', return `c`  

		- **params:**  
			`filepath`: The file path  

		- **returns:**  
			The basename  
  
	!!! abstract "method: `chmodX (self)`"
  
		Convert file1 to executable or add extract shebang to cmd line  

		- **returns:**  
			A list with or without the path of the interpreter as the first element and the script file as the last element  
  
	!!! abstract "method: `copy (self, overwrite, callback)`"
  
		Copy file1 to file2 thread-safely  

		- **params:**  
			`overwrite`: Allow overwrting file2? Default: `True`  
			`callback`:  The callback. arguments:  
				- `r` :  Whether the file exists  
				- `fs`:  This instance  

		- **returns:**  
			`True` if succeed else `False`  
  
	!!! abstract "method: `exists (self, callback)`"
  
		Tell if file1 exists thread-safely  

		- **params:**  
			`callback`: The callback. arguments:  
				- `r` : Whether the file exists  
				- `fs`: This instance  

		- **returns:**  
			`True` if exists else `False`  
  
	!!! abstract "method: `filesig (self, dirsig)`"
  
		Generate a signature for a file  

		- **params:**  
			`dirsig`: Whether expand the directory? Default: True  

		- **returns:**  
			The signature  
  
	!!! tip "staticmethod: `flush (fd, lastmsg, end)`"
  
		Flush a file descriptor  

		- **params:**  
			`fd`     : The file handler  
			`lastmsg`: The remaining content of last flush  
			`end`    : The file ends? Default: `False`  
  
	!!! abstract "method: `gz (self, overwrite, callback)`"
  
		Gzip file1 (tar-gzip if file1 is a directory) to file2 in a thread-safe way  

		- **params:**  
			`overwrite`: Allow overwrting file2? Default: `True`  
			`callback`:  The callback. arguments:  
				- `r` :  Whether the file exists  
				- `fs`:  This instance  

		- **returns:**  
			`True` if succeed else `False`  
  
	!!! abstract "method: `link (self, overwrite, callback)`"
  
		Link file1 to file2 thread-safely  

		- **params:**  
			`overwrite`: Allow overwrting file2? Default: `True`  
			`callback`:  The callback. arguments:  
				- `r` :  Whether the file exists  
				- `fs`:  This instance  

		- **returns:**  
			`True` if succeed else `False`  
  
	!!! abstract "method: `move (self, overwrite, callback)`"
  
		Move file1 to file2 thread-safely  

		- **params:**  
			`overwrite`: Allow overwrting file2? Default: `True`  
			`callback`:  The callback. arguments:  
				- `r` :  Whether the file exists  
				- `fs`:  This instance  

		- **returns:**  
			`True` if succeed else `False`  
  
	!!! abstract "method: `moveWithLink (self, overwrite, callback)`"
  
		Move file1 to file2 and link file2 to file1 in a thread-safe way  

		- **params:**  
			`overwrite`: Allow overwrting file2? Default: `True`  
			`callback`:  The callback. arguments:  
				- `r` :  Whether the file exists  
				- `fs`:  This instance  

		- **returns:**  
			`True` if succeed else `False`  
  
	!!! abstract "method: `remove (self, callback)`"
  
		Remove file1 thread-safely  

		- **params:**  
			`callback`: The callback. arguments:  
				- `r` : Whether the file exists  
				- `fs`: This instance  

		- **returns:**  
			`True` if succeed else `False`  
  
	!!! abstract "method: `samefile (self, callback)`"
  
		Tell if file1 and file2 are the same file in a thread-safe way  

		- **params:**  
			`callback`: The callback. arguments:  
				- `r` : Whether the file exists  
				- `fs`: This instance  

		- **returns:**  
			`True` if they are the same file else `False`  
  
	!!! abstract "method: `ungz (self, overwrite, callback)`"
  
		Ungzip file1 (tar-ungzip if file1 tar-gzipped to file2 in a thread-safe way  

		- **params:**  
			`overwrite`: Allow overwrting file2? Default: `True`  
			`callback`:  The callback. arguments:  
				- `r` :  Whether the file exists  
				- `fs`:  This instance  

		- **returns:**  
			`True` if succeed else `False`  
  
!!! example "function: `ungz`"
  
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
  
!!! example "function: `moveWithLink`"
  
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
  
!!! example "function: `link`"
  
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
  
!!! example "function: `copy`"
  
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
  
!!! example "function: `remove`"
  
	A shortcut of `SafeFs.remove`  

	- **params:**  
		`filepath`: The filepath  
		`callback`: The callback. arguments:  
			- `r` : Whether the file exists  
			- `fs`: This instance  

	- **returns:**  
		`True` if succeed else `False`  
  
# module: pyppl.utils.taskmgr
  
A thread module for PyPPL  
  
!!! example "class: `PQueue`"
  
	A modified PriorityQueue, which allows jobs to be submitted in batch  
  
	!!! abstract "method: `__init__ (self, maxsize, batch_len)`"
  
		Initialize the queue  

		- **params:**  
			`maxsize`  : The maxsize of the queue  
			`batch_len`: What's the length of a batch  
  
	!!! abstract "method: `get (self, block, timeout)`"
  
		Get an item from the queue  
  
	!!! abstract "method: `get_nowait (self)`"
  
		Get an item from the queue without waiting  
  
	!!! abstract "method: `put (self, item, block, timeout, where)`"
  
		Put item to the queue, just like `PriorityQueue.put` but with an extra argument  

		- **params:**  
			`where`: Which batch to put the item  
  
	!!! abstract "method: `put_nowait (self, item, where)`"
  
		Put item to the queue, just like `PriorityQueue.put_nowait` but with an extra argument  

		- **params:**  
			`where`: Which batch to put the item  
  
!!! example "class: `ThreadPool`"
  
	A thread manager for ThreadEx.  
  
	!!! abstract "method: `__init__ (self, nthread, initializer, initargs)`"
  
	!!! abstract "method: `join (self, interval, cleanup)`"
  
		Try to join the threads, able to respond to KeyboardInterrupt  

		- **params:**  
			`interval`: The interval/timeout to join every time.  
			`cleanup` : The cleanup function  
  
!!! example "class: `ThreadEx`"
  
	A thread able to send exception to main thread  
	thread.ex will hold the exception.  
  
	!!! abstract "method: `__init__ (self, group, target, name, args, kwargs)`"
  
	!!! abstract "method: `run (self)`"
  
