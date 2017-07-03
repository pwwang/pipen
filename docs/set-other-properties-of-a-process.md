# Set other properties of a process
<!-- toc -->

Currently we introduced in previous chapters to set a set of properties of a process and we will introduce the rest of them in this chapter:

| Property | Meaning | Possibile values/types | Default value | alias | Where it's mentioned |
|-|-|-|-|-|-|
| `id` | The id of the process | `str` | `<the variable name>` ||[Link][8]|
| `tag` | The tag of the process, makes it possible to have two processes with the same `id` but different `tag`. | `str` | `"notag"` ||[Link][8]|
| `desc` | The description of the process. | `str` | `"No description"` |||
| `echo` | Whether to print out the `stdout` and `stderr` | `bool` | `False` || [Link][8] |
| `input` | The input of the process | `dict`/`list`/`str` |||[Link][1]|
| `output` | The output of the process | `list`/`str` |||[Link][2]|
| `script` | The script of the process | `str` |||[Link][3]|
| `lang` | The language for the script | `str` | `"bash"` | `defaultSh`|[Link][3]|
| `exdir` | The export directory | `str` ||`exportdir`|[Link][4]|
| `exhow` | How to export | `"move"`, `"copy"`, `"symlink"`, `"gzip"` | `"move"` | `exporthow` |[Link][4] |
| `exow` | Whether to overwrite existing files when export | `bool` | `True` | `exportow`| [Link][4] |
| `cache` | Whether to cache the process | `True`, `False`, `"export"`, `"export+"` | `True` ||[Link][5] |
| `runner` | Which runner to use | `str` | `"local"` ||[Link][6] |
| `ppldir` | The directory to store `<workdir>s` for all processes in this pipeline | `str` | `"./workdir"`|tmpdir|[Link][7]|
| `workdir` | The work directory of the process | `str` | `"<id>.<tag>.<uid>"`||[Link][7]|
| `args` | The arguments for the process | `dict` | `{}` || This chapter |
| `rc` | Valid return codes | `str`/`list`/`int` | `0` || This chapter |
| `beforeCmd` | The command to run before jobs run | `str` | || This chapter |
| `afterCmd` | The command to run after jobs finish | `str` | || This chapter |
| `errorhow` | What's next if jobs fail | `"terminate"`, `"retry"`, `"ignore"` | `"terminate"`|`errhow`| This chapter |
| `errorntry` | If `errhow` is `"retry"`, how many time to re-try? | `int` | 1 | `errntry` | This chapter
| `depends` | The processes the process depends on | `proc`/`list` | | | This chapter |
| `callback` | The callback, called after the process finishes | `callable` | | | This chapter |

## Set arguments of a process `p.args`:
It is a `dict` used to set some common arguments shared within the process (different jobs). For example, all jobs use the same program: `bedtools`. but to make the process portable and shareable, you may want others can give a different path of `bedtools` as well. Then you can use `p.args`:
```python
p = proc()
p.input = {"infile1:file, infile2:file": [("file1.bed", "file2.bed")]}
p.output = "outfile:file:{{infile.fn}}.out"
p.args = {"bedtools": "/path/to/bedtools"}
p.script = """
{{p.args.bedtools}} intersect -a {{infile1}} -b {{infile2}} > {{outfile}}
"""
```
That's **NOT** recommended that you put it in the input channel:
```python
p = proc()
p.input = {"infile1:file, infile2:file, bedtools": [("file1.bed", "file2.bed", "/path/to/bedtools")]}
p.output = "outfile:file:{{infile.fn}}.out"
p.script = """
{{bedtools}} intersect -a {{infile1}} -b {{infile2}} > {{outfile}}
"""
```
Of course, you can do that, but a common argument is not usually generated from prior processes, then you have to modify the input channels. If the argument is a file, and you put it in `input` with type `file`, `pyppl` will try to create a link in `<workdir>/input`. If you have 100 jobs, we need to do that 100 times or to determine whether the link exists for 100 times. You may not want that to happen.  

> **Caution** never use a key with dot `.` in `p.args`, since we use {% raw %}`{{proc.args.key}}`{% endraw %} to access it. 

## Set the valid return/exit codes `p.rc`:
When a program exits, it will return a code (or [exit status](https://en.wikipedia.org/wiki/Exit_status)), usually a small integer to exhibit it's status. Generally if a program finishes successfully, it will return `0`, which is the default value of `p.rc`. `pyppl` relies on this return code to determine whether a job finishes successfully.  If not, `p.errorhow` will be triggered. You can set multiple valid return codes for a process: 
```python
p.rc = [0, 1]
# exit code with 0 or 1 will be both regarded as success
```

## Command to run before/after jobs run `p.beforeCmd`/`p.afterCmd`:
You can run some commands before and after the jobs run. The commands should be fit for [`Popen`](https://docs.python.org/2/library/subprocess.html#popen-constructor) with `shell=True`. For example, you can set up some environment before the jobs start to run, and remove it when they finish.  
> **Caution** `beforeCmd`/`afterCmd` only run locally, no matter which runner you choose to run the jobs.

## Error handling `p.errhow`/`p.errntry`:
When a job finishes, it should generate a `script.<index>.rc` file containing the return code. When compare with the valid return codes `p.rc`, the error triggered if it not in `p.rc`. `p.errhow` determines what's next if errors happen. 
- `"terminate"`: when errors happen, terminate the entire pipeline
- `"ignore"`: ignore the errors, continuing run the next process
- `"retry"`: re-submit and run the job again. `p.errntry` defines how many time to retry.

## Set the processes current process depends on `p.depends`:
A process can not only depend on a single process: 
```python
p2.depends = p1
```
but multiple processes 
```python
p2.depends = [p1, p0]
```
To set prior processes not only let the process use the output channel as input for current process, but also determines when the process starts to run (right after the prior processes finish).
> **Caution** You can copy a process by `p2 = p.copy()`, but remember `depends` will not be copied, you have to specify it for the copied processes.  
> When you specify new dependents for a process, its orginal ones will be removed.

## Set expectations of a process
You can use commands to check whether you have expected output. For example:
```python
p = proc ()
p.input = {"input": "1"}
p.script = "echo {{input}}"
# check the stdout
p.expect = "grep 1 {{job.outfile}}"
```

## Use callback to modify the process `p.callback`:
The processes **NOT** initialized until it's ready to run. So you may not be able to modify some of the values until it is initialized. For example, you may want to change the output channel before it passes to the its dependent process:
```python
pSingle = proc ()
pSingle.input    = {"infile:file": ["file1.txt", "file2.txt", "file3.txt"]}
pSingle.output   = "outfile:file:{{infile.fn}}.sorted"
pSingle.script   = "# Sort {{infile}} and save to {{infile.fn}}.sorted"
# pSingle.channel == [("file1.sorted",), ("file2.sorted",), ("file3.sorted",)]
# BUT NOT NOW!! the output channel is only generated after the process runs

pCombine = proc ()
pCombine.depends = pSingle
pCombine.input   = "indir:file"   
# the directory contains "file1.sorted", "file2.sorted", "file3.sorted"
pCombine.output  = "outfile:{{indir.fn}}.combined"
pCombine.script  = "# combine files to {{indir.fn}}.combined"

# To use the directory of "file1.sorted", "file2.sorted", "file3.sorted" as the input channel for pCombine
# You can use callback
def callback4pSingle (p):
    p.channel.collapse()
pSingle.callback = callback4pSingle 

pyppl().starts (pSingle).run()
```
You can also use a callback in `pCombine.input` to modify the channel, see [here][9], which is recommended. Because `p.callback` will change the original output channel of `pSingle`, but the `input` callback will keep the output channel intact. However, `p.callback` can not only change the output channel, but also change other properties of current process or even set the properties of coming processes.

> **Hint** You can also use `callfront` before the properties are computed. The argument is the proc itself.

[1]: https://pwwang.gitbooks.io/pyppl/content/specify-input-and-output-of-a-process.html#specify-input-of-a-process
[2]: https://pwwang.gitbooks.io/pyppl/content/specify-input-and-output-of-a-process.html#specify-output-of-a-process
[3]: https://pwwang.gitbooks.io/pyppl/content/write-your-script.html
[4]: https://pwwang.gitbooks.io/pyppl/content/export-output-files.html
[5]: https://pwwang.gitbooks.io/pyppl/content/caching.html
[6]: https://pwwang.gitbooks.io/pyppl/content/runners.html
[7]: https://pwwang.gitbooks.io/pyppl/content/basic-concepts-and-directory-structure.html#folder-structure
[8]: https://pwwang.gitbooks.io/pyppl/content/placeholders.html#proc-property-placeholders
[9]: https://pwwang.gitbooks.io/pyppl/content/specify-input-and-output-of-a-process.html#use-a-callback-to-modify-the-output-channel-of-the-prior-process