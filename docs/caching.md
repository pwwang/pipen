# Caching
<!-- toc -->

Once a job is cached, `pyppl` will skip running this job. But you have to tell a process how to cache its jobs by setting `p.cache` with a valid caching method:

|Caching method (`p.cache=?`)|How|
|-|-|
|`True`|A signature<sup>*</sup> of input files, script and output files of a job is cached in `<workdir>/cached.jobs`, compare the signature before a job is running.|
|`"export"`|Skip calculating signatures. If the output files exist in `p.exdir`, create links of them in `<workdir>/output`, which will be used for the dependent processes. Jobs will be skipped.|
|`"export+"`|Try to use `p.cache = True` first, if failed then use `p.cache = "export"`|
|False|Disable caching, always run jobs.|

> **Info** <sup>*</sup>: A file signature is calculated based on the path and last modified time of the file.  
  
> **Hint**: `p.cache = "export"` or `p.cache = "export+"` is extremely useful for a process that you only want it to run successfully once, export the result files and never run the process again. You can even delete the `<workdir>` of the process, but `pyppl` will find the exported files and use them as the input for its dependent processes. So you don't need to modify the pipeline.
