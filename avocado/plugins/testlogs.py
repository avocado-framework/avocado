import json
import os

from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import Init, JobPost, JobPre
from avocado.core.settings import settings
from avocado.core.teststatus import STATUSES


class TestLogsInit(Init):

    description = "Initialize testlogs plugin settings"

    def initialize(self):
        help_msg = ("Status that will trigger the output of a test's logs "
                    "after the job ends. "
                    "Valid statuses: %s" % ", ".join(STATUSES))
        settings.register_option(section='job.output.testlogs',
                                 key='statuses',
                                 key_type=list,
                                 default=[],
                                 help_msg=help_msg)

        help_msg = ('The specific log files that will be shown for tests '
                    'whose exit status match the ones defined in the '
                    '"job.output.testlogs.statuses" configuration. ')
        settings.register_option(section='job.output.testlogs',
                                 key='logfiles',
                                 key_type=list,
                                 default=['debug.log'],
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

        logfiles = job.config.get('job.output.testlogs.logfiles')
        for test in results['tests']:
            if test['status'] not in statuses:
                continue
            for logfile in logfiles:
                path = os.path.join(test['logdir'], logfile)
                try:
                    with open(path) as log:
                        LOG_UI.info('Log file "%s" content for test "%s" (%s):',
                                    logfile, test['id'], test['status'])
                        LOG_UI.debug(log.read())
                except (FileNotFoundError, PermissionError) as error:
                    LOG_UI.error('Failure to access log file "%s": %s',
                                 path, error)
