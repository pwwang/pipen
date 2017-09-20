# Templating

<!-- toc -->

``
{% raw %}
`PyPPL` has its own template engine, which derived from a [500-line-or-less template engine][1]. It also supports [Jinja2][2] if you have if installed and specify `"Jinja2"` to `pXXX.template`.
The built-in template engine is enabled by default.



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
ph  = "{{ v | lambda x: pow(2, x) }}" # please use lambda function
ret = pyppl.utils.format (ph, {v: 3})
# ret == "9"
```
- `|` connects the chains. The first chain is always the key of the data used to render the placeholder. The rest of the chains could be:
  - A lambda function with one and only one argument
  - `[i]`/`["key"]` to get value from `iter` objects
  - `.func()` to call functions of an object. (i.e. `{{v | .lower()}}` for `{v: "A"}`)
- `pyppl.utils.format(...)` always returns a **STRING**.
  - but the value passed among chains remains its own type (i.e. `{{v | lambda x: "a" + x}}` for `{v:1}` will raise a `TypeError`).
- Built-in functions, or a callable object can be used, for example:
  - `{{ v | len }}` for `{v: "abcdefg"}` will return `"7"`
  - `{{ v | __import__('math').ceil | int }}` for `{v: "8.8"}` will return `"9"`
- Frequently-used modules can be imported in the first component:
  - `{{ import math | v | math.ceil }}` 
  - `{{ from math import ceil | v | ceil }}`
  - `{{ from math import ceil; import math import floor | v | lambda x: floor(ceil(x+.5)+.5) | int}}` for `{v: "8.8"}` will return `"10"`


You can also apply a set of functions:
```python
{{ v | lambda x: pow(2,x) | lambda x: pow(2,x) }}
# "2","4","16"
```

Another trick to import module is to use `__import__`:
```python
{{ v | lambda x: __import__('math').log(x, 2) | int}} 
# {'v': 8 } ==> 3
# or simply (if you only have one argument for your function:
{{ v | __import__('math').log | int}} 
# {'v': __import__('math').e} ==> 1
# or if you use the module frequently:
{{ v | lambda x, path=__import__('os').path: path.splitext(path.basename(x)) }} 
# {'v': '/a/b/c.txt'} ==> c
```

## Built-in functions
We have a set of built-in funcitons for placeholders, they are:

| Function name | Function | Example-format | Example-data | Example-result |
|---------------|----------|----------------|--------------|----------------|
|`Rbool`|Change python value to R bool value|`{{v `&#x7c;` Rbool}}`|`{'v':1}`|`TRUE`|
|`realpath`|Get the real path|`{{v `&#x7c;` realpath}}`|`{'v':some/path}`|`<the real path of some/path>`|
|`readlink`|Read the link|`{{v `&#x7c;` readlink}}`|`{'v':some/link}`|`<the real path some/link links to`|
|`dirname`|Get the directory path of given path|`{{v `&#x7c;` dirname}}`|`{'v':/path/to/some/file}`|`/path/to/some/`|
|`basename`|Get the basename of given path|`{{v `&#x7c;` basename}}`|`{'v':/path/to/some/file[1].txt}`|`file.txt`|
|`bn`|Alias of `basename`||||
|`basename.orig`|Get the original basename of given path|`{{v `&#x7c;` basename}}`|`{'v':/path/to/some/file[1].txt}`|`file[1].txt`|
|`bn.orig`|Alias of `basename.orig`||||
|`filename`|Basename without extension|`{{v `&#x7c;` filename}}`|`{'v':'/a/b/c[1].txt'}`|`c`|
|`fn`|Alias of `filename`||||
|`filename.orig`|Oringal basename without extension|`{{v `&#x7c;` filename}}`|`{'v':'/a/b/c[1].txt'}`|`c[1]`|
|`fn.orig`|Alias of `filename.orig`||||
|`ext`|Get the extension of a file|`{{v `&#x7c;` ext}}`|`{'v':'/a/b/c.txt'}`|`.txt`|
|`prefix`|Get the prefix of a path (no extension)|`{{v `&#x7c;` prefix}}`|`{'v':'/a/b/c.d.txt'}`|`/a/b/c.d`|
|`prefix.orig`|Get the prefix of a path (no extension)|`{{v `&#x7c;` prefix}}`|`{'v':'/a/b/c.d[1].txt'}`|`/a/b/c.d[1]`|
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

[1]: https://github.com/aosabook/500lines/tree/master/template-engine
[2]: http://jinja.pocoo.org/