
`PyPPL` uses [liquidpy][1] as default template engine. It also supports [Jinja2][2] if you have it installed and then turn it on: `pXXX.template = "Jinja2"`.

# Common data avaible for rendering
When rendering a template, following data are fed to the render function. So that you can use those values in the template. Some attribute values of a process are shared for all templates that are applied:

* `proc.cache`: The cache option
* `proc.acache`: Whether clean (error check and export) the job when it's cached?
* `proc.desc`: The description of the process
* `proc.echo`: The echo option
* `proc.errhow`: What to do if error happens
* `proc.errntry`: If `errorhow == 'retry'`, how many times to re-try if a job fails
* `proc.exdir`: The export directory
* `proc.exhow`: How to export output files
* `proc.exow`: Whether to overwrite existing files when exporting output files
* `proc.forks`: How many jobs to run concurrently
* `proc.id`: The id of the process.
* `proc.lang`: The interpreter for the script
* `proc.ppldir`: Where the workdirs are located
* `proc.rc`: The rc option
* `proc.resume`: The resume option
* `proc.runner`: The runner
* `proc.sets`: A list of attribute names that has been set explictly
* `proc.size`: Number of jobs
* `proc.suffix`: The unique suffix of the process
* `proc.tag`: The tag of the process
* `proc.workdir`: The workdir of the process

# Other data for rendering
For each job, we also have some value available for rendering:

* `job.index`: The index of the job
* `job.indir`: The input directory of the job
* `job.outdir`: The output directory of the job
* `job.dir`: The directory of the job
* `job.outfile`: The stdout file of the job
* `job.errfile`: The stderr file of the job
* `job.pidfile`: The file stores the PID of the job or the identity from a queue runner.
* `job.cachedir`: The cache directory for the process to cache some intermediate results.

Input, output and args data are under namespace `i`, `o` and `args`, respectively.
For example, you have following definition:
```python
pXXX.input  = {"a": ["hello"], "b": ["/path/to/file"]}
pXXX.output = "a:{{i.a}} world!"
pXXX.args.x = 1
```
Now you can access them by: `{{i.a}}`, `{{i.b}}`, `{{o.a}}` and `{{args.x}}`

# The scope of data
|Attribute|Data available|Meaning|
|---------|------------|-------|
|`pXXX.preCmd`|`{{proc.*}}`, |Command to run before job starts|
|`pXXX.postCmd`|`{{proc.*}}`|Command to run after job finishes|
|`pXXX.output`|`{{proc.*}}`, `{{job.*}}`, `{{i.*}}`|The output of the process|
|`pXXX.expect`|All above-mentioned data|Command to check output|
|`pXXX.expart`|All above-mentioned data|Partial export|
|`pXXX.script`|All above-mentioned data|The script to run|

# Built-in filters
Sometimes we need to transform the data in a template. We have some built-in functions available for the transformation.
For built-in template engine, you may use pipe, for example: `{{i.file | basename}}`; for `Jinja2`, you have to use functions as "functions", for example: `{{basename(in.file)}}`. Here we give the examples with built-in template engine syntax.

- `R`: Transform a python value to R value. For example:

| Usage | Data | Result |
|-------|------|--------|
| `{{v ` &#x7c; ` R}}` | `{'v': True}` | `TRUE` |
|| `{'v': 'TRUE'}` | `TRUE` |
|| `{'v': 'NA'}` | `NA` |
|| `{'v': 'NULL'}` | `NULL` |
|| `{'v': 1}` | `1` |
|| `{'v': 'r:c(1,2,3)'}` | `c(1,2,3)` |
|| `{'v': [1,2,3]}` | `c(1,2,3)` |
|| `{'v': {'a':1, 'b':2}}` | `list(a=1, b=2)` |
|| `{'v': 'plainstring'}` | `"plainstring"` |

- ~~`Rvec`: Transform a python list to a R vector. For example:~~ will be deprecated, use `R` instead.
  - ~~`{{v | Rvec}}` with `{'v': [1,2,3]}` results in `c(1,2,3)`~~
- `Rlist`: Transform a python dict to a R list. For example:
  - `{{v | Rlist}}` with `{'v': {'a':1, 'b':2}}` results in `list(a=1, b=2)`
  - `{{v | Rlist}}` with `{'v': {0:1, 1:2}}` results in ```list(`0`=1, `1`=2)```
  - `{{v | Rlist: False}}` with `{'v': {0:1, 1:2}}` results in ```list(1, 2)```
  - This also applies for `R`
- `realpath`: Alias of `os.path.realpath`
- `readlink`: Alias of `os.readlink`
- `dirname`: Alias of `os.path.dirname`
- `basename`: Get the basename of a file. If a file is renamed by `PyPPL` in case of input files with the same basename, it tries to get the original basename. For example:

| Usage | Data | Result |
|-------|------|--------|
| `{{v ` &#x7c; ` basename}}` | `{'v': '/path/to/file.txt'}` | `file.txt` |
|| `{'v': '/path/to/file[1].txt'}` | `file.txt` |
| `{{v ` &#x7c; ` basename: True}}` | `{'v': '/path/to/file[1].txt'}` | `file[1].txt`|

- `bn`: Alias of `basename`
- `filename`: Similar as `basename` but without extension.
- `fn`: Alias of `filename`
- `stem`: Alias of `filename`
- `filename2`: Get the filename without dot.
- `fn2`: Alias of `filename2`. (i.e: `/a/b/c.d.e.txt` -> `c`)
- `ext`: Get extension of a file. Alias of `os.path.splitext(x)[1]`
  - Dot is included. To remove the dot: `{{v | ext | [1:]}}`
- `prefix`: Get the prefix of a path, without extension. It acts like `{{v | dirname}}/{{v | filename}}`
- `prefix2`: Get the prefix of a path without dot in filename. (i.e: `/a/b/c.d.e.txt` -> `/a/b/c`)
- `quote`: Double-quote a string.
- `asquote`: Double quote items in a list and join them by space. For example:
  - `{{v | asquote}}` with `{'v': [1,2,3]}` results in `"1" "2" "3"`
- `acquote`: Double quote items in a list and join them by comma.
- `squote`: Single-quote a string.
- `json`: Dumps a python object to a json string. Alias of `json.dumps`
- `read`: Read the content of a file.
- `readlines`: Read the lines of a file. Empty lines are skipped by default. To return the empty lines for `{'v': '/path/to/file', 'skipEmptyLines': False}`:
  - `{{v, skipEmptyLines | readlines}}`
- `repr`: Alias of python `repr` built-in function.

# Use `Liquid`:
For usage of `Jinja2`, you may refer to its [official documentation][1].

# Use Jinja2
All the data and environment definition mentioned above are all applicable when you use `Jinja2` as your template engine.
For usage of `Jinja2`, you may refer to its [official documentation][2].


[1]: https://github.com/pwwang/liquidpy
[2]: http://jinja.pocoo.org/
