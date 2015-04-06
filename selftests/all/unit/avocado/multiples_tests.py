#!/usr/bin/python

from avocado import test
from avocado import job


class MultiplesTests(test.Test):

    def setUp(self):
        self.hello = "Hi there!"

    def test_hello(self):
        self.assertEqual(self.hello, "Hi there!")

    def testIdentity(self):
        self.assertTrue(1, 1)

    def division_by_zero(self):
        return 1 / 0

    def action(self):
        pass


if __name__ == '__main__':
    job.main()
