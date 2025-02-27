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

    with pytest.raises(NoSuchSchedulerError):
        get_scheduler("nosuchscheduler")


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

    assert str(gbatch.workdir.path) == "gs://test-bucket/workdir"
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
