import unittest

from avocado_varianter_cit import Cit


class CitTest(unittest.TestCase):

    PARAMS = [('key1', ['x1', 'x2', 'x3']), ('key2', ['y1', 'y2', 'y3']),
              ('key3', ['z1', 'z2', 'z3']), ('key4', ['w1', 'w2', 'w3'])]

    def test_orders(self):
        for i in range(len(self.PARAMS)):
            cit = Cit(self.PARAMS, i+1)
            headers, _ = cit.combine()
            # headers should always be the same, no matter the order
            # of combinations
            self.assertEqual(headers, ['key1', 'key2', 'key3', 'key4'])

    def test_number_of_combinations(self):
        # the algorithm doesn't allow us to know beforehand, for a
        # reason, the precise number of combinations that will be
        # computed.  still, we can check for the minimum number of
        # combinations that should be produced
        cit = Cit(self.PARAMS, 1)
        self.assertEqual(len(cit.combine()[1]), 3)
        cit = Cit(self.PARAMS, 2)
        self.assertGreaterEqual(len(cit.combine()[1]), 9)
        cit = Cit(self.PARAMS, 3)
        self.assertGreaterEqual(len(cit.combine()[1]), 27)

    def test_max_order(self):
        # test that with a order equal or larger than the number of
        # keys, we have a predictable number of combinations
        cit = Cit(self.PARAMS, 4)
        self.assertEqual(len(cit.combine()[1]), 81)
        cit = Cit(self.PARAMS, 10)
        self.assertEqual(len(cit.combine()[1]), 81)


if __name__ == '__main__':
    unittest.main()
