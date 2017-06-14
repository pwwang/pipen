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

The complete form of an input key is `<placeholder>:<type>`. The `<type>` could be `var`, `file` or `path`(exactly the same as `file`). A type of `var` can be omitted. So `{"ph1":[1,2,3], "ph2":[4,5,6]}` is the same as `{"ph1:var":[1,2,3], "ph2:var":[4,5,6]}`

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
> **Caution** the number of placeholders should be no more than that of the output from the prior process. Otherwise, there is not enough data for the placeholders.

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


### Specify files as input
When you specify files as input, you should use `file` or `dir` flag for the placeholder: 
```python
p.input = {"infile:file": channel.fromPath("./*.txt")}
```
Then `pyppl` will create symbol links in `<workdir>/input/`. See [File placeholders](https://pwwang.gitbooks.io/pyppl/placeholders.html#file-placeholders).

> **Note** The `{{infile}}`
 will return the path of the link in `<indir>` pointing to the actual input file. If you want to get the path of the actual path: 
```
{{ infile | readlink }} or {{ infile.orig }}
```


### Bring related files to input directory
Some programs, for example, mutation calling programs, take genome reference file as input. However, during the process, they actually need the reference file to be indexed with an index file, which will not be explicitly specified with program options. Usually, they will try to find the index file according to the reference file. For example, index file `hg19.fai` or `hg19.fa.fai` for reference file `hg19.fa`. Sometimes, we will generate the index file in advance and put it together with the reference file. When you specify the reference file to `pyppl` process, we will create a link for the reference file in `<indir>`, but not for the index file. If the index file is not found, some programs will try to generate the index file, some will not and just quit. To avoid that, you can use `p.brings` to bring the index file in.
```python
# ls -l /a/b/
# <permission, size, time infomation> /a/b/hg19.fa -> /c/d/hg19.fa
#
# Suppose you have two index files to bring in:
# /c/d/hg19.fa.fai1 (sometimes can be /c/d/hg19.fai1)
# /c/d/hg19.fa.fai2 (sometimes can be /c/d/hg19.fai2)
p.input  = {"hg19fa:file": ["/a/b/hg19.fa"]}
p.brings = {
	"hg19fa":  "{{hg19fa.fn}}*.fai1",   # .fn gets the filename without extension
	"hg19fa#": "{{hg19fa.fn}}*.fai2"    # the pound sign avoids the first item to be overwritten
	                                    # but still connects the index file to hg19fa
}
# The we will find the matched index file with the pattern in the directory of the input file,
# in this case: /a/b/hg19.fa
# However, we can't find them and it's actually a link, so we will parse the link (/a/b/hg19.fa)
# and try to find whether the index files are in the directory of the parsed path of the link.
# We find them in /a/b/, then bring them to the <indir>

# To access the bring-in file in beforeCmd/afterCmd/output/script in <indir>:
# {{hg19fa.bring}}, {{hg19fa#.bring}}
# An empty string will be returned if the index file can't be found.
# You may use some other programs to generate the index file in your script in this case.
#
# To access the original path of the bring-file:
# {{hg19fa.bring.orig}}, {{hg19fa#.bring.orig}}
```

> **Caution**: If your pattern matches multiple files, only the first one by `glob.glob` will be returned. So try to write more specfic pattern for bring-in files.

### Use a callback to modify the output channel of the prior process.
You can modify the output channel of the prior process by a callback for the input value. For example:
```python
p1 = proc()
p1.input  = {"ph1":[1,2,3], "ph2":[4,5,6]}
p1.output = "out1:{{ph1}},out2:{{ph2}}"
p1.script = "# your logic here"
# the output channel is [(1,2,3), (4,5,6)]
p2.depends = p1
p2.input   = {"in1, in2": lambda ch: ch.slice(1)}  
# just use the last 2 columns: [(2,3), (5,6)]
# p1.channel keeps intact
```
You can check more examples in some channel methods: [channel.expand](https://pwwang.gitbooks.io/pyppl/channels.html#expand-a-channel-by-directory) and [channel.collapse](https://pwwang.gitbooks.io/pyppl/channels.html#collapse-a-channel-by-files-in-the-same-directory).

> **Caution** If you use callback to modify the channel, you may combine the keys: in the above case `"in1, in2": ...`, or specify them independently: `p2.input = {"in1": lambda ch: ch.slice(1,1), "in2": lambda ch: ch.slice(2)}`. But remember, **all channels** from `p2.depends` will be passed to each function. For example:
```python
p2.depends = [p0, p1]
p2.input   = {"in1": lambda ch0, ch1: ..., "in2": labmda ch0, ch1: ...}
# all channels from p2.depends are passed to each function
```

## Specify output of a process
Different from input, instead of channels, you have to tell how `pyppl` will calculate the values for the placeholders. The output can be a `list` or `str`. If it's `str`, a comma (`,`) is used to separate different placeholders:
```python
p.input  = {"invar":[1], "infile:file": ["/a/b/c.txt"]}
p.output = "outvar:var:{{invar}}2, outfile:file:{{infile.bn}}2, outdir:dir:{{indir.fn}}-dir"
# is the same as ["outvar:{{invar}}2", "outfile:file:{{infile}}2", "outdir:dir:{{indir}}2"]
# The type 'var' is omitted in the first element.
# The output channel (p.channel) will be:
# [("12", "c.txt2", "c-dir")]
```
You cannot only use the placeholders from input, but the placeholders with process/job property values. For example: `job.indir` points to the input directory of the process (`<workdir>/<job.id>/input/`). Check [all available process property placeholders](https://pwwang.gitbooks.io/pyppl/placeholders.html#proc-property-placeholders).

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

