# Caching
<!-- toc -->

Once a job is cached, `PyPPL` will skip running this job. But you have to tell a process how to cache its jobs by setting `pXXX.cache` with a valid caching method:

|Caching method (`p.cache=?`)|How|
|-|-|
|`True`|A signature<sup>*</sup> of input files, script and output files of a job is cached in `<workdir>/<job.index>/job.cache`, compare the signature before a job starts to run.|
|`False`| Disable caching, always run jobs.|
|`"export"`| First try to find the signatures, if failed, try to restore the files existed (or exported previously in `p.exdir`).

  
> **Hint**: `p.cache = "export"` is extremely useful for a process that you only want it to run successfully once, export the result files and never run the process again. You can even delete the `<workdir>` of the process, but `PyPPL` will find the exported files and use them as the input for processes depending on it, so that you don't need to modify the pipeline.  
One scenario is that you can use it to download some files and never need to download them again.
