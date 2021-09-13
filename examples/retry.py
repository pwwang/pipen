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
        if [[ $(date +"%s") -gt {{in.starttime + 3}} ]]; then
            exit 0
        else
            exit 1
        fi
    """

# Show debug information so we see the retrying message
Pipen(loglevel="debug").run(RetryProc)
