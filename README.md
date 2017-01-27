# pyppl - A python lightweight pipeline framework

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [Get started](#get-started)
  - [Requirements](#requirements)
  - [Installation](#installation)
  - [First script](#first-script)
  - [Using parameters](#using-parameters)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## Get started

### Requirements
- Python 2.7

### Installation
```python
python setup.py install
```

### First script
```python
import pyppl, sys

insrc = list('Hello world!')

p_upper        = pyppl.Process('upper')
p_upper.insrc  = insrc
p_upper.input  = "in"
p_upper.output = "{stdout}"
p_upper.script = """
  echo {in} | tr '[:lower:]' '[:upper:]' 
""" 

p_save         = pyppl.Process('save')
p_save.depends = p_upper
p_save.input   = "in"
p_save.export  = "./save/"
p_save.output  = "file:{in}.txt"
p_save.script  = """
  echo {in} > {in}.txt 
""" 

pipeline = pyppl.Pipeline()
pipeline.add (p_upper)
pipeline.run()

```

It will output:
```
[2016-11-14 12:00:52,288] [RUNNING] p_upper.upper: /tmp/pyppl-78de1c05-4d91-44cf-8775-dcd198a33c29
[2016-11-14 12:00:52,405] [RUNNING] p_save.save: /tmp/pyppl-b1b76a19-9dc9-462f-90ea-87a4f3eacf77
[2016-11-14 12:00:52,511] [ EXPORT] p_save.save: ./save/H.txt
[2016-11-14 12:00:52,513] [ EXPORT] p_save.save: ./save/E.txt
[2016-11-14 12:00:52,513] [ EXPORT] p_save.save: ./save/L.txt
[2016-11-14 12:00:52,514] [ EXPORT] p_save.save: ./save/L.txt
[2016-11-14 12:00:52,515] [ EXPORT] p_save.save: ./save/O.txt
[2016-11-14 12:00:52,516] [ EXPORT] p_save.save: ./save/.txt
[2016-11-14 12:00:52,517] [ EXPORT] p_save.save: ./save/W.txt
[2016-11-14 12:00:52,518] [ EXPORT] p_save.save: ./save/O.txt
[2016-11-14 12:00:52,519] [ EXPORT] p_save.save: ./save/R.txt
[2016-11-14 12:00:52,520] [ EXPORT] p_save.save: ./save/L.txt
[2016-11-14 12:00:52,521] [ EXPORT] p_save.save: ./save/D.txt
[2016-11-14 12:00:52,522] [ EXPORT] p_save.save: ./save/!.txt
```

The first process tries to uppercase all letters, the second then write them to files and export them.

### Using parameters
Say we save the script as first.py:

```python
import pyppl, sys

p_upper        = pyppl.Process('upper')
p_upper.input  = "in"
p_upper.output = "{stdout}"
p_upper.script = """
  echo {in} | tr '[:lower:]' '[:upper:]' 
""" 

p_save         = pyppl.Process('save')
p_save.depends = p_upper
p_save.input   = "in"
p_save.export  = "./save/"
p_save.output  = "file:{in}.txt"
p_save.script  = """
  echo {in} > {in}.txt 
""" 

pipeline = pyppl.Pipeline()
pipeline.add (p_upper)
pipeline.run()

```
then run the script:
```shell
python first.py "Hello, world!"
```
will have the same output.