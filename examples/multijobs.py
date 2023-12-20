"""An example for a process to have multiple jobs and run jobs in parallel"""
from pipen import Proc, Pipen


class MultiJobProc(Proc):
    """A process with multiple jobs"""
    input = "i"
    input_data = range(10)
    forks = 3
    # Don't cache, we need to see the jobs to run every time
    cache = False
    output = "outfile:file:{{in.i}}.txt"
    # Let the job takes long the see the parallelization from the progressbar
    script = "sleep 1; echo {{in.i}} > {{out.outfile}}"


if __name__ == "__main__":
    Pipen().set_starts(MultiJobProc).run()
