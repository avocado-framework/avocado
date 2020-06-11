from avocado import Test


class ErrorTest(Test):

    """
    Example test that ends with ERROR.

    :avocado: tags=failure_expected
    """

    def test(self):
        """
        This should end with ERROR.
        """
        self.error('This should end with ERROR.')
