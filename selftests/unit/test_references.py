import unittest.mock

from avocado.core import references


class References(unittest.TestCase):

    def test_split_file_does_not_exist(self):
        not_a_file = '/should/be/safe/to/assume/it/is/not/a/file:foo'
        path, additional_info = references.reference_split(not_a_file)
        self.assertEqual(path, '/should/be/safe/to/assume/it/is/not/a/file')
        self.assertEqual(additional_info, 'foo')

    def test_split_file_exists(self):
        file_name = 'file_contains_a_colon_:_indeed'
        with unittest.mock.patch('avocado.core.references.os.path.exists',
                                 return_value=True):
            path, additional_info = references.reference_split(file_name)
        self.assertEqual(path, file_name)
        self.assertEqual(additional_info, None)


if __name__ == '__main__':
    unittest.main()
