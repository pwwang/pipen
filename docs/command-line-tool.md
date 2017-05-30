# Command line tool
<!-- toc -->

```bash
>  pyppl-cli --help
 
usage: pyppl-cli [-h] [-w WORKDIR] {clean,list} ...

A set of CLI tools for pyppl.

positional arguments:
  {clean,list}
    clean               Clean a workdir
    list                List the status of a workdir

optional arguments:
  -h, --help            show this help message and exit
  -w WORKDIR, --workdir WORKDIR
                        The path of workdir, default: ./workdir
```

## List processes
Example:
```
 >  pyppl-cli list  

WORKDIR: ./workdir (Yellow processes are to be cleaned!)
--------------------------------------------------------

- PROCESSES: pSnpEff2Stat.vs
  ------------------------------------
  6Tka6wMZ: 2017-05-24 18:06:58 980173

- PROCESSES: pFiles2Dir.vs
  ------------------------------------
  76mwm2dC: 2017-05-24 15:03:53 806661

- PROCESSES: pPlotSnpEff.vs
  ------------------------------------
  4OX5hIPw: 2017-05-24 17:05:56 474412

- PROCESSES: pCallRate.vs
  ------------------------------------
  7P4pZK2a: 2017-05-24 19:07:21 056884

- PROCESSES: pVcf2List.vs
  ------------------------------------
  2Q1jkL5L: 2017-05-25 21:09:20 440624

- PROCESSES: pVcf2Stat.vs
  ------------------------------------
  6kuBSGJJ: 2017-05-24 18:06:28 880805

- PROCESSES: pSnpEff.vs
  ------------------------------------
  1X5cGEfP: 2017-05-24 14:02:03 270672

- PROCESSES: pVcfStats.vs
  ------------------------------------
  54VSCVcd: 2017-05-24 19:07:22 405329

- PROCESSES: pCbindList.vs
  ------------------------------------
  3YANehrC: 2017-05-25 21:09:20 440624
```

## Clean processes
If you run `pyppl-cli clean`, it will list all processes, and prompt you whether to remove the old processes with the same id and tag.  
You can run `pyppl-cli clean -f` to clean the processes without prompt.
