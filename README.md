# pyppl - A python lightweight pipeline framework
![Pypi][22] ![Github][23] ![Gitbook][21]   

[Documentation][1] | [API][2] | [Change log][19] | [Fork me][3]

<!-- toc -->
## Features
- Supports of any language to run you processes.
- Automatic deduction of input based on the process dependencies. [Details][4]
- Different ways of exporting output files (including `gzip`). [Details][5]
- Process caching (including caching using exported files). [Details][6]
- Expectations of processes. [Details][25]
- Flexible placeholder handling in output and script settings. [Details][7]
- APIs to modify channels. [Details][8]
- Different runners to run you processes on different platforms. [Details][9]
- Runner customization (you can define your own runner). [Details][10]
- Callbacks of processes. [Details][11]
- Error handling for processes. [Details][12]
- Configuration file support for pipelines. [Details][13]
- Flowchat in [DOT][14] for your pipelines. [Details][15]
- Highly reusable processes. [A set of highly reusable bioinformatics processes][24]
- Aggregations (a set of processes predefined). [Details][16]
- Detailed [documentation][1] and [API documentation][2].

## Requirements
- Linux, OSX or WSL (Windows Subsystem for Linux)
- Python 2.7+ (python3 supported)

## Installation
```bash
# install latest version
git clone https://github.com/pwwang/pyppl.git
cd pyppl
python setup.py install
# or simly:
pip install git+git://github.com/pwwang/pyppl.git

# install released version
pip install pyppl
```

## First script
To sort 5 files: 
```python
from pyppl import pyppl, proc

pSort         = proc()
# Use sys.argv as input channel,
# because this proc does not have any dependents
# infile will be the placeholder to access it in your output assignment
# and script.
# The ":file" denotes the type of input, a symbol link will be created in 
# the input directory
pSort.input   = "infile:file"
# Output file (the ":file" sign) will be generated in job output directory
# "infile" is the full path of the input file, "fn" takes its filename (without extension)
pSort.output  = "outfile:file:{{infile | fn}}.sorted"
# You can use placeholders to access input and output
pSort.script  = """
  sort -k1r {{infile}} > {{outfile}}
""" 

# Assign the entrance process
pyppl().starts(pSort).run()
```

Run `python test.py test?.txt` will output:
![First-script-output][20]

## A toy example
Sort each 5 file and then combine them into one file
```python
from pyppl import pyppl, proc

pSort         = proc()
pSort.input   = "infile:file"
pSort.output  = "outfile:file:{{infile | fn}}.sorted"
pSort.script  = """
  sort -k1r {{infile}} > {{outfile}}
""" 

pCombine      = proc()
# Will use pSort's output channel as input
pCombine.depends  = pSort
pCombine.input    = {"infiles:files": lambda ch: [ch.toList()]}
pCombine.output   = "outfile:file:{{infiles | [0] | fn}}_etc.sorted"
# Export the final result file
pCombine.exdir    = "./export" 
pCombine.script   = """
> {{outfile}}
for infile in {{infiles | asquote}}; do
	cat $infile >> {{outfile}}
done
"""

pyppl().starts(pSort).run()
```
Run `python test.py test?.txt`, then you will find the combined file named `output.sorted` in `./export`.

## Using a different interpreter:
```python
pPlot = proc()
# Specify input explicitly
pPlot.input   = {"infile:file": ["./data.txt"]}
# data.png
pPlot.output  = "outfile:file:{{infile | fn}}.png"
pPlot.lang    = "Rscript"
pPlot.script  = """
data <- read.table ("{{infile}}")
H    <- hclust(dist(data))
png (figure = “{{outfile}}”)
plot(H)
dev.off()
"""
```

## Using a different runner:
```python
pPlot = proc()
pPlot.input   = {"infile:file": ["./data1.txt", "./data2.txt", "./data3.txt", "./data4.txt", "./data5.txt"]}
pPlot.output  = "outfile:file:{{infile.fn}}.png"
pPlot.lang    = "Rscript"
pPlot.runner  = "sge"
# run all 5 jobs at the same time
pPlot.forks   = 5
pPlot.script  = """
data <- read.table ("{{infile}}")
H    <- hclust(dist(data))
png (figure = “{{outfile}}”)
plot(H)
dev.off()
"""
pyppl({
  "proc": {
    "sgeRunner": {
      "sge.q" : "1-day"
    }
  }
}).starts(pPlot).run()
```

## Draw the pipeline chart
`pyppl` can generate the graph in [DOT language][14]. 
```python
# "A" is the tag of p1
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
# saved to dot file: test.pyppl.dot
# saved to svg file: test.pyppl.svg
# run it after the chart generated:
# pyppl().starts(p1, p8, p9).flowchart().run()
```
`test.pyppl.dot`:
```dot
digraph PyPPL {
	"p1.A" -> "p2.B"
	"p1.A" -> "p3.C"
	"p8.H" -> "p3.C"
	"p2.B" -> "p4.D"
	"p3.C" -> "p4.D"
	"p4.D" -> "p5.E"
	"p4.D" -> "p6.F"
	"p9.I" -> "p6.F"
	"p5.E" -> "p7.G"
	"p6.F" -> "p7.G"
	"p6.F" [shape=box, style=filled, color="#f0f998", fontcolor=red]
	"p1.A" [shape=box, style=filled, color="#c9fcb3"]
	"p8.H" [shape=box, style=filled, color="#c9fcb3"]
	"p9.I" [shape=box, style=filled, color="#c9fcb3"]
	"p7.G" [shape=box, style=filled, color="#fcc9b3" fontcolor=red]
	"p4.D" [shape=box, style=filled, color="#f0f998", fontcolor=red]
}
```
You can use different [dot renderers][17] to render and visualize it.

`test.pyppl.svg`:  
![PyPPL chart][18]

[1]: https://pwwang.gitbooks.io/pyppl/
[2]: https://pwwang.gitbooks.io/pyppl/api.html
[3]: https://github.com/pwwang/pyppl/
[4]: https://pwwang.gitbooks.io/pyppl/specify-input-and-output-of-a-process.html#specify-input-of-a-process
[5]: https://pwwang.gitbooks.io/pyppl/export-output-files.html
[6]: https://pwwang.gitbooks.io/pyppl/caching.html
[7]: https://pwwang.gitbooks.io/pyppl/placeholders.html
[8]: https://pwwang.gitbooks.io/pyppl/channels.html
[9]: https://pwwang.gitbooks.io/pyppl/runners.html
[10]: https://pwwang.gitbooks.io/pyppl/runners.html#define-your-own-runner
[11]: https://pwwang.gitbooks.io/pyppl/set-other-properties-of-a-process.html#use-callback-to-modify-the-process-pcallback
[12]: https://pwwang.gitbooks.io/pyppl/set-other-properties-of-a-process.html#error-handling-perrhowperrntry
[13]: https://pwwang.gitbooks.io/pyppl/configure-a-pipeline.html#use-a-configuration-file
[14]: https://en.wikipedia.org/wiki/DOT_(graph_description_language)
[15]: https://pwwang.gitbooks.io/pyppl/draw-flowchart-of-a-pipeline.html
[16]: https://pwwang.gitbooks.io/pyppl/aggregations.html
[17]: https://en.wikipedia.org/wiki/DOT_(graph_description_language)#Layout_programs
[18]: https://github.com/pwwang/pyppl/raw/master/docs/pyppl.png
[19]: https://pwwang.gitbooks.io/pyppl/change-log.html
[20]: https://github.com/pwwang/pyppl/raw/master/docs/firstScript.png
[21]: https://www.gitbook.com/button/status/book/pwwang/pyppl
[22]: https://badge.fury.io/py/pyppl.svg
[23]: https://badge.fury.io/gh/pwwang%2Fpyppl.svg
[24]: https://github.com/pwwang/bioprocs
[25]: https://pwwang.gitbooks.io/pyppl/content/set-other-properties-of-a-process.html#set-expectations-of-a-process
[26]: https://pwwang.gitbooks.io/pyppl/content/faq.html
