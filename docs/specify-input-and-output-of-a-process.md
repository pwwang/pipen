# Input and output of a process
<!-- toc -->

{% raw %}
## Specify input of a process

The input of a process of basically a `dict` with keys as the placeholders and the values as the input channels:

```python
p = Proc()
p.input = {"ph1":[1,2,3], "ph2":[4,5,6]}
# You can also use combined keys and channels
# p.input = {"ph1, ph2": [(1,4), (2,5), (3,6)]}
```

The complete form of an input key is `<key>:<type>`. The `<type>` could be `var`, `file` (a.k.a `path`, `dir` or `folder`) and `files` (a.k.a `paths`, `dirs` or `folders`). **A type of `var` can be omitted.** So `{"ph1":[1,2,3], "ph2":[4,5,6]}` is the same as `{"ph1:var":[1,2,3], "ph2:var":[4,5,6]}`

You can also use a `str` or a `list` if a process depends on a prior process, it will automatically use the output channel of the prior process, or you want to use the arguments from command line as input channel (in most case for starting processes, which do not depend on any other processes). For example:

Use output channel of prior process:
```python
p1 = Proc()
p1.input  = {"ph1":[1,2,3], "ph2":[4,5,6]}
p1.output = "out1:{{in.ph1}},out2:{{in.ph2}}"
# same as p.output = ["out1:{{in.ph1}}", "out2:{{in.ph2}}"]
p1.script = "# your logic here"

p2 = proc()
p2.depends = p1
p2.input   = "in1, in2"  
# will automatically use output channel of p1
```
> **Caution** the number of input keys should be no more than that of the output from the prior process. Otherwise, there is not enough data for the keys.
> **Note** For output, `dict` is not supported. As we need the order of the keys and data to be kept when it's being passed on. But you may use `OrderedDict`.
> **Hint** If you have input keys defined by a string before, for example:
  ```python
  p1.input = "ph1, ph2"
  ```
  You can then specify the input data/channel directly:
  ```python
  p1.input = [(1,4), (2,5), (3,6)]
  # same as:
  p1.input  = {"ph1":[1,2,3], "ph2":[4,5,6]}
  ```
  One thing has to be reminded is that, you can do:
  ```python
  p1.input = {"in": "a"}  # same as p1.input = {"in": ["a"]}
  ```
  But you cannot do:
  ```python
  p1.input = "in"
  p1.input = "a" 
  # the right way is p.input = ["a"]
  # because PyPPL will take "a" as the input key instead of data, as it's a string
  ```

  
  
Use `sys.argv` (see details for [`Channel.fromArgv`](https://pwwang.gitbooks.io/pyppl/content/channels.html#initialize-a-channel)):
```python
p3 = Proc()
p3.input = "in1"
# same as p3.input = {"in1": channel.fromArgv ()}
# Run the program: > python test.py 1 2 3
# Then in job#0: {{in.in1}} -> 1
# Then in job#1: {{in.in1}} -> 2
# Then in job#2: {{in.in1}} -> 3

p4 = Proc()
p4.input = "in1, in2"
# same as p4.input = {"in1, in2": channel.fromArgv ()}
# Run the program: python test.py 1,a 2,b 3,c
# Job#0: {{in.in1}} -> 1, {{in.in2}} -> a
# Job#1: {{in.in1}} -> 2, {{in.in2}} -> b
# Job#2: {{in.in1}} -> 3, {{in.in2}} -> c
```

### Specify files as input
- Use a single file:
  When you specify file as input, you should use `file` (a.k.a `path`, `dir` or `folder`) flag for the type: 
  ```python
  p.input = {"infile:file": channel.fromPattern("./*.txt")}
  ```
  Then `PyPPL` will create symbolic links in `<workdir>/<job.index>/input/`. 
  
  > **Note** The `{{in.infile}}`
   will return the path of the link in `<indir>` pointing to the actual input file. If you want to get the path of the actual path, you may use: 
  ```
  {{ in.infile | readlink }} or {{ in._infile }}
  ```
- Use a list of files:
  Similar as a single file, but you have to specify it as `files`:
  ```python
  p.input = {"infiles:files": [channel.fromPattern("./*.txt").flatten()]}
  ```
  Then remember `{{in.infiles}}` is a list, so is `{{in._infiles}}`
- Rename input file links
  When there are input files (different files) with the same basename, later ones will be renamed in `<indir>`. For example:
  ```python
  pXXX.input = {
    "infile1:file": "/path1/to/theSameBasename.txt", 
    "infile2:file": "/path2/to/theSameBasename.txt"
  }
  ```
  Remember both files will have symblic links created in `<indir>`. To avoid `infile2` being overwritten, the basename of the link will be `theSameBasename[1].txt`. If you are using built-in template functions to get the filename (`{{in.file2 | fn}}`), we can still get `theSameBasename.txt` instead of `theSameBasename[1].txt`. `bn`, `basename`, `prefix` act similarly.

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
> 2. Multiple files can be brought, so `{{bring.bamfile}}` and `{{bring._bamfile}}` always return a list.
> 3. A link will be create in `<indir>`, of which the path can be got by `{{bring.bamfile[0]}}`. To get the original path of the index file: `{{brings._bamfile[0]}}`
> 4. You can use wildcards to find the files.
> 5. You don't need to worry if the link is renamed. `{{bamfile | bn}}` will still return `tumor.bam` if the link of it is renamed to `tumor[1].bam`.
> 6. You can bring in multiple files:
> ```python
> p.brings = {"bamfile": ["{{bamfile | bn}}.bai", "{{bamfile | bn}}.bai2"]}
> ```

### Use callback to modify the input channel
You can modify the input channel of a process by a callback. For example:
```python
p1 = Proc()
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
Different from input, instead of channels, you have to tell `PyPPL` how to compute the output channel. The output can be a `list`, `str` or `OrderedDict` (**but not a `dict`, as the order of keys has to be kept**). If it's `str`, a comma (`,`) is used to separate different keys:
```python
p.input  = {"invar":[1], "infile:file": ["/a/b/c.txt"]}
p.output = "outvar:var:{{in.invar}}2, outfile:file:{{in.infile | bn}}2, outdir:dir:{{in.indir | fn}}-dir"
# The type 'var' is omitted in the first element.
# The output channel (pXXX.channel) will be:
# [("12", "c.txt2", "c-dir")]
```
The output keys are automatically attached to the output channel, so you may use them to access the columns. In previous example:
```python
p.channel.outvar  == [('12', )]
p.channel.outfile == [('<outdir>/c.txt2', )]
p.channel.outdir  == [('<outdir>/c-dir', )]
```

## Types of input and output
|Input/Output|Type|Aliases|Behavior|Example-assignment (`p.input/output=?`)|Example-template-value|
|------------|----|-------|--------|-------|
|Input|`var`|-|Use the value directly|`{"in:var": [1]}`|`{{in.in}} -> 1`|
|Input|`file`|`path`<br />`dir`<br />`folder`|Create link in `<indir>` and assign the original path to `in._in`|`{"in:file": ["/path/to/file"]}`|`{{in.in}} -> <indir>/file`<br />`{{in._in}} -> /path/to/file`|
|Input|`files`|`paths`<br />`dirs`<br />`folders`|Same as `file` but do for multiple files|`{`<br />`"in:files": `<br />`(["/path/to/file1", `<br />`"/path/to/file2"],)`<br />`}`|`{{in.in `&#124;` asquote}} -> "<indir>/file1" "<indir>/file2"`<br />`{{in._in `&#124;` asquote}} -> "/path/to/file1" "/path/to/file2"`|
|Output|`var`|-|Specify direct value|`"out:var:{{job.index}}"`|`{{out}} -> <job.index>`|
|Output|`file`|`path`|Just specify the basename, output file will be generated in `job.outdir`|`"out:file:{{in.infile `&#124;` fn}}.out"`|`{{out}} == <outdir>/<filename of infile>.out`|
|Output|`dir`|`folder`|Do the same thing as `file` but will create the directory|`"out:dir:{{in.infile `&#124;` fn}}-outdir"`|`{{out}} == <outdir>/<filename of infile>-outdir` <br />(automatically created)|


{% endraw %}

