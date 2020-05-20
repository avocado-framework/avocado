from avocado import Test


class WarnTest(Test):

    """
    Functional test for avocado. Throw a TestWarn.
    """

    def test(self):
        """
        This should throw a TestWarn.
        """
        self.log.warn("This marks test as WARN")
