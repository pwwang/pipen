Templates are used in `output` and `script` in process definition.

## Template engines

By default, `pipen` uses [`liquid`][1] template engine to render the `output` and `script`. You can also switch the template engine to [`jinja2`][2] by specifying:

```toml
template = "jinja2"
```

in one of the configuration files, or in the `Pipen` constructor:

```python
pipeline = Pipen(..., template="jinja2", ...)
```

or in the process definition

```python
class MyProcess(Proc):
    ...
    template = "jinja2" # overwrite the global template engine
```

Besides specifying the name of a template engine, you can also specify a subclass `pipen.template.Template` as a template engine. This enables us to use our own template engine. You just have to wrap then use a subclass of `pipen.template.Template`. For example, if you want to use [`mako`][3]:

```python
from mako.template import Template as MakoTemplate
from pipen.template import Template

class TemplateMako(Template):

    def __init__(self, source, **kwargs):
        super().__init__(source)
        self.engine = MakoTemplate(source, **kwargs)

    def _render(self, data):
        return self.engine.render(**data)

# Use it for a process
from pipen import Proc

class MyProcess(Proc):
    template = TemplateMako
    ... # other configurations

```

The `template_opts` configuration is used to pass to `TemplateMako` constructor. The values is passed by to the `MakoTemplate` constructor.

You can also register the template as a plugin of pipen:

In `pyproject.toml`:

```toml
[tool.poetry.plugins.pipen_tpl]
mako = "pipen_mako:pipen_mako"
```

Or in `setup.py`:

```python
setup(
    ...,
    entry_points={"pipen_tpl": ["pipen_mako:pipen_mako"]},
)
```

Then in `pipen_mako.py` of your package:

```python
def pipen_mako():
    # TemplateMako is defined as the above
    return TemplateMako
```

## Rendering data

There are some data shared to render both `output` and `script`. However, there are some different. One of the obvious reasons is that, the `script` template can use the `output` data to render.

### `output`

The data to render the `output`:

|Name|Description|
|-|-|
|`job.index`|The index of the job, 0-based|
|`job.metadir`|The directory where job metadata is saved, typically `<pipeline-workdir>/<pipeline-name>/<proc-name>/<job.index>/`|
|`job.outdir`|*The output directory of the job: `<pipeline-workdir>/<pipeline-name>/<proc-name>/<job.index>/output`|
|`job.stdout_file`|The file that saves the stdout of the job|
|`job.stderr_file`|The file that saves the stderr of the job|
|`job.lock_file`|The file lock of the job, prevent the same job to run simultaneously so that they are "thread-safe"|
|`in`|The input data of the job. You can use `in.<input-key>` to access the data for each input key|
|`proc`|The process object, used to access their properties, such as `proc.workdir`|
|`args`|The `args` of the process|

`*`: If the process is an end process, it will be a symbolic link to `<pipeline-outdir>/<process-name>/<job.index>`. When the process has only a single job, the `<job.index>` is also omitted.

### `script`

All the data used to render `output` can also be used to render `script`. Addtionally, the rendered `output` can also be used to render `script`. For example:

```python
class MyProcess(Proc):
    input = "in"
    output = "outfile:file:{{in.in}}.txt"
    script = "echo {{in.in}} > {{out.outfile}}"
    ... # other configurations

```

With input data ["a"], the script is rendered as `echo a > <job.outdir>/a.txt`


[1]: https://github.com/pwwang/liquidpy
[2]: https://github.com/pallets/jinja
[3]: https://www.makotemplates.org/
