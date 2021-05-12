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
# Copyright: RedHat 2013-2014
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>


import os
import sys
import tempfile
import time
import traceback

try:
    from avocado.core import data_dir
except ImportError:
    sys.stderr.write("Unable to import Avocado libraries, please verify "
                     "your installation, and if necessary reinstall it.\n")
    # This exit code is replicated from avocado/core/exit_codes.py and not
    # imported because we are dealing with import failures
    sys.exit(-1)


def get_crash_dir():
    crash_dir_path = os.path.join(data_dir.get_data_dir(), "crashes")
    try:
        os.makedirs(crash_dir_path)
    except OSError:
        pass
    return crash_dir_path


def handle_exception(*exc_info):
    # Print traceback if AVOCADO_LOG_DEBUG environment variable is set
    msg = "Avocado crashed:\n" + "".join(traceback.format_exception(*exc_info))
    msg += "\n"
    if os.environ.get("AVOCADO_LOG_DEBUG"):
        os.write(2, msg.encode('utf-8'))
    # Store traceback in data_dir or TMPDIR
    prefix = "avocado-traceback-"
    prefix += time.strftime("%F_%T") + "-"
    tmp, name = tempfile.mkstemp(".log", prefix, get_crash_dir())
    os.write(tmp, msg.encode('utf-8'))
    os.close(tmp)
    # Print friendly message in console-like output
    msg = ("Avocado crashed unexpectedly: %s\nYou can find details in %s\n"
           % (exc_info[1], name))
    os.write(2, msg.encode('utf-8'))
    # This exit code is replicated from avocado/core/exit_codes.py and not
    # imported because we are dealing with import failures
    sys.exit(-1)


def main():
    sys.excepthook = handle_exception
    from avocado.core.app import AvocadoApp  # pylint: disable=E0611

    # Override tmp in case it's not set in env
    for attr in ("TMP", "TEMP", "TMPDIR"):
        if attr in os.environ:
            break
    else:   # TMP not set by user, use /var/tmp if exists
        # TMP not set by user in environment. Try to use /var/tmp to avoid
        # possible problems with "/tmp" being mounted as TMPFS without the
        # support for O_DIRECT
        if os.path.exists("/var/tmp"):
            os.environ["TMP"] = "/var/tmp"
    app = AvocadoApp()
    return app.run()


if __name__ == '__main__':
    sys.exit(main())
