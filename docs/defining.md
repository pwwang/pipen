# Basic attributes of a process

There are two ways to instantiate a process:
```python
from pyppl import Proc
p = Proc(id = 'pXXX', tag = 'tag', desc = 'description', <other attributes>)
# or
p      = Proc()
p.id   = 'pXXX'
p.tag  = 'tag'
p.desc = 'description'
# ...
# or you can even combine them:
p = Proc(id = 'pXXX', tag = 'tag')
p.desc = 'description'
```

!!! note

    If `id` is not specified, it will be inferred from the variable name. For example:
    ```python
    p = Proc()
    # then p.id == 'p'
    ```

# Set arguments of a process
It is a `dict` used to set some common arguments shared within the process (different jobs). For example, all jobs use the same program: `bedtools`. but to make the process portable and shareable, you may want others can give a different path of `bedtools` as well. Then you can use `pXXX.args`:
```python
pXXX = Proc()
pXXX.input = {"infile1:file, infile2:file": [("file1.bed", "file2.bed")]}
pXXX.output = "outfile:file:{{i.infile1 | fn}}.out"
pXXX.args = {"bedtools": "/path/to/bedtools"}
# You can also do:
# pXXX.args.bedtools = "/path/to/bedtools"
pXXX.script = """
{{args.bedtools}} intersect -a {{i.infile1}} -b {{i.infile2}} > {{o.outfile}}
"""
```
That's **NOT** recommended that you put it in the input channel:
```python
pXXX = proc()
pXXX.input = {"infile1:file, infile2:file, bedtools": [("file1.bed", "file2.bed", "/path/to/bedtools")]}
pXXX.output = "outfile:file:{{infile.fn}}.out"
pXXX.script = """
{{bedtools}} intersect -a {{infile1}} -b {{infile2}} > {{outfile}}
"""
```
Of course, you can do that, but a common argument is not usually generated from prior processes, then you have to modify the input channels. If the argument is a file, and you put it in `input` with type `file`, `PyPPL` will try to create a link in `<indir>`. If you have 100 jobs, we need to do that 100 times or to determine whether the link exists for 100 times. You may not want that to happen.

!!! caution
    When use a key with dot `.` in `pXXX.args`, we should  use `{{args[key]}}` to access it.

!!! hint
    `PyPPL` uses `Box` (from [`python-box`][14]) to allow dot to be used to refer the attributes. So you can set the value of `args` like this:
    ```python
    pXXX.args.bedtools = 'bedtools'
    ```

# Set the valid return/exit codes
When a program exits, it will return a code (or [exit status][16]), usually a small integer to exhibit it's status. Generally if a program finishes successfully, it will return `0`, which is the default value of `p.rc`. `pyppl` relies on this return code to determine whether a job finishes successfully.  If not, `p.errorhow` will be triggered. You can set multiple valid return codes for a process:
```python
p.rc = [0, 1] #or "0,1"
# exit code with 0 or 1 will be both regarded as success
```

# Command to run before/after jobs
You can run some commands before and after the jobs run. The commands should be fit for [`Popen`][15] with `shell=True`. For example, you can set up some environment before the jobs start to run, and remove it when they finish.
!!! caution
    `preCmd`/`postCmd` only run locally, no matter which runner you choose to run the jobs.


# Set the processes current process depends on
A process can not only depend on a single process:
```python
p2.depends = p1
```
but also multiple processes
```python
p2.depends = p1, p0
```
To set prior processes not only let the process use the output channel as input for current process, but also determines when the process starts to run (right after the prior processes finish).

!!! caution
    You can copy a process by `p2 = p.copy()`, but remember `depends` will not be copied, you have to specify it for the copied processes.

    When you specify new dependents for a process, its original ones will be removed, which means each time `pXXX.depends` will overwrite the previous setting.

# Use callback to modify the process
The processes **NOT** initialized until it's ready to run. So you may not be able to modify some of the values until it is initialized. For example, you may want to change the output channel before it passes to the its dependent process:
```python
pSingle = Proc ()
pSingle.input    = {"infile:file": ["file1.txt", "file2.txt", "file3.txt"]}
pSingle.output   = "outfile:file:{{i.infile | fn}}.sorted"
pSingle.script   = "# Sort {{i. infile}} and save to {{o.outfile}}.sorted"
# pSingle.channel == [("file1.sorted",), ("file2.sorted",), ("file3.sorted",)]
# BUT NOT NOW!! the output channel is only generated after the process finishes

pCombine = Proc ()
pCombine.depends = pSingle
pCombine.input   = "indir:file"
# the directory contains "file1.sorted", "file2.sorted", "file3.sorted"
pCombine.output  = "outfile:{{i.indir | fn}}.combined"
pCombine.script  = "# combine files to {{o.outfile}}.combined"

# To use the directory of "file1.sorted", "file2.sorted", "file3.sorted" as the input channel for pCombine
# You can use callback
def pSingleCallback(p):
    p.channel = p.channel.collapse()
pSingle.callback = pSingleCallback

PyPPL().start (pSingle).run()
```
You can also use a callback in `pCombine.input` to modify the channel, see [here][13], which is recommended. Because `p.callback` will change the original output channel of `pSingle`, but the `input` callback will keep the output channel intact. However, `p.callback` can not only change the output channel, but also change other properties of current process or even set the properties of coming processes.

# Use callfront to modify the process
One possible scenario is that, value in  `pXXX.args` depends on the other process.
For example:
```python
# generate bam files
# ...
pBam.output = "bamfile:file:{{i.infile | fn}}.bam"

# generate/download reference file, and index it
# ...
pRef.output = "reffile:file:{{i.in}}.fa"

# call variance
# ...
pCall.depends   = pBam, pRef
pCall.callfront = lambda p: p.args.update({'reffile': pRef.channel.reffile[0][0]})

# pCall also depends on pRef, as it needs the reference file to run.
# But you may not want to put it in input.

PyPPL().start(pBam, pRef).run()
```

# All avaiable attributes for a process

| Attribute | Meaning | Possibile values/types | Default value | Where it's first mentioned |
|-|-|-|-|-|
| `id` | The id of the process | `str` | `<the variable name>` |[Link][8]|
| `tag` | The tag of the process, makes it possible to have two processes with the same `id` but different `tag`. | `str` | `"notag"` |[Link][8]|
| `desc` | The description of the process. | `str` | `"No description"` ||
| `echo` | Whether to print out the `stdout` and `stderr` | `bool`/`dict` | `False` | [Link][8] |
| `input` | The input of the process | `dict`/`list`/`str` ||[Link][1]|
| `output` | The output of the process | `list`/`str`/`OrderedDict` ||[Link][2]|
| `script` | The script of the process | `str` ||[Link][3]|
| `lang` | The language for the script | `str` | `"bash"` | [Link][3]|
| `exdir` | The export directory | `str` ||[Link][4]|
| `exhow` | How to export | `"move"`, `"copy"`, `"symlink"`, `"gzip"` | `"move"` |[Link][4] |
| `exow` | Whether to overwrite existing files when export | `bool` | `True`| [Link][4] |
| `cache` | Whether to cache the process | `True`, `False`, `"export"` | `True` |[Link][5] |
| `runner` | Which runner to use | `str` | `"local"` |[Link][6] |
| `ppldir` | The directory to store `<workdir>s` for all processes in this pipeline | `str` | `"./workdir"`|[Link][7]|
| `workdir` | The work directory of the process | `str` | `"<id>.<tag>.<uid>"`|[Link][7]|
| `expart` | Partial export | `str`/`list` | | [Link][4] |
| `template` | The name of the template engine | `str` | `PyPPL` | [Link][8] |
| `envs` | Environments for the template engine | `dict` |  | [Link][8] |
| `acache` | Whether do cleanup (output checking/exporting) if a job was cached. | `bool` | `False` | [Link][11] |
| `dirsig` | Get the modified time for directory recursively (taking into account the dirs and files in it) for cache checking | `bool` | `True` | [Link][10] |
| `errhow` | What's next if jobs fail | `"terminate"`, `"retry"`, `"ignore"` | `"terminate"`| [Link][12] |
| `errntry` | If `errhow` is `"retry"`, how many time to re-try? | `int` | 3 | [Link][12] |
| `expect` | A command to check whether expected results generated | `str` | | [Link][12] |
| `nthread` | Number of theads used for job construction and submission | `int` | `min(int(cpu_count() / 2), 16)` | - |
| `args` | The arguments for the process | `dict` | `{}` | This chapter |
| `rc` | Valid return codes | `str`/`list`/`int` | `0` | This chapter |
| `beforeCmd` | The command to run before jobs run | `str` | | This chapter |
| `afterCmd` | The command to run after jobs finish | `str` | | This chapter |
| `depends` | The processes the process depends on | `proc`/`list` | | This chapter |
| `callback` | The callback, called after the process finishes | `callable` | | This chapter |
| `callfront` | The callfront, called after properties are computed | `callable` | | This chapter |


[1]: ../input-output/#specify-input-of-a-process
[2]: ../input-output/#specify-output-of-a-process
[3]: ../script/
[4]: ../export/
[5]: ../caching/
[6]: ../runners/
[7]: ../basics/#folder-structure
[8]: ../templating/#proc-property-placeholders
[9]: ../input-output/#use-a-callback-to-modify-the-output-channel-of-the-prior-process
[10]: ../caching/#calculating-signatures-for-caching
[11]: ../export/#control-of-export-of-cached-jobs
[12]: ../error/
[13]: ../input-output/
[14]: https://pypi.org/project/python-box/
[15]: https://docs.python.org/2/library/subprocess.html#popen-constructor
[16]: https://en.wikipedia.org/wiki/Exit_status