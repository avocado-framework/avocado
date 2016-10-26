#!/usr/bin/env python

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; specifically version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat Inc. 2016
# Author: Amador Pahim <apahim@redhat.com>

#
# Simple script that, given the Job (partial) ID, returns the job
# results directory.
#
# $ python avocado-get-job-results-dir.py <job_id>
#

import sys

from avocado.core import jobdata
from avocado.core.settings import settings

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Please inform the Job ID.")
        sys.exit(-1)

    logdir = settings.get_value(section='datadir.paths',
                                key='logs_dir', key_type='path',
                                default=None)

    if logdir is None:
        print("Log directory is not configured in Avocado settings.")
        sys.exit(-1)

    try:
        resultsdir = jobdata.get_resultsdir(logdir, sys.argv[1])
    except ValueError as exception:
        print(exception.message)
        sys.exit(-1)
    else:
        if resultsdir is None:
            print("Can't find job results directory in '%s'" % logdir)
            sys.exit(-1)

        print(resultsdir)
