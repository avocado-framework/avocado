from avocado import Test


class DoubleFail(Test):

    """
    Functional test for avocado. Straight up fail the test.

    :avocado: tags=failure_expected

    """

    def test(self):
        """
        Should fail.
        """
        raise self.fail('This test is supposed to fail')

    def tearDown(self):
        """
        Should also fail.
        """
        raise self.error('Failing during tearDown. Yay!')
