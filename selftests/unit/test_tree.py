import sys

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

from avocado.core import tree

if __name__ == "__main__":
    PATH_PREFIX = "../../../../"
else:
    PATH_PREFIX = ""


class TestPathParent(unittest.TestCase):

    def test_empty_string(self):
        self.assertEqual(tree.path_parent(''), '/')

    def test_on_root(self):
        self.assertEqual(tree.path_parent('/'), '/')

    def test_direct_parent(self):
        self.assertEqual(tree.path_parent('/os/linux'), '/os')

    def test_false_direct_parent(self):
        self.assertNotEqual(tree.path_parent('/os/linux'), '/')


if __name__ == '__main__':
    unittest.main()
