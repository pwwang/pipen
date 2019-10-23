## class: PyPPL

!!! example "class: `PyPPL (self, conf, cfgfile)`"
	The PyPPL class

	- **static variables**


		- `TIPS (list)`:  The tips for users

		- `RUNNERS (dict)`:  Registered runners

		- `COUNTER (int)`:  The counter for `PyPPL` instance

	!!! abstract "method: `__init__ (self, conf, cfgfile)`"
		PyPPL Constructor

		- **params**


			- `conf (dict)`:  the configurations for the pipeline, default: `None`

				  - Remember the profile name should be included.

			- `cfgfile (file)`:  the configuration file for the pipeline, default: `None`

	!!! tip "staticmethod: `registerRunner (runner_to_reg)`"
		Register a runner

		- **params**


			- ``runner_to_reg``:  The runner to be registered.

	!!! abstract "method: `resume (self, *args)`"
		Mark processes as to be resumed

		- **params**


			- `*args (Proc|str)`:  the processes to be marked

		- **returns**


			- `(PyPPL)`:  The pipeline object itself.

	!!! abstract "method: `resume2 (self, *args)`"
		Mark processes as to be resumed

		- **params**


			- `*args (Proc|str)`:  the processes to be marked

		- **returns**


			- `(PyPPL)`:  The pipeline object itself.

	!!! abstract "method: `run (self, profile)`"
		Run the pipeline

		- **params**


			- `profile (str|dict)`:  the profile used to run, if not found, it'll be used as runner name.

				  - default: 'default'

		- **returns**


			- `(PyPPL)`:  The pipeline object itself.

	!!! abstract "method: `start (self, *args)`"
		Set the starting processes of the pipeline

		- **params**


			- `*args (Proc|str)`:  process selectors

		- **returns**


			- `(PyPPL)`:  The pipeline object itself.

## class: Channel

!!! example "class: `Channel (iterable)`"
	The channen class, extended from `list`
	

	!!! tip "staticmethod: `_tuplize (atuple)`"
		A private method, try to convert an element to tuple
		If it's a string, convert it to `(atuple, )`
		Else if it is iterable, convert it to `tuple(atuple)`
		Otherwise, convert it to `(atuple, )`
		Notice that string is also iterable.

		- **params**


			- `atuple (str|list|tuple)`:  the element to be converted

		- **returns**


			- `(tuple)`:  The converted element

	!!! abstract "method: `attach (self, *names)`"
		Attach columns to names of Channel, so we can access each column by:
		`ch.col0` == ch.colAt(0)

		- **params**


			- `*names (str)`:  The names. Have to be as length as channel's width.

				  None of them should be Channel's property name

			- `flatten (bool)`:  Whether flatten the channel for the name being attached

	!!! abstract "method: `cbind (self, *cols)`"
		Add columns to the channel

		- **params**


			- `*cols (any)`:  The columns

		- **returns**


			- `(Channel)`:  The channel with the columns inserted.

	!!! abstract "method: `colAt (self, index)`"
		Fetch one column of a Channel

		- **params**


			- `index (int)`:  which column to fetch

		- **returns**


			- `(Channel)`:  The Channel with that column

	!!! abstract "method: `collapse (self, col)`"
		Do the reverse of expand
		length: N -> 1
		width:  M -> M

		- **params**


			- `col (int)`:      the index of the column used to collapse

		- **returns**


			- `(Channel)`:  The collapsed Channel

	!!! abstract "method: `copy (self)`"
		Copy a Channel using `copy.copy`

		- **returns**


			- `(Channel)`:  The copied Channel

	!!! tip "staticmethod: `create (alist)`"
		Create a Channel from a list

		- **params**


			- `alist (list|Channel)`:  The list, default: []

		- **returns**


			- `(Channel)`:  The Channel created from the list

	!!! abstract "method: `expand (self, col, pattern, ftype, sortby, reverse)`"
		expand the Channel according to the files in <col>, other cols will keep the same
		`[(dir1/dir2, 1)].expand (0, "*")` will expand to
		`[(dir1/dir2/file1, 1), (dir1/dir2/file2, 1), ...]`
		length: 1 -> N
		width:  M -> M

		- **params**


			- `col (int)`:  the index of the column used to expand

			- `pattern (str)`:  use a pattern to filter the files/dirs, default: `*`

			- `ftype (str)`:  the type of the files/dirs to include

				  - 'dir', 'file', 'link' or 'any' (default)

			- `sortby (str)`:   how the list is sorted

				  - 'name' (default), 'mtime', 'size'

			- `reverse (bool)`:  reverse sort. Default: False

		- **returns**


			- `(Channel)`:  The expanded Channel

	!!! abstract "method: `filter (self, func)`"
		Alias of python builtin `filter`

		- **params**


			- `func (callable)`:  the function. Default: `None`

		- **returns**


			- `(Channel)`:  The filtered Channel

	!!! abstract "method: `filterCol (self, func, col)`"
		Just filter on the specific column

		- **params**


			- `func (callable)`:  the function

			- `col (int)`:  the column to filter

		- **returns**


			- `(Channel)`:  The filtered Channel

	!!! abstract "method: `flatten (self, col)`"
		Convert a single-column Channel to a list (remove the tuple signs)
		`[(a,), (b,)]` to `[a, b]`

		- **params**


			- `col (int)`:  The column to flat. None for all columns (default)

		- **returns**


			- `(list)`:  The list converted from the Channel.

	!!! abstract "method: `fold (self, nfold)`"
		Fold a Channel. Make a row to n-length chunk rows
		```
		a1  a2  a3  a4
		b1  b2  b3  b4
		if nfold==2, fold(2) will change it to:
		a1  a2
		a3  a4
		b1  b2
		b3  b4
		```

		- **params**


			- `nfold (int)`:  the size of the chunk

		- **returns**


			- `(Channel)`:  The new Channel

	!!! tip "staticmethod: `fromArgv ()`"
		Create a Channel from `sys.argv[1:]`
		"python test.py a b c" creates a width=1 Channel
		"python test.py a,1 b,2 c,3" creates a width=2 Channel

		- **returns**


			- `(Channel)`:  The Channel created from the command line arguments

	!!! tip "staticmethod: `fromChannels (*args)`"
		Create a Channel from Channels

		- **params**


			- `*args (any)`:  The Channels or anything can be created as a `Channel`

		- **returns**


			- `(Channel)`:  The Channel merged from other Channels

	!!! tip "staticmethod: `fromFile (filename, header, skip, delimit)`"
		Create Channel from the file content
		It's like a matrix file, each row is a row for a Channel.
		And each column is a column for a Channel.

		- **params**


			- `filename (file)`:  the file

			- `header (bool)`:   Whether the file contains header. If True, will attach the header

				  - So you can use `channel.<header>` to fetch the column

			- `skip (int)`:  first lines to skip, default: `0`

			- `delimit (str)`:  the delimit for columns, default: `  `

		- **returns**


			- `(Channel)`:  A Channel created from the file

	!!! tip "staticmethod: `fromPairs (pattern)`"
		Create a width = 2 Channel from a pattern

		- **params**


			- `pattern (str)`:  the pattern

		- **returns**


			- `(Channel)`:  The Channel create from every 2 files match the pattern

	!!! tip "staticmethod: `fromParams (*pnames)`"
		Create a Channel from params

		- **params**


			- `*pnames (str)`:  The names of the option

		- **returns**


			- `(Channel)`:  The Channel created from `pyparam`.

	!!! tip "staticmethod: `fromPattern (pattern, ftype, sortby, reverse)`"
		Create a Channel from a path pattern

		- **params**


			- `pattern (str)`:  the pattern with wild cards

			- `ftype (str)`:  the type of the files/dirs to include

				  - 'dir', 'file', 'link' or 'any' (default)

			- `sortby (str)`:   how the list is sorted

				  - 'name' (default), 'mtime', 'size'

			- `reverse (bool)`:  reverse sort. Default: `False`

		- **returns**


			- `(Channel)`:  The Channel created from the path

	!!! abstract "method: `get (self, idx)`"
		Get the element of a flattened channel

		- **params**


			- `idx (int)`:  The index of the element to get. Default: 0

		- **return**


			- `(any)`:  The element

	!!! abstract "method: `insert (self, cidx, *cols)`"
		Insert columns to a channel

		- **params**


			- `cidx (int)`:  Insert into which index of column?

			- `*cols (any)`:  the columns to be bound to Channel

		- **returns**


			- `(Channel)`:  The combined Channel

	!!! abstract "method: `length (self)`"
		Get the length of a Channel
		It's just an alias of `len(chan)`

		- **returns**


			- `(int)`:  The length of the Channel

	!!! abstract "method: `map (self, func)`"
		Alias of python builtin `map`

		- **params**


			- `func (callable)`:  the function

		- **returns**


			- `(Channel)`:  The transformed Channel

	!!! abstract "method: `mapCol (self, func, col)`"
		Map for a column

		- **params**


			- `func (callable)`:  the function

			- `col (int)`:  the index of the column. Default: `0`

		- **returns**


			- `(Channel)`:  The transformed Channel

	!!! tip "staticmethod: `nones (length, width)`"
		Create a channel with `None`s

		- **params**


			- `length (int)`:  The length of the channel

			- `width (int)`:   The width of the channel

		- **returns**


			- `(Channel)`:  The created channel

	!!! abstract "method: `rbind (self, *rows)`"
		The multiple-argument versoin of `rbind`

		- **params**


			- `*rows (any)`:  the rows to be bound to Channel

		- **returns**


			- `(Channel)`:  The combined Channel

	!!! abstract "method: `reduce (self, func)`"
		Alias of python builtin `reduce`

		- **params**


			- `func (callable)`:  the function

		- **returns**


			- `(Channel)`:  The reduced value

	!!! abstract "method: `reduceCol (self, func, col)`"
		Reduce a column

		- **params**


			- `func (callable)`:  the function

			- `col (int)`:  the column to reduce

		- **returns**


			- `(Channel)`:  The reduced value

	!!! abstract "method: `repCol (self, nrep)`"
		Repeat column and return a new channel

		- **params**


			- `nrep (int)`:  how many times to repeat.

		- **returns**


			- `(Channel)`:  The new channel with repeated columns

	!!! abstract "method: `repRow (self, nrep)`"
		Repeat row and return a new channel

		- **params**


			- `nrep (int)`:  how many times to repeat.

		- **returns**


			- `(Channel)`:  The new channel with repeated rows

	!!! abstract "method: `rowAt (self, index)`"
		Fetch one row of a Channel

		- **params**


			- `index (int)`:  which row to fetch

		- **returns**


			- `(Channel)`:  The Channel with that row

	!!! abstract "method: `slice (self, start, length)`"
		Fetch some columns of a Channel

		- **params**


			- `start (int)`:   from column to start

			- `length (int)`:  how many columns to fetch, default: None (from start to the end)

		- **returns**


			- `(Channel)`:  The Channel with fetched columns

	!!! abstract "method: `split (self, flatten)`"
		Split a Channel to single-column Channels

		- **returns**


			- `(list[Channel])`:  The list of single-column Channels

	!!! abstract "method: `t (self)`"
		Transpose the channel

		- **returns**


			- `(Channel)`:  The transposed channel.

	!!! abstract "method: `transpose (self)`"
		Transpose the channel

		- **returns**


			- `(Channel)`:  The transposed channel.

	!!! abstract "method: `unfold (self, nfold)`"
		Do the reverse thing as self.fold does

		- **params**


			- `nfold (int)`:  How many rows to combind each time. default: 2

		- **returns**


			- `(Channel)`:  The unfolded Channel

	!!! abstract "method: `unique (self)`"
		Make the channel unique, remove duplicated rows
		Try to keep the order

		- **returns**


			- `(Channel)`:  The channel with unique rows.

	!!! abstract "method: `width (self)`"
		Get the width of a Channel

		- **returns**


			- `(int)`:  The width of the Channel

## class: Job

!!! example "class: `Job (self, index, proc)`"
	Describes a job, also as a base class for runner

	- **static variables**


		- `POLL_INTERVAL (int)`:  The interval between each job state polling.

	!!! abstract "method: `__init__ (self, index, proc)`"
		Initiate a job

		- **params**


			- `index (int)`:   The index of the job.

			- `proc (Proc)`:  The process of the job.

	!!! abstract "method: `build (self)`"
		Initiate a job, make directory and prepare input, output and script.
		

	!!! abstract "method: `cache (self)`"
		Truly cache the job (by signature)
		

	!!! note "property: `data ()`"
		Data for rendering templates

		- **returns**


			- `(dict)`:  The data used to render the templates.

	!!! abstract "method: `done (self, cached)`"
		Do some cleanup when job finished

		- **params**


			- `cached (bool)`:  Whether this is running for a cached job.

	!!! abstract "method: `export (self)`"
		Export the output files

	!!! abstract "method: `isExptCached (self)`"
		Prepare to use export files as cached information

		- **returns**


			- `(bool)`:  Whether the job is export-cached.

	!!! abstract "method: `isForceCached (self)`"
		Force the job to be cached.
		If the output was not generated in previous run, generate dry-run results for it.
		

	!!! abstract "method: `isRunningImpl (self)`"
		Implemetation of telling whether the job is running

		- **returns**


			- `(bool)`:  Should return whether a job is running.

	!!! abstract "method: `isTrulyCached (self)`"
		Check whether a job is truly cached (by signature)

		- **returns**


			- `(bool)`:  Whether the job is truly cached.

	!!! abstract "method: `kill (self)`"
		Kill the job

		- **returns**


			- `(bool)`:  `True` if succeeds else `False`

	!!! abstract "method: `killImpl (self)`"
		Implemetation of killing a job

	!!! abstract "method: `logger (self, *args, **kwargs)`"
		A logger wrapper to avoid instanize a logger object for each job

		- **params**


			- `*args (str)`:  messages to be logged.

			- `*kwargs`:  Other parameters for the logger.

	!!! note "property: `pid ()`"
		Get pid of the job

		- **returns**


			- `(str)`:  The job id, could be the process id or job id for other platform.

	!!! abstract "method: `poll (self)`"
		Check the status of a running job

		- **returns**


			- `(bool|str)`:  `True/False` if rcfile generared and whether job succeeds,         otherwise returns `running`.

	!!! note "property: `rc ()`"
		Get the return code

		- **returns**


			- `(int)`:  The return code.

	!!! abstract "method: `report (self)`"
		Report the job information to log
		

	!!! abstract "method: `reset (self)`"
		Clear the intermediate files and output files

	!!! abstract "method: `retry (self)`"
		If the job is available to retry

		- **returns**


			- `(bool|str)`:  `ignore` if `errhow` is `ignore`, otherwise         returns whether we could submit the job to retry.

	!!! note "property: `scriptParts ()`"
		Prepare parameters for script wrapping

		- **returns**


			- `(Box)`:  A `Box` containing the parts to wrap the script.

	!!! abstract "method: `showError (self, totalfailed)`"
		Show the error message if the job failed.

		- **params**


			- `totalfailed (int)`:  Total number of jobs failed.

	!!! abstract "method: `signature (self)`"
		Calculate the signature of the job based on the input/output and the script

		- **returns**


			- `(Box)`:  The signature of the job

	!!! abstract "method: `submit (self)`"
		Submit the job

		- **returns**


			- `(bool)`:  `True` if succeeds else `False`

	!!! abstract "method: `submitImpl (self)`"
		Implemetation of submission

	!!! abstract "method: `succeed (self)`"
		Tell if a job succeeds.
		Check whether output files generated, expectation met and return code met.

		- **return**


			- `(bool)`:  `True` if succeeds else `False`

	!!! abstract "method: `wrapScript (self)`"
		Wrap the script to run
		

## class: Jobmgr

!!! example "class: `Jobmgr (self, jobs)`"
	Job manager

	!!! abstract "method: `__init__ (self, jobs)`"
		Job manager constructor

		- **params**


			- `jobs (list)`:  All jobs of a process

	!!! abstract "method: `cleanup (self, ex)`"
		Cleanup the pipeline when
		- Ctrl-c hit
		- error encountered and `proc.errhow` = 'terminate'

		- **params**


			- `ex (Exception)`:  The exception raised by workers

	!!! abstract "method: `killWorker (self, killq)`"
		The killing worker to kill the jobs

	!!! abstract "method: `progressbar (self, event)`"
		Generate the progress bar.

		- **params**


			- `event (StateMachine event)`:  The event including job as model.

	!!! abstract "method: `start (self)`"
		Start the queue.
		

	!!! abstract "method: `worker (self)`"
		The worker to build, submit and poll the jobs

## class: Proc

!!! example "class: `Proc (self, id, tag, desc, **kwargs)`"
	The Proc class defining a process

	- **static variables**


		- `ALIAS      (dict)`:  The alias for the properties

		- `DEPRECATED (dict)`:  Deprecated property names

		- `OUT_VARTYPE    (list)`:  Variable types for output

		- `OUT_FILETYPE   (list)`:  File types for output

		- `OUT_DIRTYPE    (list)`:  Directory types for output

		- `OUT_STDOUTTYPE (list)`:  Stdout types for output

		- `OUT_STDERRTYPE (list)`:  Stderr types for output

		- `IN_VARTYPE   (list)`:  Variable types for input

		- `IN_FILETYPE  (list)`:  File types for input

		- `IN_FILESTYPE (list)`:  Files types for input

		- `EX_GZIP (list)`:  `exhow` value to gzip output files while exporting them

		- `EX_COPY (list)`:  `exhow` value to copy output files while exporting them

		- `EX_MOVE (list)`:  `exhow` value to move output files while exporting them

		- `EX_LINK (list)`:  `exhow` value to link output files while exporting them

	!!! abstract "method: `__init__ (self, id, tag, desc, **kwargs)`"
		Proc constructor

		- **params**


			- `tag  (str)   `:  The tag of the process

			- `desc (str)   `:  The description of the process

			- `id   (str)   `:  The identify of the process

			- `**kwargs`:  Other properties of the process, which can be set by `proc.xxx` later.

	!!! abstract "method: `copy (self, id, tag, desc)`"
		Copy a process

		- **params**


			- `id (str)`:  The new id of the process, default: `None` (use the varname)

			- `tag (str)`:    The tag of the new process, default: `None` (used the old one)

			- `desc (str)`:   The desc of the new process, default: `None` (used the old one)

		- **returns**


			- `(Proc)`:  The new process

	!!! abstract "method: `name (self, procset)`"
		Get my name include `procset`, `id`, `tag`

		- **params**


			- `procset (bool)`:  Whether include the procset name or not.

		- **returns**


			- `(str)`:  the name

	!!! note "property: `procset ()`"
		Get the name of the procset

		- **returns**


			- `(str)`:  The procset name

	!!! abstract "method: `run (self, profile, config)`"
		Run the process with a profile and/or a configuration

		- **params**


			- `profile (str)`:  The profile from a configuration file.

			- `config (dict)`:  A configuration passed to PyPPL construct.

	!!! note "property: `size ()`"
		Get the size of the  process

		- **returns**


			- `(int)`:  The number of jobs

	!!! note "property: `suffix ()`"
		Calcuate a uid for the process according to the configuration
		The philosophy:
		1. procs from different script must have different suffix (sys.argv[0])
		2. procs from the same script:
		  - procs with different id or tag have different suffix
		  - procs with different input have different suffix (depends, input)

		- **returns**


			- `(str)`:  The uniq id of the process

## class: ProcSet

!!! example "class: `ProcSet (self, *procs, **kwargs)`"
	The ProcSet for a set of processes
	

	!!! abstract "method: `__getitem__ (self, item, _ignore_default)`"
		Process selector, always return Proxy object

		- **params**


			- `item (any)`:  The process selector.

		- **returns**


			- `(Proxy)`:  The processes match the item.

	!!! abstract "method: `__init__ (self, *procs, **kwargs)`"
		Constructor

		- **params**


			- `*procs (Proc) `:  the set of processes

			- `**kwargs`:  Other arguments to instantiate a `ProcSet`

				  depends (bool): Whether auto deduce depends. Default: `True`

				  id (str): The id of the procset. Default: `None` (the variable name)

				  tag (str): The tag of the processes. Default: `None`

				  copy (bool): Whether copy the processes or just use them. Default: `True`

	!!! abstract "method: `copy (self, id, tag, depends)`"
		Like `proc`'s `copy` function, copy a procset. Each processes will be copied.

		- **params**


			- `id (str)`:  Use a different id if you don't want to use the variant name

			- `tag (str)`:  The new tag of all copied processes

			- `depends (bool)`:  Whether to copy the dependencies or not. Default: True

				  - dependences for processes in starts will not be copied

		- **returns**


			- `(ProcSet)`:  The new procset

	!!! abstract "method: `delegate (self, *procs)`"
		Delegate process attributes to procset.

		- **params**


			- `*procs (str|Proc)`:  The first argument is the name of the attributes.

				  - The rest of them should be `Proc`s or `Proc` selectors.

	!!! abstract "method: `delegated (self, name)`"
		Get the detegated processes by specific attribute name

		- **params**


			- `name (str)`:  the attribute name to query

		- **returns**


			- `(Proxy)`:  The set of processes

	!!! abstract "method: `module (self, name)`"
		A decorator used to define a module.

		- **params**


			- `name (callable|str)`:  The function to be decorated or the name of the module.

		- **returns**


			- `(callable)`:  The decorator

	!!! abstract "method: `restoreStates (self)`"
		Restore the initial state of a procset
		

## class: ProcTree

!!! example "class: `ProcTree (self)`"
	A tree of processes.

	- **static variables**


		- `NODES (OrderedDict)`:  The processes registered.

	!!! abstract "method: `__init__ (self)`"
		ProcTruee constructor
		

	!!! tip "staticmethod: `check (proc)`"
		Check whether a process with the same id and tag exists

		- **params**


			- `proc (Proc)`:  The `Proc` instance

	!!! abstract "method: `checkPath (self, proc)`"
		Check whether paths of a process can start from a start process

		- **params**


			- `proc (Proc)`:  The process

		- **returns**


			- `(bool|list)`:  `True` if all paths can pass, otherwise first failed path.

	!!! abstract "method: `getAllPaths (self)`"
		Get all paths of the pipeline, only used to be displayed in debug

		- **yields**


			- `(list[Proc])`:  The paths (end to start).

	!!! abstract "method: `getEnds (self)`"
		Get the end processes

		- **returns**


			- `(list[Proc])`:  The end processes

	!!! tip "staticmethod: `getNext (proc)`"
		Get next processes of process

		- **params**


			- `proc (Proc)`:  The `Proc` instance

		- **returns**


			- `(list[Proc])`:  The processes depend on this process

	!!! tip "staticmethod: `getNextStr (proc)`"
		Get the names of processes depend on a process

		- **params**


			- `proc (Proc)`:  The `Proc` instance

		- **returns**


			- `(str)`:  The names

	!!! abstract "method: `getNextToRun (cls)`"
		Get the process to run next

		- **returns**


			- `(Proc)`:  The process next to run

	!!! abstract "method: `getPaths (self, proc, proc0)`"
		Infer the path to a process
		```
		p1 -> p2 -> p3
		    p4  _/
		Paths for p3: [[p4], [p2, p1]]
		```

		- **params**


			- `proc (Proc)`:  The process

			- `proc0 (Proc)`:  The original process, because this function runs recursively.

		- **returns**


			- `(list[list])`:  The path to the process.

	!!! abstract "method: `getPathsToStarts (self, proc)`"
		Filter the paths with start processes

		- **params**


			- `proc (Proc)`:  The process

		- **returns**


			- `(list[list])`:  The filtered path

	!!! tip "staticmethod: `getPrevStr (proc)`"
		Get the names of processes a process depends on

		- **params**


			- `proc (Proc)`:  The `Proc` instance

		- **returns**


			- `(str)`:  The names

	!!! abstract "method: `getStarts (self)`"
		Get the start processes

		- **returns**


			- `(list[Proc])`:  The start processes

	!!! abstract "method: `init (self)`"
		Set the status of all `ProcNode`s
		

	!!! tip "staticmethod: `register (*procs)`"
		Register the process

		- **params**


			- `*procs (Proc)`:  The `Proc` instance

	!!! tip "staticmethod: `reset ()`"
		Reset the status of all `ProcNode`s
		

	!!! abstract "method: `setStarts (self, starts)`"
		Set the start processes

		- **params**


			- `starts (list[Proc])`:  The start processes

## class: Logger

!!! example "class: `Logger (self, name, bake)`"
	A wrapper of logger
	

	!!! abstract "method: `__getattr__ (self, name)`"
		Allows logger.info way to specify the level

		- **params**


			- `name (str)`:  The level name.

		- **returns**


			- `(callable)`:  The logger with the level

	!!! abstract "method: `__getitem__ (self, name)`"
		Alias of `__getattr__`

	!!! abstract "method: `__init__ (self, name, bake)`"
		The logger wrapper construct

		- **params**


			- `name (str)`:  The logger name. Default: `PyPPL`

			- `bake (dict)`:  The arguments to bake a new logger.

	!!! abstract "method: `bake (self, **kwargs)`"
		Bake the logger with certain arguments

		- **params**


			- `*kwargs`:  arguments used to bake a new logger

		- **returns**


			- `(Logger)`:  The new logger.

	!!! abstract "method: `init (self, conf)`"
		Initiate the logger, called by the construct,
		Just in case, we want to change the config and
		Reinitiate the logger.

		- **params**


			- `conf (Config)`:  The configuration used to initiate logger.

	!!! tip "staticmethod: `initLevels (levels, leveldiffs)`"
		Initiate the levels, get real levels.

		- **params**


			- `levels (str|list)`:  The levels or level names

			- `leveldiffs (str|list)`:  The diffs of levels

		- **returns**


			- `(set)`:  The real levels.

	!!! note "property: `pbar ()`"
		Mark the record as a progress record.
		Allow `logger.pbar.info` access

		- **returns**


			- `(Logger)`:  The Logger object itself

## class: Template

!!! example "class: `Template (self, source, **envs)`"
	Template wrapper base class

	- **static variables**


		- `DEFAULT_ENVS (dict)`:  The default environment.

	!!! abstract "method: `__init__ (self, source, **envs)`"
		Template construct
		

	!!! abstract "method: `registerEnvs (self, **envs)`"
		Register extra environment

		- **params**


			- `**envs`:  The environment

	!!! abstract "method: `render (self, data)`"
		Render the template

		- **parmas**


			- `data (dict)`:  The data used to render

## class: TemplateLiquid

!!! example "class: `TemplateLiquid (self, source, **envs)`"
	liquidpy template wrapper.
	

## class: TemplateJinja2

!!! example "class: `TemplateJinja2 (self, source, **envs)`"
	Jinja2 template wrapper
	

