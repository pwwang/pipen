# Configure your logs
<!-- toc -->

{% raw %}
`PyPPL` has fancy logs. You can define how they look like (theme) and what messages to show (levels).

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
    "log": {
        "theme": "magentaOnWhite"
    }
}
```
Or when you initialize a pipeline:
```python
PyPPL({"log": {"theme": "magentaOnWhite"}}).start(...).run()
```
If you want to disable the theme, just set `"theme"` to `False` (`false` for `json`)
If you set `theme` to `True`, then default theme `greenOnBlack` is used.

## Levels of pyppl logs
Please note that the levels are different from those of python's `logging` module. For `logging` module has [6 levels][9], with different int values. However, pyppl's log has many levels, or more suitable, flags, which don't have corresponding values. They are somehow equal, but some of them always print out unless you ask them not to.

|Log level|Belongs to groups|Meaning
|-|-|-|
|`PROCESS`|`all, basic, normal, nodebug`|Mark when a process initiates|
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
>**NOTE** The log levels are a little bit different from here, please see [debug your script][27].

You may also specify the group name in your pipeline configuration file:
```json
{
    "log": {
        "levels": "nodebug"
    }
}
```
Or when you initialize a pipeline:
```python
PyPPL({"log": {"levels": "nodebug"}}).start(...).run()
```

You can also explicitly define a set of messages with different levels to show in the logs:
```json
{
    "log": {"levels": [">>>>>>>", "RUNNING", "CACHED"]}
}
```

Even you can modify the base groups:
```json
{
    "log": {
        "levels": "normal",
        "lvldiff": ["+DEBUG", "P.ARGS", "-SUBMIT"]
    }
}
```
Then the `DEBUG`, `P.ARGS` messages will show, and `SUBMIT` will hide.

## Define your theme

Let's see how the built-in theme looks like first:
in `pyppl/logger.py`:
```python
themes = {
  'greenOnBlack': {
    'PROCESS' : [colors.bold + colors.cyan, colors.bold + colors.underline + colors.cyan],
    'DONE'    : colors.bold + colors.green,
    'DEBUG'   : colors.bold + colors.black,
    'DEPENDS' : colors.magenta,
    'PROCESS' : [colors.bold + colors.cyan, colors.bold + colors.underline + colors.cyan],
    'in:SUBMIT,JOBDONE,INFO,P.PROPS,OUTPUT,EXPORT,INPUT,P.ARGS,BRINGS': colors.green,
    'has:ERR' : colors.red,
    'in:WARNING,RETRY' : colors.bold + colors.yellow,
    'in:CACHED,RUNNING': colors.yellow,
    ''        : colors.white
  },
  # other themes
}
```
For the keys, you may either directly use the level name or have some prefix to define how to match the level names:
- `in:` matches the messages with level name in the following list, which is separated by comma (`,`).
- `has:` matches the messages with level name containing the following string.
- `starts:` matches the messages with level name starting with the following string.
- `re`: uses the following string as regular expression to match  
Then empty string key (`''`) defines the colors to use for the messages that can not match any of the above rules.

For the values, basically it's a 2-element list, where the first one defines the color to show the level name; and the second is the color to render the message. If only one color offered, it will be used for both level name and message.

If you just want to modify the built-in themes, you can do it before you specify it to the pyppl constructor:
```python
from PyPPL import logger, PyPPL
logger.themes['greenOnBlack']['DONE'] = logger.colors.cyan
# ... define some procs
PyPPL({'log':{'theme': 'greenOnBlack'}}).start(...).run()
```

Yes, of course, you can also define a completely new theme:
```python
from pyppl import logger, PyPPL
# ... define procs
PyPPL({'log': 
    {'theme': {
        'DONE': logger.colors.green,
        'DEBUG': logger.colors.black,
        'starts:LOG': logger.colors.bgwhite + logger.colors.black,
        # ...
    }}
}).start(...).run()
```

Available colors in `logger.colors`:

|Key|Color|Key|Color|Key|Color|Key|Color|Key|Color|
|---|-----|---|-----|---|-----|---|-----|---|-----|
|`none`|`''`<sup>1</sup>|`black`|![A][10]|`red`|![A][11]|`green`|![A][12]|`yellow`|![A][13]|
|`end`|<sup>2</sup>|`blue`|![A][14]|`magenta`|![A][15]|`cyan`|![A][16]|`white`|![A][17]|
|`bold`|**A**<sup>3</sup>|`bgblack`|![A][18]|`bgred`|![A][19]|`bggreen`|![A][20]|`bgyellow`|![A][21]|
|`underline`|_<sup>4</sup>|`bgblue`|![A][22]|`bgmagenta`|![A][23]|`bgcyan`|![A][24]|`bgwhite`|![A][25]|

1. An empty string; 2. End of coloring; 3. Show bold characters; 4. Show underline characters.

You can also use the directly terminal escape sequences, like `\033[30m` for black (check [here][26]).

If you define a theme in a configuration file, you may use the escape sequences or also use the color names:
```json
{
    "log": {"theme": {
        "DONE": "{{colors.green}}",
        "DEBUG": "{{colors.black}}",
        "starts:LOG": "{{colors.bgwhite}}{{colors.black}}",
        # ...
    }}
}
```

## Log to file
By default, pyppl will not log to a file until you set a file path to `{"log": {"file": "/path/to/logfile"}}` in the configuration. Or you can specfiy `False` to it to disable logging to file. If you set it to `True`, a default log file will be used, which is: `"./pipeline.pyppl.log"` if your pipeline is from file: `./pipeline.py`
>**NOTE** Filters and themes are not applied to handler to log to file. So you can always find all logs in the log file if your have it enabled.

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
[10]: https://placehold.it/32/eeeeee/000000?text=A
[11]: https://placehold.it/32/eeeeee/ff0000?text=A
[12]: https://placehold.it/32/eeeeee/00ff00?text=A
[13]: https://placehold.it/32/eeeeee/ffff00?text=A
[14]: https://placehold.it/32/eeeeee/0000ff?text=A
[15]: https://placehold.it/32/eeeeee/ff00ff?text=A
[16]: https://placehold.it/32/eeeeee/00ffff?text=A
[17]: https://placehold.it/32/eeeeee/ffffff?text=A
[18]: https://placehold.it/32/000000/eeeeee?text=A
[19]: https://placehold.it/32/ff0000/eeeeee?text=A
[20]: https://placehold.it/32/00ff00/eeeeee?text=A
[21]: https://placehold.it/32/ffff00/eeeeee?text=A
[22]: https://placehold.it/32/0000ff/eeeeee?text=A
[23]: https://placehold.it/32/ff00ff/eeeeee?text=A
[24]: https://placehold.it/32/00ffff/eeeeee?text=A
[25]: https://placehold.it/32/ffffff/eeeeee?text=A
[26]: https://en.wikipedia.org/wiki/ANSI_escape_code
[27]: https://pwwang.gitbooks.io/pyppl/write-your-script.html#debug-your-script