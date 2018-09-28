# FAQ

**Q: How should I migrate from 0.8.x?**

- First letters of class names are capitalized (i.e. `proc` -> `Proc`, `aggr` -> `Aggr`). Note that previous class `pyppl` was changed to `PyPPL`.
- Default configuration files were changed to `~/.PyPPL.json` and `~/.PyPPL`
- Log configurations were grouped to `{"log": {...}}` instead of `{"logtheme": ..., "loglevels": ...}`
- Flowchart is themeable now: in configuration file: `{"flowchart": {...}}`
- Templating enhanced from previous placeholders (Jinja2 supported). See [templating](./placeholders/)
- Input and output placeholders are now under `in` and `out` namespaces, respectively.
- `updateArgs` is merged into `set` for `Aggr`.
- Module `doct` removed, `python-box` is used instead.

**Q: Do I have to use the variable name as the process id?**

A: No, you can use a different one by `pWhatever = Proc (id=pYourId)`, or `pWhatever = Proc ()`, and then change the id by `pWhatever.id = 'pYourId'`

**Q: What's the difference between **`input`** and **`args`**?**

A: Basically, `args` are supposed to be arguments shared among all jobs in the process. Files in `args` are not linked in the `job.indir` folder.

**Q: Does a **`Proc`** remain the same after it's used to construct an **`Aggr`**?**

A: No, it will be a copy of the original one. So the original be used somewhere else.

**Q: Can I dry-run a process?**  

A: Yes, just use the dry  runner: `p.runner = "dry"`. The runner will just create empty files/directories for output, and skip to run the script.

**Q: Can I disable the logs on the terminal?**  

A: Yes, just set `{"log": {"levels": None}}` in pipeline configurations.

**Q: How to migrate from 1.1.2**

A: v1.2.0+ uses `liquidpy` as default template engine. Input and output are now under namespace `i` and `o` instead of `in` and `out`.

