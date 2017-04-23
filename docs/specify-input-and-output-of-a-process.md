# Specify input of a process
The input of a process of basically a `dict` with keys the placeholders and the values the input channels:

```python
p = proc()
p.input = {"ph1":[1,2,3], "ph2":[4,5,6]}
# You can also use combined keys and channels
# p.input = {"ph1, ph2": [(1,4), (2,5), (3,6)]}
```

The complete form of an input key is `<placeholder>:<type>`. The `<type>` could be `var`, `file` or `path`(exactly the same as `file`). A type of `var` can be omitted. So `{"ph1":[1,2,3], "ph2":[4,5,6]}` is the same as `{"ph1:var":[1,2,3], "ph2:var":[4,5,6]}`

if a process depends on a prior process, it will automatically use the output channel of the prior process. For example:
```python
p1 = proc()
p1.input  = {"ph1":[1,2,3], "ph2":[4,5,6]}
p1.output = "out1:{{ph1}},out2:{{ph2}}"
p1.script = "# your logic here"

p2.depends = p1
p2.input   = "in1, in2"  
# will automatically use output channel of p1
```
> NOTE: the number of placeholders should be no more than that of the output from the prior process. Otherwise, there is not enough data for the placeholders.

## Specify files as input
When you specify files as input, you should use `file` or `dir` flag for the placeholder: 
```python
p.input = {"infile:file": channel.fromPath("./*.txt")}
```
Then `pyppl` will create symbol links in `<workdir>/input/` and an extra set of placeholders will be created: `infile.fn`, `infile.bn` and `infile.ext`. See [File placeholders](https://pwwang.gitbooks.io/pyppl/placeholders.html#file-placeholders).

## Use a callback to modify the output channel of the prior process.
You can modify the output channel of the prior process by a callback for the input value. For example:
```python
p1 = proc()
p1.input  = {"ph1":[1,2,3], "ph2":[4,5,6]}
p1.output = "out1:{{ph1}},out2:{{ph2}}"
p1.script = "# your logic here"
# the output channel is [(1,2,3), (4,5,6)]
p2.depends = p1
p2.input   = {"in1, in2": lambda ch: ch.colAt(1)}  
# just use the second column: [(2,), (5,)]
# p1.channel keeps intact
```
You can check more examples in some channel methods: [channel.expand](https://pwwang.gitbooks.io/pyppl/channels.html#expand-a-channel-by-directory) and [channel.collapse](https://pwwang.gitbooks.io/pyppl/channels.html#collapse-a-channel-by-files-in-the-same-directory).

> NOTE: If you use callback to modify the channel, you have to combine the keys

# Specify output of a process
Different from input, instead of channels, you have to tell how `pyppl` will calculate the values for the placeholders. The output can be a `list` or `str`. If it's `str`, a comma (`,`) is used to separate different placeholders:
```python
p.input  = {"invar":[1], "infile:file": ["/a/b/c.txt"]}
p.output = "outvar:var:{{invar}}2, outfile:file:{{infile.bn}}2, outdir:dir:{{indir.fn}}-dir"
# is the same as ["outvar:{{invar}}2", "outfile:file:{{infile}}2", "outdir:dir:{{indir}}2"]
# The type 'var' is omitted in the first element.
# The output channel (p.channel) will be:
# [("12", "c.txt2", "c-dir")]
```
The available types `var`, `file`, `path` and `dir`. `path` is actually an alias of `file`. If your output is a directory, and you want `pyppl` to automatically create it, you should use `dir`.
> NOTE: always the basename of your output files/directories, so that they will be generated in the `<workdir>/output/`. Later `pyppl` is able to export them and cache the jobs.
> So don't use `infile` and `indir` directly in output unless you want to use the path of the links linking the input files, Instead, use `infile.fn`, `infile.bn`, `indir.fn` and `indir.bn`.

