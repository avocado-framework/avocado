from avocado import Test


class NastyException:

    """ Please never use something like this!!! (old-style exception) """

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class FailTest(Test):

    """
    This test raises old-style-class exception

    :avocado: tags=failure_expected
    """

    @staticmethod
    def test():
        """
        Avocado should report this as TestError.
        """
        raise NastyException("Nasty-string-like-exception")   # pylint: disable=E0710
