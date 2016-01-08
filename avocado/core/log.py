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
# Copyright: Red Hat Inc. 2013-2014
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>


from StringIO import StringIO
import logging
import os
import sys

from . import output


__all__ = ["early_start", "enable_stderr", "reconfigure"]


if hasattr(logging, 'NullHandler'):
    NULL_HANDLER = logging.NullHandler
else:
    import logutils
    NULL_HANDLER = logutils.NullHandler


STDOUT = sys.stdout
STDERR = sys.stderr


def early_start():
    """
    Replace all outputs with in-memory handlers
    """
    if os.environ.get('DEBUG_AVOCADO'):
        output.add_log_handler("avocado.app.debug", None, STDERR,
                               logging.DEBUG)
    if os.environ.get('DEBUG_EARLY'):
        output.add_log_handler("", None, STDERR, logging.DEBUG)
        output.add_log_handler("avocado.test", None, STDERR, logging.DEBUG)
    else:
        sys.stdout = StringIO()
        sys.stderr = sys.stdout
        output.add_log_handler("", output.MemStreamHandler, None,
                               logging.DEBUG)
    logging.root.level = logging.DEBUG


def enable_stderr():
    """
    Enable direct stdout/stderr (useful for handling errors)
    """
    if hasattr(sys.stdout, 'getvalue'):
        STDERR.write(sys.stdout.getvalue())
    sys.stdout = STDOUT
    sys.stderr = STDERR


def reconfigure(args):
    """
    Adjust logging handlers accordingly to app args and re-log messages.
    """
    # Reconfigure stream loggers
    enabled = getattr(args, "log", ["app,early,debug"])
    if os.environ.get("DEBUG_EARLY") and "early" not in enabled:
        enabled.append("early")
    if os.environ.get("DEBUG_AVOCADO") and "debug" not in enabled:
        enabled.append("debug")
    if getattr(args, "show_job_log", False) and "test" not in enabled:
        enabled.append("test")
    if getattr(args, "silent", False):
        del enabled[:]
    if "app" in enabled:
        appl = logging.getLogger("avocado.app")
        apph = output.ProgressStreamHandler()
        apph.setFormatter(logging.Formatter("%(message)s"))
        apph.addFilter(output.FilterInfo())
        apph.stream = STDOUT
        appl.addHandler(apph)
        appl.propagate = False
        appl.level = logging.INFO
        appeh = output.logging.StreamHandler()
        appeh.setFormatter(logging.Formatter("%(message)s"))
        appeh.addFilter(output.FilterError())
        appeh.stream = STDERR
        appl.addHandler(appeh)
        appl.propagate = False
    else:
        output.disable_log_handler("avocado.app")
    if not os.environ.get("DEBUG_EARLY"):
        logging.getLogger("avocado.test.stdout").propagate = False
        logging.getLogger("avocado.test.stderr").propagate = False
        if "early" in enabled:
            enable_stderr()
            output.add_log_handler("", None, STDERR, logging.DEBUG)
            output.add_log_handler("avocado.test", None, STDERR,
                                   logging.DEBUG)
        else:
            # FIXME: When log and output are merged, to this in
            # start_job_logging
            # Don't relog old messages!
            sys.stdout = STDOUT
            sys.stderr = STDERR
            output.disable_log_handler("")
            output.disable_log_handler("avocado.test")
    if "remote" in enabled:
        output.add_log_handler("avocado.fabric", stream=STDERR)
        output.add_log_handler("paramiko", stream=STDERR)
    else:
        output.disable_log_handler("avocado.fabric")
        output.disable_log_handler("paramiko")
    if not os.environ.get('DEBUG_AVOCADO'):     # Not already enabled by env
        if "debug" in enabled:
            output.add_log_handler("avocado.app.debug", stream=STDERR)
        else:
            output.disable_log_handler("avocado.app.debug")

    # Remove the in-memory handlers
    for handler in logging.root.handlers:
        if isinstance(handler, output.MemStreamHandler):
            logging.root.handlers.remove(handler)

    # Log early_messages
    for record in output.MemStreamHandler.log:
        logging.getLogger(record.name).handle(record)
