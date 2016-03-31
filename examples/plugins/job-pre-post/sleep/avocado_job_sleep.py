import time
import logging

from avocado.core.settings import settings
from avocado.plugins.base import JobPrePost


class Sleep(JobPrePost):

    name = 'sleep'
    description = 'Sleeps for a number of seconds'

    def run(self, job):
        log = logging.getLogger("avocado.app")
        seconds = settings.get_value(section="plugins.job.sleep",
                                     key="seconds",
                                     key_type=int,
                                     default=3)
        for i in range(seconds):
            log.info("Sleeping %2i/%s", i+1, seconds)
            time.sleep(1)
