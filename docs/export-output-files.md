# Export output files
Output files are generated in `<outdir>`(`<workdir>/output`) if you specify the basename for a `file/path/dir` output placeholder. You can export them to a specific directory by specify the directory to the `exportdir`(alias: `exdir`) of a process: `p.exdir = <exdir>`.

You can use different ways to export output files:

| Ways to export | What happens |
|----------------|--------------|
|`move`(default) |Move output files to the directory, leave links to them in `<outdir>` (make sure dependent processes can run).|
|`copy`|Copy output files to the directory|
|`symlink`|Create symbol links to the output files in the directory|
|`gzip`|If output is a file, will do `gzip` of the file and save the gzipped file in the export directory; if output is a directory, will do `tar -zcvf` of the output directory and save the result file in the export directory.|

 You can export the output files of any process. 