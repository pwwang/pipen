
<!-- toc -->

`PyPPL` will generate a graph in [DOT language][1], according to the process dependencies.
You can have multiple [renderers][2] to visualize to graph. A typical one is [Graphviz][3]. With its python port [graphviz][7] installed, you can output the flowchart to an svg figure.

# Generate the flowchart
For example, if we have a pipeline written in `pipeline.py`:
```python
from pyppl import PyPPL, Proc

p1 = Proc()
p2 = Proc()
p3 = Proc()
p4 = Proc()
p5 = Proc()
p6 = Proc()
p7 = Proc()
p8 = Proc()
p9 = Proc()
"""
           p1         p8
        /      \      /
     p2           p3
        \      /
           p4         p9
        /      \      /
     p5          p6 (export)
        \      /
          p7 (export)
"""
p2.depends = p1
p3.depends = p1, p8
p4.depends = p2, p3
p4.exdir   = "./export"
p5.depends = p4
p6.depends = p4, p9
p6.exdir   = "./export"
p7.depends = p5, p6
p7.exdir   = "./export"

# make sure at least one job is created.
p1.input = {"in": [0]}
p8.input = {"in": [0]}
p9.input = {"in": [0]}

PyPPL().star(p1, p8, p9).flowchart().run()
```

You can specify different files to store the dot and svg file:
```python
pyppl().starts(p1, p8, p9).flowchart("/another/dot/file", "/another/svg/file")
```
> **Note** The svg file will be only generated if you specify the right command to do it.

For example, if you have [Graphviz](http://www.graphviz.org/) installed, you will have `dot` available to convert the dot file to svg file:
```python
PyPPL().start(p1, p8, p9).flowchart(
    "/another/dot/file",
    "/another/svg/file"
)
```

The graph (`svgfile`) will be like:

![Pipeline][4]

The green processes are the starting processes; ones with purple text are processes that will export the output files; and nodes in red are the end processes of the pipeline.

# Use the dark theme
```python
PyPPL({"default": {
    '_flowchart': {'theme': 'dark'}
}}).star(p1, p8, p9).flowchart().run()
```
![Pipeline-flowchart-dark][5]

You can also hide some processes in the flowchart. For example, you may hide `p3`, then it will look like:
```
           p1     p8
        /   |    /
     p2     |   /
        \   |  /
           p4         p9
        /      \      /
     p5          p6 (export)
        \      /
          p7 (export)
```

!!! note
    `p4` can not be hidden in this case, because we don't known how we should connect `p2, p3` to `p5, p6`. The processes that can be hidden are only the ones with in-degree (# of processes it depends on) or out-degree (# processes depends on it) 1. Start and end processes can not be hidden.

# Define your own theme
You just need to define the style for each type of nodes (refer [DOT node shapes][6] for detailed styles):
You may also put the definition in the default configuration file (`~/.PyPPL.json`)
```python
PyPPL({'default': {
    '_flowchart': {
        'theme': {
            'base':  {
                'shape':     'box',
                'style':     'rounded,filled',
                'fillcolor': '#555555',
                'color':     '#ffffff',
                'fontcolor': '#ffffff',
            },
            'start': {
                'style': 'filled',
                'color': '#59b95d', # green
                'penwidth': 2,
            },
            'end': {
                'style': 'filled',
                'color': '#ea7d75', # red
                'penwidth': 2,
            },
            'export': {
                'fontcolor': '#db95e6', # purple
            },
            'skip': {
                'fillcolor': '#eaeaea', # gray
            },
            'skip+': {
                'fillcolor': '#e9e9e9', # gray
            },
            'resume': {
                'fillcolor': '#1b5a2d', # light green
            },
            'procset': {
                'style': 'filled',
                'color': '#eeeeee', # almost white
            }
        }
    }
}}).star(p1, p8, p9).flowchart().run()
```

Explanations of node types:

- `base`: The base node style
- `start`: The style for starting processes
- `end`: The style for starting processes
- `export`: The style for processes have output file to be exported
- `skip`: The style for processes to be skiped
- `skip+`: The style for processes to be skiped but ouput channel will be computed
- `resume`: The style for the processes to be resumed
- `procset`: The style for the group, where all processes belong to the same procset.


[1]: https://en.wikipedia.org/wiki/DOT_(graph_description_language)
[2]: https://en.wikipedia.org/wiki/DOT_(graph_description_language)#Layout_programs
[3]: https://en.wikipedia.org/wiki/Graphviz
[4]: ./drawFlowchart_pyppl.png
[5]: ./drawFlowchart_pyppl_dark.png
[6]: http://www.graphviz.org/doc/info/shapes.html
[7]: https://github.com/xflr6/graphviz/