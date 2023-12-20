"""An example to retry the jobs when error happends"""
import time
from pipen import Pipen, Proc


class RetryProc(Proc):
    """Retry the jobs when fail"""
    input = "starttime"
    input_data = [int(time.time())]
    error_strategy = "retry"
    # Make sure the job succeeds finally
    num_retries = 10
    script = """
        timefile="{{job.outdir}}/time.txt"
        now=$(date +"%s")
        expect={{in.starttime + 10}}
        if [[ $now -gt $expect ]]; then
            echo $now $expect 0 >> "$timefile"
            exit 0
        else
            echo $now $expect 1 >> "$timefile"
            exit 1
        fi
    """


if __name__ == "__main__":
    # Show debug information so we see the retrying message
    Pipen(loglevel="debug").set_starts(RetryProc).run()
