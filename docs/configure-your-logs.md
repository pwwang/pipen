# Configure your logs

{% raw %}
`pyppl` has fancy logs. You can define how they look like (theme) and what messages to show (levels).

## Built-in log themes
We have some built-in themes:

greenOnBlack (default):
![greenOnBlack][3]

greenOnWhite:
![greenOnWhite][4]
blueOnBlack:
![blueOnBlack][1]

blueOnWhite:
![blueOnWhite][2]

magentaOnBlack:
![magentaOnBlack][5]

magentaOnWhite:
![magentaOnWhite][6]

If you don't like them, you can also disable them:
![noThemeOnBlack][7]
![noThemeOnWhite][8]

To use them, just specify the name in your pipeline configuration file:
```json
{
    "logtheme": "magentaOnWhite"
}
```
Or when you initialize a pipeline:
```python
pyppl({"logtheme": "magentaOnWhite"}).starts(...).run()
```
If you want to disable the theme, just set `"logtheme"` to `False` (`false` for `json`)
If you set `logtheme` to `True`, then default theme `greenOnBlack` is used.

## Levels of pyppl logs
Please note that the levels are different from those of python's `logging` module. For `logging` module has [6 levels][9], with different int values. However, pyppl's log has many levels, or more suitable, flags, which don't have corresponding values. They are somehow equal, but some of them always print out unless you ask them not to.

|Log level|Belongs to groups|Meaning
|-|-|-|
|`>>>>>>>`|`all, basic, normal, nodebug`|Mark when a process initiates|
|`DEPENDS`|`all, basic, normal, nodebug`|Show dependencies of a process|
|`STDOUT`|`all, basic, normal, nodebug`|Show the STDOUT from a process|
|`STDERR`|`all, basic, normal, nodebug`|Show the STDERR from a process|
|`ERROR`|`all, basic, normal, nodebug`|Show errors|
|`INFO`|`all, basic, normal, nodebug`|Some information|
|`DONE`|`all, basic, normal, nodebug`|Mark when a process is done|
|`RUNNING`|`all, basic, normal, nodebug`|Mark when a process starts to run|
|`CACHED`|`all, basic, normal, nodebug`|Mark when a process is cached|
|`EXPORT`|`all, basic, normal, nodebug`|Mark when a job is exporting output files|
|`PYPPL`|`all, basic, normal, nodebug`|When pipeline starts|
|`TIPS`|`all, basic, normal, nodebug`|Show tips|
|`CONFIG`|`all, basic, normal, nodebug`|Show configuration is read from file|
|`CMDOUT`|`all, basic, normal, nodebug`|Show the STDOUT for `beforeCmd`/`afterCmd`|
|`CMDERR`|`all, basic, normal, nodebug`|Show the STDERR for `beforeCmd`/`afterCmd`|
|`RETRY`|`all, basic, normal, nodebug`|Mark when a job retries|
|`INPUT`|`all, normal, nodebug`|Show the input for a job|
|`OUTPUT`|`all, normal, nodebug`|Show the output for a job|
|`BRINGS`|`all, normal, nodebug`|Show the bring-in files|
|`SUBMIT`|`all, basic, normal, nodebug`|Mark when a job is being submitting|
|`P.PROPS`|`all, normal, nodebug`|Show some properties of a process|
|`P.ARGS`|`all, nodebug`|Show the args of a process|
|`JOBDONE`|`all, nodebug`|Mark when a job is done|

You may also specify the group name in your pipeline configuration file:
```json
{
    "loglevels": "nodebug"
}
```
Or when you initialize a pipeline:
```python
pyppl({"loglevels": "nodebug"}).starts(...).run()
```

You can also explicitly define a set of messages with different levels to show in the logs:
```json
{
    "loglevels": [">>>>>>>", "RUNNING", "CACHED"]
}
```

Even you can modify the base groups:
```json
{
    "loglevels": "normal",
    "loglvldiff": ["+DEBUG", "P.ARGS", "-SUBMIT"]
}
```
Then the `DEBUG`, `P.ARGS` messages will show, and `SUBMIT` will hide.

## Define your theme

Let's see how the built-in theme looks like first:
in `pyppl/helpers/logger.py`:
```python
themes = {
  'greenOnBlack': {
    'DONE'    : colors.bold + colors.green,
    'DEBUG'   : colors.bold + colors.black,
    '>>>>>>>' : [colors.bold + colors.cyan, colors.bold + colors.underline + colors.cyan],
    'in:SUBMIT,JOBDONE,INFO,P.PROPS,DEPENDS,OUTPUT,EXPORT,INPUT,P.ARGS,BRINGS': colors.green,
    'has:ERR' : colors.red,
    'in:WARNING,RETRY' : colors.bold + colors.yellow,
    'in:CACHED,RUNNING': colors.yellow,
    ''        : colors.white
  },
  # other themes
}
```

You can modify the theme before you specify it to the pyppl constructor:
```python
from pyppl import logger
logger.themes['greenOnBlack']['DONE'] = logger.colors.cyan
```
































{% endraw %}


[1]: https://raw.githubusercontent.com/pwwang/pyppl/master/docs/blueOnBlack.png
[2]: https://raw.githubusercontent.com/pwwang/pyppl/master/docs/blueOnWhite.png
[3]: https://raw.githubusercontent.com/pwwang/pyppl/master/docs/greenOnBlack.png
[4]: https://raw.githubusercontent.com/pwwang/pyppl/master/docs/greenOnWhite.png
[5]: https://raw.githubusercontent.com/pwwang/pyppl/master/docs/magentaOnBlack.png
[6]: https://raw.githubusercontent.com/pwwang/pyppl/master/docs/magentaOnWhite.png
[7]: https://raw.githubusercontent.com/pwwang/pyppl/master/docs/noThemeOnBlack.png
[8]: https://raw.githubusercontent.com/pwwang/pyppl/master/docs/noThemeOnWhite.png
[9]: https://docs.python.org/2/library/logging.html#logging-levels







