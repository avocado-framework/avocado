import unittest

from avocado.utils import vmimage


class VMImage(unittest.TestCase):

    def test_list_providers(self):
        self.assertIsNotNone(vmimage.list_providers())


if __name__ == '__main__':
    unittest.main()
