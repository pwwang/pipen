

# Channels

Channels are used to pass data from one `proc` to the other. It is basically a `list`, each element is a `tuple`. The length a the `tuple` corresponds to the number of variables of the input or output of a `proc`.
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
Then for job#0 `"{{v1}}"` will be replaced by `a1`




