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
# Copyright: Red Hat Inc. 2014
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>
# Author: Lukas Doktor <ldoktor@redhat.com>
"""
This file contains tools for (not only) Avocado developers.
"""
import logging
import os
import time

# Use this for debug logging
LOGGER = logging.getLogger("avocado.app.debug")

# measure_duration global storage
__MEASURE_DURATION = {}


def measure_duration(func):
    """
    Use this as decorator to measure duration of the function execution.
    The output is "Function $name: ($current_duration, $accumulated_duration)"
    """
    def wrapper(*args, **kwargs):
        """ Wrapper function """
        start = time.time()
        try:
            return func(*args, **kwargs)
        finally:
            duration = time.time() - start
            __MEASURE_DURATION[func] = (__MEASURE_DURATION.get(func, 0) +
                                        duration)
            LOGGER.debug("PERF: %s: (%ss, %ss)", func, duration,
                         __MEASURE_DURATION[func])
    return wrapper


def log_calls_class(length=None):
    """
    Use this as decorator to log the function methods' calls.
    :param length: Max message length
    """
    def wrap(orig_cls):
        for key, attr in orig_cls.__dict__.items():
            if callable(attr):
                setattr(orig_cls, key,
                        _log_calls(attr, length, orig_cls.__name__))
        return orig_cls
    return wrap


def _log_calls(func, length=None, cls_name=None):
    """
    log_calls wrapper function
    """
    def wrapper(*args, **kwargs):
        """ Wrapper function """
        msg = ("CALL: %s:%s%s(%s, %s)"
               % (os.path.relpath(func.__code__.co_filename),
                  cls_name, func.__name__,
                  ", ".join([str(_) for _ in args]),
                  ", ".join(["%s=%s" % (key, value)
                             for key, value in kwargs.items()])))
        if length:
            msg = msg[:length]
        LOGGER.debug(msg)
        return func(*args, **kwargs)
    if cls_name:
        cls_name = cls_name + "."
    return wrapper


def log_calls(length=None, cls_name=None):
    """
    Use this as decorator to log the function call altogether with arguments.
    :param length: Max message length
    :param cls_name: Optional class name prefix
    """
    def wrap(func):
        return _log_calls(func, length, cls_name)
    return wrap
