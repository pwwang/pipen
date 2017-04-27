# Placeholders
<!-- toc -->

`pyppl` uses placeholders from `input`, `output` and some properties of a `proc` to hold the values in `output`, `beforeCmd`, `afterCmd` and `script`. For example:
```python
p = proc()
p.input  = {"v":[0,1,2]}
p.script = """
echo {{v}}
"""
```
`{{` and `}}` wrap a placeholder. the above example, there are 3 jobs, which will echo `0`, `1` and `2`, respectively. 

## Transform values by placeholders
You can apply some function to transform values by placeholders:
```python
{{ v | pow(2, _) }}
# "1","2","4"
```
`|` separates the placeholder and the function, `_` represents the value on the left.
> **Caution** a placeholder always returns a string.

You can also apply a set of functions:
```python
{{ v | pow(2, _) | pow(2, _) }}
# "2","4","16"
```

Import modules in a placeholder:
```python
{{ v | __import__('math').exp(_) }}
# "1", "2.71828182846", "7.38905609893"
```

Use `lambda` functions:
```python
{{ v | (lambda x: x*2)(_) }}
# "0", "2", "4"
```
> **Caution** always call the function instead of just define the function (`(lambda ...)(_)` instead of `lambda ...`).

## File placeholders
If an `input` or `output` as a file: `infile:file`, then `{{infile}}` will be the link path that links to the input file in the input directory of a process (`proc`). `{{infile.bn}}` is the basename (without extension), `{{infile.fn}}` holds the filename (with extension), and `{{infile.ext}}` indicates the extensions. Examples:

|`infile`    |`infile.fn`   |`infile.bn`    | `infile.ext`|
|------------|--------------|---------------|-------------|
|`/a/b/c.txt`|`c`           |`c.txt`        | `.txt`      |
|`./dir`     |`dir`         |`dir`          | [EMPTY STRING]     |

> **Note** `filevar:file` is almost the same as `filevar:dir`, the only difference is that if `filevar:dir` is in the output, the directory will be created automatically.

## `Proc` property placeholders
You can also use some `proc` property values with placeholders: `{{proc.<property>}}`. Available properties:

| property     | alias   |meaning               |
|--------------|---------|----------------------|
|id|| The id of the process, in most case the variable name. `p = proc() # p.id == "p"`|
|tag||A tag of the process|
|tmpdir||Where the workdir locates|
|workdir||The work directory|
|forks||How many jobs to run concurrently|
|cache||The cache option|
|echo||Whether to print stdout and stderr to the screen|
|runner||The runner|
|defaultSh|lang|The interpreter for the script|
|errorhow|errhow|What to do if error happens|
|errorntry|errntry|If `errorhow == 'retry'`, how many times to re-try|
|exportdir|exdir|The export directory|
|exporthow|exhow|How to export output files|
|exportow|exow|Whether to overwrite existing files when export|
|indir||The input directory for the process|
|outdir||The output directory for the process|
|length||How many jobs are there for the process|
|args||Additional arguments for the process, typically a `dict`. For example: `p.args={"a":1}` you may use {% raw %}`{{proc.args.a}}`{% endraw %} to access it.|

## Job index placeholders
You can use `{{#}}` to replace the job index. For example:
`p.output = {"outfile:file:{{#}}.txt"}` specifies output file according to job index for each job.