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
