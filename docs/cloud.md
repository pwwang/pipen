Since `v0.16.0`, `pipen` supports the cloud naively. There are two ways by means of cloud support:

- Run the pipeline locally (or schedulers like `sge`, `slurm`, etc.) and save the files to the cloud.
- Run the pipeline on the cloud.

## Run the pipeline locally and save the files to the cloud

To run the pipeline locally and save the files to the cloud, you need to install `pipen` with cloud support:

```bash
pip install xqute[cloudsh]
# To support a specific cloud service provider
pip install cloudpathlib[s3]
pip install cloudpathlib[gs]
pip install cloudpathlib[azure]
```

The you can directly assign a cloud path as a pipeline working directory:

```python
from pipen import Pipen, Proc, run


class P1(Proc):
    """Sort input file"""
    input = "in:var"
    input_data = ["Hello World"]
    output = "outfile:file:out.txt"
    # Note that out.outfile is on the cloud but the script is executed locally
    # we can use cloudsh to save the output to the cloud
    script = "echo {{in.in}} | cloudsh sink {{out.outfile}}"


class MyPipeline(Pipen):
    starts = P1
    workdir = "gs://mybucket/mypipeline/workdir"
    output = "gs://mybucket/mypipeline/output"


if __name__ == "__main__":
    MyPipeline().run()
```

Like the following figure, the pipeline is run locally but the meta information is grabbed from and saved to the cloud (workdir).
No local files are generated.

For the output files, if a process is a non-export process, the output files are saved to the workdir.
If a process is an export process, the output files are saved to the output directory (export dir).

![pipen-cloud1](./pipen-cloud1.png)

## Run the pipeline on the cloud

Currently, `pipen` only supports running the pipeline on the cloud with google batch jobs.

To run the pipeline on the cloud, you need to install `pipen` with cloud support:

```bash
pip install xqute[gs]
```

It is used to communicate with google cloud storage files. No `cloudsh` is needed, since operating the cloud files will be happening on the cloud (with the cloud paths mounted to the VM). You also need to have [google cloud sdk][1] installed and configured, which is used to communicate with google batch jobs (submit jobs, get job status, etc.).

```python
from pipen import Pipen, Proc, run


class P1(Proc):
    """Sort input file"""
    input = "in:var"
    input_data = ["Hello World"]
    output = "outfile:file:out.txt"
    # Note that out.outfile is on the cloud but the script is executed locally
    # we can use cloudsh to save the output to the cloud
    script = "echo {{in.in}} | cloudsh sink {{out.outfile}}"


class MyPipeline(Pipen):
    starts = P1
    workdir = "gs://mybucket/mypipeline/workdir"
    output = "gs://mybucket/mypipeline/output"
    scheduler = "gbatch"


if __name__ == "__main__":
    MyPipeline().run()
```

The only difference is that we need to set `scheduler` to `gbatch` (google batch jobs).

As shown in the following figure, the pipeline is run on the cloud platform, and the workdir and export dir will be mounted to the VM. So the process script can directly access the cloud files, no `cloudsh` or `gcloud` tools are needed.

![pipen-cloud2](./pipen-cloud2.png)

[1]: https://cloud.google.com/sdk?hl=en
