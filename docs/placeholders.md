# Placeholders
<!-- toc -->

{% raw %}
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
{{ v | lambda x: x*2 }}
# "0", "2", "4"
```
> **Note** Only one argument is allow for lambda function here.

## Built-in functions
We have a set of built-in funcitons for placeholders, they are:
| Function name | Function | Example-format | Example-data | Example-result |
|-|-|-|-|-|
|`Rbool`|Change python value to R bool value|`{{v|Rbool}}`|`{'v':1}`|`TRUE`|
|`realpath`|Get the real path|`{{v|realpath}}`|`{'v':some/path}`|`<the real path of some/path>`|
|`readlink`|Read the link|`{{v|readlink}}`|`{'v':some/link}`|`<the real path some/link links to`|
|`dirname`|Get the directory path of given path|`{{v|dirname}}`|`{'v':/path/to/some/file}`|`/path/to/some/`|
|`basename`|Get the basename of given path|`{{v|basename}}`|`{'v':/path/to/some/file.txt}`|`file.txt`|
|`bn`|Alias of `basename`||||
|`filename`|Basename without extension|`{{v|filename}}`|`{'v':'/a/b/c.txt'}`|`c`|
|`fn`|Alias of `filename`||||
|`ext`|Get the extension of a file|`{{v|ext}}`|`{'v':'/a/b/c.txt'}`|`.txt`|
|`fnnodot`|Get the filename without a dot in it|`{{v|fnnodot}}`|`{'v':'/a/b/c.d.txt'}`|`c`|
|`prefix`|Get the prefix of a path (no extension)|`{{v|prefix}}`|`{'v':'/a/b/c.d.txt'}`|`/a/b/c.d`|
|`pxnodot`|Get the prefix without a dot in it|`{{v|pxnodot}}`|`{'v':'/a/b/c.d.txt'}`|`/a/b/c`|
|`asquote`|Quote an array(list) with quote and joined with space|`{{v|asquote}}`|`{'v':['1','2']}`|`"1" "2"`|
|`acquote`|Quote an array(list) with quote and joined with comma|`{{v|acquote}}`|`{'v':['1','2']}`|`"1","2"`|
|`quote`|Quote a string|`{{v|quote}}`|`{'v':'1'}`|`"1"`|
|`squote`|Single-quote a string|`{{v|quote}}`|`{'v':'1'}`|`'1'`|

> **Hint** To get the extension without the leading dot: `{{v | ext | [1:]}}`

## Define your own shortcut functions
You can define your own shortcut functions for placeholders:
```python
from pyppl import utils
utils.format.shorts['replace'] = "lambda x: x.replace('aaa', 'bbb')"
# utils.format("{{a | replace}}", {"a": "1aaa2"}) == "1bbb2"
```

## `Proc` and `Job` property placeholders
You can also use some `proc`/`job` property values with placeholders: `{{proc.<property>}}`/`{{job.<property>}}`. Available properties:

| property     | alias   |meaning               |
|--------------|---------|----------------------|
|`proc.id`|| The id of the process, in most case the variable name. `p = proc() # p.id == "p"`|
|`proc.tag`||A tag of the process|
|`proc.tmpdir`||Where the workdir locates|
|`proc.workdir`||The work directory|
|`proc.forks`||How many jobs to run concurrently|
|`proc.cache`||The cache option|
|`proc.echo`||Whether to print stdout and stderr to the screen|
|`proc.runner`||The runner|
|`proc.defaultSh`|`proc.lang`|The interpreter for the script|
|`proc.errorhow`|`proc.errhow`|What to do if error happens|
|`proc.errorntry`|`proc.errntry`|If `errorhow == 'retry'`, how many times to re-try|
|`proc.exportdir`|`proc.exdir`|The export directory|
|`proc.exporthow`|`proc.exhow`|How to export output files|
|`proc.exportow`|`proc.exow`|Whether to overwrite existing files when export|
|`proc.length`||How many jobs are there for the process|
|`proc.args`||Additional arguments for the process, typically a `dict`. For example: `p.args={"a":1}` you may use `{{proc.args.a}}` to access it.|
|`job.id`|`#`|The job id|
|`job.indir`||The input directory of the job|
|`job.outdir`||The output directory of the job|
|`job.dir`||The directory of the job|
|`job.outfile`||The file with the STDOUT|
|`job.errfile`||The file with the STDERR|

{% endraw %}
