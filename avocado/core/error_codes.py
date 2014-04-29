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
Maps the different avocado failure statuses to unix return codes.

The current return codes are:
    * AVOCADO_ALL_OK
        Both job and tests PASSed
    * AVOCADO_TESTS_FAIL
        Job went fine, but some tests FAILed or ERRORed
    * AVOCADO_JOB_FAIL
        Something went wrong with the Job itself, by explicit
        :class:`avocado.core.exceptions.JobError` exception.
    * AVOCADO_CRASH
        Something else went wrong and avocado plain crashed.
"""

numeric_status = {"AVOCADO_ALL_OK": 0,
                  "AVOCADO_TESTS_FAIL": 1,
                  "AVOCADO_JOB_FAIL": 2,
                  "AVOCADO_CRASH": 3}
