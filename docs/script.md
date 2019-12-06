
<!-- toc -->

# Choose your language
You can either specify the path of interpreter to `pXXX.lang`. If the interpreter is in `$PATH`, you can directly give the basename of the interpreter.
For example, if you have your own perl installed at `/home/user/bin/perl`, then you need to tell `PyPPL` where it is: `pXXX.lang = "/home/user/bin/perl"`. If `/home/user/bin` is in your `$PATH`, you can simply do: `p.lang = "perl"`
You can also use [shebang][1] to specify the interperter:
```perl
#!/home/usr/bin/perl
# You perl code goes here
```

# Use script from a file
You can also put the script into a file, and use it with a `file:` prefix: `pXXX.script = "file:/a/b/c.pl"`

!!! note
    You may also use a relative-path template, which is relative to where `pXXX.script` is defined. For example: `pXXX.script = "file:./scripts/script.py"` is defined in `/a/b/pipeline.py`, then the script file refers to `/a/b/scripts/script.py`

!!! hint
    Indents are important in python, when you write your scripts, you have to follow exactly the indents in the script string, for example:

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
But with `'# PYPPL INDENT REMOVE'`, you can do it more elegantly:
```python
def test():
    p = proc()
    p.lang = "python"
    p.script = """
    # make sure it's not at the beginning of the file
    # PYPPL INDENT REMOVE
    import os
    import re
    def somefunc():
        pass
    """
```
The leading white spaces of line `# PYPPL INDENT REMOVE` will be removed for each line (including itself) below it. In this case, the extra `<tab>` of pass will be kept.
You may use `# PYPPL INDENT KEEP` to stop removing the white spaces for the following lines.

!!! caution
    `# PYPPL INDENT REMOVE` Should not be at the beginning of the file, otherwise the leading spaces will be stripped so we can detect how many spaces should be removed for the following lines.

# Debug your script
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

!!! note
    You have to tell `PyPPL` which jobs to output these logs.
    Just simply by:
    ```python
    # You have to specify an empty string to 'type' to disable other outputs, unless you want them.
    pXXX.echo = {'jobs': [0,1,2,3], 'type': ''}
    ```

!!! note
    The level name you specified after `pyppl.log` does not apply to [normal log filters or themes][2], because the actual level is `_FLAG` in this case. So unless you set `loglevels` to `None`, it will be anyway printed out. For themes, the color at the empty string key will be used.

    You can define filters or themes for this kind of logs, just remember the actual level name has an `_` prefix. See [here][2] to learn how to define filters and themes.

# Caching your results
Each time when we re-run the job, job status will get cleared, including the return code, stdout, stderr and the output results, as well. For complex jobs or jobs with multiple intermediate files, sometime, you may not want to re-generate those intermediate files. In this case, you can save those files in `{{job.cachedir}}`. For example, following job has two steps, append one line to the input file, and then append another.
```python
# pXXX.lang = 'python'
from pathlib import Path
infile = Path({{i.infile | quote}})
outfile = Path({{o.outfile | quote}})
cachedir = Path({{job.cachedir | quote}})
cachefile = cachedir / (infile.name + 'intermediate')
imfile = Path({{job.outdir}}) / (infile.name + 'intermediate')
# let's check if cached intermediate file exists
if not cachefile.exists():
    # do step 1
    cachefile.write_text(infile.read_text() + '\nLine 1')
# create a link to the cache file
# next time when we run this job, cache file still exists,
# we just need to create a link for the intermediate file.
imfile.symlink_to(cachefile)

# do step 2
outfile.write_text(imfile.read_text() + '\nLine 2')
```

# Output stdout/stderr to PyPPL logs
Instead of log some information, you may also choose to output the stdout/stderr from the jobs to the main `PyPPL` log.

This is controlled by setting `p.echo`, which is set to `False` by default. The full configuration of the value could be:
```python
{
    'jobs': [0, 1], # the jobs that are allowed to output
    # the regular expression for each type of output
    'type': {'stdout': r'^STDOUT:', 'stderr': r'^STDERR'}
}
```
But there are also some abbrevations for the setting:

|Abbrevation (`p.echo = ?`)|Full setting|Memo|
|-|-|-|
|`False`|`False`|Disable output|
|`True`|`{'jobs':[0], 'type': {'stderr':None, 'stdout':None}}`|Output all stdout/stderr of job #0|
|`'stderr'`|`{'jobs':[0], 'type': {'stderr':None}}`|Output all stderr of job #0|
|`{'jobs':0, 'type': 'stdout'}`|`{'jobs':[0], 'type': {'stdout':None}}`|Output all stdout of job #0|
|`{'type': {'all': r'^output'}}`|`{ 'jobs': [0], 'type': {'stdout': r'^output', 'stderr': r'^output'} }`|Output all lines starting with `"output"` from stdout/stderr of job #0|

For job indexes, you can also use abbreviations, for example,
`0-5` for `[0,1,2,3,4,5]` and `1, 4-6` for `[1,4,5,6]`

[1]: https://en.wikipedia.org/wiki/Shebang_(Unix)
[2]: ../logs/
