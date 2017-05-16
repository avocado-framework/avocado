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

from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import ResultEvents
from avocado.core.plugin_interfaces import JobPre, JobPost
from avocado.core import output


class Human(ResultEvents):

    """
    Human result UI
    """

    name = 'human'
    description = "Human Interface UI"

    output_mapping = {'PASS': output.TERM_SUPPORT.PASS,
                      'ERROR': output.TERM_SUPPORT.ERROR,
                      'FAIL': output.TERM_SUPPORT.FAIL,
                      'SKIP': output.TERM_SUPPORT.SKIP,
                      'WARN': output.TERM_SUPPORT.WARN,
                      'INTERRUPTED': output.TERM_SUPPORT.INTERRUPT,
                      'CANCEL': output.TERM_SUPPORT.CANCEL}

    def __init__(self, args):
        self.__throbber = output.Throbber()
        stdout_claimed_by = getattr(args, 'stdout_claimed_by', None)
        self.owns_stdout = not stdout_claimed_by

    def pre_tests(self, job):
        if not self.owns_stdout:
            return
        LOG_UI.info("JOB ID     : %s", job.unique_id)
        replay_source_job = getattr(job.args, "replay_sourcejob", False)
        if replay_source_job:
            LOG_UI.info("SRC JOB ID : %s", replay_source_job)
        LOG_UI.info("JOB LOG    : %s", job.logfile)

    def start_test(self, result, state):
        if not self.owns_stdout:
            return
        if "name" in state:
            name = state["name"]
            uid = name.str_uid
            name = name.name + name.str_variant
        else:
            name = "<unknown>"
            uid = '?'
        LOG_UI.debug(' (%s/%s) %s:  ', uid, result.tests_total, name,
                     extra={"skip_newline": True})

    def test_progress(self, progress=False):
        if not self.owns_stdout:
            return
        if progress:
            color = output.TERM_SUPPORT.PASS
        else:
            color = output.TERM_SUPPORT.PARTIAL
        LOG_UI.debug(color + self.__throbber.render() +
                     output.TERM_SUPPORT.ENDC, extra={"skip_newline": True})

    def end_test(self, result, state):
        if not self.owns_stdout:
            return
        status = state.get("status", "ERROR")
        if status == "TEST_NA":
            status = "SKIP"
        duration = (" (%.2f s)" % state.get('time_elapsed', -1)
                    if status != "SKIP"
                    else "")
        LOG_UI.debug(output.TERM_SUPPORT.MOVE_BACK +
                     self.output_mapping[status] +
                     status + output.TERM_SUPPORT.ENDC +
                     duration)

    def post_tests(self, job):
        if not self.owns_stdout:
            return
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
            if not getattr(job.args, 'stdout_claimed_by', None):
                LOG_UI.info("JOB TIME   : %.2f s", job.time_elapsed)
