
## Specify input of a process

The input of a process is specified with `input`, the keys of the input data, and `input_data`, the real input data

!!! tip

    Why separate the keys and data?

    Because the keys and data are not always combined, for example, we need the keys to infer the `output` and `script` (using them in the template), but the data may be deferred to obtain from the output of dependency processes.


The complete form of an input key (`input`) is `<key>:<type>`. The `<type>` could be `var`, `file`, `dir`, `files` and `dirs`. **A type of `var` can be omitted.** So `ph1, ph2` is the same as `ph1:var, ph2:var`

If a process is requiring other processes, the specified `input_data` will be ignored, and will use the output data of their required processes:

```python
class P1(Proc):
    input = "v1"
    output = "o1:{{in.v1}}" # pass by v1 as output variable
    input_data = ["a"]

class P2(Proc):
    input = "v2"
    output = "o2:{{in.v2}}"
    input_data = ["b"]

class P3(Proc):
    requires = [P1, P2]
    input = "i1, i2"
    output = "o3:{{in.i1}}_{{in.i2}}" # will be "a_b"
    # input_data = []  # ignored with a warning

Pipen().run(P1, P2)
```

!!! Tip

    The direct `input_data` is ignore, but you can use a callback to modify the input channel.
    For example:

    ```python
    class P4(Proc):
        requires = [P1, P2]
        input = "i1, i2"
        input_data = lambda ch: ch.applymap(str.upper)
        output = "o3:{{in.i1}}_{{in.i2}}" # will be "A_B"
    ```

!!! Note

    When the input data does have enough columns, `None` will be used with warnings. And when the input data has more columns than the input keys, the extra columns are dropped and ignored, also with warnings

## Specify output of a process

Different from input, instead of channels, you have to tell `pipen` how to compute the output channel. The output can be a `list` or `str`. If it's `str`, a comma (`,`) is used to separate different keys:

To use templating in `output`, see [`templating`][1].

```python
class P1(Proc):
    input = "invar, infile"
    input_data = [(1, "/a/b/c.txt")]
    output = (
        "outvar:{{in.invar}}2, "
        "outfile:file:{{in.infile.split('/')[-1]}}2, "
        "outdir:dir:{{in.infile.split('/')[-1].split('.')[0]}}-dir"
    )

# The type 'var' is omitted in the first element.
# The output channel will be:
#
#    outvar    outfile                 outdir
#    <object>  <object>                <object>
# 0  "12"      "<job.outdir>/c.text2"  "<job.outdir>/c-dir"
```

## Types of input and output

### Input

|Type|Meaning|
|----|-------|
|`var`|Use the values directly|
|`file`|Treat the data as a file path|
|`dir`|Treat the data as a directory path|
|`files`|Treat the data as a list of file paths|
|`dirs`|Treat the data as a list of directory paths|

For `file`/`files`, when checking whether a job is cached, their last modified time will be checked.

For `dir`/`dirs`, if `dirsig > 0`, then the files inside the directories will be checked. Otherwise, the directories themselves are checked for last modified time.


### Output

|Type|Meaning|Memo|
|----|-------|----|
|`var`|Use the values directly||
|`dir`|Use the data as a directory path|The directory will be created directly|
|`file`|Use the data as a file path||

[1]: ../templating
