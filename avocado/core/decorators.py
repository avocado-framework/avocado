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
# Copyright: Red Hat Inc. 2017
# Author: Amador Pahim <apahim@redhat.com>

from functools import wraps

from . import exceptions


def skip(message=None):
    """
    Decorator to skip a test.
    """
    def decorator(function):
        if not isinstance(function, type):
            @wraps(function)
            def wrapper(*args, **kwargs):
                raise exceptions.TestSkip(message)
            function = wrapper
        return function
    return decorator


def skipIf(condition, message=None):
    """
    Decorator to skip a test if a condition is True.
    """
    if condition:
        return skip(message)
    return _itself


def skipUnless(condition, message=None):
    """
    Decorator to skip a test if a condition is False.
    """
    if not condition:
        return skip(message)
    return _itself


def _itself(obj):
    return obj
