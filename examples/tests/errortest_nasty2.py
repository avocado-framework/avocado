from avocado import Test


class NastyException(Exception):

    """ Please never use something like this!!! """

    def __init__(self, msg):  # pylint: disable=W0231
        self.msg = msg

    def __str__(self):
        return self.msg

    def __unicode__(self):
        return self.msg


class FailTest(Test):

    """
    Very nasty exception test

    :avocado: tags=failure_expected
    """

    def test(self):
        """
        Avocado should report this as TestError.
        """
        raise NastyException(None)  # str(Exception) fails!
