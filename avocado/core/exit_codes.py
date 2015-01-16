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

"""
Avocado exit codes.

The current exit codes are:
    * AVOCADO_ALL_OK (0)
        Both job and tests PASSed
    * AVOCADO_TESTS_FAIL (1)
        Job went fine, but some tests FAILed or ERRORed
    * AVOCADO_JOB_FAIL (2)
        Something went wrong with the Job itself, by explicit
        :class:`avocado.core.exceptions.JobError` exception.
    * AVOCADO_FAIL (3)
        Something else went wrong and avocado failed (or crashed). Commonly
        used on command line validation errors.
    * AVOCADO_JOB_INTERRUPTED (4)
        The job was explicitly interrupted. Usually this means that a user
        hit CTRL+C while the job was still running.
"""

AVOCADO_ALL_OK = 0
AVOCADO_TESTS_FAIL = 1
AVOCADO_JOB_FAIL = 2
AVOCADO_FAIL = 3
AVOCADO_JOB_INTERRUPTED = 4
