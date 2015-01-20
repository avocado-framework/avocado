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


class JobError(Exception):

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


class TestNotFoundError(TestBaseException):

    """
    Indicates that the test was not found.

    Causes: non existing path or could not resolve alias.
    """
    status = "NOT_FOUND"


class NotATestError(TestBaseException):

    """
    Indicates that the file is not a test.

    Causes: Non executable, non python file or python module without
    an avocado test class in it.
    """
    status = "NOT_A_TEST"


class TestTimeoutError(TestBaseException):

    """
    Indicates that the test did not finish before the timeout specified.
    """
    status = "ERROR"


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


class TestNAError(TestBaseException):

    """
    Indictates that the test is Not Applicable.

    Should be thrown when various conditions are such that the test is
    inappropriate. For example, inappropriate architecture, wrong OS version,
    program being tested does not have the expected capability (older version).
    """
    status = "TEST_NA"


class TestFail(TestBaseException):

    """
    Indicates that the test failed. The test job will continue, though.
    """
    status = "FAIL"


class TestWarn(TestBaseException):

    """
    Indicates that bad things (may) have happened, but not an explicit
    failure.
    """
    status = "WARN"


class CmdError(Exception):

    def __init__(self, command=None, result=None):
        self.command = command
        self.result = result

    def __str__(self):
        if self.result is not None:
            if self.result.interrupted:
                return "Command %s interrupted by user (Ctrl+C)" % self.command
            if self.result.exit_status is None:
                msg = "Command '%s' failed and is not responding to signals"
                msg %= self.command
            else:
                msg = "Command '%s' failed (rc=%d)"
                msg %= (self.command, self.result.exit_status)
            return msg
        else:
            return "CmdError"
