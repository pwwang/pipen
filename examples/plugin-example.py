"""An example showing how to create a plugin"""

from pipen import Proc, Pipen, plugin
from pipen.utils import get_logger

logger = get_logger("notify", "info")


class NotifyPlugin:
    version = "0.0.0"

    @plugin.impl
    def on_setup(pipen):
        logger.info("Calling on_setup")

    @plugin.impl
    async def on_start(pipen):
        logger.info("Calling on_start")

    @plugin.impl
    async def on_complete(pipen, succeeded):
        logger.info("Calling on_complete, succeeded = %s", succeeded)

    @plugin.impl
    async def on_proc_start(proc):
        logger.info("Calling on_proc_start")

    @plugin.impl
    async def on_proc_done(proc, succeeded):
        logger.info("Calling on_proc_done, succeeded = %s", succeeded)

    @plugin.impl
    async def on_job_polling(job, counter):
        logger.info("Calling on_job_polling")


class AProcess(Proc):
    input = "a"
    script = 'sleep 2'


if __name__ == "__main__":
    Pipen(plugins=[NotifyPlugin], cache=False).set_starts(AProcess).run()
