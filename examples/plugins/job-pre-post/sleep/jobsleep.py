import time
import logging

from avocado.core import settings
from avocado.plugins.base import JobPrePost


class Sleep(JobPrePost):

    name = 'sleep'
    description = 'Sleeps for a number of seconds'

    def run(self, job):
        log = logging.getLogger("avocado.app")
        seconds = settings.settings.get_value("plugins.job.sleep", "seconds",
                                              3, type=int)
        for i in range(seconds):
            log.info("Sleeping %2i/%s", i+1, seconds)
            time.sleep(1)
