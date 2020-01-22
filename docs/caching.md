<!-- toc -->

# Process caching
Once a job is cached, `PyPPL` will skip running this job. But you have to tell a process how to cache its jobs by setting `pXXX.cache` with a valid caching method:

|Caching method (`p.cache=?`)|How|
|-|-|
|`True`|A signature<sup>*</sup> of input files, script and output files of a job is cached in `<workdir>/<job.index>/job.cache`, compare the signature before a job starts to run.|
|`False`| Disable caching, always run jobs.|
|`"force"`| Force caching, as long as the jobs have been successfully executed at last run, regardless of any changes to input/output/script. This is useful, for example, when you just change the number of threads for the job, but you don't want to rerun the job.|

# Calculating signatures for caching
By default, `PyPPL` uses the last modified time to generate signatures for files and directories. However, for large directories, it may take notably long time to walk over all the files in those directories. If not necessary, you may simply as `PyPPL` to get the last modified time for the directories themselves instead of the infiles inside them by setting `p.dirsig = False`
