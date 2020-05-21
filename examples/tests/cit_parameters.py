from avocado import Test


class CitParameters(Test):

    """
    Example test that fetches the parameters set on examples/cit/params.ini

    :avocado: tags=fast
    """

    def test(self):
        self.params.get('color')
        self.params.get('shape')
        self.params.get('state')
        self.params.get('material')
        self.params.get('coating')
