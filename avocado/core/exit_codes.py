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

These codes are returned on the command line and may be used by applications
that interface (that is, run) the Avocado command line application.

Besides main status about the execution of the command line application, these
exit status may also give extra, although limited, information about test
statuses.
"""

#: Both job and tests PASSed
AVOCADO_ALL_OK = 0x0000

#: Job went fine, but some tests FAILed or ERRORed
AVOCADO_TESTS_FAIL = 0x0001

#: Something went wrong with an Avocado Job execution, usually by
#: an explicit :class:`avocado.core.exceptions.JobError` exception.
AVOCADO_JOB_FAIL = 0x0002

#: Something else went wrong and avocado failed (or crashed). Commonly
#: used on command line validation errors.
AVOCADO_FAIL = 0x0004

#: The job was explicitly interrupted. Usually this means that a user
#: hit CTRL+C while the job was still running.
AVOCADO_JOB_INTERRUPTED = 0x0008

#: Some internal avocado routine has not completed and probably it wasn't at
#: the JOB level. Usually this means that something it was skipped but it is
#: safe to ignore.
AVOCADO_WARNING = 0x0016

#: Avocado generic crash
AVOCADO_GENERIC_CRASH = -1
