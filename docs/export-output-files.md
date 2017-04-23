# Export output files
Output files are generated in `<outdir>`(`<workdir>/output`) if you specify the basename for a `file/path/dir` output placeholder. You can export them to a specific directory by specify the directory to `exportdir`(alias: `exdir`) of a process: `p.exdir = <exdir>`.

You can use different ways (specify it to `exporthow`(alias: `exhow`) of a process) to export output files:

| Ways to export (`p.exhow=?`) | What happens |
|----------------|--------------|
|`move`(default) |Move output files to the directory, leave links to them in `<outdir>` (make sure dependent processes can run).|
|`copy`|Copy output files to the directory|
|`symlink`|Create symbol links to the output files in the directory|
|`gzip`|If output is a file, will do `gzip` of the file and save the gzipped file in the export directory; if output is a directory, will do `tar -zcvf` of the output directory and save the result file in the export directory.|

You can export the output files of any process. Note that even though the export directory is specified to a process, but the minimum unit is a `job`, whose output files are ready to be exported once it finishes successfully.

You can ask `pyppl` whether to overwrite the existing files in the export directory by set `exportow`(alias:`exow`) to `True` (overwrite) or `False` (not overwrite).

If the export directory you specified does not exist, `pyppl` will try to create it.