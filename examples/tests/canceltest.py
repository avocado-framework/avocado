from avocado import Test


class CancelTest(Test):

    """
    Example test that cancels the current test from inside the test.
    """

    def test(self):
        self.cancel("This should end with CANCEL.")
