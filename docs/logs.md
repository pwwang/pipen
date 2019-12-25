
`PyPPL` has fancy logs. You can define how they look like (theme) and what messages to show (levels).

## Built-in log themes
We have some built-in themes:

green_on_black (default):
![green_on_black][3]

green_on_white:
![green_on_white][4]

blue_on_black:
![blue_on_black][1]

blue_on_white:
![blue_on_white][2]

magenta_on_black:
![magenta_on_black][5]

magenta_on_white:
![magenta_on_white][6]

If you don't like them, you can also disable them:
![noTheme_on_black][7]
![noTheme_on_white][8]

To use them, just specify the name in your pipeline configuration file:
```python
dict(default=dict(
    logger = dict(
        theme = 'magenta_on_white'
    )
))
```
Or when you initialize a pipeline:
```python
PyPPL(logger_theme = 'green_on_black').start(...).run()
```
If you want to disable the theme, just set `"theme"` to `False` (`false` for `json`)
If you set `theme` to `True`, then default theme `green_on_black` is used.

## Level groups

Unlike python's default logging system, we have group of levels. The group is like the python logging level. However, here we have more, and with different values:

```python
GROUP_VALUES = dict(
    TITLE    = 80,
    SUBTITLE = 70,
    STATUS   = 60,
    CRITICAL = 50,
    ERROR    = 40,
    WARNING  = 30,
    INFO     = 20,
    DEBUG    = 10,
    NOTSET   = 0
)
```

And each group has different levels

```python
LEVEL_GROUPS = dict(
    TITLE    = ['PROCESS'],
    SUBTITLE = ['DEPENDS', 'DONE'],
    STATUS   = ['WORKDIR', 'CACHED', 'P_DONE'],
    CRITICAL = ['INFO', 'BLDING', 'SBMTING', 'RUNNING', 'JOBDONE', 'KILLING'],
    ERROR    = ['ERROR'],
    WARNING  = ['WARNING', 'RTRYING'],
    INFO     = ['PYPPL', 'PLUGIN', 'TIPS', 'CONFIG'],
    DEBUG    = ['DEBUG'],
)
```

So if you set `PyPPL(logger_level = 'INFO')`; that means the levels in groups with value >= 20 will be shown.

|Logger level|Meaning|
|-|-|
|`PROCESS`|Mark when a process initiates|
|`DEPENDS`|Show dependencies of a process|
|`ERROR`|Show errors|
|`INFO`|Some information|
|`DONE`|Mark when a process is done|
|`BLDING`|Mark when a job starts to build|
|`SBMTING`|Mark when a job starts to submit|
|`RUNNING`|Mark when a job starts to run|
|`RTRYING`|Mark when a job starts to retry|
|`CACHED`|Mark when a job is cached|
|`PYPPL`|When pipeline starts|
|`TIPS`|Show tips|
|`CONFIG`|Show configuration is read from file|
|`WORKDIR`|Show the workdir for a process|
|`JOBDONE`|Mark when a job is done|


You can modify based on the group:
```python
# also show debug message, but don't show the tips
PyPPL(logger_level = 'info', logger_leveldiffs = ["+DEBUG", "-TIPS"])
```

## Define your own theme

Let's see how the built-in theme looks like first:
in `pyppl/logger.py`:
```python
THEMES = dict(
    green_on_black = dict(
        TITLE    = '{s.BRIGHT}{f.CYAN}',
        SUBTITLE = '{f.MAGENTA}',
        STATUS   = '{f.YELLOW}',
        CRITICAL = '{f.GREEN}',
        ERROR    = '{f.RED}',
        WARNING  = '{s.BRIGHT}{f.YELLOW}',
        DEBUG    = '{s.DIM}{f.WHITE}',
        NOTSET   = ''
    ),

    # other themes
}
```
See available colors and styles [here][28]
You can also use the directly terminal escape sequences, like `\033[30m` for black (check [here][26]).

You can save it in configurations:
```toml
# pyppl.toml
[logger.theme]
TITLE    = '{s.BRIGHT}{f.CYAN}'
SUBTITLE = '{f.MAGENTA}'
STATUS   = '{f.YELLOW}'
CRITICAL = '{f.GREEN}'
ERROR    = '{f.RED}'
WARNING  = '{s.BRIGHT}{f.YELLOW}'
DEBUG    = '{s.DIM}{f.WHITE}'
NOTSET   = ''
```

Or pass it at runtime:
```python
PyPPL(logger_theme = dict(TITLE = '{s.BRIGHT}{f.CYAN}', ...))
```

## Log to file
By default, `PyPPL` will not log to a file until you set a file path to `{"logger": {"file": "/path/to/logfile"}}` in the configuration. Or you can specfiy `False` to it to disable logging to file. If you set it to `True`, a default log file will be used, which is: `"./<pipeline name>.pyppl.log"`

!!! note
    Themes are not applied to handler to log to file.

## Progress bar
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

Note that if a cell represents multiple jobs, it has a priority as listed below:
```python
STATES = Diot(
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
