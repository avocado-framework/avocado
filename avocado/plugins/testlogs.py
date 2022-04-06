import json
import os

from avocado.core.output import LOG_JOB, LOG_UI
from avocado.core.plugin_interfaces import Init, JobPost, JobPre, ResultEvents
from avocado.core.settings import settings
from avocado.core.teststatus import STATUSES


class TestLogsUIInit(Init):

    description = "Initialize testlogs plugin settings"

    def initialize(self):
        help_msg = (f"Status that will trigger the output of a test's logs "
                    f"after the job ends. "
                    f"Valid statuses: {', '.join(STATUSES)}")
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

        help_msg = (f"Status that will trigger the output of a summary "
                    f"after the job ends. This is useful to list failed "
                    f"tests for instances at the end of a job run. "
                    f"Valid statuses: {', '.join(STATUSES)}")
        settings.register_option(section='job.output.testlogs',
                                 key='summary_statuses',
                                 key_type=list,
                                 default=['FAIL', 'ERROR'],
                                 help_msg=help_msg)


class TestLogsUI(JobPre, JobPost):

    description = "Shows content from tests' logs"

    def pre(self, job):
        pass

    def post(self, job):
        statuses = job.config.get('job.output.testlogs.statuses')
        summary = job.config.get('job.output.testlogs.summary_statuses')

        if job.config.get('stdout_claimed_by') is not None:
            return

        try:
            with open(os.path.join(job.logdir, 'results.json'),
                      encoding='utf-8') as json_file:
                results = json.load(json_file)
        except FileNotFoundError:
            return

        logfiles = job.config.get('job.output.testlogs.logfiles')
        summary_tests = []
        for test in results['tests']:
            if test['status'] in summary:
                line = f"{test['name']}: {test['status']}"
                summary_tests.append(line)
            if not statuses or test['status'] not in statuses:
                continue
            for logfile in logfiles:
                path = os.path.join(test['logdir'], logfile)
                try:
                    with open(path, encoding='utf-8') as log:
                        LOG_UI.info('Log file "%s" content for test "%s" (%s):',
                                    logfile, test['id'], test['status'])
                        LOG_UI.debug(log.read())
                except (FileNotFoundError, PermissionError) as error:
                    LOG_UI.error('Failure to access log file "%s": %s',
                                 path, error)

        if summary_tests:
            LOG_UI.info("")
            LOG_UI.info("Test summary:")
            for test in sorted(summary_tests):
                LOG_UI.error(test)


class TestLogging(ResultEvents):
    """
    TODO: The description should be changed when the legacy runner will be
          deprecated.
    """

    description = "Nrunner specific Test logs for Job"

    def __init__(self, config):
        self.runner = config.get('run.test_runner')

    @staticmethod
    def _get_name(state):
        name = state.get('name')
        if name is None:
            return "<unknown>"
        return name.name + name.str_variant

    def pre_tests(self, job):
        pass

    def post_tests(self, job):
        pass

    def start_test(self, result, state):
        LOG_JOB.info('%s: STARTED', self._get_name(state))

    def test_progress(self, progress=False):
        pass

    def end_test(self, result, state):
        LOG_JOB.info('%s: %s', self._get_name(state),
                     state.get("status", "ERROR"))
        LOG_JOB.info('More information in %s', state.get('task_path', ''))
