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
# Copyright: Red Hat Inc. 2014-2015
# Author: Ruda Moura <rmoura@redhat.com>

"""Remote test class."""


class RemoteTest(object):

    """
    Mimics :class:`avocado.core.test.Test` for remote tests.
    """

    def __init__(self, name, status, time, start, end, fail_reason, logdir,
                 logfile):
        note = "Not supported yet"
        self.name = name
        self.status = status
        self.time_elapsed = time
        self.time_start = start
        self.time_end = end
        self.fail_class = note
        self.traceback = note
        self.text_output = note
        self.fail_reason = fail_reason
        self.whiteboard = ''
        self.job_unique_id = ''
        self.logdir = logdir
        self.logfile = logfile

    def get_state(self):
        """
        Serialize selected attributes representing the test state

        :returns: a dictionary containing relevant test state data
        :rtype: dict
        """
        d = self.__dict__
        d['class_name'] = self.__class__.__name__
        return d
