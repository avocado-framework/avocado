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

import types
from functools import wraps

from . import exceptions as core_exceptions


def deco_factory(behavior, signal):
    """
    Decorator factory.

    Returns a decorator used to signal the test when specified exception is
    raised.
    :param behavior: expected test result behavior.
    :param signal: delegating exception.
    """
    def signal_on(exceptions=None):
        """
        {0} the test when decorated function produces exception of the
        specified type.

        :param exceptions: Tuple or single exception to be assumed as
                           test {1} [Exception].
        :note: self.error, self.cancel and self.fail remain intact.
        :note: to allow simple usage param 'exceptions' must not be callable.
        """
        func = False
        if exceptions is None:
            exceptions = Exception
        elif isinstance(exceptions, types.FunctionType):
            func = exceptions
            exceptions = Exception

        def decorate(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except core_exceptions.TestBaseException as exc:
                    raise exc
                except exceptions as details:
                    raise signal(repr(details)) from details
            return wrapper
        return decorate(func) if func else decorate

    name = "{behavior}_on".format(behavior=behavior)
    signal_on.__name__ = signal_on.__qualname__ = name
    signal_on.__doc__ = signal_on.__doc__.format(behavior.capitalize(),
                                                 behavior.upper())
    return signal_on


fail_on = deco_factory("fail", core_exceptions.TestFail)


cancel_on = deco_factory("cancel", core_exceptions.TestCancel)


def skip(message=None):
    """
    Decorator to skip a test.
    """
    def decorator(obj):
        def method_decorator(function):
            if not isinstance(function, type):
                @wraps(function)
                def wrapper(*args, **kwargs):  # pylint: disable=W0613
                    raise core_exceptions.TestSkipError(message)
                function = wrapper
            function.__skip_test_decorator__ = True
            return function

        def class_decorator(cls):
            for key in cls.__dict__:
                if callable(getattr(cls, key)):
                    wrapped = method_decorator(getattr(cls, key))
                    setattr(cls, key, wrapped)
            return cls

        if isinstance(obj, type):
            return class_decorator(obj)
        else:
            return method_decorator(obj)
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
