from avocado import Test, fail_on


class Pip(Test):
    """
    :avocado: dependency={"type": "pip", "name": "pip", "action": "install"}
    """

    @fail_on(ImportError)
    def test(self):
        import pip  # pylint: disable=W0611
