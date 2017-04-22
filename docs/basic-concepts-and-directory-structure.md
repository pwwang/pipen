# Basic concepts and folder structure

## Layers of a pipeline
![Basic concepts](https://github.com/pwwang/pyppl/raw/master/docs/concept.png)
The pipeline consists of channels and processes. A process may have many jobs. Each job uses the corresponding element from the input channel of the process, and generates values for output channel of the output.  
Actually, what you need to do is just specify the first input channel, and then tell `pyppl` the dependencies of the processes. The later processes will use the output channel of the processes they depend on.

## Folder structure
| Path | Content | Memo |
|------|---------|------|
|`./workdir/`|Where the work directories of all processes of current pipeline locate.|If `proc.tmpdir` is not specified, `workdir` in current directory will be created and used.|
|`./workdir/PyPPL.<id>.<tag>.<uid>/`|The work directory of current process.|The `uid` is a unique id of the process according to its configuration.|
|`./workdir/PyPPL.<id>.<tag>.<uid>/scripts/`|Where you can find all the scripts, stdout file, stderr file and return code file and also other help files for other runners.|-  `script.<index>`: the real script to run, you can also use it to debug<br />- `script.<index>.stdout`: the stdout file<br />- `script.<index>.stderr`: the stderr file<br />- `script.<index>.rc`: the file contains return code<br />- `script.<index>.ssh`: the file for ssh runner<br />- `script.<index>.sge`: the file for sge runner|
|`./workdir/PyPPL.<id>.<tag>.<uid>/input/`|Where you can find the links to all the input files||
|`./workdir/PyPPL.<id>.<tag>.<uid>/output/`|Where you can find all the output files||