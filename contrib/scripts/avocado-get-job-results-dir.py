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

from avocado.core import data_dir

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.stderr.write("Please inform the Job ID.\n")
        sys.exit(-1)

    resultsdir = data_dir.get_job_results_dir(sys.argv[1])
    if resultsdir is None:
        sys.stderr.write("Can't find job results directory for '%s'\n" %
                         sys.argv[1])
        sys.exit(-1)

    sys.stdout.write('%s\n' % resultsdir)
