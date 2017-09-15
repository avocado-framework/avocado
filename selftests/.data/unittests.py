#!/usr/bin/env python
import unittest


class First(unittest.TestCase):
    def test_pass(self):
        pass


class Second(unittest.TestCase):
    def test_fail(self):
        self.fail("this is suppose to fail")

    def test_error(self):
        raise RuntimeError("This is suppose to error")

    @unittest.skip("This is suppose to be skipped")
    def test_skip(self):
        pass


if __name__ == "__main__":
    unittest.main()
