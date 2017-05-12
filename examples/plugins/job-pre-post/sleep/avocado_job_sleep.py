import time

from avocado.core.output import LOG_UI
from avocado.core.settings import settings
from avocado.core.plugin_interfaces import JobPre, JobPost


class Sleep(JobPre, JobPost):

    name = 'sleep'
    description = 'Sleeps for a number of seconds'

    def __init__(self):
        self.seconds = settings.get_value(section="plugins.job.sleep",
                                          key="seconds",
                                          key_type=int,
                                          default=3)

    def sleep(self, job):
        for i in xrange(1, self.seconds + 1):
            LOG_UI.info("Sleeping %2i/%s", i, self.seconds)
            time.sleep(1)

    pre = post = sleep
