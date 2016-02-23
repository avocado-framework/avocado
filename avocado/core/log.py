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
    if os.environ.get('AVOCADO_LOG_DEBUG'):
        output.add_log_handler("avocado.app.debug", logging.StreamHandler,
                               STDERR, logging.DEBUG)
    if os.environ.get('AVOCADO_LOG_EARLY'):
        output.add_log_handler("", logging.StreamHandler, STDERR,
                               logging.DEBUG)
        output.add_log_handler("avocado.test", logging.StreamHandler, STDERR,
                               logging.DEBUG)
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
    enabled = getattr(args, "log", ["app", "early", "debug"])
    if os.environ.get("AVOCADO_LOG_EARLY") and "early" not in enabled:
        args.log.append("early")
        enabled.append("early")
    if os.environ.get("AVOCADO_LOG_DEBUG") and "debug" not in enabled:
        args.log.append("debug")
        enabled.append("debug")
    if getattr(args, "show_job_log", False):
        args.log = ["test"]
        enabled = ["test"]
    if getattr(args, "silent", False):
        del args.log[:]
        del enabled[:]
    if "app" in enabled:
        app_logger = logging.getLogger("avocado.app")
        app_handler = output.ProgressStreamHandler()
        app_handler.setFormatter(logging.Formatter("%(message)s"))
        app_handler.addFilter(output.FilterInfo())
        app_handler.stream = STDOUT
        app_logger.addHandler(app_handler)
        app_logger.propagate = False
        app_logger.level = logging.INFO
        app_err_handler = output.logging.StreamHandler()
        app_err_handler.setFormatter(logging.Formatter("%(message)s"))
        app_err_handler.addFilter(output.FilterError())
        app_err_handler.stream = STDERR
        app_logger.addHandler(app_err_handler)
        app_logger.propagate = False
    else:
        output.disable_log_handler("avocado.app")
    if not os.environ.get("AVOCADO_LOG_EARLY"):
        logging.getLogger("avocado.test.stdout").propagate = False
        logging.getLogger("avocado.test.stderr").propagate = False
        if "early" in enabled:
            enable_stderr()
            output.add_log_handler("", logging.StreamHandler, STDERR,
                                   logging.DEBUG)
            output.add_log_handler("avocado.test", logging.StreamHandler,
                                   STDERR, logging.DEBUG)
        else:
            # TODO: When stdout/stderr is not used by avocado we should move
            # this to output.start_job_logging
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
    if not os.environ.get('AVOCADO_LOG_DEBUG'):     # Not already enabled by env
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
