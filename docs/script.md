
For templating in `script`, see [`templating`][2]

## Choosing your language

You can specify the path of interpreter to `lang`. If the interpreter is in `$PATH`, you can directly give the basename of the interpreter (i.e. `python` instead of `/path/to/python`).

For example, if you have your own perl installed at `/home/user/bin/perl`, then you need to tell `pipen` where it is: `lang = "/home/user/bin/perl"`. If `/home/user/bin` is in your `$PATH`, you can simply do: `lang = "perl"`

You can also use [shebang][1] to specify the interperter:
```perl
#!/home/usr/bin/perl
# You perl code goes here
```

If you have shebang in your script, the `lang` specified in the configuration files and `Pipen` constructor will be ignored (but the one specified in process definition is not).

## Use script from a file

You can also put the script into a file, and use it with a `file://` prefix: `script = "file:///a/b/c.pl"`

!!! note

    You may also use a script file with a relative path, which is relative to where process is defined. For example: a process with `script = "file://./scripts/script.py"` is defined in `/a/b/pipeline.py`, then the script file refers to `/a/b/scripts/script.py`

!!! hint

    Indents are important in python, when you write your scripts, you don't have to worry about the indents in your first empty lines. For example, you don't have to do this:

    ```python
    class P1(Proc):
        lang = "python"
        script = """
    import os
    import re
    def somefunc ():
        pass
    """
    ```

    You can do this:

    ```python
    class P1(Proc):
        lang = "python"
        script = """
        import os
        import re
        def somefunc ():
            pass
        """
    ```

    Only the first non-empty line is used to detect the indent for the whole script.

## Debugging your script

If you need to debug your script, you just need to find the real running script, which is at: `<pipeline-workdir>/<proc-name>/<job.index>/job.script`. The template is rendered already in the file. You can debug it using the tool according to the language you used for the script.

## Caching your results

Job results get automatically cached previous run is successful and input/output data are not changed, see [caching][3].

However, there are cases when you want to cache some results even when the job fails. For example, there is a very time-consuming chunk of code in your script that you don't want to run that part each time if it finishes once. In that case, you can save the intermediate results in a directory under `<job.outdir>`, where the directory is not specified in `output`. This keeps that directory untouched each time when the running data get purged if previous run fails.

[1]: https://en.wikipedia.org/wiki/Shebang_(Unix)
[2]: templating.md
[3]: caching.md
