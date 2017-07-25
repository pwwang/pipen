# Specify input and output of a process
<!-- toc -->

{% raw %}
## Specify input of a process

The input of a process of basically a `dict` with keys the placeholders and the values the input channels:

```python
p = proc()
p.input = {"ph1":[1,2,3], "ph2":[4,5,6]}
# You can also use combined keys and channels
# p.input = {"ph1, ph2": [(1,4), (2,5), (3,6)]}
```

The complete form of an input key is `<placeholder>:<type>`. The `<type>` could be `var`, `file` (a.k.a `path`, `dir` or `folder`) and `files` (a.k.a `paths`, `dirs` or `folders`). **A type of `var` can be omitted.** So `{"ph1":[1,2,3], "ph2":[4,5,6]}` is the same as `{"ph1:var":[1,2,3], "ph2:var":[4,5,6]}`

You can also use a `str` or a `list` if a process depends on a prior process, it will automatically use the output channel of the prior process, or you want to use the arguments from command line as input channel (in most case for starting processes, which do not depend on any other processes). For example:

Use output channel of prior process:
```python
p1 = proc()
p1.input  = {"ph1":[1,2,3], "ph2":[4,5,6]}
p1.output = "out1:{{ph1}},out2:{{ph2}}"
# same as p.output = ["out1:{{ph1}}", "out2:{{ph2}}"]
p1.script = "# your logic here"

p2 = proc()
p2.depends = p1
p2.input   = "in1, in2"  
# will automatically use output channel of p1
```
> **Caution** the number of input keys should be no more than that of the output from the prior process. Otherwise, there is not enough data for the keys.
> **Note** For output, `dict` is not supported. As we need the order of the keys and data to be kept when it's being passed on.

Use `sys.argv` (see details for [`channel.fromArgv`](https://pwwang.gitbooks.io/pyppl/content/channels.html#initialize-a-channel)):
```python
p3 = proc()
p3.input = "in1"
# same as p3.input = {"in1": channel.fromArgv ()}
# python test.py 1 2 3
# p3.input = {"in1": ["1", "2", "3"]}

p4 = proc()
p3.input = "in1, in2"
# same as p3.input = {"in1, in2": channel.fromArgv ()}
# python test.py 1,a 2,b 3,c
# p3.input = {"in1": [("1", "a"), ("2", "b"), ("3", "c")]}
```

### Specify file as input
When you specify file as input, you should use `file` (a.k.a `path`, `dir` or `folder`) flag for the type: 
```python
p.input = {"infile:file": channel.fromPath("./*.txt")}
```
Then `pyppl` will create symbolic links in `<workdir>/<job.index>/input/`. See [File placeholders](https://pwwang.gitbooks.io/pyppl/placeholders.html#file-placeholders).

> **Note** The `{{infile}}`
 will return the path of the link in `<indir>` pointing to the actual input file. If you want to get the path of the actual path, you may use: 
```
{{ infile | readlink }} or {{ infile.orig }}
```


### Bring related files to input directory
Some programs, for example, mutation calling programs, take bam files as input. However, during the process, they actually need the bam files to be indexed with an index file (.bai), which will not be explicitly specified with program options. Usually, they will try to find the index file according to the path of the bam files. For example, index file `tumor.bam.bai` for input file `tumor.bam`. Sometimes, we will generate the index file in advance and put it together with the input file. When you specify the bam files to `pyppl` process, we will create a link for it in `<indir>`, but not for the index file (we don't know, right?). If the index file is not found, some programs will try to generate the index file, some will not and just quit. To avoid that, you can use `p.brings` to bring the index file in.
```python
# ls /a/b/
# /a/b/tumor.bam /a/b/tumor.bam.bai

p.input  = {"bamfile:file": ["/a/b/tumor.bam"]}
p.brings = {
	"bamfile": "{{bamfile | bn}}.bai"
}
```

> **Note** 
> 1. If `/a/b/tumor.bam` is a symbolic link to `/c/d/tumor.bam`, the index file `/c/d/tumor.bam.bai` will also be found.
> 2. A link will be create in `<indir>`, of which the path can be got by `{{brings.bamfile}}`. To get the original path of the index file: `{{brings.bamfile.orig}}`
> 3. You can use wildcards to find the files, the first matched file will be brought in.
> 4. You can bring in multiple files:
> ```python
> p.brings = {"bamfile": "{{bamfile | bn}}.bai", "bamfile#": "{{bamfile | bn}}.bai2"}
> # to access path of the second bring-in file: {{brings.bamfile#}}
> # its original path: {{brings.bamfile#.orig}}
> ```

### Use a callback to modify the output channel of the prior process.
You can modify the output channel of the prior process by a callback for the input value. For example:
```python
p1 = proc()
p1.input  = {"ph1":[1,2,3], "ph2":[4,5,6]}
p1.output = "out1:{{ph1}},out2:{{ph2}}"
p1.script = "# your logic here"
# the output channel is [(1,4), (2,5), (3,6)]
p2.depends = p1
p2.input   = {"in1, in2": lambda ch: ch.slice(1)}  
# just use the last 2 columns: [(2,5), (3,6)]
# p1.channel keeps intact
```
You can check more examples in some channel methods: [channel.expand](https://pwwang.gitbooks.io/pyppl/channels.html#expand-a-channel-by-directory) and [channel.collapse](https://pwwang.gitbooks.io/pyppl/channels.html#collapse-a-channel-by-files-in-a-common-ancestor-directory).

> **Caution** If you use callback to modify the channel, you may combine the keys: in the above case `"in1, in2": ...`, or specify them independently: `p2.input = {"in1": lambda ch: ch.slice(1,1), "in2": lambda ch: ch.slice(2)}`. But remember, **all channels** from `p2.depends` will be passed to each callback function. For example:
```python
p2.depends = [p0, p1]
p2.input   = {"in1": lambda ch0, ch1: ..., "in2": labmda ch0, ch1: ...}
# all channels from p2.depends are passed to each function
```

## Specify output of a process
Different from input, instead of channels, you have to tell how `pyppl` will calculate the values for the placeholders. The output can be a `list` or `str` (**but not a `dict`, as the order of keys has to be kept**). If it's `str`, a comma (`,`) is used to separate different keys:
```python
p.input  = {"invar":[1], "infile:file": ["/a/b/c.txt"]}
p.output = "outvar:var:{{invar}}2, outfile:file:{{infile.bn}}2, outdir:dir:{{indir.fn}}-dir"
# is the same as ["outvar:{{invar}}2", "outfile:file:{{infile}}2", "outdir:dir:{{indir}}2"]
# The type 'var' is omitted in the first element.
# The output channel (p.channel) will be:
# [("12", "c.txt2", "c-dir")]
```
You can use not only the placeholders from input, but also the placeholders with process/job property values. For example: `job.indir` points to the input directory of the job (`<workdir>/<job.index>/input/`). Check [all available process property placeholders](https://pwwang.gitbooks.io/pyppl/placeholders.html#proc-property-placeholders).

## Types of input and output
|Input/Output|Type|Aliases|Behavior|Example-assignment (`p.input/output=?`)|Example-placeholder-value|
|------------|----|-------|--------|-------|
|Input|`var`|-|Use the value directly|`{"in:var": [1]}`|`{{in}} == 1`|
|Input|`file`|`path`<br />`dir`<br />`folder`|Create link in `job.indir` and assign the original path to `in.orig`|`{"in:file": ["/path/to/file"]}`|`{{in}} == <job.indir>/file`<br />`{{in.orig}} == /path/to/file`|
|Input|`files`|`paths`<br />`dirs`<br />`folders`|Same as `file` but do for multiple files|`{`<br />`"in:files": channel.create([`<br />`(["/path/to/file1", `<br />`"/path/to/file2"],)`<br />`])`<br />`}`|`{{in `&#124;` " ".join(_)}} == /path/to/file1 /path/to/file2`<br />`{{in `&#124;` asquote}} == "/path/to/file1" "/path/to/file2"`|
|Output|`var`|-|Specify direct value|`"out:var:{{#}}"`|`{{out}} == {{#}}` (job.id)|
|Output|`file`|`path`|Just specify the basename, output file will be generated in `job.outdir`|`"out:file:{{infile `&#124;` fn}}.out"`|`{{out}} == <job.outdir>/<filename of infile>.out`|
|Output|`dir`|`folder`|Do the same thing as `file` but will create the directory|`"out:dir:{{infile `&#124;` fn}}-outdir"`|`{{out}} == <job.outdir>/<filename of infile>-outdir` <br />(automatically created)|


{% endraw %}

