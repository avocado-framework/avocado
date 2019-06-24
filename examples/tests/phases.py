#!/usr/bin/env python

from avocado import main
from avocado import Test


class Phases(Test):

    """
    Example test for checking the reported test phases
    """

    def setUp(self):
        self.assertEqual(self.phase, 'SETUP')

    def test(self):
        self.assertEqual(self.phase, 'TEST')

    def tearDown(self):
        self.assertEqual(self.phase, 'TEARDOWN')


if __name__ == "__main__":
    main()
