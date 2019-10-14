<!-- toc -->

# Process caching
Once a job is cached, `PyPPL` will skip running this job. But you have to tell a process how to cache its jobs by setting `pXXX.cache` with a valid caching method:

|Caching method (`p.cache=?`)|How|
|-|-|
|`True`|A signature<sup>*</sup> of input files, script and output files of a job is cached in `<workdir>/<job.index>/job.cache`, compare the signature before a job starts to run.|
|`False`| Disable caching, always run jobs.|
|`"export"`| First try to find the signatures, if failed, try to restore the files existed (or exported previously in `p.exdir`).|
|`"force"`| Force the job to be cached. Helpful while debugging. If you have job run independently, you can use this to force `PyPPL` to use those results in the pipelin. If you don't have any results generated previously, then dry-run results will be generated instead.|


> **Hint**: `p.cache = "export"` is extremely useful for a process that you only want it to run successfully once, export the result files and never run the process again. You can even delete the `<workdir>` of the process, but `PyPPL` will find the exported files and use them as the input for processes depending on it, so that you don't need to modify the pipeline.
One scenario is that you can use it to download some files and never need to download them again.

# Resuming from processes
Sometimes, you may not want to start at the very begining of a pipeline. Then you can resume it from some intermediate processes.
To resume pipeline from a process, you have to make sure that the output files of the processes that this process depends on are already generated. Then you can do:
```python
PyPPL().start(...).resume(pXXX).run()
```
Or if the process uses the data from other processes, especially the output channel, you may need `PyPPL` to infer (not neccessary run the script) the output data for processes that this process depends on. Then you can do:
```python
PyPPL().start(...).resume2(pXXX).run()
```
You may also use a common id to set a set of processes:
```python
p1 = Proc(id = 'p', tag = '1st')
p2 = Proc(id = 'p', tag = '2nd')
p3 = Proc(id = 'p', tag = '3rd')
# pipeline will be resumed from p1, p2, p3
PyPPL().start(...).resume('p').run()
```

# Calculating signatures for caching
By default, `PyPPL` uses the last modified time to generate signatures for files and directories. However, for large directories, it may take notably long time to walk over all the files in those directories. If not necessary, you may simply as `PyPPL` to get the last modified time for the directories themselves instead of the infiles inside them by setting `p.dirsig = False`


