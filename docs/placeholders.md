#Placeholders

<!-- toc -->

{% raw %}
`pyppl` uses placeholders from `input`, `output` and some properties of `pyppl.proc`/`pyppl.job` to hold the values in `output`, `beforeCmd`, `afterCmd` and `script`. For example:
```python
p = proc()
p.input = {"v":[0,1,2]}
p.script = """
echo {{v}}
"""
```
`{{` and `}}` wrap a placeholder. the above example, there are 3 jobs, which will echo `0`, `1` and `2`, respectively.

## Transform values by placeholders
You can apply some function to transform values by placeholders:
```python
#{{ v | pow(2, _) }}  # NOTE: this is deprecated!
ph  = "{{ v | lambda x: pow(2, x) }}" # please use lambda function
ret = pyppl.utils.format (ph, {v: 3})
# ret == "9"
```
- `|` connects the chains. The first chain is always the key of the data used to render the placeholder. The rest of the chains could be:
  - A lambda function with one and only one argument
  - `[i]`/`["key"]` to get value from `iter` objects
  - `.func()` to call functions of an object. (i.e. `{{v | .lower()}}` for `{v: "A"}`)
- ~~`_` represents the value of previous chain~~ is deprecated!.
- `pyppl.utils.format(...)` always returns a **STRING**.
  - but the value passed among chains remains its own type (i.e. `{{v | lambda x: "a" + x}}` for `{v:1}` will raise a `TypeError`).


You can also apply a set of functions:
```python
#{{ v | pow(2, _) | pow(2, _) }}
{{ v | lambda x: pow(2,x) | lambda x: pow(2,x) }}
# "2","4","16"
```

Import modules in a placeholder:
```python
#{{ v | __import__('math').exp(_) }}
{{ v | lambda x: __import__('math').exp(x) }}
# "1", "2.71828182846", "7.38905609893"
```

## Built-in functions
We have a set of built-in funcitons for placeholders, they are:

| Function name | Function | Example-format | Example-data | Example-result |
|---------------|----------|----------------|--------------|----------------|
|`Rbool`|Change python value to R bool value|`{{v `&#x7c;` Rbool}}`|`{'v':1}`|`TRUE`|
|`realpath`|Get the real path|`{{v `&#x7c;` realpath}}`|`{'v':some/path}`|`<the real path of some/path>`|
|`readlink`|Read the link|`{{v `&#x7c;` readlink}}`|`{'v':some/link}`|`<the real path some/link links to`|
|`dirname`|Get the directory path of given path|`{{v `&#x7c;` dirname}}`|`{'v':/path/to/some/file}`|`/path/to/some/`|
|`basename`|Get the basename of given path|`{{v `&#x7c;` basename}}`|`{'v':/path/to/some/file.txt}`|`file.txt`|
|`bn`|Alias of `basename`||||
|`filename`|Basename without extension|`{{v `&#x7c;` filename}}`|`{'v':'/a/b/c.txt'}`|`c`|
|`fn`|Alias of `filename`||||
|`ext`|Get the extension of a file|`{{v `&#x7c;` ext}}`|`{'v':'/a/b/c.txt'}`|`.txt`|
|`prefix`|Get the prefix of a path (no extension)|`{{v `&#x7c;` prefix}}`|`{'v':'/a/b/c.d.txt'}`|`/a/b/c.d`|
|`asquote`|Quote an array(list) with quote and joined with space|`{{v `&#x7c;` asquote}}`|`{'v':['1','2']}`|`"1" "2"`|
|`acquote`|Quote an array(list) with quote and joined with comma|`{{v `&#x7c;` acquote}}`|`{'v':['1','2']}`|`"1","2"`|
|`quote`|Quote a string|`{{v `&#x7c;` quote}}`|`{'v':'1'}`|`"1"`|
|`squote`|Single-quote a string|`{{v `&#x7c;` squote}}`|`{'v':'1'}`|`'1'`|
|`json`|Dumps an python object to json string|`{{v `&#x7c;` quote}}`|`{'v':{'a':1}}`|`'{"a": 1}'`|
|`read`|Read the content from a file|`{{v `&#x7c;` read}}`|`{'v':'/path/to/file'}`|`'<file content>'`|
|`readlines`|Read the file content as lines (`EOL` stripped)|`{{v `&#x7c;` readlines `&#x7c;` json}}`|`{'v':'/path/to/file'}`|`'["<line1>", "<line2>", ...]'`|

> **Hint** To get the extension without the leading dot: `{{v | ext | [1:]}}`

## Define your own shortcut functions
You can define your own shortcut functions for placeholders:
```python
from pyppl import utils
utils.format.shorts['replace'] = "lambda x: x.replace('aaa', 'bbb')"
# utils.format("{{a | replace}}", {"a": "1aaa2"}) == "1bbb2"
```

## `proc` and `job` property placeholders
You can also use some `proc`/`job` property values with placeholders: `{{proc.<property>}}`/`{{job.<property>}}`. Available properties:

| property | alias |meaning |
|--------------|---------|----------------------|
|`proc.id`|| The id of the process, in most case the variable name. `p = proc() # p.id == "p"`|
|`proc.tag`||A tag of the process|
|`proc.tmpdir`||Where the workdir locates|
|`proc.workdir`||The work directory|
|`proc.forks`||How many jobs to run concurrently|
|`proc.cache`||The cache option|
|`proc.echo`||Whether to print stdout and stderr to the screen|
|`proc.runner`||The runner|
|`proc.defaultSh`(deprecated)|`proc.lang`|The interpreter for the script|
|`proc.errorhow`|`proc.errhow`|What to do if error happens|
|`proc.errorntry`|`proc.errntry`|If `errorhow == 'retry'`, how many times to re-try|
|`proc.exportdir`|`proc.exdir`|The export directory|
|`proc.exporthow`|`proc.exhow`|How to export output files|
|`proc.exportow`|`proc.exow`|Whether to overwrite existing files when export|
|`proc.length`||How many jobs are there for the process|
|`proc.suffix`||The suffix of the process|
|`proc.args`||Additional arguments for the process, typically a `dict`. For example: `p.args={"a":1}` you may use `{{args.a}}` to access it.|
|`job.id`||The pid or the id from a queue set by `job.pid`|
|`job.index`|`#`|The job index|
|`job.indir`||The input directory of the job|
|`job.outdir`||The output directory of the job|
|`job.dir`||The directory of the job|
|`job.outfile`||The file with the STDOUT|
|`job.errfile`||The file with the STDERR|

{% endraw %}
