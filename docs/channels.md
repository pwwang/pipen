# Channels

<!-- toc -->

{% raw %}
Channels are used to pass data from one process (an instance of `Proc`) to another. It is derived from a `list`, where each element is a `tuple`. **So all python functions/methods that apply on `list` will also apply on `Channel`.** The length a the `tuple` corresponds to the number of variables of the input or output of a `proc`.
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
- From a non-iterable element (string is considered non-iterable):  
  This will create a single element channel.
  ```python
  from PyPPL import Channel
  c = Channel.create(1)
  # produce [(1,)]
  c = Channel.create("a,b")
  # produce [("a,b",)]
  ```
  So `pXXX.input = {'a': 1}` implies one single job will be created for `pXXX` and `{{in.a}}` gives `1` for that job.
- From a `list` or a `tuple`
  ```python
  c = Channel.create(["a", "b"])
  # produce [("a", ), ("b", )]
  c = Channel.create(("a", "b"))
  # produce [("a", "b")]
  ```  
  > **Note** Please use `Channel.create(...)` instead of `Channel(...)` unless each element is 'tuplized' properly. 
  ```python
  channel.create([1,2,3]) != channel([1,2,3])
  channel.create([1,2,3]) == channel([(1,), (2,), (3,)])
  ```
- From other channels:   
  ```python
  ch1 = Channel.create([(1, 2), (3, 4)])
  ch2 = Channel.create('a')
  ch3 = Channel.create([5, 6])
  ch  = Channel.fromChannels(ch1, ch2, ch3)
  # channels are column-bound
  # ch == [(1, 2, 'a', 5), (3, 4, 'a', 6)]
  ```

- From a file path pattern:  
  Use `glob.glob` to grab files by the pattern, you may use different arguments for filter, sort or reverse the list:
  - filter the files with type (`t`): `dir`, `file`, `link` or `any` (default), 
  - sort them by (`sortby`): `size`, `mtime` or `name` (default)
  - reverse the list (`reverse`): `False` (default, don't reverse)
  ```python
  c = Channel.fromPattern ("/a/b/*.txt", t = 'any', sortby = 'size', reverse = False)
  ```

- From file pairs:
  ```python
  c = Channel.fromPairs ("/a/b/*.txt")
  # the files will be sorted by names and then split into pairs
  # c == [("/a/b/a1.txt", "/a/b/a2.txt"), ("/a/b/b1.txt", "/a/b/b2.txt")]
  ```
  
- From file content:  
  For example, we have a file `"chan.txt"` with content:
  ```
  a1<tab>b1<tab>c1
  a2<tab>b2<tab>c2
  ```  
  Read the file as a channel:
  ```python
  c = Channel.fromFile ("chan.txt")
  # c == [("a1", "b1", "c1"), ("a2", "b2", "c2")]
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
  
- From command line argument parser:
  See [command line argument parser][1] for details.
  ```python
  from PyPPL import Channel, params
  params.a = 'a'
  params.b = 2
  params.b.type = int
  params.c = [1, 2]
  params.c.type = list
  params.d = ['a', 'b']
  params.d.type = list
  params.e = []
  params.e.type = list
  
  ch = Channel.fromParams('c', 'e')
  # Raises ValueError, non-equal length
  ch = Channel.fromParams('c', 'd')
  # ch == [(1, 'a'), (2, 'b')]
  ch = Channel.fromParams('a', 'b')
  # ch == [('a', 2)]
  ```

## Methods for channels
### Get the length and width of a channel
```python
chan = Channel.create ([(1,2,3), (4,5,6)])
#chan.length() == 2 == len(chan)
#chan.width()  == 3
```

### Expand a channel by directory
`Channel.expand (col= 0, pattern = '*', t='any', sortby='name', reverse=False)`

Sometimes we prepare files in one process (for example, split a big file into small ones in a directory), then handle these files by different jobs in another process, so that they can be processed simultaneously. 

![channel.expand](https://github.com/pwwang/pyppl/raw/master/docs/channel-expand.png) 

For example:
```python
# the original file: a.txt
p1 = Proc()
p1.input  = {"infile:file": ["a.txt"]}
p1.output = "outdir:dir:{{infile | fn}}"
p1.script = "# the script to split a.txt to 1.txt, 2.txt, 3.txt ... to {{outdir}}"

p2 = Proc()
p2.depends = p1
# expand channel [("outdir/a/",)] to channel:
# [("outdir/a/1.txt",), ("outdir/a/2.txt",), ("outdir/a/3.txt",), ...]
p2.input   = {"infile:file": lambda ch: ch.expand()}
p2.output  = {"outfile:file:{{infile.fn}}.result"}
p2.script  = "# handle each file (1.txt, 2.txt, 3.txt, ...) to result file (1.result, 2.result, 3.result, ...)"

PyPPL().start(p1).run()
```
If a channel is a multi-variable channel (containing 2 or more columns), you may specify the index of the column, which should be a directory. For the previous example:
```python
p1.output = "outvar:{{infile | ext | [1:]}}, outdir:dir:{{infile | fn}}"
# ...
p2.depends = p1
p2.input   = {"invar,infile:file": lambda ch: ch.expand(1)}
# expands to: 
# [("txt", "outdir/a/1.txt"), ("txt", "outdir/a/2.txt"), ("txt", "outdir/a/3.txt"), ...]
# ...
```
You may also filter the files with a pattern (arguments `t`, `sortby` and `reverse` act exactly as `Channel.fromPattern`):
```python
p2.input   = {"invar,infile:file": lambda ch: ch.expand(1, "*.txt")}
# only include .txt files
```
> **Caution** `expand` only works for original channels with length is 1, which will expand to `N` (number of files included)

### Collapse a channel by files in a common ancestor directory
`Channel.collapse(col=0)`

It's basically the reverse process of `expand`. It applies when you deal with different files and in next process you need them all involved (i.e. combine the results):

![channel.expand](https://github.com/pwwang/pyppl/raw/master/docs/channel-collapse.png) 

For example:
```python
# the original file: a.txt
p1 = Proc()
p1.input  = {"infile:file": ["/a/b/1.txt", "/a/b/2.txt", "/a/b/3.txt"]}
p1.output = {"outfile:file": "{{infile | fn}}.txt2"}
p1.script = """
# the script to deal with each input file:
# /a/b/1.txt -> <outdir>/1.txt2
# /a/b/2.txt -> <outdir>/2.txt2
# /a/b/3.txt -> <outdir>/3.txt2
"""

p2 = Proc()
p2.depends = p1
# collapse channel [("<outdir>/1.txt2",), ("<outdir>/2.txt2",), ("<outdir>/3.txt2",)] to channel:
# [("<outdir>/", )]
p2.input   = {"indir:file": lambda ch: ch.collapse()}
p2.output  = {"outfile:file:{{indir | fn}}.result"}
p2.script  = """
# combine 1.txt2, 2.txt2, 3.txt3 in {{in.indir}} to {{out.outfile}}
"""
PyPPL().start(p1).run()
```
If the files in the channel are not at column 0, you have to specify it: 
```python
p1.input  = {"infile:file": [("a", "/a/b/1.txt"), ("a", "/a/b/2.txt"), ("a", "/a/b/3.txt")]}
# ...
p2.input  = {"indir:file": lambda ch: ch.collapse(1)}
# collapse to: [("a", "<outdir>/")]
# ...
```
> **Caution** 
> 1. `os.path.dirname(os.path.commonprefix(...))` is used to detect the common ancestor directory, so the files could be `['/a/1/1.file', '/a/2/1.file']`. In this case `/a/` will be returned.
> 2. values at other columns should be the same, `PyPPL` will NOT check it, the first value at the column will be used.

### Fetch columns from a channel
- `Channel.slice(start, length=None)`
```
chan1 = Channel.create ([(1,2,3,4), (4,5,6,7)])
chan2 = chan1.slice(1,2)
# chan2 == [(2,3), (5,6)]
chan3 = chan1.slice(2)
# chan3 == [(3,4), (6,7)]
chan4 = chan1.slice(-1)
# chan4 == [(4,), (7,)]
```

- `Channel.colAt(index)`
`chan.colAt(index) == chan.slice(index, 1)`

### Flatten a channel
`Channel.flatten(col = None)`
Flatten a channel, make it into a list.
```python
chan  = Channel.create ([(1,2,3), (4,5,6)])
f1 = chan.flatten()
# f1 == [1,2,3,4,5,6]
f2 = chan.flatten(1)
# f1 == [2,5]
```

### Split a channel to single-width channels
`Channel.split(flatten = False)`
```python
chan  = Channel.create ([(1,2,3), (4,5,6)])
chans = chan.split()
# isinstance (chans, list) == True
# isinstance (chans, Channel) == False
# chans == [
#   [(1,), (4,)],  # isinstance (chans[0], Channel) == True
#   [(2,), (5,)],
#   [(3,), (6,)],
# ]
chans2 = chan.split(True)
# chans2 == [
#   [1, 4],        # isinstance (chans2[0], Channel) == False
#   [2, 5],
#   [3, 6],
# ]
```

### Attach column names
`Channel.attach(*names)`
We can attach the column names and then use them to access the columns.
```python
ch = Channel.create([(1,2,3), (4,5,6)])
ch.attach ('col1', 'col2', 'col3')
# ch.col1 == [(1,), (4,)]
# ch.col2 == [(2,), (5,)]
# ch.col3 == [(3,), (6,)]
# isinstance(ch.col1, Channel) == True

# flatten the columns
ch.attach ('col1', 'col2', 'col3', True)
# ch.col1 == [1,4]
# ch.col2 == [2.5]
# ch.col3 == [3,6]
# isinstance(ch.col1, Channel) == False
```

### Map, filter, reduce
- `Channel.map(func)`
- `Channel.mapCol(func, col=0)`
```python
ch1 = Channel.create()
ch2 = Channel.create([1,2,3,4,5])
ch3 = Channel.create([('a', 1), ('b', 2)])
# ch1.map(lambda x: (x[0]*x[0],)) == []
# ch2.map(lambda x: (x[0]*x[0],)) == [(1,),(4,),(9,),(16,),(25,)]
# ch3.map(lambda x: (x[0], x[1]*x[1])) == [('a', 1), ('b', 4)]
# ch1.mapCol(lambda x: x*x) == []
# ch2.mapCol(lambda x: x*x) == [(1,),(4,),(9,),(16,),(25,)]
# ch3.mapCol(lambda x: x*x, 1) == [('a', 1), ('b', 4)]
# map & mapCol return an instance of Channel
```
- `Channel.filter(func)`
- `Channel.filterCol(func, col=0)`
```python
ch1 = Channel.create([
  (1,    0,     0,   1  ),
  ('a',  '',    'b', '0'),
  (True, False, 0,   1  ),
  ([],   [1],   [2], [0]),
])
# Filter by the first column, only first three rows remained
ch1.filterCol() == ch1[:3] 
# Filter by the second column, only the last row remained
ch1.filterCol(col = 1) == ch1[3:4]
# Filter by the third column, the 2nd and 4th row remained
ch1.filterCol(col = 2) == [ch1[1], ch1[3]]
# Filter by the fourth column, all rows remained
ch1.filterCol(col = 3) == ch1
# Filter with a function:		
ch1.filter(lambda x: isinstance(x[2], int)) == [ch1[0], ch1[2]]
# filter & filterCol return an instance of Channel
```
- `Channel.reduce(func)`
- `Channel.reduceCol(func, col=0)`
```python
ch1 = Channel.create()
# Raises TypeError, no elements
ch1.reduce(lambda x,y: x+y)
ch1 = Channel.create([1,2,3,4,5])
# Notice the different
ch1.reduce(lambda x,y: x+y) == (1, 2, 3, 4, 5) # x and y are tuples
ch1.reduceCol(lambda x,y: x+y) == 15           # x and y are numbers
```

### Add rows/columns to a channel

- `Channel.rbind(*rows)`  

   Each row can be either a channel, a tuple, a list or a non-iterable element(including string)   
  ```python
  ch1 = Channel.create()
  ch2 = Channel.create((1,2,3))
  
  row1 = Channel.create(1)
  row2 = Channel.create((2,2,2))
  row3 = [3]
  row4 = (3,)
  row5 = (4,4,4)
  row6 = [4,4,4]
  row7 = 5
  
  ch1.rbind(row1) == [(1, )]
  ch2.rbind(row1) == [(1,2,3),(1,1,1)],
  ch1.rbind(row2) == [(2,2,2)]
  ch2.rbind(row2) == [(1,2,3), (2,2,2)]
  ch1.rbind(row3) == [(3,)]
  ch2.rbind(row3) == [(1,2,3),(3,3,3)]
  ch1.rbind(row4) == [(3,)]
  ch2.rbind(row4) == [(1,2,3),(3,3,3)]
  ch1.rbind(row5) == [(4,4,4)]
  ch2.rbind(row5) == [(1,2,3),(4,4,4)]
  ch1.rbind(row6) == [(4,4,4)]
  ch2.rbind(row6) == [(1,2,3),(4,4,4)]
  ch1.rbind(row7) == [(5,)]
  ch2.rbind(row7) == [(1,2,3),(5,5,5)]
  ```


- `Channel.cbind(*cols)`
  ```python
  ch1 = Channel.create([(1, 2), (3, 4)])
  ch2 = Channel.create([5, 6])
  
  ch1.cbind(ch2) == [(1, 2, 5), (3, 4, 6)]
  
  ch2 = Channel.create(5)
  ch1.cbind(ch2)    == [(1, 2, 5), (3, 4, 5)]
  ch1.cbind([5, 6]) == [(1, 2, 5), (3, 4, 6)]
  ch1.cbind((5, 6)) == [(1, 2, 5), (3, 4, 6)]
  ch1.cbind("a")    == [(1, 2, 'a'), (3, 4, 'a')]
  
  ch1 = Channel.create()
  ch2 = Channel.create([21, 22])
  ch3 = 3
  ch4 = [41, 42]
  ch5 = (51, 52)
  ch6 = "a"
  
  ch1.cbind(ch2, ch3, ch4, ch5, ch6) == [(21, 3, 41, 51, 'a'), (22, 3, 42, 52, 'a')]
  ch1.cbind(ch3).cbind(ch6) == [(3, 'a')]
  ```

- `Channel.insert(index, col)`  
  ```python
  ch1 = Channel.create([(1, 2), (3, 4)])
  ch2 = Channel.create([5, 6])
  ch1.insert(0, ch2)    == [(5, 1, 2), (6, 3, 4)]
  ch1.insert(1, ch2)    == [(1, 5, 2), (3, 6, 4)]
  ch1.insert(-1, ch2)   == [(1, 5, 2), (3, 6, 4)]
  ch1.insert(None, ch2) == [(1, 2, 5), (3, 4, 6)]
  
  ch2 = Channel.create(5)
  ch1.insert(0, ch2)    == [(5, 1, 2), (5, 3, 4)]
  ch1.insert(1, ch2)    == [(1, 5, 2), (3, 5, 4)]
  ch1.insert(-1, ch2)   == [(1, 5, 2), (3, 5, 4)]
  ch1.insert(None, ch2) == [(1, 2, 5), (3, 4, 5)]
  
  ch1.insert(0, [5, 6])    == [(5, 1, 2), (6, 3, 4)]
  ch1.insert(1, [5, 6])    == [(1, 5, 2), (3, 6, 4)]
  ch1.insert(-1, [5, 6])   == [(1, 5, 2), (3, 6, 4)]
  ch1.insert(None, [5, 6]) == [(1, 2, 5), (3, 4, 6)]
  ch1.insert(0, (5, 6))    == [(5, 1, 2), (6, 3, 4)]
  ch1.insert(1, (5, 6))    == [(1, 5, 2), (3, 6, 4)]
  ch1.insert(-1, (5, 6))   == [(1, 5, 2), (3, 6, 4)]
  ch1.insert(None, (5, 6)) == [(1, 2, 5), (3, 4, 6)]
  ch1.insert(0, "a")       == [('a', 1, 2), ('a', 3, 4)]
  ch1.insert(1, "a")       == [(1, 'a', 2), (3, 'a', 4)]
  ch1.insert(-1, "a")      == [(1, 'a', 2), (3, 'a', 4)]
  ch1.insert(None, "a")    == [(1, 2, 'a'), (3, 4, 'a')]
  
  self.assertEqual(ch1, [(1, 2), (3, 4)])
  
  ch1 = Channel.create()
  ch2 = Channel.create([21, 22])
  ch3 = 3
  ch4 = [41, 42]
  ch5 = (51, 52)
  ch6 = "a"
  # Raises ValueError, when 1 is inserted, it is a 1-width channel, then you can't insert a 2-width to it.
  ch1.insert(1, ch2)
  ch1.insert(0, ch2, ch3, ch4, ch5, ch6) == [(21, 3, 41, 51, 'a'), (22, 3, 42, 52, 'a')]
  ```

### Fold a channel
`Channel.fold(n = 1)`
Fold a `channel`, Make a row to n-length chunk rows
For example, you have the following channel:

|a1|a2|a3|a4|
|-|-|-|-|
|b1|b2|b3|b4|

After apply `chan.fold(2)` you will get:

|a1|a2|
|-|-|
|a3|a4|
|b1|b2|
|b3|b4|

### Unfold a channel
`Channel.unfold(n=2)`
Combine n-rows into one row; do the reverse thing as `Channel.fold`. But note that the different meaning of `n`. In `fold`, `n` means the length of the chunk that a row is cut to; will in `unfold`, it means how many rows to combine.

### Copy a channel
`Channel.copy()`

{% endraw %}

[1]: https://pwwang.gitbooks.io/PyPPL/command-line-argument-parser.html

