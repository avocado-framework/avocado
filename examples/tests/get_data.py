from __future__ import print_function

from avocado import Test


class GetData(Test):

    """
    Example for get_data() API usage
    """

    def test_a(self):
        """
        Test contains data files under both test data directory, and
        also under variants directory.

        One of the variants directory is named after the full variant
        name (including the full hash) while others only omit the
        hash and only use the name.  Hash-less directories are useful
        because test variant data doesn't usually change at the same
        rate as the variants content.
        """
        file_data = self.get_data('file_data')
        self.assertIsNotNone(file_data)
        self.assertEqual(open(file_data).read(), 'get_data.py')

        test_data = self.get_data('test_data')
        self.assertIsNotNone(test_data)
        self.assertEqual(open(test_data).read(), 'a')

        in_variant = self.params.get('in_variant', default=False)
        if in_variant:
            variant_data = self.get_data('variant_data')
            self.assertIsNotNone(variant_data)

        self.assertIsNone(self.get_data('does_not_exist'))

        # Write to stdout with print() to test output check capabilities,
        # a feature that uses the data directories (get_data()) itself
        print("This is output from test_a")

    def test_b(self):
        """
        Test contains data files under the test data directory, but
        has no associated variants directories.
        """
        file_data = self.get_data('file_data')
        self.assertIsNotNone(file_data)
        self.assertEqual(open(file_data).read(), 'get_data.py')

        test_data = self.get_data('test_data')
        self.assertIsNotNone(test_data)
        self.assertEqual(open(test_data).read(), 'b')

        variant_data = self.get_data('variant_data')
        self.assertIsNone(variant_data)

        print("This is output from test_b")
