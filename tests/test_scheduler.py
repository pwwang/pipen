import pytest
from unittest.mock import MagicMock

from yunpath import AnyPath
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


def test_container_scheduler_init(tmp_path):
    scheduler = get_scheduler("container")(
        image="bash:latest",
        entrypoint="/usr/local/bin/bash",
        workdir=tmp_path / "workdir",
        bin="true",
    )
    pipeline = MagicMock(outdir=tmp_path / "outdir")
    proc = MagicMock(pipeline=pipeline)
    proc.name = "test_proc"
    scheduler.post_init(proc)
    assert (
        scheduler.volumes[-1]
        == f"{tmp_path}/outdir:/mnt/disks/pipen-pipeline/outdir"
    )


def test_gbatch_scheduler_init():
    gbatch_sched = get_scheduler("gbatch")

    with pytest.raises(
        ValueError, match="'fast_mount' for gbatch scheduler should be in the format"
    ):
        gbatch_sched(
            project="test_project",
            location="test_location",
            workdir="gs://test-bucket/workdir",
            fast_mount="test",
        )

    with pytest.raises(
        ValueError,
        match="'fast_mount' for gbatch scheduler should be a Google Cloud Storage",
    ):
        gbatch_sched(
            project="test_project",
            location="test_location",
            workdir="gs://test-bucket/workdir",
            fast_mount="file:///tmp/test:/mnt/disks//test",
        )

    with pytest.raises(TypeError):
        gbatch_sched(
            project="test_project",
            location="test_location",
            workdir="gs://test-bucket/workdir",
            fast_container={"image_uri": "some-image"},
            taskGroups=1,
        )

    gbatch = gbatch_sched(
        project="test_project",
        location="test_location",
        workdir="gs://test-bucket/workdir",
        fast_mount="gs://test-bucket/path:/mnt/disks/path",
        fast_container={
            "image_uri": "some-image",
            "entrypoint": "/bin/bashx",
            "commands": ["-c"],
        }
    )
    task_spec = gbatch.config.taskGroups[0].taskSpec
    assert gbatch.project == "test_project"
    assert gbatch.location == "test_location"
    assert task_spec.volumes[-1].mountPath == "/mnt/disks/path"
    assert task_spec.volumes[-1].gcs.remotePath == "test-bucket/path"
    assert task_spec.runnables[0].container.image_uri == "some-image"
    assert task_spec.runnables[0].container.entrypoint == "/bin/bashx"
    assert task_spec.runnables[0].container.commands == ["-c"]


def test_gbatch_scheduler_post_init_non_gs_outdir():
    gbatch = get_scheduler("gbatch")(
        project="test_project",
        location="test_location",
        workdir="gs://test-bucket/workdir",
    )
    pipeline = MagicMock(outdir="/local/outdir")
    proc = MagicMock(pipeline=pipeline)
    proc.name = "test_proc"
    with pytest.raises(ValueError):
        gbatch.post_init(proc)


def test_gbatch_scheduler_post_init():
    gbatch = get_scheduler("gbatch")(
        project="test_project",
        location="test_location",
        workdir="gs://test-bucket/workdir",
    )
    pipeline_outdir = AnyPath("gs://test-bucket/outdir")
    pipeline = MagicMock(outdir=pipeline_outdir)
    proc = MagicMock(pipeline=pipeline)
    proc.name = "test_proc"
    gbatch.post_init(proc)

    assert str(gbatch.workdir) == "gs://test-bucket/workdir"
    assert (
        str(gbatch.workdir.mounted) == f"{GbatchScheduler.MOUNTED_METADIR}/{proc.name}"
    )
    assert (
        gbatch.config.taskGroups[0].taskSpec.volumes[-1].mountPath
        == f"{GbatchScheduler.MOUNTED_OUTDIR}"
    )
    assert (
        gbatch.config.taskGroups[0].taskSpec.volumes[-1].gcs.remotePath
        == "test-bucket/outdir"
    )
    assert (
        gbatch.config.taskGroups[0].taskSpec.volumes[-2].mountPath
        == f"{GbatchScheduler.MOUNTED_METADIR}/{proc.name}"
    )
    assert (
        gbatch.config.taskGroups[0].taskSpec.volumes[-2].gcs.remotePath
        == "test-bucket/workdir"
    )
