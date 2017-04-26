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
        |-- cached.jobs
        |-- input/
        |-- output/
        `-- scripts/
            |-- script.<index>
            |-- script.<index>.rc
            |-- script.<index>.stdout
            |-- script.<index>.stderr
            |-- [script.<index>.ssh]
            `-- [script.<index>.sge]
```

| Path | Content | Memo |
|------|---------|------|
|`./workdir/`|Where the work directories of all processes of current pipeline locate.||
|`./workdir/PyPPL.<id>.<tag>.<uid>/`|The work directory of current process.|The `uid` is a unique id of the process according to its configuration.|
|`./workdir/PyPPL.<id>.<tag>.<uid>/cached.jobs`|Saves the signatures of cached jobs||
|`./workdir/PyPPL.<id>.<tag>.<uid>/scripts/`|Where you can find all the scripts, stdout file, stderr file and return code file and also other help files for other runners.|-  `script.<index>`: the real script to run, you can also use it to debug<br />- `script.<index>.stdout`: the stdout file<br />- `script.<index>.stderr`: the stderr file<br />- `script.<index>.rc`: the file contains return code<br />- `script.<index>.ssh`: the file for ssh runner<br />- `script.<index>.sge`: the file for sge runner|
|`./workdir/PyPPL.<id>.<tag>.<uid>/input/`|Where you can find the links to all the input files||
|`./workdir/PyPPL.<id>.<tag>.<uid>/output/`|Where you can find all the output files||

> **Note** You can set the `./workdir` to somewhere else by `p.tmpdir`, also the `<workdir>` for a process (`./workdir/PyPPL.<id>.<tag>.<uid>`) to somewhere else by `p.workdir`. You are encouraged to set `p.tmpdir` **BUT NOT** `p.workdir`, as it contains a `uid` if it is automatically computed. It is specially useful when you try to detect whether the job is still running as the command has the `uid` in the path.
All `<workdir>` refers to `./workdir/PyPPL.<id>.<tag>.<uid>/`, `<indir>` to `./workdir/PyPPL.<id>.<tag>.<uid>/input/` and `<outdir>` to `./workdir/PyPPL.<id>.<tag>.<uid>/output/` in this documentation.