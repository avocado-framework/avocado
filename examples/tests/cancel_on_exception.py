import avocado


class CancelOnException(avocado.Test):

    """
    Test illustrating the usage of the cancel_on decorator.
    """

    @staticmethod
    def test():
        """
        This should end with CANCEL.

        Avocado tests should end with ERROR when a generic exception such as
        RuntimeError is raised. The avocado.cancel_on decorator allows you
        to override this behavior, and turn your generic exceptions into
        test CANCEL.
        """
        @avocado.cancel_on(RuntimeError)
        def foo():
            raise RuntimeError
        foo()
