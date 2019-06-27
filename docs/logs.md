
`PyPPL` has fancy logs. You can define how they look like (theme) and what messages to show (levels).

# Built-in log themes
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
    "_log": {
        "theme": "magentaOnWhite"
    }
}
```
Or when you initialize a pipeline:
```python
PyPPL({"default": {"_log": {"theme": "magentaOnWhite"}}}).start(...).run()
```
If you want to disable the theme, just set `"theme"` to `False` (`false` for `json`)
If you set `theme` to `True`, then default theme `greenOnBlack` is used.

# Levels of PyPPL logs
Please note that the levels are different from those of python's `logging` module. For `logging` module has [6 levels][9], with different int values. However, pyppl's log has many levels, or more suitable, flags, which don't have corresponding values. They are somehow equal, but some of them always print out unless you ask them not to.

|Log level|Belongs to groups|Meaning
|-|-|-|
|`PROCESS`|`all, basic, normal`|Mark when a process initiates|
|`DEPENDS`|`all, basic, normal`|Show dependencies of a process|
|`STDOUT`|`all, basic, normal`|Show the STDOUT from a process|
|`STDERR`|`all, basic, normal`|Show the STDERR from a process|
|`ERROR`|`all, basic, normal`|Show errors|
|`INFO`|`all, basic, normal`|Some information|
|`DONE`|`all, basic, normal`|Mark when a process is done|
|`BLDING`|`all, basic, normal`|Mark when a job starts to build|
|`SBMTING`|`all, basic, normal`|Mark when a job starts to submit|
|`RUNNING`|`all, basic, normal`|Mark when a job starts to run|
|`RTRYING`|`all, basic, normal`|Mark when a job starts to retry|
|`CACHED`|`all, basic, normal`|Mark when a job is cached|
|`EXPORT`|`all, basic, normal`|Mark when a job is exporting output files|
|`PYPPL`|`all, basic, normal`|When pipeline starts|
|`TIPS`|`all, basic, normal`|Show tips|
|`CONFIG`|`all, basic, normal`|Show configuration is read from file|
|`CMDOUT`|`all, basic, normal`|Show the STDOUT for `preCmd`/`postCmd`|
|`CMDERR`|`all, basic, normal`|Show the STDERR for `preCmd`/`postCmd`|
|`RETRY`|`all, basic, normal`|Mark when a job retries|
|`WORKDIR`|`all, basic, normal`|Show the workdir for a process|
|`INPUT`|`all, normal`|Show the input for a job|
|`OUTPUT`|`all, normal`|Show the output for a job|
|`SUBMIT`|`all, basic, normal`|Mark when a job is being submitting|
|`P_PROPS`|`all, normal`|Show some properties of a process|
|`P_ARGS`|`all`|Show the args of a process|
|`JOBDONE`|`all`|Mark when a job is done|

!!! note
    The log levels are a little bit different from here, please see [debug your script][27].

You may also specify the group name in your pipeline configuration file:
```json
{
    "_log": {
        "levels":"all"
    },
    // running profiles ...
}
```
Or when you initialize a pipeline:
```python
PyPPL({"default": {"_log": {"levels":"all"}}}).start(...).run()
```

You can also explicitly define a set of messages with different levels to show in the logs:
```json
{
    "_log": {"levels": ["PROCESS", "RUNNING", "CACHED"]}
}
```

Even you can modify the base groups:
```json
{
    "_log": {
        "levels": "normal",
        "leveldiffs": ["+DEBUG", "P_ARGS", "-SUBMIT"]
    }
}
```
Then the `DEBUG`, `P_ARGS` messages will show, and `SUBMIT` will hide.

# Define your own theme

Let's see how the built-in theme looks like first:
in `pyppl/logger.py`:
```python
from colorama import Fore, Style
themes = {
  'greenOnBlack': {
    'PROCESS' : Style.BRIGHT + Fore.CYAN,
    'DONE'    : Style.BRIGHT + Fore.GREEN,
    'DEBUG'   : Style.BRIGHT + Fore.BLACK,
    'DEPENDS' : Fore.MAGENTA,
    'PROCESS' : Style.BRIGHT + Fore.CYAN,
    'in:SUBMIT,JOBDONE,INFO,P_PROPS,OUTPUT,EXPORT,INPUT,P_ARGS,BRINGS': Fore.GREEN,
    'has:ERR' : Fore.RED,
    'in:WARNING,RETRY' : Style.BRIGHT + Fore.YELLOW,
    'in:CACHED,RUNNING': Fore.YELLOW,
    ''        : Fore.WHITE
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

For the values, you can also use the placeholders if the theme is defined in a configuration file (`yaml` for example):
```yaml
default:
    _log:
        theme:
            DONE: {Style.BRIGHT}{Fore.GREEN}
            # or s for Style, f For Fore
            # DONE: {s.BRIGHT}{f.GREEN}
```

See available colors and styles [here][28]
You can also use the directly terminal escape sequences, like `\033[30m` for black (check [here][26]).

# Log to file
By default, pyppl will not log to a file until you set a file path to `{"_log": {"file": "/path/to/logfile"}}` in the configuration. Or you can specfiy `False` to it to disable logging to file. If you set it to `True`, a default log file will be used, which is: `"./pipeline.pyppl.log"` if your pipeline is from file: `./pipeline.py`

!!! note
    Themes are not applied to handler to log to file.

# Progress bar
Job status and progress are indicated in the log with progress bar:
```python
PBAR_MARKS = {
	STATES.INIT         : ' ',
	STATES.BUILDING     : '~',
	STATES.BUILT        : '-',
	STATES.BUILTFAILED  : '!',
	STATES.SUBMITTING   : '+',
	STATES.SUBMITTED    : '>',
	STATES.SUBMITFAILED : '$',
	STATES.RUNNING      : '>',
	STATES.RETRYING     : '-',
	STATES.DONE         : '=',
	STATES.DONECACHED   : 'z',
	STATES.DONEFAILED   : 'x',
	STATES.ENDFAILED    : 'X',
	STATES.KILLING      : '<',
	STATES.KILLED       : '*',
	STATES.KILLFAILED   : '*',
}
```
By default, the size of the progress bar has a length of `50`, you may change it in your configuration: `{'_log': {'pbar': 100}}`

Note that if a cell represents multiple jobs, it has a priority as listed below:
```python
STATES = Box(
	INIT         = '00_init',
	BUILDING     = '99_building',
	BUILT        = '97_built',
	BUILTFAILED  = '98_builtfailed',
	SUBMITTING   = '89_submitting',
	SUBMITTED    = '88_submitted',
	SUBMITFAILED = '87_submitfailed',
	RUNNING      = '78_running',
	RETRYING     = '79_retrying',
	DONE         = '67_done',
	DONECACHED   = '66_donecached',
	DONEFAILED   = '68_donefailed',
	ENDFAILED    = '69_endfailed',
	KILLING      = '59_killing',
	KILLED       = '57_killed',
	KILLFAILED   = '58_killfailed',
)
```

But if the progress bar belongs to a job (shown when a job is submitted or done), the status of the job has the highest priority. So in the above example, if the progress bar belongs to job #1:
```
[JOBDONE] [1/9] [>----] Done:  x.x% | Running: x
           ^ Indicating current job (">" for running)
```
So even job #2 belongs to the first cell and it's done, the mark is still `=`.

# Shortening in log
As in most cases, we use real paths. So sometimes they can be so long to show in the logs. We now (v1.4.2+) allow to shorten these paths in the way of changing:
```
/abcdef/ghijkl/mnopqr/stuvw/xyz1234
```
to (`shorten = 20`)
```
'/ab/gh/mn/st/xyz1234'
```
We try to shorten the parents on the path evenly, so that for some shells, it's easier for them to complete the whole path.

You can configure them in the configuration file:
```yaml
default:
    _log:
        shorten: 100
```
`shorten` also takes effect on some long strings in the log, for example:
`1234567890123` will be shorten into `123 ... 123` with `shorten = 11`


[1]: ./blueOnBlack.png
[2]: ./blueOnWhite.png
[3]: ./greenOnBlack.png
[4]: ./greenOnWhite.png
[5]: ./magentaOnBlack.png
[6]: ./magentaOnWhite.png
[7]: ./noThemeOnBlack.png
[8]: ./noThemeOnWhite.png
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
[27]: ../script/#debug-your-script
[28]: https://pypi.org/project/colorama/