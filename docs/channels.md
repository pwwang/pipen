

# Channels

Channels are used to pass data from one `proc` to the other. It is basically a `list`, each element is a `tuple`. **So all python functions/methods that apply on `list` will also apply on `channel`.** The length a the `tuple` corresponds to the number of variables of the input or output of a `proc`.
```python
# v1  v2  v3
c = [
 (a1, b1, c1),  # data for job #0
 (a2, b2, c2),  # data for job #1
# ...
]
```
If we specify this channel to the input of a `proc`:
```python
p = proc()
p.input = {"v1,v2,v3": c}
```
Then the values for different variables in different jobs wil be:

| Job Index | v1 | v2  | v3 |
|-----------|----|-----|----|
| 0         | a1 | b1  | c1 |
| 1         | a2 | b2  | c2 |
| ...       |... | ... |... |


## Initialize a channel
There are several ways to initialize a channel:
- From a `list`:  
```python
c = channel.create([0,1,2])
# produce [(0,), (1,), (2,)]
# You can ignore the tuple sign (,) for single-variable (single-column) channel
```

- From other `channels`:   
```python
c = channel.fromChannels(ch1, ch2, ...)
# This will do column bind, 
# requires channels have the same length
# ch1 == [(1,2,3), (4,5,6)]
# ch2 == [('a'), ('b')]
# c   == [(1,2,3,'a'), (4,5,6, 'b')]
```

- From a file path pattern: 
```python
c = channel.fromPath ("/a/b/*.txt", "any")
# You can specify type to filter the file list
# Possible file type: any(default), file, dir and link
# ls /a/b/
# 1.txt 2.txt 3.txt 4.txt
# c == [("/a/b/1.txt",), ("/a/b/2.txt",), ("/a/b/3.txt",), ("/a/b/4.txt",)]
```

- From file pairs:
```python
c = channel.fromPath ("/a/b/*.txt")
# the files will be sorted and then split into pairs
# c == [("/a/b/1.txt", "/a/b/2.txt"), ("/a/b/3.txt", "/a/b/4.txt")]
```

- From `sys.argv` (command line arguments):
```python
c == channel.fromArgv()
# python whatever.py /a/b/*.txt
# c == [("/a/b/1.txt",), ("/a/b/2.txt",), ("/a/b/3.txt",), ("/a/b/4.txt",)]
# Make a multple-variable channel:
# python whatever.py /a/b/1.txt,/a/b/2.txt /a/b/3.txt,/a/b/4.txt
# c == [("/a/b/1.txt", "/a/b/2.txt"), ("/a/b/3.txt", "/a/b/4.txt")]
```

## Available methods for channels
### Get the length and width of a channel
```python
chan = channel.create ([(1,2,3), (4,5,6)])
chan.length() == 2 == len(chan)
chan.width()  == 3
```

### Expand a channel by directory
`channel.expand (index = 0, pattern = '*')`

Sometimes we prepare files in one job (for example, split a big file into small ones in a directory), then handle these files by different jobs in a process, so that they can be processed simultaneously. 

![channel.expand](https://github.com/pwwang/pyppl/raw/master/docs/channel-expand.png) 

For example:
```python
# the original file: a.txt
p1 = proc()
p1.input  = {"infile:file": ["a.txt"]}
p1.output = {"outdir:dir": "{{infile.fn}}"}
p1.script = "# the script to split a.txt to 1.txt, 2.txt, 3.txt ... to {{outdir}}"

p2 = proc()
p2.depends = p1
# expand channel [("<outdir>/a/",)] to channel:
# [("<outdir>/a/1.txt",), ("<outdir>/a/2.txt",), ("<outdir>/a/3.txt",), ...]
p2.input   = {"infile:file": lambda ch: ch.expand()}
p2.output  = {"outfile:file:{{infile.fn}}.result"}
p2.script  = "# handle each file (1.txt, 2.txt, 3.txt, ...) to result file (1.result, 2.result, 3.result, ...)"

pyppl().starts(p1).run()
```
If a channel is a multi-variable channel (containing 2 or more columns), you may specify the index of the column, which is the directory.
```python
p1.input   = {"invar, infile:file": [("a", "a.txt")]}
# ...
p2.input   = {"invar, infile:file": lambda ch: ch.expand(1)}
# expands to: 
# [("a", "<outdir>/a/1.txt"), ("a", "<outdir>/a/2.txt"), ("a", "<outdir>/a/3.txt"), ...]
# ...
```
You may also filter the files with a pattern:
```python
p2.input   = {"invar, infile:file": lambda ch: ch.expand(1, "*.txt")}
# only incude .txt files
```
> NOTE: `expand` only works for original channels with length is 1, which will expand to `N` (number of files included)

### Collapse a channel by files in the same directory
`channel.collapse(index=0)`

It's basically the reverse process of `expand`. It applies when you deal with different files and in next process you want to combine the results:

![channel.expand](https://github.com/pwwang/pyppl/raw/master/docs/channel-collapse.png) 

For example:
```python
# the original file: a.txt
p1 = proc()
p1.input  = {"infile:file": ["/a/b/1.txt", "/a/b/2.txt", "/a/b/3.txt"]}
p1.output = {"outdir:dir": "{{infile.fn}}.txt2"}
p1.script = """
# the script to deal with each input file:
# /a/b/1.txt -> <outdir>/1.txt2
# /a/b/2.txt -> <outdir>/2.txt2
# /a/b/3.txt -> <outdir>/3.txt2
"""

p2 = proc()
p2.depends = p1
# collapse channel [("<outdir>/1.txt2",), ("<outdir>/2.txt2",), ("<outdir>/3.txt2",)] to channel:
# [("<outdir>/", )]
p2.input   = {"indir:file": lambda ch: ch.collapse()}
p2.output  = {"outfile:file:{{indir.fn}}.result"}
p2.script  = """
# combine 1.txt2, 2.txt2, 3.txt3 in {{indir}} to {{outfile}}
"""
pyppl().starts(p1).run()
```
If the files in the channel are not at column 0, you have to specify it: 
```python
p1.input  = {"infile:file": [("a", "/a/b/1.txt"), ("a", "/a/b/2.txt"), ("a", "/a/b/3.txt")]}
# ...
p2.input  = {"indir:file": lambda ch: ch.collapse(1)}
# collapse to: [("a", "<outdir>/")]
# ...
```
> NOTE: 
> 1. the files have to be in the same directory, `pyppl` won't check it, the directory of the first file will be used.
> 2. values at other columns should be the same, `pyppl` won't check it, the first value at the column will be used.

### Fetch column(s) from a channel
- `channel.slice(start, length=None)`
```
chan1 = channel.create ([(1,2,3,4), (4,5,6,7)])
chan2 = chan1.slice(1,2)
# chan2 == [(2,3), (5,6)]
chan3 = chan1.slice(2)
# chan3 == [(3,4), (6,7)]
chan4 = chan1.slice(-1)
# chan4 == [(4,), (7,)]
```

- `channel.colAt(index)`
`chan.colAt(index) == chan.slice(index, 1)`

### Split a channel to channels with width = 1
`channel.split()`
```python
chan  = channel.create ([(1,2,3), (4,5,6)])
chans = chan.split()
# isinstance (chans, list) == True
# isinstance (chans, channel) == False
# chans == [
#   [(1,), (4,)],
#   [(2,), (5,)],
#   [(3,), (6,)],
# ]
```

### `map`, `filter`, `reduce`
- `channel.map(func)`
- `channel.filter(func)`
- `channel.reduce(func)`

They act as the same as the python's builtin functions `map`, `filter` and `reduce`. `chan.map(func) == map(func, chan)` 

### Add rows/columns to a channel

- `channel.rbindMany(*rows)`
```python
chan = channel.create([(1,2,3), (4,5,6)])
col1 = ['a', 'b', 'c']
col2 = [7, 8, 9]
chan.cbindMany(col1, col2)
# chan == [(1,2,3), (4,5,6), ('a','b','c'), (7,8,9)]
```

- `channel.rbind(row)`
It is a single-argument version of `channel.rbindMany`.

- `channel.cbindMany(*cols)`
```python
chan = channel.create([(1,2,3), (4,5,6)])
col1 = ['a', 'b']
col2 = [7, 8]
chan.cbindMany(col1, col2)
# chan == [(1,2,3,'a',7), (4,5,6,'b',8)]
```

- `channel.cbind(col)`
It is a single-argument version of `channel.cbindMany`.
- `channel.merge(*chans)`
It actually does similarly as `cbindMany`. The difference is that `chan` in `chans` can have multiple columns; while `col` in `cols` can just have one column. The channels to be merged must have the same length. `channel.fromChannels` actually does the same as `merge`, but with an empty channel.

- `channel.insert(index, col)`
Insert a column to a channel, the `col` can be a `list` or scalar value. If it is a scalar value, it'll be extended to a list with the same length of the channel.
```python
chan = channel.create([(1,2,3), (4,5,6)])
chan.insert(1, [7,8])
# chan == [(1,7,2,3), (4,8,5,6)]
chan.insert(None, 0)
# chan == [(1,7,2,3,0), (4,8,5,6,0)]
```
If original channel is an empty channel:
```python
chan = channel.create()
chan.insert (0, 1)
# chan == [(1, )]
chan = channel.create()
chan.insert (0, [1,2,3])
# chan == [(1,), (2,), (3,)]
```

### Convert a width=1 channel to `list`
`channel.toList()`

```python
chan = channel.create([1,2,3])
# chan == [(1,), (2,), (3,)]
l    = chan.toList()
# l == [1,2,3]
```

> NOTE: it only works with width=1 channels. If `chan.width() != 1`, a `ValueError` will be raised.

### Copy a channel
`channel.copy()`

Remember, when you try to add row(s)/column(s) to a channel, the functions not only return the changed channel, but the channel itself will also be changed. To keep it unchanged:
```python
chan    = channel.create()
chan1   = chan.insert (0, [1,2,3])
# chan  == [(1,), (2,), (3,)]
# chan1 =  [(1,), (2,), (3,)]
chan    = channel.create()
chan1   = chan.copy().insert(0, [1,2,3])
# chan  == []
# chan1 =  [(1,), (2,), (3,)]
```


