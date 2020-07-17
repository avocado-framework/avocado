import time

from avocado.core.future.settings import settings as future_settings
from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import Init, JobPost, JobPre


class SleepInit(Init):
    name = 'sleep-init'
    description = 'Sleep plugin initialization'

    def initialize(self):
        help_msg = 'Number of seconds to sleep.'
        future_settings.register_option(section='plugins.job.sleep',
                                        key='seconds',
                                        default=3,
                                        help_msg=help_msg)


class Sleep(JobPre, JobPost):
    name = 'sleep'
    description = 'Sleeps for a number of seconds'

    def sleep(self, job):  # pylint: disable=W0613
        seconds = job.config.get('plugins.job.sleep.seconds')
        for i in range(1, seconds + 1):
            LOG_UI.info("Sleeping %2i/%s", i, seconds)
            time.sleep(1)

    pre = post = sleep
