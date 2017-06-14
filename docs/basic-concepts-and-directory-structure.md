# Basic concepts and folder structure

<!-- toc -->

## Layers of a pipeline
![Basic concepts](https://github.com/pwwang/pyppl/raw/master/docs/concept.png)
The pipeline consists of channels and processes. A process may have many jobs. Each job uses the corresponding element from the input channel of the process, and generates values for output channel of the output.  
Actually, what you need to do is just specify the first input channel, and then tell `pyppl` the dependencies of the processes. The later processes will use the output channel of the processes they depend on.

## Folder structure
```
./
|-- pipeline.py
`-- workdir/
	`-- PyPPL.<id>.<tag>.<uid>/   
		`-- <job.id>/
			|-- input/
			|-- output/
			|-- job.cache
			|-- job.script
			|-- job.rc
			|-- job.stdout
			|-- job.stderr
			|-- [job.script.ssh]
			`-- [job.script.sge]
```

| Path | Content | Memo |
|------|---------|------|
|`workdir/`|Where the pipeline directories of all processes of current pipeline locate.|Can be set by `p.ppldir`|
|`PyPPL.<id>.<tag>.<uid>/`|The work directory of current process.|The `uid` is a unique id of the process according to its configuration.<br/>You may set it by `p.workdir`|
|`<job.id>/`|The job directory||
|`<job.id>/input/`|Where you can find the links to all the input files||
|`<job.id>/output/`|Where you can find all the output files||
|`<job.id>/job.cache`|The file containing the signature of the job||
|`<job.id>/job.script`|To script file to be running||
|`<job.id>/job.rc`|To file containing the return code||
|`<job.id>/job.stdout`|The STDOUT of the script||
|`<job.id>/job.stderr`|The STDERR of the script||
|`<job.id>/job.script.ssh`|The script file for ssh runner||
|`<job.id>/job.script.sge`|The script file for sge runner||

> **Note**  You are encouraged to set `p.ppldir` **BUT NOT** `p.workdir`, as it contains a `uid` if it is automatically computed. It is specially useful when you try to detect whether the job is still running as the command has the `uid` in the path.  
All `<workdir>` refers to `./workdir/PyPPL.<id>.<tag>.<uid>/`, `<indir>` to `./workdir/PyPPL.<id>.<tag>.<uid>/<job.id>/input/` and `<outdir>` to `./workdir/PyPPL.<id>.<tag>.<uid>/<job.id>/output/` in this documentation.