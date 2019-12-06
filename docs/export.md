
<!-- toc -->

Output files are generated in `<outdir>`(`<job.index>/output`) if you specify the basename for a `file/path/dir` for process output. You can export them to a specific directory by specify the directory to `exdir` of a process: `pXXX.exdir = <exdir>`.

You can use different ways (specify it to `exporthow` (alias: `exhow`) of a process) to export output files:

| Ways to export (`p.exhow=?`) | Aliases | What happens |
|------------------------------|---------|--------------|
|`move`(default) |`mv`|Move output files to the directory, leave links to them in `<outdir>` (make sure processes depend on this one can run normally).|
|`copy`|`cp`|Copy output files to the directory|
|`symlink`|`link`, `symbol`|Create symbolic links to the output files in the directory|
|`gzip`|`gz`|If output is a file, will do `gzip` of the file and save the gzipped file in the export directory; if output is a directory, will do `tar -zcvf` of the output directory and save the result file in the export directory.|

You can export the output files of any process. Note that even though the export directory is specific to a process, the minimum unit is a `job`, whose output files are ready to be exported once it finishes successfully.

You can ask `PyPPL` whether to overwrite the existing files in the export directory by set `exow` as `True` (overwrite) or `False` (do not overwrite).

!!! note
	if the directory you specified to `pXXX.exdir` does not exist, it will be created automatically, including those intermediate directories if necessary.

# Partial export
You can also partially export the output files by set value to `pXXX.expart`.
You have 2 ways to select the files:
- Output key. For example, for `p.output = "outfile1:file:a.txt1, outfile2:file:b.txt2"`, you can export only `outfile1` by: `p.expart = "outfile1"`
- Glob patterns. In the above example, you can also do: `p.expart = "*.txt1"`

You can have multiple selectors: `p.expart = ["*.txt1", "outfile2"]` to export all files.

!!! note
	1. Export-caching will not be allowed when using partial export.
	2. Templating is applied for this option.
	3. `expart` will first match output keys and then be used as a glob pattern. So if you have
	```python
	# ...
	p.output = "outfile1:file:outfile2, outfile2:file:b.txt2"
	# ...
	p.expart = ["outfile2"]
	```
	then `b.txt2` will be exported instead of `<job.outdir>/outfile2`

# Control of export of cached jobs
By default, if a job is cached, then it will not try to export the output files again (assuming that you have already successfully run the job and exported the output files). But you can force to export them anyway by setting `p.acache = True`
