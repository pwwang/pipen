# Write and debug your script
<!-- toc -->

## Choose your language
You can either specify the path of interpreter to `pXXX.lang`. If the interpreter is in `$PATH`, you can directly give the basename of the interpreter.  
For example, if you have your own perl installed at `/home/user/bin/perl`, then you need to tell `PyPPL` where it is: `pXXX.lang = "/home/user/bin/perl"`. If `/home/user/bin` is in your `$PATH`, you can simply do: `p.lang = "perl"`  
You can also use [shebang][1] to specify the interperter:
```perl
#!/home/usr/bin/perl
# You perl code goes here
```

## Use script from a file
You can also put the script into a file, and use it with a `file:` prefix: `pXXX.script = "file:/a/b/c.pl"`  

> **Note**: You may also use a relative-path template, which is relative to where `pXXX.script` is defined. For example: `pXXX.script = "file:./scripts/script.py"` is defined in `/a/b/pipeline.py`, then the script file refers to `/a/b/scripts/script.py`

> **HINT**: Indents are important in python, when you write your scripts, you have to follow exactly the indents in the script string, for example:
```python
def test():
    p = Proc()
    p.lang = "python"
    p.script = """
import os
import re
def somefunc ():
    pass
"""
```
But with `'## indent remove ##'`, you can do it more elegantly:
```python
def test():
    p = proc()
    p.lang = "python"
    p.script = """
    # make sure it's not at the beginning of the file
    ## PYPPL INDENT REMOVE ## 
    import os
    import re
    def somefunc():
        pass
    """
```
The leading white spaces of line `## indent remove ##` will be removed for each line (including itself) below it. In this case, the extra `<tab>` of pass will be kept.  
You may use `## indent keep ##` to stop removing the white spaces for the following lines.
> **Caution** `## indent remove ##` Should not be at the beginning of the file, otherwise the leading spaces will be stripped so we can detect how many spaces should be removed for the following lines.

## Debug your script
If you need to debug your script, you just need to find the real running script, which is at: `<workdir>/<job.index>/job.script`. The template is rendered already in the file. You can debug it using the tool according to the language you used for the script.

You may also add logs to pyppl's main logs on the screen or in log files. To do that, you just need to print you message starting with `pyppl.log` to STDERR:
```python
# python
import sys
sys.stderr.write('pyppl.log: Something for debug.')
```

```bash
# bash
echo "pyppl.log: Something for debug." 1>&2
```

```R
# Rscript
cat("pyppl.log: Something for debug.", file = stderr())
```
Either one of the above will have a log message like:
```
[2017-01-01 01:01:01][    LOG] Something for debug.
```
You may also use a different log level (flag):
```python
# python
import sys
sys.stderr.write('pyppl.log.flag: Something for debug.')
```
Then the log message will be:
```
[2017-01-01 01:01:01][   FLAG] Something for debug.
```

>**NOTE** The level name you specified after `pyppl.log` does not apply to [normal log filters or themes][2], because the actual level is `_FLAG` in this case. So unless you set `loglevels` to `None`, it will be anyway printed out. For themes, the color at the empty string key will be used. 
> You can define filters or themes for this kind of logs, just remember the actual level name has an `_` prefix. See [here][2] to learn how to define filters and themes.


[1]: https://en.wikipedia.org/wiki/Shebang_(Unix)
[2]: https://pwwang.gitbooks.io/pyppl/configure-your-logs.html