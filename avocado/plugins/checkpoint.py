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
# Copyright: Red Hat Inc. 2014, 2017
# Author: Cleber Rosa <cleber@redhat.com>
# Author: Benjamin Berg <bberg@redhat.com>

"""Checkpoint Plugin"""

import os
import sqlite3
import datetime
import logging

from avocado.core.plugin_interfaces import ResultEvents
from avocado.core.dispatcher import ResultDispatcher

class Checkpoint(ResultEvents):

    """
    Checkpoint Results class.

    This class writes out the results at the start of a/each test to ensure
    that the result set is in a sane state in case avocado or even the whole
    system crashes.
    """

    name = 'checkpoint'
    description = "Checkpoint results before running each test"

    def __init__(self, args):
        """
        Creates an instance of CheckpointJournal.

        :param job: an instance of :class:`avocado.core.job.Job`.
        """
        self.log = logging.getLogger("avocado.app")
        self._result_dispatcher = ResultDispatcher()

    def pre_tests(self, job):
        self._job = job
        pass

    def start_test(self, result, state):
        # NOTE: During local execution this function is called from inside
        #       a forked subprocess.

        # Copy the state, put it into an INTERRUPTED state and append it
        incomplete_state = dict(state)
        incomplete_state['status'] = 'INTERRUPTED'
        result.tests.append(incomplete_state)

        if self._result_dispatcher:
            self._result_dispatcher.map_method('render',
                                               self._job.result,
                                               self._job)

        del result.tests[-1]

        # Try to sync everything to disk
        try:
            fd, fd_dir = -1, -1
            fd = os.open(os.path.join(self._job.logdir, 'results.json'), os.O_RDONLY)
            fd_dir = os.open(self._job.logdir, os.O_RDONLY)
        except Exception, e:
            self.log.error("Could not sync (json) output for checkpointing, recovery might not work! %s" % str(e))
        finally:
            if fd >= 0:
                os.close(fd)
            if fd_dir >= 0:
                os.close(fd_dir)


    def test_progress(self, progress=False):
        pass

    def end_test(self, result, state):
        pass

    def post_tests(self, job):
        pass

