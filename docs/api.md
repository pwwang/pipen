## pyppl.template


- **desc**

  Template adaptor for PyPPL

- **variables**

  - `DEFAULT_ENVS (dict)`:  The default environments for templates

!!! example "class: `Template`"

  Base class wrapper to wrap template for PyPPL


  !!! abstract "method: `__init__(self, source, **envs)`"

    Template construct


  !!! abstract "method: `register_envs(self, **envs)`"

    Register extra environment

    - **params**

      - `**envs`:  The environment

  !!! abstract "method: `render(self, data)`"

    Render the template

    - **parmas**

      - `data (dict)`:  The data used to render

!!! example "class: `TemplateJinja2`"

  Jinja2 template wrapper


  !!! abstract "method: `register_envs(self, **envs)`"

    Register extra environment

    - **params**

      - `**envs`:  The environment

  !!! abstract "method: `render(self, data)`"

    Render the template

    - **parmas**

      - `data (dict)`:  The data used to render

!!! example "class: `TemplateLiquid`"

  liquidpy template wrapper.


  !!! abstract "method: `register_envs(self, **envs)`"

    Register extra environment

    - **params**

      - `**envs`:  The environment

  !!! abstract "method: `render(self, data)`"

    Render the template

    - **parmas**

      - `data (dict)`:  The data used to render
## pyppl.procset


- **desc**

  The procset for a set of procs

!!! example "class: `ProcSet`"

  The ProcSet for a set of processes


  !!! abstract "method: `__init__(self, *procs)`"

    Constructor

    - **params**

      - `*procs (Proc) `:  the set of processes

      - `**kwargs`:  Other arguments to instantiate a `ProcSet`

          depends (bool): Whether auto deduce depends. Default: `True`

          id (str): The id of the procset. Default: `None` (the variable name)

          tag (str): The tag of the processes. Default: `None`

          copy (bool): Whether copy the processes or just use them. Default: `True`

  !!! abstract "method: `copy(self, id, tag, depends)`"

    Like `proc`'s `copy` function, copy a procset. Each processes will be copied.

    - **params**

      - `id (str)`:  Use a different id if you don't want to use the variant name

      - `tag (str)`:  The new tag of all copied processes

      - `depends (bool)`:  Whether to copy the dependencies or not. Default: True

          - dependences for processes in starts will not be copied

    - **returns**

      - `(ProcSet)`:  The new procset

  !!! abstract "method: `delegate(self, attr, *procs)`"

    Delegate process attributes to procset.

    - **params**

      - `*procs (str|Proc)`:  The first argument is the name of the attributes.

          - The rest of them should be `Proc`s or `Proc` selectors.

  !!! abstract "method: `delegated(self, name)`"

    Get the detegated processes by specific attribute name

    - **params**

      - `name (str)`:  the attribute name to query

    - **returns**

      - `(Proxy)`:  The set of processes

  !!! abstract "method: `module(self, name)`"

    A decorator used to define a module.

    - **params**

      - `name (callable|str)`:  The function to be decorated or the name of the module.

    - **returns**

      - `(callable)`:  The decorator

  !!! abstract "method: `restore_states(self)`"

    Restore the initial state of a procset

## pyppl.proc


- **desc**

  Process for PyPPL

!!! example "class: `Proc`"

  Process of a pipeline


  !!! note "property: `cache`"

    Should we cache the results or read results from cache?

  !!! note "property: `id`"

    The identity of the process

  !!! note "property: `tag`"

    The tag of the process

  !!! abstract "method: `add_config(self, name, default, converter, runtime)`"

    Add a plugin configuration

    - **params**

      - `name (str)`:  The name of the plugin configuration

      - `default (any)`:  The default value

      - `converter (callable)`:  The converter function for the value

      - `runtime (str)`:  How should we deal with it while         runtime_config is passed and its setcounter > 1

          - override: Override the value

          - update: Update the value if it's a dict otherwise override its

          - ignore: Ignore the value from runtime_config

  !!! abstract "method: `copy(self, id, **kwargs)`"

    Copy a process to a new one
    Depends and nexts will be copied

    - **params**

      - `id`:  The id of the new process

      - `kwargs`:  Other arguments for constructing a process

  !!! abstract "method: `run(self, runtime_config)`"

    Run the process

    - **params**

      - `runtime_config (simpleconf.Config)`:  The runtime configuration
## pyppl.utils


- **desc**

  Utility functions for PyPPL

!!! abstract "method: `always_list(data, trim)`"

  Convert a string or a list with element

  - **params**

    - ``data``:  the data to be converted

    - ``trim``:  trim the whitespaces for each item or not. Default: True

  - **examples**

      ```python

      data = ["a, b, c", "d"]

      ret  = always_list (data)

      # ret == ["a", "b", "c", "d"]

      ```

  - **returns**

      The split list

!!! abstract "method: `brief_list(blist, base)`"

  Briefly show an integer list, combine the continuous numbers.

  - **params**

    - `blist`:  The list

  - **returns**

    - `(str)`:  The string to show for the briefed list.

!!! abstract "method: `chmod_x(filepath)`"

  Convert file1 to executable or add extract shebang to cmd line

  - **params**

    - `filepath (path)`:  The file path

  - **returns**

    - `(list)`:  with or without the path of the interpreter as the first element

      and the script file as the last element

!!! abstract "method: `expand_numbers(numbers)`"

  Expand a descriptive numbers like '0,3-5,7' into read numbers:
  [0,3,4,5,7]

  - **params**

    - `numbers (str)`:  The string of numbers to expand.

  - **returns**

      (list) The real numbers

!!! abstract "method: `filesig(filepath, dirsig)`"

  Generate a signature for a file

  - **params**

    - ``dirsig``:  Whether expand the directory? Default: True

  - **returns**

      The signature

!!! abstract "method: `format_secs(seconds)`"

  Format a time duration

  - **params**

    - ``seconds``:  the time duration in seconds

  - **returns**

      The formated string.

    - `For example`:  "01:01:01.001" stands for 1 hour 1 min 1 sec and 1 minisec.

!!! abstract "method: `funcsig(func)`"

  Get the signature of a function
  Try to get the source first, if failed, try to get its name, otherwise return None

  - **params**

    - ``func``:  The function

  - **returns**

      The signature

!!! abstract "method: `name2filename(name)`"

  Convert any name to a valid filename

  - **params**

    - `name (str)`:  The name to be converted

  - **returns**

    - `(str)`:  The converted name

!!! abstract "method: `try_deepcopy(obj, _recurvise)`"

  Try do deepcopy an object. If fails, just do a shallow copy.

  - **params**

    - `obj (any)`:  The object

    - `_recurvise (bool)`:  A flag to avoid deep recursion

  - **returns**

    - `(any)`:  The copied object

!!! example "class: `PQueue`"

  A modified PriorityQueue, which allows jobs to be submitted in batch


  !!! abstract "method: `__init__(self, maxsize, batch_len)`"

    A Priority Queue for PyPPL jobs
      0                              0 done,             wait for 1
        1        start 0    1        start 1             start 2
        2      ------>  0   2      ------>      2      --------->
          3                   3               1   3                    3
          4                   4                   4                2   4
                                       1

    - **params**

      - `maxsize  `:  The maxsize of the queue. Default: None

      - `batch_len`:  What's the length of a batch

  !!! abstract "method: `get(self)`"

    Get an item from the queue

    - **returns**

      - `(int, int)`:  The index of the item and the batch of it

  !!! abstract "method: `put(self, item, batch)`"

    Put item to any batch

    - **params**

      - `item (any)`:  item to put

      - `batch (int)`:  target batch

  !!! abstract "method: `put_next(self, item, batch)`"

    Put item to next batch

    - **params**

      - `item (any)`:  item to put

      - `batch (int)`:  current batch
## pyppl.job


- **desc**

  Job for PyPPL

!!! example "class: `Job`"

  Job class

  - **arguments**

    - `index (int)`:  The index of the job

    - `proc (Proc)`:  The process

  !!! note "property: `logger`"

    A logger wrapper to avoid instanize a logger object for each job

    - **params**

      - `*args (str)`:  messages to be logged.

      - `*kwargs`:  Other parameters for the logger.

  !!! note "property: `signature`"

    Calculate the signature of the job based on the input/output and the script.
    If file does not exist, it will not be in the signature.
    The signature is like:
    ```json
    {
      "i": {
        "invar:var": <invar>,
        "infile:file": <infile>,
        "infiles:files": [<infiles...>]
      },
      "o": {
        "outvar:var": <outvar>,
        "outfile:file": <outfile>,
        "outdir:dir": <outdir>
      }
      "mtime": <max mtime of input and script>,
    }
    ```

    - **returns**

      - `(Diot)`:  The signature of the job

  !!! abstract "method: `add_config(self, name, default, converter)`"

    Add a config to plugin config, used for plugins

    - **params**

      - `name (str)`:  The name of the config.

          To proptect your config, better use a prefix

      - `default (Any)`:  The default value for the config

      - `converter (callable)`:  The converter for the value

  !!! abstract "method: `build(self)`"

    Initiate a job, make directory and prepare input, output and script.


  !!! abstract "method: `cache(self)`"

    Truly cache the job (by signature)


  !!! abstract "method: `done(self, cached, status)`"

    Do some cleanup when job finished

    - **params**

      - `cached (bool)`:  Whether this is running for a cached job.

  !!! abstract "method: `kill(self)`"

    Kill the job

    - **returns**

      - `(bool)`:  `True` if succeeds else `False`

  !!! abstract "method: `poll(self)`"

    Check the status of a running job

    - **returns**

      - `(bool|str)`:  `True/False` if rcfile generared and whether job succeeds,         otherwise returns `running`.

  !!! abstract "method: `reset(self)`"

    Clear the intermediate files and output files

  !!! abstract "method: `retry(self)`"

    If the job is available to retry

    - **returns**

      - `(bool|str)`:  `ignore` if `errhow` is `ignore`, otherwise         returns whether we could submit the job to retry.

  !!! abstract "method: `submit(self)`"

    Submit the job

    - **returns**

      - `(bool)`:  `True` if succeeds else `False`
## pyppl.pyppl


- **desc**

  Pipeline for PyPPL

- **variables**

  - `SEPARATOR_LEN (int)`:  the length of the separators in log

  - `PROCESSES (set)`:  The process pool where the processes are registered

  - `TIPS (list)`:  Some tips to show in log

  - `PIPELINES (dict)`:  Exists pipelines

!!! example "class: `PyPPL`"

  The class for the whole pipeline


  !!! abstract "method: `__init__(self, config, name, config_files, **kwconfigs)`"

    The construct for PyPPL

    - **params**

      - `config (dict)`:  the runtime configuration for the pipeline

      - `name (str)`:  The name of the pipeline

      - `config_files (list)`:  A list of runtime configuration files

      - `**kwconfigs`:  flattened runtime configurations, for example

          - you can do: `PyPPL(forks = 10)`, or even

          - `PyPPL(logger_level = 'debug')`

  !!! abstract "method: `method(self, func)`"

    Add a method to PyPPL object

    - **params**

      - `func (callable)`:  the function to add

  !!! abstract "method: `run(self, profile)`"

    Run the pipeline with certain profile

    - **params**

      - `profile (str)`:  The profile name

  !!! abstract "method: `start(self, *anything)`"

    Set the start processes for the pipeline

    - **params**

      - `*anything`:  Anything that can be converted to processes

          - Could be a string or a wildcard to search for processes

          - or the process itself
## pyppl.channel


- **desc**

  Channel for pyppl

!!! example "class: `Channel`"

  The channen class, extended from `list`


  !!! abstract "method: `attach(self, *names)`"

    Attach columns to names of Channel, so we can access each column by:
    `ch.col0` == ch.colAt(0)

    - **params**

      - `*names (str)`:  The names. Have to be as length as channel's width.

          None of them should be Channel's property name

      - `flatten (bool)`:  Whether flatten the channel for the name being attached

  !!! abstract "method: `cbind(self, *cols)`"

    Add columns to the channel

    - **params**

      - `*cols (any)`:  The columns

    - **returns**

      - `(Channel)`:  The channel with the columns inserted.

  !!! abstract "method: `colAt(self, index)`"

    Fetch one column of a Channel

    - **params**

      - `index (int)`:  which column to fetch

    - **returns**

      - `(Channel)`:  The Channel with that column

  !!! abstract "method: `col_at(self, index)`"

    Fetch one column of a Channel

    - **params**

      - `index (int)`:  which column to fetch

    - **returns**

      - `(Channel)`:  The Channel with that column

  !!! abstract "method: `collapse(self, col)`"

    Do the reverse of expand
    length: N -> 1
    width:  M -> M

    - **params**

      - `col (int)`:      the index of the column used to collapse

    - **returns**

      - `(Channel)`:  The collapsed Channel

  !!! abstract "method: `copy(self)`"

    Copy a Channel using `copy.copy`

    - **returns**

      - `(Channel)`:  The copied Channel

  !!! abstract "method: `create(alist)`"

    Create a Channel from a list

    - **params**

      - `alist (list|Channel)`:  The list, default: []

    - **returns**

      - `(Channel)`:  The Channel created from the list

  !!! abstract "method: `expand(self, col, pattern, ftype, sortby, reverse)`"

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

  !!! abstract "method: `filter(self, func)`"

    Alias of python builtin `filter`

    - **params**

      - `func (callable)`:  the function. Default: `None`

    - **returns**

      - `(Channel)`:  The filtered Channel

  !!! abstract "method: `filterCol(self, func, col)`"

    Just filter on the specific column

    - **params**

      - `func (callable)`:  the function

      - `col (int)`:  the column to filter

    - **returns**

      - `(Channel)`:  The filtered Channel

  !!! abstract "method: `filter_col(self, func, col)`"

    Just filter on the specific column

    - **params**

      - `func (callable)`:  the function

      - `col (int)`:  the column to filter

    - **returns**

      - `(Channel)`:  The filtered Channel

  !!! abstract "method: `flatten(self, col)`"

    Convert a single-column Channel to a list (remove the tuple signs)
    `[(a,), (b,)]` to `[a, b]`

    - **params**

      - `col (int)`:  The column to flat. None for all columns (default)

    - **returns**

      - `(list)`:  The list converted from the Channel.

  !!! abstract "method: `fold(self, nfold)`"

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

  !!! abstract "method: `fromArgv()`"

    Create a Channel from `sys.argv[1:]`
    "python test.py a b c" creates a width=1 Channel
    "python test.py a,1 b,2 c,3" creates a width=2 Channel

    - **returns**

      - `(Channel)`:  The Channel created from the command line arguments

  !!! abstract "method: `fromChannels(*args)`"

    Create a Channel from Channels

    - **params**

      - `*args (any)`:  The Channels or anything can be created as a `Channel`

    - **returns**

      - `(Channel)`:  The Channel merged from other Channels

  !!! abstract "method: `fromFile(filename, header, skip, delimit)`"

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

  !!! abstract "method: `fromPairs(pattern)`"

    Create a width = 2 Channel from a pattern

    - **params**

      - `pattern (str)`:  the pattern

    - **returns**

      - `(Channel)`:  The Channel create from every 2 files match the pattern

  !!! abstract "method: `fromParams(*pnames)`"

    Create a Channel from params

    - **params**

      - `*pnames (str)`:  The names of the option

    - **returns**

      - `(Channel)`:  The Channel created from `pyparam`.

  !!! abstract "method: `fromPattern(pattern, ftype, sortby, reverse)`"

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

  !!! abstract "method: `from_argv()`"

    Create a Channel from `sys.argv[1:]`
    "python test.py a b c" creates a width=1 Channel
    "python test.py a,1 b,2 c,3" creates a width=2 Channel

    - **returns**

      - `(Channel)`:  The Channel created from the command line arguments

  !!! abstract "method: `from_channels(*args)`"

    Create a Channel from Channels

    - **params**

      - `*args (any)`:  The Channels or anything can be created as a `Channel`

    - **returns**

      - `(Channel)`:  The Channel merged from other Channels

  !!! abstract "method: `from_file(filename, header, skip, delimit)`"

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

  !!! abstract "method: `from_pairs(pattern)`"

    Create a width = 2 Channel from a pattern

    - **params**

      - `pattern (str)`:  the pattern

    - **returns**

      - `(Channel)`:  The Channel create from every 2 files match the pattern

  !!! abstract "method: `from_params(*pnames)`"

    Create a Channel from params

    - **params**

      - `*pnames (str)`:  The names of the option

    - **returns**

      - `(Channel)`:  The Channel created from `pyparam`.

  !!! abstract "method: `from_pattern(pattern, ftype, sortby, reverse)`"

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

  !!! abstract "method: `get(self, idx)`"

    Get the element of a flattened channel

    - **params**

      - `idx (int)`:  The index of the element to get. Default: 0

    - **return**

      - `(any)`:  The element

  !!! abstract "method: `insert(self, cidx, *cols)`"

    Insert columns to a channel

    - **params**

      - `cidx (int)`:  Insert into which index of column?

      - `*cols (any)`:  the columns to be bound to Channel

    - **returns**

      - `(Channel)`:  The combined Channel

  !!! abstract "method: `length(self)`"

    Get the length of a Channel
    It's just an alias of `len(chan)`

    - **returns**

      - `(int)`:  The length of the Channel

  !!! abstract "method: `map(self, func)`"

    Alias of python builtin `map`

    - **params**

      - `func (callable)`:  the function

    - **returns**

      - `(Channel)`:  The transformed Channel

  !!! abstract "method: `mapCol(self, func, col)`"

    Map for a column

    - **params**

      - `func (callable)`:  the function

      - `col (int)`:  the index of the column. Default: `0`

    - **returns**

      - `(Channel)`:  The transformed Channel

  !!! abstract "method: `map_col(self, func, col)`"

    Map for a column

    - **params**

      - `func (callable)`:  the function

      - `col (int)`:  the index of the column. Default: `0`

    - **returns**

      - `(Channel)`:  The transformed Channel

  !!! abstract "method: `nones(length, width)`"

    Create a channel with `None`s

    - **params**

      - `length (int)`:  The length of the channel

      - `width (int)`:   The width of the channel

    - **returns**

      - `(Channel)`:  The created channel

  !!! abstract "method: `rbind(self, *rows)`"

    The multiple-argument versoin of `rbind`

    - **params**

      - `*rows (any)`:  the rows to be bound to Channel

    - **returns**

      - `(Channel)`:  The combined Channel

  !!! abstract "method: `reduce(self, func)`"

    Alias of python builtin `reduce`

    - **params**

      - `func (callable)`:  the function

    - **returns**

      - `(Channel)`:  The reduced value

  !!! abstract "method: `reduceCol(self, func, col)`"

    Reduce a column

    - **params**

      - `func (callable)`:  the function

      - `col (int)`:  the column to reduce

    - **returns**

      - `(Channel)`:  The reduced value

  !!! abstract "method: `reduce_col(self, func, col)`"

    Reduce a column

    - **params**

      - `func (callable)`:  the function

      - `col (int)`:  the column to reduce

    - **returns**

      - `(Channel)`:  The reduced value

  !!! abstract "method: `repCol(self, nrep)`"

    Repeat column and return a new channel

    - **params**

      - `nrep (int)`:  how many times to repeat.

    - **returns**

      - `(Channel)`:  The new channel with repeated columns

  !!! abstract "method: `repRow(self, nrep)`"

    Repeat row and return a new channel

    - **params**

      - `nrep (int)`:  how many times to repeat.

    - **returns**

      - `(Channel)`:  The new channel with repeated rows

  !!! abstract "method: `rep_col(self, nrep)`"

    Repeat column and return a new channel

    - **params**

      - `nrep (int)`:  how many times to repeat.

    - **returns**

      - `(Channel)`:  The new channel with repeated columns

  !!! abstract "method: `rep_row(self, nrep)`"

    Repeat row and return a new channel

    - **params**

      - `nrep (int)`:  how many times to repeat.

    - **returns**

      - `(Channel)`:  The new channel with repeated rows

  !!! abstract "method: `rowAt(self, index)`"

    Fetch one row of a Channel

    - **params**

      - `index (int)`:  which row to fetch

    - **returns**

      - `(Channel)`:  The Channel with that row

  !!! abstract "method: `row_at(self, index)`"

    Fetch one row of a Channel

    - **params**

      - `index (int)`:  which row to fetch

    - **returns**

      - `(Channel)`:  The Channel with that row

  !!! abstract "method: `slice(self, start, length)`"

    Fetch some columns of a Channel

    - **params**

      - `start (int)`:   from column to start

      - `length (int)`:  how many columns to fetch, default: None (from start to the end)

    - **returns**

      - `(Channel)`:  The Channel with fetched columns

  !!! abstract "method: `split(self, flatten)`"

    Split a Channel to single-column Channels

    - **returns**

      - `(list[Channel])`:  The list of single-column Channels

  !!! abstract "method: `t(self)`"

    Transpose the channel

    - **returns**

      - `(Channel)`:  The transposed channel.

  !!! abstract "method: `transpose(self)`"

    Transpose the channel

    - **returns**

      - `(Channel)`:  The transposed channel.

  !!! abstract "method: `unfold(self, nfold)`"

    Do the reverse thing as self.fold does

    - **params**

      - `nfold (int)`:  How many rows to combind each time. default: 2

    - **returns**

      - `(Channel)`:  The unfolded Channel

  !!! abstract "method: `unique(self)`"

    Make the channel unique, remove duplicated rows
    Try to keep the order

    - **returns**

      - `(Channel)`:  The channel with unique rows.

  !!! abstract "method: `width(self)`"

    Get the width of a Channel

    - **returns**

      - `(int)`:  The width of the Channel
## pyppl.exception


- **desc**

  Exceptions for PyPPL

!!! example "class: `JobBuildingError`"

  Failed to build the job

!!! example "class: `JobFailError`"

  Job results validation failed

!!! example "class: `JobInputParseError`"

  Failed to parse job input

!!! example "class: `JobOutputParseError`"

  Failed to parse job output

!!! example "class: `PluginConfigKeyError`"

  When try to update plugin config from a dictionary with key not added

!!! example "class: `PluginNoSuchPlugin`"

  When try to find a plugin not existing

!!! example "class: `ProcessAlreadyRegistered`"

  Process already registered with the same id and tag

  !!! abstract "method: `__init__(self, message, proc1, proc2)`"

    Construct for ProcessAlreadyRegistered

    - **params**

      - `message (str)`:  The message, make the class to be compatible with Exception

      - `proc1 (Proc)`:  the first Proc

      - `proc2 (Proc)`:  the second Proc

!!! example "class: `ProcessAttributeError`"

  Process AttributeError

!!! example "class: `ProcessInputError`"

  Process Input error

!!! example "class: `ProcessOutputError`"

  Process Output error

!!! example "class: `ProcessScriptError`"

  Process script building error

!!! example "class: `PyPPLFindNoProcesses`"

  When failed to find any processes with given pattern

!!! example "class: `PyPPLInvalidConfigurationKey`"

  When invalid configuration key passed

!!! example "class: `PyPPLNameError`"

  Pipeline name duplicated after transformed by utils.name2filename

!!! example "class: `PyPPLResumeError`"

  Try to resume when no start process has been specified

!!! example "class: `RunnerMorethanOneRunnerEnabled`"

  When more than one runners are enabled

!!! example "class: `RunnerNoSuchRunner`"

  When no such runner is found

!!! example "class: `RunnerTypeError`"

  Wrong type of runner
## pyppl.jobmgr


- **desc**

  Job manager for PyPPL

- **variables**

  - `STATES (dict)`:  Possible states for the job

  - `PBAR_MARKS (dict)`:  The marks on progress bar for different states

  - `PBAR_LEVEL (dict)`:  The levels for different states

  - `PBAR_SIZE (int)`:  the size of the progress bar

!!! example "class: `Jobmgr`"

  Job manager

  !!! abstract "method: `__init__(self, jobs)`"

    Job manager constructor

    - **params**

      - `jobs (list)`:  All jobs of a process

  !!! abstract "method: `cleanup(self, ex)`"

    Cleanup the pipeline when
    - Ctrl-C hit
    - error encountered and `proc.errhow` = 'terminate'

    - **params**

      - `ex (Exception)`:  The exception raised by workers

  !!! hint "function: `kill_worker(cls, killq)`"

    The killing worker to kill the jobs

  !!! abstract "method: `progressbar(self, event)`"

    Generate the progress bar.

    - **params**

      - `event (StateMachine event)`:  The event including job as model.

  !!! abstract "method: `start(self)`"

    Start the queue.


  !!! abstract "method: `worker(self)`"

    The worker to build, submit and poll the jobs
## pyppl.plugin


- **desc**

  Plugin system for PyPPL

- **variables**

  - `PMNAME (str)`:  The name of the plugin manager

  - `hookimpl (pluggy.HookimplMarker)`:  Used to mark the implementation of hooks

  - `hookspec (pluggy.HookspecMarker)`:  Used to mark the hooks

!!! abstract "method: `cli_addcmd(commands)`"

  PLUGIN API
  Add command and options to CLI

  - **params**

    - `commands (Commands)`:  The Commands instance

!!! abstract "method: `cli_execcmd(command, opts)`"

  PLUGIN API
  Execute the command being added to CLI

  - **params**

    - `command (str)`:  The command

    - `opts (dict)`:  The options

!!! abstract "method: `config_plugins(*plugins)`"

  Parse configurations for plugins and enable/disable plugins accordingly.

  - **params**

    - `*plugins ([any])`:  The plugins

        plugins with 'no:' will be disabled.

!!! abstract "method: `disable_plugin(plugin)`"

  Try to disable a plugin

  - **params**

    - `plugin (any)`:  A plugin or the name of a plugin

!!! abstract "method: `job_build(job, status)`"

  PLUGIN API
  After a job is being built

  - **params**

    - `job (Job)`:  The Job instance

    - `status (str)`:  The status of the job building

        - True: The job is successfully built

        - False: The job is failed to build

        - cached: The job is cached

!!! abstract "method: `job_done(job, status)`"

  PLUGIN API
  After a job is done

  - **params**

    - `job (Job)`:  The Job instance

    - `status (str)`:  The status of the job

        - succeeded: The job is successfully done

        - failed: The job is failed

        - cached: The job is cached

!!! abstract "method: `job_init(job)`"

  PLUGIN API
  Right after job initiates

  - **params**

    - `job (Job)`:  The Job instance

!!! abstract "method: `job_kill(job, status)`"

  PLUGIN API
  After a job is being killed

  - **params**

    - `job (Job)`:  The Job instance

    - `status (str)`:  The status of the job killing

        - 'succeeded': The job is successfully killed

        - 'failed': The job is failed to kill

!!! abstract "method: `job_poll(job, status)`"

  PLUGIN API
  Poll the status of a job

  - **params**

    - `job (Job)`:  The Job instance

    - `status (str)`:  The status of the job

        - 'running': The job is still running

        - 'done': Polling is done, rcfile is generated

!!! abstract "method: `job_submit(job, status)`"

  PLUGIN API
  After a job is being submitted

  - **params**

    - `job (Job)`:  The Job instance

    - `status (str)`:  The status of the job submission

        - 'succeeded': The job is successfully submitted

        - 'failed': The job is failed to submit

        - 'running': The job is already running

!!! abstract "method: `job_succeeded(job)`"

  PLUGIN API
  Tell if job is successfully done or not
  One can add not rigorous check. By default, only
  if returncode is 0 checked.
  return False to tell if job is failed otherwise
  use the default status or results from other plugins

  - **params**

    - `job (Job)`:  The Job instance

!!! abstract "method: `logger_init(logger)`"

  PLUGIN API
  Initiate logger, most manipulate levels

  - **params**

    - `logger (Logger)`:  The Logger instance

!!! abstract "method: `proc_init(proc)`"

  PLUGIN API
  Right after a Proc being initialized

  - **params**

    - `proc (Proc)`:  The Proc instance

!!! abstract "method: `proc_postrun(proc, status)`"

  PLUGIN API
  After a process has done

  - **params**

    - `proc (Proc)`:  The Proc instance

    - `status (str)`:  succeeded/failed

!!! abstract "method: `proc_prerun(proc)`"

  PLUGIN API
  Before a process starts
  If False returned, process will not start
  The value returned by the first plugin will be used, which means
  once a plugin stops process from running, others cannot resume it.

  - **params**

    - `proc (Proc)`:  The Proc instance

!!! abstract "method: `pyppl_init(ppl)`"

  PLUGIN API
  Right after a pipeline initiates

  - **params**

    - `ppl (PyPPL)`:  The PyPPL instance

!!! abstract "method: `pyppl_postrun(ppl)`"

  PLUGIN API
  After the pipeline is done
  If the pipeline fails, this won't run.
  Use proc_postrun(proc = proc, status = 'failed') instead.

  - **params**

    - `ppl (PyPPL)`:  The PyPPL instance

!!! abstract "method: `pyppl_prerun(ppl)`"

  PLUGIN API
  Before pipeline starts to run
  If False returned, the pipeline will not run
  The value returned by the first plugin will be used, which means
  once a plugin stops process from running, others cannot resume it.

  - **params**

    - `ppl (PyPPL)`:  The PyPPL instance

!!! abstract "method: `setup(config)`"

  PLUGIN API
  Add default configs

  - **params**

    - `config (Config)`:  The default configurations

!!! example "class: `PluginConfig`"

  Plugin configuration for Proc/Job

  !!! abstract "method: `__init__(self, pconfig)`"

    Construct for PluginConfig

    - **params**

      - `pconfig (dict)`:  the default plugin configuration

  !!! abstract "method: `add(self, name, default, converter, update)`"

    Add a config item

    - **params**

      - `name (str)`:  The name of the config item.

      - `default (any)`:  The default value

      - `converter (callable)`:  The converter to convert the value whenever the value is set.

      - `update (str)`:  With setcounter > 1, should we update the value or ignore it in .update()?

          - if value is not a dictionary, update will just replace the value.

  !!! abstract "method: `setcounter(self, name)`"

    Get the set counter for properties

    - **params**

      - `name (str)`:  the name of the configuration item

  !!! abstract "method: `update(self, pconfig)`"

    Update the configuration
    Depends on `update` argument while the configuration is added

    - **params**

      - `pconfig (dict)`:  the configuration to update from
## pyppl.logger


- **desc**

  Custome logger for PyPPL

- **variables**

  - `LOG_FORMAT (str)`:  The format of loggers

  - `LOGTIME_FORMAT (str)`:  The format of time for loggers

  - `GROUP_VALUES (dict)`:  The values for each level group

  - `LEVEL_GROUPS (dict)`:  The groups of levels

  - `THEMES (dict)`:  The builtin themes

  - `SUBLEVELS (dict)`:  the sub levels used to limit loggers of the same type

!!! abstract "method: `get_group(level)`"

  Get the group name of the level

  - **params**

    - `level (str)`:  The level, should be UPPERCASE

  - **returns**

    - `(str)`:  The group name

!!! abstract "method: `get_value(level)`"

  Get the value of the level

  - **params**

    - `level (str)`:  The level, should be UPPERCASE

  - **returns**

    - `(int)`:  The value of the group where the level is in.

!!! abstract "method: `init_levels(group, leveldiffs)`"

  Initiate the levels, get real levels.

  - **params**

    - `group (str)`:  The group of levels

    - `leveldiffs (str|list)`:  The diffs of levels

  - **returns**

    - `(set)`:  The real levels.

!!! example "class: `Logger`"

  A wrapper of logger


  !!! abstract "method: `__init__(self, name, bake)`"

    The logger wrapper construct

    - **params**

      - `name (str)`:  The logger name. Default: `PyPPL`

      - `bake (dict)`:  The arguments to bake a new logger.

  !!! note "property: `pbar`"

    Mark the record as a progress record.
    Allow `logger.pbar.info` access

    - **returns**

      - `(Logger)`:  The Logger object itself

  !!! abstract "method: `add_level(self, level, group)`"


    - **params**

      - `level (str)`:  The log level name

          Make sure it's less than 7 characters

      - `group (str)`:  The group the level is to be added

  !!! abstract "method: `add_sublevel(self, slevel, lines)`"


    - **params**

      - `slevel (str)`:  The debug level

      - `lines (int)`:  The number of lines allowed for the debug level

          - Negative value means a summary will be printed

  !!! abstract "method: `bake(self, **kwargs)`"

    Bake the logger with certain arguments

    - **params**

      - `*kwargs`:  arguments used to bake a new logger

    - **returns**

      - `(Logger)`:  The new logger.

  !!! abstract "method: `init(self, config)`"

    Initiate the logger, called by the construct,
    Just in case, we want to change the config and as default_config
    Reinitiate the logger.

    - **params**

      - `conf (Config)`:  The configuration used to initiate logger.

!!! example "class: `Theme`"

  The theme for the logger

  - **variables**

    - `COLORS (dict)`:  Color collections used to format theme

  !!! abstract "method: `__init__(self, theme)`"

    Construct for Theme

    - **params**

      - `theme (str)`:  the name of the theme

  !!! abstract "method: `get_color(self, level)`"

    Get the color for a given level

    - **params**

      - ``level``:  The level

    - **returns**

        The color of the level by the theme.
## pyppl.runner


- **desc**

  Make runners as plugins for PyPPL

- **variables**

  - `PMNAME (str)`:  The name of the runner manager

  - `RUNNERS (dict)`:  All ever registered runners

  - `DEFAULT_POLL_INTERVAL (int)`:  The default poll interval to check job status

  - `hookimpl (pluggy.HookimplMarker)`:  The marker for runner hook Implementations

  - `hookspec (pluggy.HookspecMarker)`:  The marker for runner hooks

!!! abstract "method: `current_runner()`"

  Get current runner name

  - **returns**

    - `(str)`:  current runner name

!!! abstract "method: `isrunning(job)`"

  RUNNER API
  Tell if the job is running

  - **params**

    - `job (Job)`:  the job instance

!!! abstract "method: `kill(job)`"

  RUNNER API
  Try to kill the job

  - **params**

    - `job (Job)`:  the job instance

!!! abstract "method: `poll_interval()`"

  Get the poll interval for current runner

  - **returns**

    - `(int)`:  poll interval for querying job status

!!! abstract "method: `register_runner(runner, name)`"

  Register a runner

  - **params**

    - `runner (callable)`:  The runner, a module or a class object

    - `name (str)`:  The name of the runner to registered

!!! abstract "method: `script_parts(job)`"

  RUNNER API
  Overwrite script parts

  - **params**

    - `job (Job)`:  the job instance

!!! abstract "method: `submit(job)`"

  RUNNER API
  Submit a job

  - **params**

    - `job (Job)`:  the job instance

!!! abstract "method: `use_runner(runner)`"

  runner should be a module or the name of a module,
  with or without "pyppl_runner_" prefix
  To enable a runner, we need to disable other runners

  - **params**

    - `runner (str)`:  the name of runner

!!! example "class: `PyPPLRunnerLocal`"

  PyPPL's default runner

  !!! abstract "method: `isrunning(self, job)`"

    Try to tell whether the job is still running.

    - **params**

      - `job (Job)`:  the job instance

    - **returns**

        `True` if yes, otherwise `False`

  !!! abstract "method: `kill(self, job)`"

    Try to kill the running jobs if I am exiting

    - **params**

      - `job (Job)`:  the job instance

  !!! abstract "method: `submit(self, job)`"

    Try to submit the job

    - **params**

      - `job (Job)`:  the job instance
