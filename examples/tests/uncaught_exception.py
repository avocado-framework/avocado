from avocado import Test


class ErrorTest(Test):

    """
    Example test that raises generic exception

    :avocado: tags=failure_expected
    """

    @staticmethod
    def test():
        """
        This should end with ERROR.
        """
        raise Exception("This is a generic exception")
