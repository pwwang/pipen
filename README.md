# pyppl - A python lightweight pipeline framework

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [Get started](#get-started)
  - [Requirements](#requirements)
  - [Installation](#installation)
  - [First script](#first-script)
  - [Using arguments](#using-arguments)
  - [Using a different interpreter:](#using-a-different-interpreter)
  - [See documentations.](#see-documentations)

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
import sys
from pyppl.pyppl import pyppl
from pyppl.helpers.proc import proc
from pyppl.helpers.channel import channel

inchan = channel.create (list("Hello"))

p_upper           = proc('upper')
p_upper.input     = {"in": inchan}
p_upper.output    = "outfile:file:{{in}}.txt"
p_upper.exportdir = "./"
p_upper.script    = """
  echo {{in}} | tr '[:lower:]' '[:upper:]' > {{outfile}}
""" 

pyppl().starts(p_upper).run()
```

It will output:
```
[2017-02-02 16:23:32,515] [  PyPPL] Version: 0.1.0
[2017-02-02 16:23:32,515] [   TIPS] You can find the stderr in <workdir>/.scripts/script.<index>.stderr
[2017-02-02 16:23:32,517] [RUNNING] p_upper.upper: /tmp/PyPPL_p_upper_upper.6bf016ac
[2017-02-02 16:23:33,056] [ EXPORT] p_upper.upper: ./H.txt (copy)
[2017-02-02 16:23:33,058] [ EXPORT] p_upper.upper: ./e.txt (copy)
[2017-02-02 16:23:33,058] [ EXPORT] p_upper.upper: ./l.txt (copy)
[2017-02-02 16:23:33,059] [ EXPORT] p_upper.upper: ./l.txt (copy)
[2017-02-02 16:23:33,060] [ EXPORT] p_upper.upper: ./o.txt (copy)
[2017-02-02 16:23:33,061] [   DONE]
```

The first process tries to uppercase all letters, the second then write them to files and export them.

### Using arguments
Say we save the script as first.py:

```python
p_upper           = proc('upper')
p_upper.input     = "in" # no channels assigned
p_upper.output    = "outfile:file:{{in}}.txt"
p_upper.exportdir = "./"
p_upper.script    = """
  echo {{in}} | tr '[:lower:]' '[:upper:]' > {{outfile}}
""" 

pyppl().starts(p_upper).run()
```
then run the script:
```shell
python first.py w
```
will only have `w` capitalized and saved.

To have more letters involved, you have to specify the `input` as:
```python
p_upper.input  = {"in": channel.fromArgv(1)}
```
Then run:
```bash
python first.py H e l l o
```
will have the same output as the first script.

### Using a different interpreter:
```python
p_python = proc()
p_python.input = "in"
p_python.output = "out:{{in}}"
p_python.defaultSh = "python"
p_python.script = "print {{in}}"
""" or you can also specify a shebang in script:
p_python.script = "
#!/usr/bin/env python
print "{{in}}"
"
"""
pyppl().starts(p_python).run()
```

### See [documentations](DOC.md).

