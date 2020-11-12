import json
import os

from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import Init, JobPost, JobPre
from avocado.core.settings import settings
from avocado.core.teststatus import user_facing_status


class TestLogsInit(Init):

    description = "Initialize testlogs plugin settings"

    def initialize(self):
        help_msg = ("Status that will trigger the output of a test's logs "
                    "after the job ends. "
                    "Valid statuses: %s" % ", ".join(user_facing_status))
        settings.register_option(section='job.output.testlogs',
                                 key='statuses',
                                 key_type=list,
                                 default=[],
                                 help_msg=help_msg)


class TestLogs(JobPre, JobPost):

    description = "Shows content from tests' logs"

    def pre(self, job):
        pass

    def post(self, job):
        statuses = job.config.get('job.output.testlogs.statuses')
        if not statuses:
            return

        try:
            with open(os.path.join(job.logdir, 'results.json')) as json_file:
                results = json.load(json_file)
        except FileNotFoundError:
            return

        for test in results['tests']:
            if test['status'] not in statuses:
                continue
            LOG_UI.info('Log content for test "%s" (%s)', test['id'], test['status'])
            with open(test['logfile']) as log:
                LOG_UI.debug(log.read())
