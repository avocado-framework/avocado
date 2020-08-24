from avocado import Test


class PassTest(Test):

    """
    Example test that passes.

    :avocado: requirement={"core": "avocado"}
    """

    def test(self):
        """
        A test simply doesn't have to fail in order to pass
        """
