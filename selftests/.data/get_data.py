from avocado import Test


class GetData(Test):

    """
    Example for get_data() API usage
    """

    def test_a(self):
        """
        This large (on purpose) test, tests get_data() with "file",
        "test" and "variant" sources.

        Then, it adds other checks that include all sources.
        """
        # File-level checks
        file_data = self.get_data('file_data')
        self.assertIsNotNone(file_data)
        self.assertEqual(file_data,
                         self.get_data('file_data', source='file'))
        self.assertEqual(file_data,
                         self.get_data('file_data', source='file',
                                       must_exist=False))
        self.assertEqual(open(file_data, encoding='utf-8').read(), 'get_data.py')

        # Test-level checks
        test_data = self.get_data('test_data')
        self.assertIsNotNone(test_data)
        self.assertEqual(test_data,
                         self.get_data('test_data', source='test'))
        self.assertEqual(test_data,
                         self.get_data('test_data', source='test',
                                       must_exist=False))
        self.assertEqual(open(test_data, encoding='utf-8').read(), 'a')

        # Variant-level checks
        in_variant = self.params.get('in_variant', default=False)
        if in_variant:
            variant_data = self.get_data('variant_data')
            self.assertIsNotNone(variant_data)
            self.assertEqual(variant_data,
                             self.get_data('variant_data', source='variant'))
            self.assertEqual(variant_data,
                             self.get_data('variant_data', source='variant',
                                           must_exist=False))

        # A variation of data files that do not exist
        self.assertIsNone(self.get_data('does_not_exist'))
        self.assertIsNone(self.get_data('file_data', source='test'))
        self.assertIsNone(self.get_data('test_data', source='file'))
        if in_variant:
            self.assertIsNone(self.get_data('variant_data', source='test'))

        # All `get_data()` called with `must_exist=False` should
        # return a valid location for a (to be created?) data file
        self.assertIsNotNone(self.get_data('does_not_exist', must_exist=False))
        self.assertIsNotNone(self.get_data('does_not_exist', source='file',
                                           must_exist=False))
        self.assertIsNotNone(self.get_data('does_not_exist', source='test',
                                           must_exist=False))
        if in_variant:
            self.assertIsNotNone(self.get_data('does_not_exist',
                                               source='variant',
                                               must_exist=False))

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
        self.assertEqual(open(file_data, encoding='utf-8').read(), 'get_data.py')

        test_data = self.get_data('test_data')
        self.assertIsNotNone(test_data)
        self.assertEqual(open(test_data, encoding='utf-8').read(), 'b')

        variant_data = self.get_data('variant_data')
        self.assertIsNone(variant_data)

        print("This is output from test_b")
