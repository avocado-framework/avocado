# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat, Inc. 2016
# Author: Cleber Rosa <crosa@redhat.com>
"""
Human result UI
"""

from avocado.core import output
from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import Init, JobPost, JobPre, ResultEvents
from avocado.core.settings import settings
from avocado.core.teststatus import STATUSES

#: STATUSES contains the finished status, but lacks the novel concept
#: of nrunner having tests STARTED (that is, in progress).  This contains
#: a more complete list of statuses that includes "STARTED"
COMPLETE_STATUSES = STATUSES + ['STARTED']


class HumanInit(Init):

    description = "Initialize human ui plugin settings"

    def initialize(self):
        help_msg = (f"Status that will be omitted from the Human UI. "
                    f"Valid statuses: {', '.join(COMPLETE_STATUSES)}")
        settings.register_option(section='human_ui.omit',
                                 key='statuses',
                                 key_type=list,
                                 default=[],
                                 help_msg=help_msg)


class Human(ResultEvents):

    """
    Human result UI
    """

    name = 'human'
    description = "Human Interface UI"

    def __init__(self, config):
        stdout_claimed_by = config.get('stdout_claimed_by', None)
        self.owns_stdout = not stdout_claimed_by
        self.omit_statuses = config.get('human_ui.omit.statuses')

    def pre_tests(self, job):
        if not self.owns_stdout:
            return
        LOG_UI.info("JOB ID     : %s", job.unique_id)
        # TODO: this is part of the legacy implementation of the
        # replay plugin and should be removed soon.
        replay_enabled = replay_source_job = job.config.get("replay_sourcejob", False)
        # The "avocado replay" plugin sets a different namespace
        if not replay_source_job:
            replay_enabled = job.config.get("job.replay.enabled")
            replay_source_job = job.config.get("job.replay.source_job_id")
        if replay_enabled and replay_source_job:
            LOG_UI.info("SRC JOB ID : %s", replay_source_job)
        LOG_UI.info("JOB LOG    : %s", job.logfile)

    def start_test(self, result, state):
        if not self.owns_stdout:
            return
        if "STARTED" in self.omit_statuses:
            return

        if "name" in state:
            name = state["name"]
            uid = name.str_uid
            name = name.name + name.str_variant
        else:
            name = "<unknown>"
            uid = '?'
        LOG_UI.debug(' (%s/%s) %s: STARTED', uid, result.tests_total, name)

    def test_progress(self, progress=False):
        pass

    @staticmethod
    def get_colored_status(status, extra=None):
        out = (output.TERM_SUPPORT.MOVE_BACK + output.TEST_STATUS_MAPPING[status] +
               status)
        if extra:
            if len(extra) > 255:
                extra = extra[:255] + '...'
            extra = extra.replace('\n', '\\n')
            out += ": " + extra
        out += output.TERM_SUPPORT.ENDC
        return out

    def end_test(self, result, state):
        if not self.owns_stdout:
            return
        status = state.get("status", "ERROR")
        if status in self.omit_statuses:
            return

        if status == "TEST_NA":
            status = "SKIP"
        duration = (f" ({state.get('time_elapsed', -1):.2f} s)"
                    if status != "SKIP"
                    else "")
        if "name" in state:
            name = state["name"]
            uid = name.str_uid
            name = name.name + name.str_variant
        else:
            name = "<unknown>"
            uid = '?'

        msg = self.get_colored_status(status, state.get("fail_reason", None))
        LOG_UI.debug(' (%s/%s) %s:  ', uid, result.tests_total, name,
                     extra={"skip_newline": True})
        LOG_UI.debug(msg + duration)

    def post_tests(self, job):
        if not self.owns_stdout:
            return

        if job.interrupted_reason is not None:
            LOG_UI.info(job.interrupted_reason)

        if job.status == 'PASS':
            LOG_UI.info("RESULTS    : PASS %d | ERROR %d | FAIL %d | SKIP %d | "
                        "WARN %d | INTERRUPT %s | CANCEL %s", job.result.passed,
                        job.result.errors, job.result.failed, job.result.skipped,
                        job.result.warned, job.result.interrupted,
                        job.result.cancelled)


class HumanJob(JobPre, JobPost):

    """
    Human result UI
    """

    name = 'human'
    description = "Human Interface UI"

    def pre(self, job):
        pass

    def post(self, job):
        if job.status == 'PASS':
            if not job.config.get('stdout_claimed_by', None):
                LOG_UI.info("JOB TIME   : %.2f s", job.time_elapsed)
