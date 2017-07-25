# Write your script
<!-- toc -->

## Choose your language
You can either specify the path of interpreter to `p.lang`~~or p.defaultSh~~ (deprecated), if the interpreter is in `$PATH`, you can directly give the basename of the interpreter.  
For example, if you have your own perl installed at `/home/user/bin/perl`, then you need to tell `pyppl` where it is: `p.lang = "/home/user/bin/perl"`. If `/home/user/bin` is in your `$PATH`, you can simply do: `p.lang = "perl"`  
You can also use [shebang][1] to specify the interperter:
```perl
#!/home/usr/bin/perl
# You perl code goes here
```
Theoretically, `pyppl` supports any language.

## Use placeholders
You can use all available placeholders in the script. Each job will have its own script. See [here](https://pwwang.gitbooks.io/pyppl/content/placeholders.html) for details of placeholders.

## Use a template
You can also put the script into a file, and use it with a `template:` prefix: `p.script = "template:/a/b/c.pl"`  
You may also use the placeholders in the template, where everything should be the same when you put the script directly to `p.script`, the only difference is the control characters.
For example, in a template file, you use `"\t"` for a tab, but when directly specified to `p.script` property, you have to use `"\\t"`
> **Note**: You may also use a relative-path template, which is relative to `os.path.dirname (sys.argv[0])`
> Template extension is not supported yet.

> **HINT**: Indents are import in python, when you write your scripts, you have to follow exactly the indents in the script string, for example:
```python
def test():
    p = proc()
    p.lang = "python"
    p.script = """
import os
import re
def somefunc ():
    pass
"""
```
But with `'# Indent: remove'`, you can do it more elegantly:
```python
def test():
    p = proc()
    p.lang = "python"
    p.script = """
    # Indent: remove 
    import os
    import re
    def somefunc():
        pass
    """
```
The leading white spaces of line `# Indent: remove` will be removed for each line (including itself) below it. In this case, the extra `<tab>` of pass will be kept.  
You may use `# Indent: keep` to stop removing the white spaces for the following lines.

## Debug your script
If you need to debug your script, you just need to find the real running script, which is at: `<workdir>/<index>/job.script`. All the placeholders in the script have been replaced with actual values. You can debug it using the tool according to the language you used for the script.

[1]: https://en.wikipedia.org/wiki/Shebang_(Unix)
