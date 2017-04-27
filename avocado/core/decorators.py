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
import types

from . import exceptions as core_exceptions


def fail_on(exceptions=None):
    """
    Fail the test when decorated function produces exception of the specified
    type.

    (For example, our method may raise IndexError on tested software failure.
    We can either try/catch it or use this decorator instead)

    :param exceptions: Tuple or single exception to be assumed as
                       test fail [Exception]
    :note: self.error and self.skip behavior remains intact
    :note: To allow simple usage param "exceptions" must not be callable
    """
    func = False
    if exceptions is None:
        exceptions = Exception
    elif isinstance(exceptions, types.FunctionType):     # @fail_on without ()
        func = exceptions
        exceptions = Exception

    def decorate(func):
        """ Decorator """
        @wraps(func)
        def wrap(*args, **kwargs):
            """ Function wrapper """
            try:
                return func(*args, **kwargs)
            except core_exceptions.TestBaseException:
                raise
            except exceptions as details:
                raise core_exceptions.TestFail(str(details))
        return wrap
    if func:
        return decorate(func)
    return decorate


def skip(message=None):
    """
    Decorator to skip a test.
    """
    def decorator(function):
        if not isinstance(function, type):
            @wraps(function)
            def wrapper(*args, **kwargs):
                raise core_exceptions.TestSkipError(message)
            function = wrapper
        function.__skip_test_decorator__ = True
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
