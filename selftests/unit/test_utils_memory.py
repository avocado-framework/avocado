import unittest

try:
    from unittest import mock
except ImportError:
    import mock

from avocado.utils import memory


class UtilsMemoryTest(unittest.TestCase):

    def test_numa_nodes_with_memory(self):
        file_values = [u"0\n", u"1-3", u"0-1,12-14\n"]
        expected_values = [[0], [1, 2, 3], [0, 1, 12, 13, 14]]
        for value, exp in zip(file_values, expected_values):
            with mock.patch('os.path.exists', return_value=True):
                with mock.patch('avocado.utils.genio.read_file',
                                return_value=value):
                    self.assertEqual(memory.numa_nodes_with_memory(), exp)


if __name__ == '__main__':
    unittest.main()
