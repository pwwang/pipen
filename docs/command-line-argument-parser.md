# Command line argument parser
<!-- toc -->

This module is just for your convenience. You are free to use Python's built-in `argparse` module or just use `sys.argv`.

To start with, just import it from `pyppl`:
```python
from pyppl import params
```

## Add an option
```python
params.opt = 'a'
# or
# params.opt.setValue('a')
params.opt2.setType(list).setRequired()

# then don't forget to parse the command line arguments:
params.parse()
```
Then `python pipeline.py --param-opt b --param-opt2 1 2 3` will overwrite the value.  
`list` option can also be specified as `--param-opt2 1 --param-opt2 2 --param-opt2 3`
To use the value:
```python
var = params.opt.value + '2'
# var is 'b2'
var2 = params.opt2.value + [4]
# var2 is ['1', '2', '3', 4]
```

If you feel annoying using `params.xxx.value` to have the value of the option, you can convert the `params` object to a `pyppl.doct` object:
```python
ps = params.toDoct()
```
Then you can refer the values directly by:
```python
var = ps.opt + '2'
var2 = ps.opt2 + [4]
```


## Set properties of an option
An option has server properties:
- `desc`: The description of the option, shows in the help page. Default: `''`
- `required`: Whether the option is required. Default: `False`
- `show`: Whether this option should be shown in the help page. Default: `True`
- `type`: The type of the option value. Default: `str`
- `name`: The name of the option, then in command line, `--param-<name>` refers to the option.
- `value`: The default value of the option.

You can either set the value of an option by 
```python
params.opt.required = True
```
or
```python
params.opt.setRequired(True)
# params.opt.setDesc('Desctipion')
# params.opt.setShow(False)
# params.opt.setType(list)
# params.opt.setName('opt1')
# params.opt.setValue([1,2,3])
# or they can be chained:
# params.opt.setDesc('Desctipion') \
#           .setShow(False)        \
#           .setType(list)         \
#           .setName('opt1')       \
#           .setValue([1,2,3])
```
>**NOTE**: About the `type`:
- To explicitly specify type of an option, you have to use the type itself, instead of the name of the type. That mean `str` instead of `"str"`
- The type can be implied by: `params.opt = []` (implies `list`). But `params.opt.setValue('a')` or `params.opt.value = 1` won't change the type, instead, the value will be coerced to the type previously specified/implied.

## Load params from a dict
You can define a `dict`, and then load it to `params`:
```python
d2load = {
    'p1': 1,
    'p1.required': True,
    'p2': [1,2,3],
    'p2.show': True,
    'p3': 2.3,
    'p3.desc': 'The p3 params',
    'p3.required': True,
    'p3.show': True
}
params.loadDict (d2load)
# params.p1.value    == 1
# params.p1.required == True
# params.p1.show     == False
# params.p1.type     == int
# params.p2.value    == [1,2,3]
# params.p2.required == False
# params.p2.show     == True
# params.p2.type     == list
# params.p3.value    == 2.3
# params.p3.required == True
# params.p3.show     == False
# params.p3.type     == float
```
Note that by default, the options from the `dict` will be hidden from the help page. If you want to show some of them, just set `p2.show = True`, or you want to show them all: `params.loadDict(d2load, show = True)`

## Load params from a configuration file
If the configuration file has a name ending with '.json', then `json.load` will be used to load the file into a `dict`, and `params.loadDict` will be used to load it to `params`

Else python's `ConfigParse` will be used. All params in the configuration file should be under one section with whatever name:
```ini
[Config]
p1: 1
p1.required: True
p2: [1,2,3]
p2.show: True
p3: 2.3
p3.desc = 'The p3 params'
p3.required: True
p3.show: True
```

Similarly, you can set the default value for `show` property by: `params.loadCfgfile("params.config", show=True)`

## Set other properties of params
- `params.usage('--param-infile <infile> [Options]')` The usage of the program
- `params.example('python prog.py /path/to/file <options>')` The example of usages
- `params.desc('What does the program do?')` The description of the program
- `params.prefix('--p-')` The prefix of the options. Default: `--param-`
- `params.helpOpts('--help, -H')` The option to show the help page.  

>**Hint**
- You can also chain those settings: `params.usage(...).example(...)`  
- Multiple usages and examples can be separated by `'\n'`
- You can also set the `helpOpts` by `list`: `params.helpOpts(['-h', '-?'])`
- An empty string in `helpOpts` means to show help page if no arguments offered.