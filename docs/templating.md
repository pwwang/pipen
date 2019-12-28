
`PyPPL` uses [liquidpy][1] as default template engine. It also supports [Jinja2][2] if you have it installed and then turn it on: `pXXX.template = "Jinja2"`.

## Common data avaible for rendering
When rendering a template, one can use any `Proc` properties. For example:

```liquid
{{proc.id}}
{# pXXX #}
```

## Other data for rendering
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

## The scope of data
`{{args.*}}` can be used in all positions listed below

|Attribute|Data available|Meaning|
|---------|------------|-------|
|`pXXX.output`|`{{proc.*}}`, `{{job.*}}`, `{{i.*}}`|The output of the process|
|`pXXX.script`|All above-mentioned data|The script to run|

## Use of `Liquid`:
For usage of `liquidpy`, you may refer to its [official documentation][1].

## Use of Jinja2
All the data and environment definition mentioned above are all applicable when you use `Jinja2` as your template engine.
For usage of `Jinja2`, you may refer to its [official documentation][2].

## Wrapping a template engine
Of course, one can use his favorite template engine in `PyPPL`, but just have to wrap it:

```python
from pyppl import Proc
from pyppl.template import Template

class AnotherLiquidWrapper(Template):
	"""@API
	liquidpy template wrapper.
	"""

	def __init__(self, source, **envs):
		"""
		Initiate the engine with source and envs
		@params:
			`source`: The souce text
			`envs`: The env data
		"""
		super(TemplateLiquid, self).__init__(source ,**envs)
		self.envs['__engine'] = 'liquid'
		self.engine = Liquid(source, **self.envs)
		self.source = source

	def _render(self, data):
		"""
		Render the template
		@params:
			data (dict): The data used for rendering
		@returns:
			The rendered string
		"""
		return self.engine.render(**data)

pXXX = Proc(template = AnotherLiquidWrapper)
```

[1]: https://github.com/pwwang/liquidpy
[2]: http://jinja.pocoo.org/
