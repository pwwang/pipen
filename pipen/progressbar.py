"""Provide the PipelinePBar and ProcPBar classes"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .utils import truncate_text

if TYPE_CHECKING:  # pragma: no cover
    import enlighten

# [12/02/20 12:44:06] I core
#                 pipeline: 100%|
# |        desc_len      |
PBAR_DESC_LEN = 23


class ProcPBar:
    """The progress bar for processes"""

    __slots__ = (
        "counter",
        "proc_size",
        "bar_format",
        "queued_counter",
        "submitted_counter",
        "running_counter",
        "success_counter",
        "failure_counter",
    )

    def __init__(
        self, manager: enlighten.Manager, proc_size: int, proc_name: str
    ) -> None:
        """Initialize the progress bar for a process"""
        if proc_size > 1:
            self.bar_format = None
            bar_format = (
                "{desc}{desc_pad}{percentage:3.0f}%|{bar}| "
                "I:{count_0:<{len_total}d} "
                "Q:{count_1:<{len_total}d} "
                "S:{count_2:<{len_total}d} "
                "R:{count_3:<{len_total}d} "
                "D:{count_4:>{len_total}d}|{count_5:<{len_total}d} "
                "[{rate:5.2f}{unit_pad}{unit}/s]"
            )
        else:
            self.bar_format = (
                "{{desc}}{{desc_pad}}{{percentage:3.0f}}%|{{bar}}| "
                "{:^9} [{{rate:5.2f}}{{unit_pad}}{{unit}}/s]"
            )
            bar_format = self.bar_format.format("-----------")

        self.counter: enlighten.Counter = manager.counter(
            total=proc_size,
            color="grey",
            desc=proc_name,
            unit="jobs ",
            leave=False,
        )
        self.proc_size = proc_size
        self.queued_counter: enlighten.SubCounter = self.counter.add_subcounter(
            "lightblue"
        )
        self.submitted_counter: enlighten.SubCounter = self.counter.add_subcounter(
            "cyan"
        )
        self.running_counter: enlighten.SubCounter = self.counter.add_subcounter(
            "yellow"
        )
        self.success_counter: enlighten.SubCounter = self.counter.add_subcounter(
            "green"
        )
        self.failure_counter: enlighten.SubCounter = self.counter.add_subcounter("red")
        # defer setting the bar_format, in case self.counter is rendered too early
        # ValueError: Reserve field 'count_0' specified in format,
        # but no subcounters are configured
        self.counter.bar_format = bar_format

    def update_job_inited(self):
        """Update the progress bar when a job is init'ed"""
        if self.bar_format:
            self.counter.bar_format = self.bar_format.format("Init'ed")

        self.counter.update()

    def update_job_queued(self):
        """Update the progress bar when a job is queued"""
        if self.bar_format:
            self.counter.bar_format = self.bar_format.format("Queued")
        try:
            self.queued_counter.update_from(self.counter)
        except ValueError:  # pragma: no cover
            pass

    def update_job_submitted(self):
        """Update the progress bar when a job is init'ed"""
        if self.bar_format:
            self.counter.bar_format = self.bar_format.format("Submitted")
        try:
            self.submitted_counter.update_from(self.queued_counter)
        except ValueError:  # pragma: no cover
            pass

    def update_job_retrying(self):  # pragma: no cover
        """Update the progress bar when a job is retrying"""
        if self.bar_format:
            self.counter.bar_format = self.bar_format.format("Retrying")

        self.failure_counter.update(-1)
        self.running_counter.update(0, force=True)
        self.submitted_counter.update(0, force=True)
        self.queued_counter.update(0, force=True)
        self.counter.update(1, force=True)

    def update_job_running(self):
        """Update the progress bar when a job is running"""
        if self.bar_format:
            self.counter.bar_format = self.bar_format.format("Running")
        try:
            self.running_counter.update_from(self.submitted_counter)
        except ValueError:  # pragma: no cover
            pass

    def update_job_succeeded(self, cached: bool = False):
        """Update the progress bar when a job is succeeded"""
        if self.bar_format:
            self.counter.bar_format = self.bar_format.format(
                "Cached" if cached else "Succeeded"
            )
        try:
            self.success_counter.update_from(self.running_counter)
        except ValueError:  # pragma: no cover
            pass

    def update_job_failed(self):
        """Update the progress bar when a job is failed"""
        if self.bar_format:
            self.counter.bar_format = self.bar_format.format("Failed")
        try:
            self.failure_counter.update_from(self.running_counter)
        except ValueError:  # pragma: no cover
            pass

    def done(self):
        """The process is done"""
        try:
            self.counter.close()
        except:  # noqa: E722  # pragma: no cover
            pass


class PipelinePBar:
    """Progress bar for the pipeline"""

    __slots__ = (
        "manager",
        "running_counter",
        "success_counter",
        "failure_counter",
        "desc_len",
    )

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
            bar_format=(
                "{desc}{desc_pad}{percentage:3.0f}%|{bar}| "
                f"{{count:{{len_total}}d}}/{n_procs} "
                "[{rate:5.2f}{unit_pad}{unit}/s]"
            ),
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
        try:
            self.running_counter.close()
            self.manager.stop()
        except:  # noqa: E722  # pragma: no cover
            pass
