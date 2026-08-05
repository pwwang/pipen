import pytest
from unittest.mock import MagicMock

from pathlib import Path
from panpath import PanPath
from pipen.scheduler import (
    get_scheduler,
    LocalScheduler,
    SgeScheduler,
    SshScheduler,
    SlurmScheduler,
    GbatchScheduler,
    ContainerScheduler,
    NoSuchSchedulerError,
)
from .helpers import SimpleProc, pipen_container  # noqa: F401


def test_get_scheduler():

    local = get_scheduler("local")
    assert local is LocalScheduler

    local = get_scheduler(local)
    assert local is LocalScheduler

    sge = get_scheduler("sge")
    assert sge is SgeScheduler

    sge = get_scheduler(sge)
    assert sge is SgeScheduler

    slurm = get_scheduler("slurm")
    assert slurm is SlurmScheduler

    slurm = get_scheduler(slurm)
    assert slurm is SlurmScheduler

    ssh = get_scheduler("ssh")
    assert ssh is SshScheduler

    ssh = get_scheduler(ssh)
    assert ssh is SshScheduler

    gbatch = get_scheduler("gbatch")
    assert gbatch is GbatchScheduler

    gbatch = get_scheduler(gbatch)
    assert gbatch is GbatchScheduler

    container = get_scheduler("container")
    assert container is ContainerScheduler

    container = get_scheduler(container)
    assert container is ContainerScheduler

    with pytest.raises(NoSuchSchedulerError):
        get_scheduler("nosuchscheduler")


async def test_container_scheduler_init(tmp_path):
    tmp_path = PanPath(tmp_path)
    scheduler = get_scheduler("container")(
        image="bash:latest",
        entrypoint="/usr/local/bin/bash",
        workdir=tmp_path / "workdir",
        bin="true",
    )
    pipeline = MagicMock(outdir=tmp_path / "outdir")
    pipeline.name = "test_pipeline"
    proc = MagicMock(pipeline=pipeline)
    proc.name = "test_proc"
    await scheduler.post_init(proc)
    assert (
        scheduler.volumes[-1]
        == f"{tmp_path}/outdir:/mnt/disks/.pipen-test_pipeline-output"
    )


def test_gbatch_scheduler_init():
    gbatch_sched = get_scheduler("gbatch")

    with pytest.raises(ValueError):
        gbatch_sched(
            project="test_project",
            location="test_location",
            workdir="gs://test-bucket/workdir",
            mount="test",
        )

    with pytest.raises(TypeError):
        gbatch_sched(
            project="test_project",
            location="test_location",
            workdir="gs://test-bucket/workdir",
            image_uri="some-image",
            taskGroups=1,
        )

    gbatch = gbatch_sched(
        project="test_project",
        location="test_location",
        workdir="gs://test-bucket/workdir",
        mount="gs://test-bucket/path:/mnt/disks/path",
        image_uri="some-image",
        entrypoint="/bin/bashx",
        commands=["-c"],
    )
    task_spec = gbatch.config["taskGroups"][0]["taskSpec"]
    assert gbatch.project == "test_project"
    assert gbatch.location == "test_location"

    assert task_spec["volumes"][-1]["mountPath"] == "/mnt/disks/path"
    assert task_spec["volumes"][-1]["gcs"]["remotePath"] == "test-bucket/path"
    assert task_spec["runnables"][0]["container"]["image_uri"] == "some-image"
    assert task_spec["runnables"][0]["container"]["entrypoint"] == "/bin/bashx"
    assert task_spec["runnables"][0]["container"]["commands"] == ["-c"]


async def test_gbatch_scheduler_post_init_non_gs_outdir():
    gbatch = get_scheduler("gbatch")(
        project="test_project",
        location="test_location",
        workdir="gs://test-bucket/workdir",
    )
    pipeline = MagicMock(outdir=PanPath("/local/outdir"))
    proc = MagicMock(pipeline=pipeline)
    proc.name = "test_proc"
    with pytest.raises(ValueError):
        await gbatch.post_init(proc)


async def test_gbatch_scheduler_post_init():
    gbatch = get_scheduler("gbatch")(
        project="test_project",
        location="test_location",
        workdir="gs://test-bucket/workdir",
    )
    pipeline_outdir = PanPath("gs://test-bucket/outdir")
    pipeline = MagicMock(outdir=pipeline_outdir)
    pipeline.name = "test_pipeline"
    proc = MagicMock(pipeline=pipeline)
    proc.name = "test_proc"
    await gbatch.post_init(proc)

    assert str(gbatch.workdir) == "gs://test-bucket/workdir"
    assert str(gbatch.workdir.mounted) == "/mnt/disks/.pipen/workdir"
    volumes = gbatch.config["taskGroups"][0]["taskSpec"]["volumes"]
    assert volumes[-1]["mountPath"] == "/mnt/disks/.pipen-test_pipeline-output"
    assert volumes[-1]["gcs"]["remotePath"] == "test-bucket/outdir"
    assert volumes[-2]["mountPath"] == "/mnt/disks/.pipen"
    assert volumes[-2]["gcs"]["remotePath"] == "test-bucket"


async def test_gbatch_scheduler_mount_as_cwd():
    gbatch = get_scheduler("gbatch")(
        project="test_project",
        location="test_location",
        workdir=".pipen/Process",
        mount_as_cwd="gs://test-bucket/cwd",
    )
    pipeline_outdir = PanPath("Pipeline-output")
    pipeline = MagicMock(outdir=pipeline_outdir)
    pipeline.name = "Pipeline"
    proc = MagicMock(pipeline=pipeline, _export_dir=PanPath("Pipeline-output"))
    proc.name = "Process"
    await gbatch.post_init(proc)

    assert str(gbatch.workdir) == "gs://test-bucket/cwd/.pipen/Process"
    assert str(gbatch.workdir.mounted) == "/mnt/disks/.cwd/.pipen/Process"
    volumes = gbatch.config["taskGroups"][0]["taskSpec"]["volumes"]
    assert len(volumes) == 1
    assert volumes[0]["mountPath"] == "/mnt/disks/.cwd"
    assert volumes[0]["gcs"]["remotePath"] == "test-bucket/cwd"
    assert str(proc._export_dir.mounted) == "/mnt/disks/.cwd/Pipeline-output"


async def test_gbatch_scheduler_mount_as_cwd_with_abs_workdir_outdir():
    gbatch = get_scheduler("gbatch")(
        project="test_project",
        location="test_location",
        workdir="gs://test-bucket/.pipen/Process",
        mount_as_cwd="gs://test-bucket/cwd",
    )
    pipeline_outdir = PanPath("gs://test-bucket/Pipeline-output")
    pipeline = MagicMock(outdir=pipeline_outdir)
    pipeline.name = "Pipeline"
    proc = MagicMock(pipeline=pipeline)
    proc.name = "Process"
    await gbatch.post_init(proc)

    assert str(gbatch.workdir) == "gs://test-bucket/.pipen/Process"
    assert str(gbatch.workdir.mounted) == "/mnt/disks/.pipen/Process"
    volumes = gbatch.config["taskGroups"][0]["taskSpec"]["volumes"]
    assert len(volumes) == 3
    assert volumes[0]["mountPath"] == "/mnt/disks/.cwd"
    assert volumes[0]["gcs"]["remotePath"] == "test-bucket/cwd"
    assert volumes[1]["mountPath"] == "/mnt/disks/.pipen"
    assert volumes[1]["gcs"]["remotePath"] == "test-bucket/.pipen"
    assert volumes[2]["mountPath"] == "/mnt/disks/.pipen-Pipeline-output"
    assert volumes[2]["gcs"]["remotePath"] == "test-bucket/Pipeline-output"


async def test_container_scheduler_mount_as_cwd(tmp_path):
    tmp_path = PanPath(tmp_path)
    scheduler = get_scheduler("container")(
        image="bash:latest",
        entrypoint="/usr/local/bin/bash",
        workdir=".pipen/Process",
        bin="true",
        mount_as_cwd=tmp_path / "cwd",
    )
    pipeline = MagicMock(outdir=Path("Pipeline-output"))
    pipeline.name = "test_pipeline"
    proc = MagicMock(pipeline=pipeline)
    proc.name = "test_proc"
    await scheduler.post_init(proc)

    assert str(scheduler.workdir) == str(tmp_path / "cwd/.pipen/Process")
    assert str(scheduler.workdir.mounted) == "/mnt/disks/.cwd/.pipen/Process"
    assert len(scheduler.volumes) == 1
    assert scheduler.volumes[0] == f"{tmp_path}/cwd:/mnt/disks/.cwd"


async def test_container_scheduler_mount_as_cwd_with_abs_workdir_outdir(tmp_path):
    tmp_path = PanPath(tmp_path)
    scheduler = get_scheduler("container")(
        image="bash:latest",
        entrypoint="/usr/local/bin/bash",
        workdir=tmp_path / ".pipen/Process",
        bin="true",
        mount_as_cwd=tmp_path / "cwd",
    )
    pipeline = MagicMock(outdir=tmp_path / "Pipeline-output")
    pipeline.name = "Pipeline"
    proc = MagicMock(pipeline=pipeline)
    proc.name = "test_proc"
    await scheduler.post_init(proc)

    assert str(scheduler.workdir) == str(tmp_path / ".pipen/Process")
    assert str(scheduler.workdir.mounted) == "/mnt/disks/.pipen/Process"
    assert len(scheduler.volumes) == 3
    assert scheduler.volumes[0] == f"{tmp_path}/cwd:/mnt/disks/.cwd"
    assert scheduler.volumes[1] == f"{tmp_path}/.pipen:/mnt/disks/.pipen"
    assert scheduler.volumes[2] == (
        f"{tmp_path}/Pipeline-output:/mnt/disks/.pipen-Pipeline-output"
    )
