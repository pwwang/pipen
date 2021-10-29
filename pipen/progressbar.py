"""Provide the PipelinePBar and ProcPBar classes"""
from typing import TYPE_CHECKING

from .utils import truncate_text

if TYPE_CHECKING:  # pragma: no cover
    import enlighten

# [12/02/20 12:44:06] I /main
#                 pipeline: 100%|
# |        desc_len      |
PBAR_DESC_LEN = 23


class ProcPBar:
    """The progress bar for processes"""

    def __init__(
        self, manager: "enlighten.Manager", proc_size: int, proc_name: str
    ) -> None:
        self.submitted_counter = manager.counter(
            total=proc_size,
            color="cyan",
            desc=proc_name,
            unit="jobs",
            leave=False,
        )
        self.running_counter = self.submitted_counter.add_subcounter("yellow")
        self.success_counter = self.submitted_counter.add_subcounter("green")
        self.failure_counter = self.submitted_counter.add_subcounter("red")

    def update_job_submitted(self):
        """Update the progress bar when a job is submitted"""
        self.submitted_counter.update()

    def update_job_retrying(self):
        """Update the progress bar when a job is retrying"""
        # self.running_counter.count -= 1
        self.failure_counter.update(-1)

    def update_job_running(self):
        """Update the progress bar when a job is running"""
        self.running_counter.update_from(self.submitted_counter)

    def update_job_succeeded(self):
        """Update the progress bar when a job is succeeded"""
        try:
            self.success_counter.update_from(self.running_counter)
        except ValueError:  # pragma: no cover
            self.success_counter.update_from(self.submitted_counter)

    def update_job_failed(self):
        """Update the progress bar when a job is failed"""
        try:
            self.failure_counter.update_from(self.running_counter)
        except ValueError:  # pragma: no cover
            self.failure_counter.update_from(self.submitted_counter)

    def done(self):
        """The process is done"""
        self.submitted_counter.close()


class PipelinePBar:
    """Progress bar for the pipeline"""

    def __init__(self, n_procs: int, ppln_name: str) -> None:
        """Initialize progress bar for pipeline"""
        import enlighten
        desc_len = PBAR_DESC_LEN
        ppln_name = truncate_text(ppln_name, desc_len)
        self.manager = enlighten.get_manager()
        self.running_counter = self.manager.counter(
            total=n_procs,
            color="yellow",
            desc=f"{ppln_name:>{desc_len}}:",
            unit="procs",
        )
        self.success_counter = self.running_counter.add_subcounter("green")
        self.failure_counter = self.running_counter.add_subcounter("red")
        self.desc_len = desc_len

    def proc_bar(self, proc_size: int, proc_name: str) -> ProcPBar:
        """Get the progress bar for a process

        Args:
            proc_size: The size of the process
            proc_name: The name of the process

        Returns:
            The progress bar for the given process
        """
        proc_name = truncate_text(proc_name, self.desc_len)
        proc_name = f"{proc_name:>{self.desc_len}}:"
        return ProcPBar(self.manager, proc_size, proc_name)

    def update_proc_running(self):
        """Update the progress bar when a process is running"""
        self.running_counter.update()

    def update_proc_done(self):
        """Update the progress bar when a process is done"""
        self.success_counter.update_from(self.running_counter)

    def update_proc_error(self):
        """Update the progress bar when a process is errored"""
        self.failure_counter.update_from(self.running_counter)

    def done(self) -> None:
        """When the pipeline is done"""
        self.running_counter.close()
        self.manager.stop()
