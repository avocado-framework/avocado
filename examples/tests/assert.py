from avocado import Test


class MyException(Exception):
    pass


def raises_exception():
    raise MyException


class Assert(Test):

    def test_assert_raises(self):
        with self.assertRaises(MyException):
            raises_exception()

    def test_fails_to_raise(self):
        with self.assertRaises(MyException):
            pass
