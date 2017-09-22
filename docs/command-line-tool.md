# Command line tool
<!-- toc -->

When you are debuggin a processes, specially when you are modify input, output and script, the suffix a process will change. Then there will be several `<workdir>` created in `<ppldir>`. The command line tool helps to maintain and clean up the `<workdir>`s

```bash
> bin/pyppl --help
usage: pyppl [-h] [-w WORKDIR] {clean,list,compare} ...

A set of CLI tools for pyppl.

positional arguments:
  {clean,list,compare}
    clean               Clean a workdir
    list                List the status of a workdir
    compare             Compare the settings of two processes.

optional arguments:
  -h, --help            show this help message and exit
  -w WORKDIR, --workdir WORKDIR
                        The path of workdir, default: ./workdir
```

`pyppl` has a common option `-w` or `--workdir` to specify the work directory with the  processes you want to list, clean or compare. By default, it looks at the processes in `./workdir`

## List processes
![pyppl-cli][1]

`pyppl list` command will list the processes in`./workdir`. It will group the processes with same `id` and `tag`, and compare their time start to run. The latest one will show at the first place, follows the second latest, ... If a `proc.settings` cannot be found in the process directory, it will be shown in red.

## Clean processes
![pyppl-clean][2]

`pyppl list` command will ask whether you want to remove the process directory for the older processes with the same `id` and `tag`.

You can remove all those older process directories without confirmation by `pyppl clean --force`

>**CAUTION** Be careful when you have multiple pipelines in `./workdir`. 
For a single pipeline, it does allow you have processes with same `id` and `tag`. However, for multiple pipelines, you may have. And if the two processes have the same `ppldir` (i.e. `./workdir`), they will have directories with the same `id` and `tag`, but different `suffix`. In this case, if you use `pyppl clean --force`, it will only try to keep only the latest one.
So the best way is to set different tags for the processes with same ids in different pipelines.
Or you can do it without `--force` and keep the ones you want.

## Compare the settings of two pipeines
![pyppl-compare][3]

`pyppl compare` uses python's `difflib` to compare the `proc.settings` files in the directories of two processes. it can take a process group name (i.e. `-p pSort.notag`, in this case, actually, the tag can be omitted if it is `notag`, so you can use `-p pSort`) to compare the top 2 latest processes or two process names with suffices (i.e. `-p1 pSort.notag.4HIhyVbp -p2 pSort.notag.7hNBe2uT`. 

You can also specify the direct path of process groups/directories:
```sh
pyppl -p ./workdir/PyPPL.pSort.notag 
# or mixed
pyppl -p1 ./workdir/PyPPL.pSort.notag.4HIhyVbp -p2 pSort.notag.7hNBe2uT 
```
The direct path will ignore the `workdir` specified by `-w`.  


 

[1]: https://raw.githubusercontent.com/pwwang/pyppl/master/docs/pyppl-cli-list.png
[2]: https://raw.githubusercontent.com/pwwang/pyppl/master/docs/pyppl-cli-clean.png
[3]: https://raw.githubusercontent.com/pwwang/pyppl/master/docs/pyppl-cli-compare.png
