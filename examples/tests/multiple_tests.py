from avocado import Test


class MultipleTests(Test):

    """
    Following the unittest module pattern, every test method starts
    with a literal 'test' prefix, so that 'test_foo' and 'testFoo' are
    test methods, but 'division_by_zero' and 'action' are not.
    """

    def setUp(self):
        self.hello = "Hi there!"

    def test_hello(self):
        self.assertEqual(self.hello, "Hi there!")

    def testIdentity(self):
        self.assertIs(1, 1)

    @staticmethod
    def division_by_zero():
        """
        This method should never execute
        """
        return 1 / 0

    @staticmethod
    def action():
        """
        This method should never execute
        """
        raise Exception('This action method should never be executed.')
