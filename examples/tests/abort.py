import os

from avocado import Test


class AbortTest(Test):

    """
    A test that just calls abort() (and abort).

    :avocado: tags=failure_expected
    """

    timeout = 2.0

    @staticmethod
    def test():
        os.abort()
