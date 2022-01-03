import unittest.mock

from avocado.utils import memory


class Test(unittest.TestCase):

    def test_numa_nodes_with_memory(self):
        file_values = ["0\n", "1-3", "0-1,12-14\n"]
        expected_values = [[0], [1, 2, 3], [0, 1, 12, 13, 14]]
        for value, exp in zip(file_values, expected_values):
            with unittest.mock.patch('os.path.exists', return_value=True):
                with unittest.mock.patch('avocado.utils.genio.read_file',
                                         return_value=value):
                    self.assertEqual(memory.numa_nodes_with_memory(), exp)


BUDDY_INFO_RESPONSE = (
    """Node 0, zone      DMA      1      1      0      0      1      1
Node 0, zone    DMA32    987    679   1004   3068   2795   1432
Node 1, zone   Normal   5430   9759   9044   9751  16482   8924""")


@unittest.mock.patch('avocado.utils.memory._get_buddy_info_content',
                     return_value=BUDDY_INFO_RESPONSE)
class GetBuddyInfo(unittest.TestCase):

    def test_simple_chunk_size(self, buddy_mocked):
        chunk_size = '0'
        result = memory.get_buddy_info(chunk_size)
        self.assertEqual(result[chunk_size], 6418)
        self.assertTrue(buddy_mocked.called)

    def test_less_than_chunk_size(self, buddy_mocked):
        chunk_size = '<2'
        result = memory.get_buddy_info(chunk_size)
        self.assertEqual(result['0'], 6418)
        self.assertEqual(result['1'], 10439)
        self.assertTrue(buddy_mocked.called)

    def test_less_than_equal_chunk_size(self, buddy_mocked):
        chunk_size = '<=2'
        result = memory.get_buddy_info(chunk_size)
        self.assertEqual(result['0'], 6418)
        self.assertEqual(result['1'], 10439)
        self.assertEqual(result['2'], 10048)
        self.assertTrue(buddy_mocked.called)

    def test_greater_than_chunk_size(self, buddy_mocked):
        chunk_size = '>3'
        result = memory.get_buddy_info(chunk_size)
        self.assertEqual(result['4'], 19278)
        self.assertEqual(result['5'], 10357)
        self.assertTrue(buddy_mocked.called)

    def test_greater_than_equal_chunk_size(self, buddy_mocked):
        chunk_size = '>=3'
        result = memory.get_buddy_info(chunk_size)
        self.assertEqual(result['3'], 12819)
        self.assertEqual(result['4'], 19278)
        self.assertEqual(result['5'], 10357)
        self.assertTrue(buddy_mocked.called)

    def test_multiple_chunk_size(self, buddy_mocked):
        chunk_size = '2 4'
        result = memory.get_buddy_info(chunk_size)
        self.assertEqual(result['2'], 10048)
        self.assertEqual(result['4'], 19278)
        self.assertTrue(buddy_mocked.called)

    def test_multiple_chunk_size_filtering_simple(self, buddy_mocked):
        chunk_size = '>2 <4'
        result = memory.get_buddy_info(chunk_size)
        self.assertEqual(result['3'], 12819)
        self.assertTrue(buddy_mocked.called)

    def test_multiple_chunk_size_filtering(self, buddy_mocked):
        chunk_size = '>=2 <=4'
        result = memory.get_buddy_info(chunk_size)
        self.assertEqual(result['2'], 10048)
        self.assertEqual(result['3'], 12819)
        self.assertEqual(result['4'], 19278)
        self.assertTrue(buddy_mocked.called)

    def test_multiple_chunk_size_filtering_invalid(self, buddy_mocked):
        chunk_size = '>2 <2'
        result = memory.get_buddy_info(chunk_size)
        self.assertEqual(result, {})
        self.assertTrue(buddy_mocked.called)

    def test_filtering_node(self, buddy_mocked):
        chunk_size = '0'
        result = memory.get_buddy_info(chunk_size, nodes='1')
        self.assertEqual(result[chunk_size], 5430)
        self.assertTrue(buddy_mocked.called)

    def test_filtering_zone(self, buddy_mocked):
        chunk_size = '0'
        result = memory.get_buddy_info(chunk_size, zones='DMA32')
        self.assertEqual(result[chunk_size], 987)
        self.assertTrue(buddy_mocked.called)


if __name__ == '__main__':
    unittest.main()
