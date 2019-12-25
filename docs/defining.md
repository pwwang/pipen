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
    `PyPPL` uses `Diot` (from [`diot`][14]) to allow dot to be used to refer the attributes. So you can set the value of `args` like this:
    ```python
    pXXX.args.bedtools = 'bedtools'
    ```

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

# All avaiable attributes for a process

| Attribute | Meaning | Possibile values/types | Default value | Where it's first mentioned |
|-|-|-|-|-|
| `id` | The id of the process | `str` | `<the variable name>` |[Link][8]|
| `tag` | The tag of the process, makes it possible to have two processes with the same `id` but different `tag`. | `str` | `"notag"` |[Link][8]|
| `desc` | The description of the process. | `str` | `"No description"` ||
| `input` | The input of the process | `dict`/`list`/`str` ||[Link][1]|
| `output` | The output of the process | `list`/`str`/`OrderedDict` ||[Link][2]|
| `script` | The script of the process | `str` ||[Link][3]|
| `lang` | The language for the script | `str` | `"bash"` | [Link][3]|
| `cache` | Whether to cache the process | `True`, `False`, `"export"` | `True` |[Link][5] |
| `runner` | Which runner to use | `str` | `"local"` |[Link][6] |
| `ppldir` | The directory to store `<workdir>s` for all processes in this pipeline | `str` | `"./workdir"`|[Link][7]|
| `workdir` | The work directory of the process | `str` | `"<id>.<tag>.<uid>"`|[Link][7]|
| `template` | The name of the template engine | `str` | `PyPPL` | [Link][8] |
| `envs` | Environments for the template engine | `dict` |  | [Link][8] |
| `dirsig` | Get the modified time for directory recursively (taking into account the dirs and files in it) for cache checking | `bool` | `True` | [Link][10] |
| `errhow` | What's next if jobs fail | `"terminate"`, `"retry"`, `"ignore"` | `"terminate"`| [Link][12] |
| `errntry` | If `errhow` is `"retry"`, how many time to re-try? | `int` | 3 | [Link][12] |
| `nthread` | Number of theads used for job construction and submission | `int` | `min(int(cpu_count() / 2), 16)` | - |
| `args` | The arguments for the process | `dict` | `{}` | This chapter |
| `depends` | The processes the process depends on | `proc`/`list` | | This chapter |

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
[14]: https://pypi.org/project/diot/
[15]: https://docs.python.org/2/library/subprocess.html#popen-constructor
[16]: https://en.wikipedia.org/wiki/Exit_status
