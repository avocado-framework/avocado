#!/usr/bin/env python
from avocado import Test
from avocado import main


class MultipleTests(Test):

    """
    Following the idea of unittest module,
    every test method starts with a 'test' prefix,
    so that 'test_foo' and 'testFoo' are test methods,
    but 'division_by_zero' and 'action' are not.
    """

    def setUp(self):
        self.hello = "Hi there!"

    def test_hello(self):
        self.assertEqual(self.hello, "Hi there!")

    def testIdentity(self):
        self.assertTrue(1, 1)

    def division_by_zero(self):
        """
        This method should never execute
        """
        return 1 / 0

    def action(self):
        """
        This method should never execute
        """
        raise Exception('This action method should never be executed.')


if __name__ == '__main__':
    main()
