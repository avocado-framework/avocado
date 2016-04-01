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

"""
Exception classes, useful for tests, and other parts of the framework code.
"""
from functools import wraps
import types


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
            except TestBaseException:
                raise
            except exceptions as details:
                raise TestFail(str(details))
        return wrap
    if func:
        return decorate(func)
    return decorate


class JobBaseException(Exception):

    """
    The parent of all job exceptions.

    You should be never raising this, but just in case, we'll set its
    status' as FAIL.
    """
    status = "FAIL"


class JobError(JobBaseException):

    """
    A generic error happened during a job execution.
    """
    status = "ERROR"


class OptionValidationError(Exception):

    """
    An invalid option was passed to the test runner
    """
    status = "ERROR"


class TestBaseException(Exception):

    """
    The parent of all test exceptions.

    You should be never raising this, but just in case, we'll set its
    status' as FAIL.
    """
    status = "FAIL"


class TestSetupFail(TestBaseException):

    """
    Indicates an error during a setup or cleanup procedure.
    """
    status = "ERROR"


class TestError(TestBaseException):

    """
    Indicates that the test was not fully executed and an error happened.

    This is the sort of exception you raise if the test was partially
    executed and could not complete due to a setup, configuration,
    or another fatal condition.
    """
    status = "ERROR"


class NotATestError(TestBaseException):

    """
    Indicates that the file is not a test.

    Causes: Non executable, non python file or python module without
    an avocado test class in it.
    """
    status = "NOT_A_TEST"


class TestNotFoundError(TestBaseException):

    """
    Indicates that the test was not found in the test directory.
    """
    status = "ERROR"


class TestTimeoutInterrupted(TestBaseException):

    """
    Indicates that the test did not finish before the timeout specified.
    """
    status = "INTERRUPTED"


class TestTimeoutSkip(TestBaseException):

    """
    Indicates that the test is skipped due to a job timeout.
    """
    status = "SKIP"


class TestInterruptedError(TestBaseException):

    """
    Indicates that the test was interrupted by the user (Ctrl+C)
    """
    status = "INTERRUPTED"


class TestAbortError(TestBaseException):

    """
    Indicates that the test was prematurely aborted.
    """
    status = "ERROR"


class TestSkipError(TestBaseException):

    """
    Indictates that the test is skipped.

    Should be thrown when various conditions are such that the test is
    inappropriate. For example, inappropriate architecture, wrong OS version,
    program being tested does not have the expected capability (older version).
    """
    status = "SKIP"


class TestFail(TestBaseException, AssertionError):

    """
    Indicates that the test failed.

    TestFail inherits from AssertionError in order to keep compatibility
    with vanilla python unittests (they only consider failures the ones
    deriving from AssertionError).
    """
    status = "FAIL"


class TestWarn(TestBaseException):

    """
    Indicates that bad things (may) have happened, but not an explicit
    failure.
    """
    status = "WARN"
