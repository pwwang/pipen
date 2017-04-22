

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
### Expand a channel by directory
Sometimes we prepare files in one job (for example, split a big file into small ones in a directory), then handle these files by different jobs in a process, so that they can be processed simultaneously. 



