# Draw flowchart of a pipeline
<!-- toc -->

`pyppl` will generate a graph in [DOT language][1], according to the process dependencies. 
You can have multiple [renderers][2] to visualize to graph. A typical one is [Graphviz][3]. Once you have Graphviz installed, you will have a command line tool `dot` available, which takes the dot file as input and can output to a bunch of figure format. For example, if we have a pipeline written in `pipeline.py`:
```python
p1 = proc("A")
p2 = proc("B")
p3 = proc("C")
p4 = proc("D")
p5 = proc("E")
p6 = proc("F")
p7 = proc("G")
p8 = proc("H")
p9 = proc("I")
p1.script = "echo 1"
p1.input  = {"input": ['a']}
p8.input  = {"input": ['a']}
p9.input  = {"input": ['a']}
p2.input  = "input"
p3.input  = "input"
p4.input  = "input"
p5.input  = "input"
p6.input  = "input"
p7.input  = "input"
p1.output = "{{input}}" 
p2.script = "echo 1"
p2.output = "{{input}}" 
p3.script = "echo 1"
p3.output = "{{input}}" 
p4.script = "echo 1"
p4.output = "{{input}}" 
p5.script = "echo 1"
p5.output = "{{input}}" 
p6.script = "echo 1"
p6.output = "{{input}}" 
p7.script = "echo 1"
p7.output = "{{input}}" 
p8.script = "echo 1"
p8.output = "{{input}}" 
p9.script = "echo 1"
p9.output = "{{input}}" 
"""
			   1A         8H
			/      \      /
		 2B           3C
			\      /
			  4D(e)       9I
			/      \      /
		 5E          6F(e)
			\      /
			  7G(e)
"""
p2.depends = p1
p3.depends = [p1, p8]
p4.depends = [p2, p3]
p4.exdir   = "./"
p5.depends = p4
p6.depends = [p4, p9]
p6.exdir   = "./"
p7.depends = [p5, p6]
p7.exdir   = "./"
pyppl().starts(p1, p8, p9).flowchart()
# ppl = pyppl().starts(p1, p8, p9).flowchart()
# run it: ppl.run()
# or:
# pyppl().starts(p1, p8, p9).flowchart().run()
```

You can specify different files to store the dot and svg file:
```python
pyppl().starts(p1, p8, p9).flowchart("/another/dot/file", "/another/svg/file")
```
> **Note** The svg file will be only generated if you specify the right command to do it.

For example, if you have [Graphviz](http://www.graphviz.org/) installed, you will have `dot` available to convert the dot file to svg file:
```python
pyppl().starts(p1, p8, p9).flowchart(
	"/another/dot/file", 
	"/another/svg/file", 
	"dot -Tsvg {{dotfile}} > {{svgfile}}"
)
```

The graph (`fcfile`) will be like:  
![Pipeline][4]

The green processes are the starting processes; ones with red text are processes that will export the output files; and nodes in red are the end processes of the pipeline.

[1]: https://en.wikipedia.org/wiki/DOT_(graph_description_language)
[2]: https://en.wikipedia.org/wiki/DOT_(graph_description_language)#Layout_programs
[3]: https://en.wikipedia.org/wiki/Graphviz
[4]: https://github.com/pwwang/pyppl/raw/master/docs/pyppl.png