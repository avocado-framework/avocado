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


class JobTestSuiteError(JobBaseException):

    """
    Generic error happened during the creation of a job's test suite
    """
    status = "ERROR"


class JobTestSuiteEmptyError(JobTestSuiteError):

    """
    Error raised when the creation of a test suite results in an empty suite
    """
    status = "ERROR"


class JobTestSuiteReferenceResolutionError(JobTestSuiteError):

    """
    Test References did not produce a valid reference by any resolver
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
    Indicates that the test is skipped.

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


class TestCancel(TestBaseException):
    """
    Indicates that a test was canceled.

    Should be thrown when the cancel() test method is used.
    """
    status = "CANCEL"
