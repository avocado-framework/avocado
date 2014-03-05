"""
Internal global error types.
"""

class TestBaseException(Exception):

    """The parent of all test exceptions."""
    # Children are required to override this.  Never instantiate directly.
    exit_status = "NEVER_RAISE_THIS"


class TestError(TestBaseException):

    """Indicates that something went wrong with the test harness itself."""
    exit_status = "ERROR"


class TestNAError(TestBaseException):

    """Indictates that the test is Not Applicable.  Should be thrown
    when various conditions are such that the test is inappropriate."""
    exit_status = "TEST_NA"


class TestFail(TestBaseException):

    """Indicates that the test failed, but the job will not continue."""
    exit_status = "FAIL"


class TestWarn(TestBaseException):

    """Indicates that bad things (may) have happened, but not an explicit
    failure."""
    exit_status = "WARN"
