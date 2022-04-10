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
# Copyright: Red Hat Inc. 2022
# Authors: Beraldo Leal <bleal@redhat.com>

import os

from avocado.core.plugin_interfaces import ResultEvents


class ByStatusLink(ResultEvents):
    description = "Creates symlinks on file system grouped by status"

    def __init__(self, config):
        pass

    def pre_tests(self, job):
        pass

    def post_tests(self, job):
        pass

    def start_test(self, result, state):
        pass

    def test_progress(self, progress=False):
        pass

    def end_test(self, result, state):
        link = state.get('logdir')
        where = os.path.join(os.path.dirname(link),
                             'by-status',
                             state.get('status'))
        os.makedirs(where, exist_ok=True)
        os.symlink(link, os.path.join(where, os.path.basename(link)))
