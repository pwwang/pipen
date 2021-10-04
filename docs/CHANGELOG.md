## 0.1.3

- ✨Add `on_proc_init()` hook to enables plugins to modify the default attributes of processes

## 0.1.2

- 💥 Use `set_starts()` and `set_data()` to set start processes of a pipeline.

## 0.1.1

- 💥 Allow plugins to modify other configs via on_setup() hook
- 🎨 Move progress bar to the last
- 🩹 Warn when no input_data specified for start process
- 💬 Change end to export
- 🚚 Move on_init() so it's able to redefine default configs
- 💥 Change `exec_cmd` hook of cli plugin to `exec_command`


## 0.1.0

It's now fully documented. See documentations.

## 0.0.4
- Clear output if not cached.
- Make process running order fixed

## 0.0.3
- Fix caching issue
- Add singleton to proc to force singleton
- Log an empty line after all processes finish
- Allow input to be None
- Separate channels from different required procs
- Move proc prepare before run
- Change the order proc banner printing, making sure it prints before other logs for the proc
- FIx job not cached if input is missing
- Don't redirect output only if absolute path specified
- Make input files resolved(absolute path)
- Give more detailed ProcDependencyError
- Force job status to be failed when Ctrl + c
- Fix files for input when it is a pandas dataframe
- Add job name prefix for scheduler
- Adopt datar for channels

## 0.0.2
- Add on_proc_property_computed hook
- Add plugin options for pipen construct
- Keep args, envs, scheduler_opts and plugin_opts as Diot object for procs
- Fix shebang not working in script
- Make sure job rendering data are stringified.
- Move starts as a method so that pipelines can be initialized before processes.
- Use plyrda instead of siuba for channel
- Add template rendering error to indicate where the rendering error happens;
- Add succeeded to on_complete hook;
- Add hook on_proc_start;
- Add argument succedded for hook on_proc_done;
- Realign pipeline and proc names in progress bars
- Remove debug log in job preparing, which will appear on the top of the logs

## 0.0.1

- Reimplement PyPPL using asyncio
