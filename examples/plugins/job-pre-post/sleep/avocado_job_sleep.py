import time

from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import Init, JobPost, JobPre
from avocado.core.settings import settings


class SleepInit(Init):
    name = 'sleep-init'
    description = 'Sleep plugin initialization'

    def initialize(self):
        help_msg = 'Number of seconds to sleep.'
        settings.register_option(section='plugins.job.sleep',
                                 key='seconds',
                                 default=3,
                                 help_msg=help_msg)


class Sleep(JobPre, JobPost):
    name = 'sleep'
    description = 'Sleeps for a number of seconds'

    @staticmethod
    def sleep(job):  # pylint: disable=W0613
        seconds = job.config.get('plugins.job.sleep.seconds')
        for i in range(1, seconds + 1):
            LOG_UI.info("Sleeping %2i/%s", i, seconds)
            time.sleep(1)

    pre = post = sleep
