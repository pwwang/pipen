You can tell `pipen` how to handle when a job fails to run.

You can specify one of the following to `error_strategy`

- `halt`: Any failure will just halt the whole pipeline
- `ignore`: Ignore the error and keep running (assuming the job runs successfully anyway)
- `retry`: Retry to job running
  - After `num_retries` times of retrying, if the job is still failing, then halt the pipeline.

`pipen` uses `xqute` to handle the errors. See also [here][1].

[1]: https://pwwang.github.io/xqute/api/xqute.defaults/#xqute.defaults.JobErrorStrategy
