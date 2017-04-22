

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
```
c = channel.create([0,1,2])
# produce [(0,), (1,), (2,)]
```
- From other `channel`s:   
```
c = channel.fromChannels(ch1, ch2, ...)
#This will do column bind, 
#requires channels have the same length
```
- From a file path pattern: 
```
c = channel.fromPath ("/a/b/*.txt", "any")
# You can specify type to filter the file list
# Possible file type: any(default), file, dir and link
```


