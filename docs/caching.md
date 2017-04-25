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
