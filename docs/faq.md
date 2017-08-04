# FAQ

**Q: Do I have to use the variable name as the process id?**

A: No, you can use a different one by `pWhatever = proc (id=pYourId)`, or `pWhatever = proc ()`, and then change the id by `pWhatever.id = 'pYourId'`

**Q: When should I use `p.brings`?**

A: In most cases, index files. You don't want those files to be involved in the caching, and they somehow depend on input files but not explicmentioned.

**Q: What's the difference between `input` and `args`?**

A: Basically, `args` are supposed to be arguments shared among all jobs in the process. Files in `args` are not linked in the `job.indir` folder.

**Q: Does a `proc` remain the same after it's used to construct an `aggr`?**

A: No, it will be a copy of the original one. So the original be used somewhere else.

**Q: Can I skip a process, or run a process conditionally?**

A: Yes, you may specify the directory of input files to `p.exdir`. 
For conditional process, you can use `callfront` to specify the `p.exdir`:
```python
def condRun (p):
    if <some conditions>:
        p.exdir = <directory of input files>
        p.cache = 'export'
    else:
        p.exdir = ''
        p.cache = True

condProc = pyppl.proc(desc = 'Conditional process.')
#...
condProc.callfront = condRun

```
Remember that the process should have the same basenames for input and output files.

**Q: Can I dry-run a process?**
A: Yes, just use the dry  runner: `p.runner = "dry"`. The runner will just create empty files/directories for output, and skip to run the script.

**Q: Can I disable the logs on the terminal?**
A: Yes, just set `"loglevels"` to `None` in pipeline configurations.

